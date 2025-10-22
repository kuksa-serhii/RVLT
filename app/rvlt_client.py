import asyncio
import sys
import numpy as np
import sounddevice as sd
import argparse  # Added for profile loading
from queue import Queue
from loguru import logger

from azure.cognitiveservices.speech import (
    SpeechConfig,
    ResultReason,
    CancellationDetails,
    SpeechSynthesisOutputFormat,
    SpeechRecognitionEventArgs
)
# --- MODIFIED IMPORT (Audio) ---
# Import audio-specific classes from the .audio submodule
from azure.cognitiveservices.speech.audio import (
    AudioConfig,
    AudioStreamFormat,
    # StreamContainerFormat, # This class name changed or is no longer used here. Removing.
    PullAudioInputStream
)
# --- END MODIFICATION ---

# --- MODIFIED IMPORT (Translation) ---
# We now import translation-specific classes from the .translation submodule
from azure.cognitiveservices.speech.translation import (
    SpeechTranslationConfig,  # <-- IMPORT THE CORRECT CONFIG CLASS
    TranslationRecognizer,
    TranslationSynthesisEventArgs
)
# --- END MODIFICATION ---

from app.config import settings
from app.utils import find_device_index, play_audio_blocking

# --- Logger Setup ---
logger.add(
    "rvlt_run.log",
    rotation="10 MB",
    retention=5,
    level=settings.logging.get("level", "INFO"),
    enqueue=True
)

# --- SoundDevice Stream Class (Restored) ---
class SoundDeviceStream(PullAudioInputStream):
    """
    Implements PullAudioInputStream to feed audio data from sounddevice to the Azure SDK.
    This class was missing its body, causing the IndentationError.
    """
    def __init__(self, device_idx: int, sr: int, format: AudioStreamFormat):
        super().__init__(format)
        self.device_idx = device_idx
        self.sr = sr
        self.queue = Queue()
        # Block size read by sounddevice
        self.blocksize = int(sr * settings.audio.get("frame_ms", 20) / 1000)
        self.stream = None

    def read(self, size: int) -> bytes:
        """ SDK calls this method when it needs data. """
        try:
            # Wait for data. If queue is empty, return silence (b'').
            chunk = self.queue.get(timeout=0.01) 
            return chunk if len(chunk) <= size else chunk[:size]
        except:
            # On timeout, return silence of the requested size
            return b'\x00' * size

    def _callback(self, indata, frames, time, status):
        """ Callback for sounddevice InputStream. """
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        # PCM16, 1 channel. Send as bytes.
        self.queue.put(indata.tobytes())

    def start_stream(self):
        """ Start the sounddevice capture stream. """
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
        """ Stop the stream. """
        if self.stream and self.stream.active:
            self.stream.stop(); self.stream.close()
        logger.info("[Audio In] Stopped capture stream.")


# --- Main Logic (Profile-based) ---

async def main():
    # --- 1. Parse Arguments ---
    parser = argparse.ArgumentParser(description="Real-time Voice Translator Client")
    parser.add_argument(
        "--profile", 
        type=str, 
        required=True, 
        choices=settings.profiles.keys(),
        help="Profile to run (e.g., 'understand' or 'answer')"
    )
    args = parser.parse_args()
    
    # Load configuration for the chosen profile
    try:
        profile = settings.profiles[args.profile]
        logger.info(f"Loading profile: [{args.profile.upper()}] - {profile['description']}")
    except KeyError:
        logger.error(f"Profile '{args.profile}' not found in config.py.")
        return

    # --- 2. Audio & Config Setup ---
    device_sr = settings.audio.get("sample_rate", 48000)
    in_name = profile["input_device"]
    output_device_name = profile["output_device"] # Needed for synthesis
    
    try:
        in_idx = find_device_index(
            in_name, 
            "input", 
            prefer_hostapi=settings.audio.get("prefer_hostapi")
        )
        # Check output device availability immediately
        find_device_index(
            output_device_name, 
            "output", 
            prefer_hostapi=settings.audio.get("prefer_hostapi")
        )
        logger.success(f"Audio devices OK: Input '{in_name}' -> Output '{output_device_name}'")
    except RuntimeError as e:
        logger.error(f"Device error: {e}. Check device names in app/config.py.")
        return

    # --- 3. Azure SDK Setup ---
    speech_key = settings.azure["speech_key"]
    speech_region = settings.azure["speech_region"]

    if not speech_key or not speech_region:
         raise RuntimeError("Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION in .env")

    # --- MODIFICATION ---
    # Use SpeechTranslationConfig for translation, not base SpeechConfig
    speech_config = SpeechTranslationConfig(subscription=speech_key, region=speech_region)
    # --- END MODIFICATION ---
    
    # Configure the SPECIFIC translation
    # This line will now work correctly
    speech_config.add_target_language(profile["target_lang"]) 
    speech_config.set_property_by_name(f"SpeechSynthesisVoiceName.{profile['target_lang']}", profile["tts_voice"])
    speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)

    # --- 4. Audio Stream Setup ---
    audio_format = AudioStreamFormat(
        samples_per_second=device_sr,
        bits_per_sample=16,
        channels=1
        # We don't specify container_format for PullAudioInputStream
    )
    audio_stream_source = SoundDeviceStream(in_idx, device_sr, audio_format)
    audio_config = AudioConfig(stream=audio_stream_source)
    
    # --- 5. Event Handlers (defined inside main) ---
    
    def recognized(evt: SpeechRecognitionEventArgs):
        """ Handles the 'recognized' event. """
        result = evt.result
        
        if result.reason == ResultReason.Translated:
            text_recognized = result.text
            text_translated = result.translation
            
            logger.info(f"==> [FROM {profile['source_lang'].upper()}] {text_recognized}")
            logger.success(f"==> [TO {profile['target_lang'].upper()}] {text_translated}")

        elif result.reason == ResultReason.RecognizedSpeech:
            logger.debug(f"[Recognizing] {result.text} (Intermediate)")
        elif result.season == ResultReason.NoMatch:
            logger.debug("No speech could be recognized.")

    def synthesis_handler(evt: TranslationSynthesisEventArgs):
        """ Handles the 'synthesis' event (when audio arrives). """
        if evt.result.audio and evt.result.audio_length > 0:
            audio_data = evt.result.audio
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            tts_sample_rate = 24000 # Azure TTS Neural Voices
            
            # Play audio to the device specified in the PROFILE
            play_audio_blocking(
                audio_np, 
                sr=tts_sample_rate, 
                device_name=output_device_name # Use variable from main()
            )
            logger.debug(f"[TTS] Played {evt.result.audio_length} bytes of audio.")

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
    
    # Set recognition language from profile (more reliable than auto-detect)
    recognizer.speech_recognition_language = profile["source_lang"]

    # Subscribe to events
    recognizer.recognized.connect(recognized)
    recognizer.session_started.connect(session_started)
    recognizer.canceled.connect(canceled)
    recognizer.synthesis_event.connect(synthesis_handler)
    
    # --- 7. Run Continuous Recognition ---
    logger.info(f"Starting continuous recognition for profile [{args.profile.upper()}]...")
    
    audio_stream_source.start_stream()
    recognizer.start_continuous_recognition()

    try:
        while True:
            await asyncio.sleep(0.5)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass # Handle Ctrl+C gracefully

    finally:
        logger.info(f"Stopping recognition for profile [{args.profile.upper()}]...")
        recognizer.stop_continuous_recognition()
        audio_stream_source.stop_stream()
        logger.info("Cleanup complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(e)
        sys.exit(1)

