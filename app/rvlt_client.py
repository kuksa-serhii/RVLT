import asyncio
import sys
import numpy as np
import sounddevice as sd
import argparse
from queue import Queue
from loguru import logger

# Corrected SDK imports
from azure.cognitiveservices.speech import (
    SpeechConfig,
    ResultReason,
    CancellationDetails,
    SpeechRecognitionEventArgs
)
from azure.cognitiveservices.speech.audio import (
    AudioConfig,
    PullAudioInputStream,
    AudioStreamFormat
)
from azure.cognitiveservices.speech.translation import (
    SpeechTranslationConfig,
    TranslationRecognizer,
    TranslationSynthesisEventArgs
)

from app.config import settings
from app.utils import find_device_index, play_audio_blocking

# --- Logging Setup ---
logger.add(
    "rvlt_run.log",
    rotation="10 MB",
    retention=5,
    level=settings.logging.get("level", "INFO"),
    enqueue=True
)

# --- SoundDevice Stream Class ---
class SoundDeviceStream(PullAudioInputStream):
    """
    Custom PullAudioInputStream implementation that feeds audio data
    from a sounddevice.InputStream into the Azure Speech SDK.
    """
    def __init__(self, device_idx: int, sr: int, format: AudioStreamFormat):
        # Спочатку ініціалізуйте всі атрибути 'self'
        self.device_idx = device_idx
        self.sr = sr
        self.queue = Queue()
        # Blocksize: number of samples per callback
        self.blocksize = int(sr * settings.audio.get("frame_ms", 20) / 1000)
        self.stream = None
        logger.debug(f"Stream initialized. SR={sr}Hz, Blocksize={self.blocksize} samples.")
        
        # Викличте super().__init__ в кінці, передавши йому необхідний callback
        super().__init__(pull_stream_callback=self.read)

    def read(self, size: int) -> bytes:
        """
        SDK calls this method to pull audio data.
        'size' is the max number of bytes to return.
        """
        try:
            # Get data from queue. Timeout ensures this call doesn't block forever.
            chunk = self.queue.get(timeout=0.05)
            return chunk if len(chunk) <= size else chunk[:size]
        except:
            # On timeout (queue empty), return silence to keep stream alive
            return b'\x00' * size

    def _callback(self, indata, frames, time, status):
        """
        Callback function for the sounddevice InputStream.
        Puts raw audio data (bytes) into the queue.
        """
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        # indata is PCM16, 1 channel. Convert to bytes and queue.
        self.queue.put(indata.tobytes())

    def start_stream(self):
        """Starts the sounddevice InputStream."""
        wa_in = sd.WasapiSettings(exclusive=False)
        self.stream = sd.InputStream(
            samplerate=self.sr,
            channels=1,
            device=self.device_idx,
            dtype='int16',
            blocksize=self.blocksize,
            callback=self._callback,
            extra_settings=wa_in
        )
        self.stream.start()
        logger.info(f"[Audio In] Started capture from index {self.device_idx} @ {self.sr} Hz (WASAPI shared)")

    def stop_stream(self):
        """Stops the sounddevice InputStream."""
        if self.stream and self.stream.active:
            self.stream.stop()
            self.stream.close()
        logger.info("[Audio In] Stopped capture stream.")


# --- Main Logic ---

