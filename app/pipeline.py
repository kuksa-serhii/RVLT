"""
Main pipeline for PTT translation.

Orchestrates audio capture, STT, translation, TTS, and playback.
"""

import logging
import threading
import queue
import time
from typing import Optional
import numpy as np

from .config import Config
from .audio_devices import AudioInputStream, AudioOutputStream, find_device_by_name
from .resample import downsample_48k_to_16k_int16
from .voicemeeter_ctrl import VoicemeeterController
from .ptt import PTTHandler
from .azure_speech import AzureSTT, AzureTTS
from .utils import Timer, TimingStats, dump_audio_wav

logger = logging.getLogger(__name__)


class PTTPipeline:
    """
    Main PTT translation pipeline: UA→EN speech translation.
    
    Flow:
    1. PTT pressed → Voicemeeter switches strips
    2. Capture mic @ 48 kHz → downsample to 16 kHz → push to STT
    3. STT recognizes UA → translates to EN
    4. TTS synthesizes EN → 48 kHz PCM
    5. Play PCM to Voicemeeter Virtual Input
    6. PTT released → revert strips, stop playback
    """
    
    def __init__(self, config: Config):
        """
        Initialize pipeline.
        
        Args:
            config: Configuration object
        """
        self.config = config
        
        # Components
        self.vm_ctrl = VoicemeeterController(kind="banana")
        self.ptt_handler = PTTHandler(
            ptt_key=config.ptt.ptt_key,
            debounce_ms=config.ptt.debounce_ms
        )
        
        self.stt: Optional[AzureSTT] = None
        self.tts: Optional[AzureTTS] = None
        
        self.input_stream: Optional[AudioInputStream] = None
        self.output_stream: Optional[AudioOutputStream] = None
        
        # Audio buffer for captured frames
        self.audio_buffer_48k: queue.Queue[np.ndarray] = queue.Queue(maxsize=100)
        
        # State
        self._ptt_active = False
        self._running = False
        self._processing_thread: Optional[threading.Thread] = None
        
        # Timing stats
        self.timing_capture_to_stt = TimingStats("Capture→STT")
        self.timing_stt_to_translation = TimingStats("STT→Translation")
        self.timing_translation_to_tts = TimingStats("Translation→TTS")
        self.timing_total = TimingStats("Total PTT→Audio")
        
        logger.info("PTTPipeline initialized")
    
    def setup(self) -> bool:
        """
        Set up all components.
        
        Returns:
            True if successful
        """
        # Connect to Voicemeeter
        if not self.vm_ctrl.connect():
            logger.error("Failed to connect to Voicemeeter")
            return False
        
        # Initialize Azure STT
        try:
            self.stt = AzureSTT(
                speech_key=self.config.speech.speech_key,
                speech_region=self.config.speech.speech_region,
                source_language=self.config.speech.stt_lang_ptt,
                target_language="en"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure STT: {e}")
            return False
        
        # Initialize Azure TTS
        try:
            self.tts = AzureTTS(
                speech_key=self.config.speech.speech_key,
                speech_region=self.config.speech.speech_region,
                voice_name=self.config.speech.tts_voice_en
            )
        except Exception as e:
            logger.error(f"Failed to initialize Azure TTS: {e}")
            return False
        
        # Find audio devices
        mic_device_idx = None
        tts_device_idx = None
        
        if self.config.audio.mic_device:
            mic_device_idx = find_device_by_name(self.config.audio.mic_device, input_device=True)
            if mic_device_idx is None:
                logger.warning(f"Mic device not found: {self.config.audio.mic_device}, using default")
        
        if self.config.audio.tts_device:
            tts_device_idx = find_device_by_name(self.config.audio.tts_device, input_device=False)
            if tts_device_idx is None:
                logger.warning(f"TTS device not found: {self.config.audio.tts_device}, using default")
        
        # Create audio streams (don't start yet)
        self.input_stream = AudioInputStream(
            device=mic_device_idx,
            samplerate=self.config.audio.device_sr_in,
            frame_ms=self.config.audio.frame_ms,
            channels=1,
            callback=self._on_audio_captured
        )
        
        self.output_stream = AudioOutputStream(
            device=tts_device_idx,
            samplerate=self.config.audio.tts_sr,
            channels=1
        )
        
        # Subscribe to PTT events
        self.ptt_handler.subscribe(
            on_pressed=self._on_ptt_pressed,
            on_released=self._on_ptt_released
        )
        
        logger.info("Pipeline setup complete")
        return True
    
    def start(self):
        """Start the pipeline."""
        if self._running:
            logger.warning("Pipeline already running")
            return
        
        self._running = True
        
        # Start processing thread
        self._processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self._processing_thread.start()
        
        # Start PTT handler
        self.ptt_handler.start()
        
        logger.info("Pipeline started - waiting for PTT")
    
    def stop(self):
        """Stop the pipeline."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop PTT
        self.ptt_handler.stop()
        
        # Stop streams
        if self.input_stream:
            self.input_stream.stop()
        if self.output_stream:
            self.output_stream.stop()
        
        # Stop STT
        if self.stt:
            self.stt.stop()
        
        # Disconnect Voicemeeter
        self.vm_ctrl.disconnect()
        
        # Log final stats
        self.timing_capture_to_stt.log_stats()
        self.timing_stt_to_translation.log_stats()
        self.timing_translation_to_tts.log_stats()
        self.timing_total.log_stats()
        
        logger.info("Pipeline stopped")
    
    def _on_ptt_pressed(self):
        """Handle PTT press event."""
        logger.info("=== PTT PRESSED ===")
        
        self._ptt_active = True
        
        # Switch Voicemeeter strips
        self.vm_ctrl.set_ptt_mode(
            pressed=True,
            strip_mic=self.config.voicemeeter.strip_mic,
            strip_tts=self.config.voicemeeter.strip_tts
        )
        
        # Clear audio buffer
        while not self.audio_buffer_48k.empty():
            try:
                self.audio_buffer_48k.get_nowait()
            except queue.Empty:
                break
        
        # Start capture
        self.input_stream.start()
        
        # Start STT
        self.stt.start()
        
        logger.info("Listening...")
    
    def _on_ptt_released(self):
        """Handle PTT release event."""
        logger.info("=== PTT RELEASED ===")
        
        self._ptt_active = False
        
        # Stop capture
        self.input_stream.stop()
        
        # Allow short tail for VAD, then stop STT
        time.sleep(0.3)
        self.stt.stop()
        
        logger.info("Processing...")
    
    def _on_audio_captured(self, audio_mono_int16: np.ndarray):
        """
        Callback for captured audio frames.
        
        Args:
            audio_mono_int16: Mono int16 audio at 48 kHz
        """
        if not self._ptt_active:
            return
        
        try:
            self.audio_buffer_48k.put_nowait(audio_mono_int16.copy())
        except queue.Full:
            logger.warning("Audio buffer full, dropping frame")
    
    def _processing_loop(self):
        """Background thread for processing audio and managing translation pipeline."""
        logger.info("Processing loop started")
        
        while self._running:
            try:
                # Process captured audio → STT
                if self._ptt_active:
                    self._process_captured_audio()
                
                # Check for translation results
                self._check_translation_results()
                
                time.sleep(0.01)  # 10 ms
            
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
        
        logger.info("Processing loop stopped")
    
    def _process_captured_audio(self):
        """Process captured audio frames and push to STT."""
        try:
            # Get frame from buffer (non-blocking)
            audio_48k = self.audio_buffer_48k.get(timeout=0.01)
            
            with Timer("Downsample", self.timing_capture_to_stt):
                # Downsample to 16 kHz
                audio_16k = downsample_48k_to_16k_int16(audio_48k)
                
                # Push to STT
                if self.stt:
                    self.stt.push_pcm16_16k(audio_16k.tobytes())
        
        except queue.Empty:
            pass
    
    def _check_translation_results(self):
        """Check for STT results and trigger TTS."""
        if not self.stt:
            return
        
        # Check for translation
        translation = self.stt.read_translation(timeout_ms=10)
        
        if translation:
            logger.info(f"Translation: {translation}")
            
            with Timer("TTS", self.timing_translation_to_tts):
                # Synthesize to 48 kHz PCM
                audio_pcm48 = self.tts.synthesize_to_pcm48(translation)
            
            if audio_pcm48:
                # Play audio
                self._play_audio(audio_pcm48)
    
    def _play_audio(self, audio_bytes: bytes):
        """
        Play synthesized audio to output device.
        
        Args:
            audio_bytes: Raw PCM48 bytes
        """
        try:
            # Convert bytes to int16 array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Dump for debugging if enabled
            if self.config.logging.dump_audio:
                timestamp = int(time.time() * 1000)
                dump_audio_wav(
                    audio_array,
                    48000,
                    f"{self.config.logging.dump_path}/tts_{timestamp}.wav",
                    "TTS output"
                )
            
            # Start output stream if not running
            if not self.output_stream.stream:
                self.output_stream.start()
            
            # Write to stream
            self.output_stream.write(audio_array)
            
            logger.info(f"Played {len(audio_array)} samples")
        
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        if not self.setup():
            raise RuntimeError("Pipeline setup failed")
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
