"""
Azure Speech SDK integration for STT, Translation, and TTS.

Handles speech recognition, translation, and synthesis with proper audio format configuration.
"""

import logging
import threading
from typing import Optional, Callable
from queue import Queue, Empty
import io

logger = logging.getLogger(__name__)

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    AZURE_SPEECH_AVAILABLE = False
    logger.warning("Azure Speech SDK not available")


class AzureSTT:
    """
    Azure Speech-to-Text with push audio stream at 16 kHz mono int16.
    
    Supports translation from Ukrainian to English.
    """
    
    def __init__(
        self,
        speech_key: str,
        speech_region: str,
        source_language: str = "uk-UA",
        target_language: str = "en"
    ):
        """
        Initialize Azure STT.
        
        Args:
            speech_key: Azure Speech API key
            speech_region: Azure region (e.g., 'westeurope')
            source_language: Source language code (e.g., 'uk-UA')
            target_language: Target language code for translation (e.g., 'en')
        """
        if not AZURE_SPEECH_AVAILABLE:
            raise RuntimeError("Azure Speech SDK not available")
        
        self.speech_key = speech_key
        self.speech_region = speech_region
        self.source_language = source_language
        self.target_language = target_language
        
        # Create speech config
        self.speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=speech_region
        )
        
        # Create push stream with 16 kHz mono int16 format
        self.stream_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=16000,
            bits_per_sample=16,
            channels=1
        )
        
        self.push_stream: Optional[speechsdk.audio.PushAudioInputStream] = None
        self.audio_config: Optional[speechsdk.audio.AudioConfig] = None
        self.recognizer: Optional[speechsdk.translation.TranslationRecognizer] = None
        
        self._transcript_queue: Queue[str] = Queue()
        self._translation_queue: Queue[str] = Queue()
        self._is_recognizing = False
        self._lock = threading.Lock()
        
        logger.info(f"AzureSTT initialized: {source_language} -> {target_language}")
    
    def start(self):
        """Start the speech recognizer."""
        with self._lock:
            if self._is_recognizing:
                logger.warning("STT already started")
                return
            
            # Create new push stream
            self.push_stream = speechsdk.audio.PushAudioInputStream(self.stream_format)
            self.audio_config = speechsdk.audio.AudioConfig(stream=self.push_stream)
            
            # Create translation config
            translation_config = speechsdk.translation.SpeechTranslationConfig(
                subscription=self.speech_key,
                region=self.speech_region
            )
            translation_config.speech_recognition_language = self.source_language
            translation_config.add_target_language(self.target_language)
            
            # Create recognizer
            self.recognizer = speechsdk.translation.TranslationRecognizer(
                translation_config=translation_config,
                audio_config=self.audio_config
            )
            
            # Setup event handlers
            self.recognizer.recognized.connect(self._on_recognized)
            self.recognizer.canceled.connect(self._on_canceled)
            
            # Start continuous recognition
            self.recognizer.start_continuous_recognition()
            self._is_recognizing = True
            
            logger.info("STT started")
    
    def stop(self):
        """Stop the speech recognizer."""
        with self._lock:
            if not self._is_recognizing:
                return
            
            if self.recognizer:
                self.recognizer.stop_continuous_recognition()
                self.recognizer = None
            
            if self.push_stream:
                self.push_stream.close()
                self.push_stream = None
            
            self._is_recognizing = False
            logger.info("STT stopped")
    
    def push_pcm16_16k(self, audio_bytes: bytes):
        """
        Push 16 kHz mono int16 PCM audio to the recognizer.
        
        Args:
            audio_bytes: Raw PCM16 audio data at 16 kHz
        """
        if not self._is_recognizing or not self.push_stream:
            logger.warning("Cannot push audio - STT not started")
            return
        
        try:
            self.push_stream.write(audio_bytes)
        except Exception as e:
            logger.error(f"Error pushing audio: {e}")
    
    def read_transcript(self, timeout_ms: int = 100) -> Optional[str]:
        """
        Read recognized transcript (non-blocking with timeout).
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Transcript text or None if timeout
        """
        try:
            return self._transcript_queue.get(timeout=timeout_ms / 1000.0)
        except Empty:
            return None
    
    def read_translation(self, timeout_ms: int = 100) -> Optional[str]:
        """
        Read translated text (non-blocking with timeout).
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Translated text or None if timeout
        """
        try:
            return self._translation_queue.get(timeout=timeout_ms / 1000.0)
        except Empty:
            return None
    
    def _on_recognized(self, evt):
        """Handler for recognized speech events."""
        if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
            transcript = evt.result.text
            translation = evt.result.translations.get(self.target_language, "")
            
            logger.info(f"Recognized: {transcript}")
            logger.info(f"Translated: {translation}")
            
            self._transcript_queue.put(transcript)
            if translation:
                self._translation_queue.put(translation)
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            logger.debug("No speech recognized")
    
    def _on_canceled(self, evt):
        """Handler for canceled events."""
        logger.warning(f"Recognition canceled: {evt}")


class AzureTTS:
    """
    Azure Text-to-Speech synthesizer outputting 48 kHz mono int16 PCM.
    """
    
    def __init__(
        self,
        speech_key: str,
        speech_region: str,
        voice_name: str = "en-GB-RyanNeural"
    ):
        """
        Initialize Azure TTS.
        
        Args:
            speech_key: Azure Speech API key
            speech_region: Azure region
            voice_name: Voice name (e.g., 'en-GB-RyanNeural')
        """
        if not AZURE_SPEECH_AVAILABLE:
            raise RuntimeError("Azure Speech SDK not available")
        
        self.speech_key = speech_key
        self.speech_region = speech_region
        self.voice_name = voice_name
        
        # Create speech config
        self.speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=speech_region
        )
        
        # Set output format to 48 kHz 16-bit mono PCM
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw48Khz16BitMonoPcm
        )
        
        self.speech_config.speech_synthesis_voice_name = voice_name
        
        logger.info(f"AzureTTS initialized: voice={voice_name}")
    
    def synthesize_to_pcm48(self, text: str) -> Optional[bytes]:
        """
        Synthesize text to 48 kHz mono int16 PCM (blocking).
        
        Args:
            text: Text to synthesize
            
        Returns:
            Raw PCM audio bytes or None if error
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return None
        
        try:
            # Create synthesizer with null output (we'll get raw audio)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None
            )
            
            # Synthesize
            result = synthesizer.speak_text(text)
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(f"TTS synthesized {len(result.audio_data)} bytes for: {text[:50]}...")
                return result.audio_data
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.error(f"TTS canceled: {cancellation.reason} - {cancellation.error_details}")
                return None
            else:
                logger.error(f"TTS failed with reason: {result.reason}")
                return None
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
    
    def synthesize_to_pcm48_async(
        self,
        text: str,
        callback: Callable[[Optional[bytes]], None]
    ):
        """
        Synthesize text asynchronously (TODO: implement streaming).
        
        Args:
            text: Text to synthesize
            callback: Called with audio bytes when complete
        """
        # TODO: Implement streaming TTS for lower latency
        def _thread_func():
            audio = self.synthesize_to_pcm48(text)
            callback(audio)
        
        thread = threading.Thread(target=_thread_func, daemon=True)
        thread.start()