async def main():
    # --- 1. Argument Parsing ---
    parser = argparse.ArgumentParser(description="Real-time Voice Translator Client")
    parser.add_argument(
        "--profile",
        type=str,
        required=True,
        choices=settings.profiles.keys(),
        help="Profile to run (e.g., 'understand' or 'answer')"
    )
    args = parser.parse_args()
    
    # Load configuration for the selected profile
    try:
        profile = settings.profiles[args.profile]
        logger.info(f"Loading profile: [{args.profile.upper()}] - {profile['description']}")
    except KeyError:
        logger.error(f"Profile '{args.profile}' not found in config.py.")
        return

    # --- 2. Audio & Config Setup ---
    # CRITICAL: Sample rate is now per-profile
    device_sr = profile["sample_rate"]
    in_name = profile["input_device"]
    output_device_name = profile["output_device"] # Needed for synthesis
    
    try:
        in_idx = find_device_index(
            in_name,
            "input",
            prefer_hostapi=settings.audio.get("prefer_hostapi")
        )
        # Check output device immediately to fail fast
        find_device_index(
            output_device_name,
            "output",
            prefer_hostapi=settings.audio.get("prefer_hostapi")
        )
        logger.success(f"Audio devices OK: Input '{in_name}' -> Output '{output_device_name}' @ {device_sr}Hz")
    except RuntimeError as e:
        logger.error(f"Device error: {e}. Check device names/SR in app/config.py.")
        return

    # --- 3. Azure SDK Setup ---
    speech_key = settings.azure["speech_key"]
    speech_region = settings.azure["speech_region"]

    if not speech_key or not speech_region:
         raise RuntimeError("Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION in .env")

    # Use SpeechTranslationConfig for translation
    speech_config = SpeechTranslationConfig(subscription=speech_key, region=speech_region)
    
    # Configure the specific translation
    speech_config.add_target_language(profile["target_lang"])
    speech_config.voice_name = profile["tts_voice"]

    # --- 4. Audio Stream Setup ---
    audio_format = AudioStreamFormat(
        samples_per_second=device_sr,
        bits_per_sample=16,
        channels=1
    )
    audio_stream_source = SoundDeviceStream(in_idx, device_sr, audio_format)
    audio_config = AudioConfig(stream=audio_stream_source)
    
    # --- 5. Event Handlers (defined inside main) ---
    
    def recognized(evt: SpeechRecognitionEventArgs):
        """Handler for 'recognized' event."""
        result = evt.result
        
        if result.reason == ResultReason.TranslatedSpeech:
            text_recognized = result.text
            # Access translation via dictionary
            text_translated = result.translations[profile["target_lang"]]
            
            logger.info(f"==> [FROM {result.language.upper()}] {text_recognized}")
            logger.success(f"==> [TO {profile['target_lang'].upper()}] {text_translated}")

        elif result.reason == ResultReason.RecognizedSpeech:
            logger.debug(f"[Recognizing] {result.text} (Intermediate)")
        elif result.reason == ResultReason.NoMatch:
            logger.debug(f"No speech could be recognized. Reason: {result.no_match_details}")

    def synthesis_handler(evt: TranslationSynthesisEventArgs):
        """Handler for 'synthesis' event (when audio arrives)."""
        if evt.result.audio and len(evt.result.audio) > 0:
            audio_data = evt.result.audio
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # Azure TTS Neural Voices typically output at 24000 Hz
            tts_sample_rate = 24000
            
            # Play audio to the device specified in the PROFILE
            play_audio_blocking(
                audio_np,
                sr=tts_sample_rate,
                device_name=output_device_name # Uses variable from main()
            )
            logger.debug(f"[TTS] Played {len(audio_data)} bytes of audio.")

    def canceled(evt: SpeechRecognitionEventArgs):
        logger.error(f"[CANCELED] Reason: {evt.result.cancellation_details.reason}")
        if evt.result.cancellation_details.reason == CancellationDetails.Reason.Error:
            logger.error(f"[CANCELED] Error Code: {evt.result.cancellation_details.error_details}")
        sys.exit(1)

    def session_started(evt):
        logger.info(f"[SESSION] Started: {evt.session_id}")
    
    # --- 6. Translation Recognizer ---
    recognizer = TranslationRecognizer(
        translation_config=speech_config,
        audio_config=audio_config
    )
    
    # Set the source language (more reliable than auto-detect)
    recognizer.source_language = profile["source_lang"]

    # Subscribe to events
    recognizer.recognized.connect(recognized)
    recognizer.session_started.connect(session_started)
    recognizer.canceled.connect(canceled)
    recognizer.synthesizing.connect(synthesis_handler) # Use 'synthesizing'
    
    # --- 7. Run Continuous Recognition ---
    logger.info(f"Starting continuous recognition for profile [{args.profile.upper()}]...")
    
    audio_stream_source.start_stream()
    recognizer.start_continuous_recognition_async()

    try:
        while True:
            await asyncio.sleep(0.5)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass # Handle Ctrl+C gracefully

    finally:
        logger.info(f"Stopping recognition for profile [{args.profile.upper()}]...")
        recognizer.stop_continuous_recognition_async().get()
        audio_stream_source.stop_stream()
        logger.info("Cleanup complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(e)
        sys.exit(1)