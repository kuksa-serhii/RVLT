# rvlt_client.py
import asyncio
import sys
import numpy as np
import sounddevice as sd
import argparse  # Новий імпорт
from queue import Queue
from loguru import logger

from azure.cognitiveservices.speech import (
    SpeechConfig,
    AudioConfig,
    SpeechRecognitionEventArgs,
    TranslationRecognizer,
    TranslationSynthesisEventArgs,
    AudioStreamFormat,
    StreamContainerFormat,
    PullAudioInputStream,
    ResultReason,
    CancellationDetails,
    SpeechSynthesisOutputFormat  # Новий імпорт
)

from app.config import settings
from app.utils import find_device_index, play_audio_blocking

# --- Налаштування логування (без змін) ---
# ... (залишається як було) ...

# --- SoundDevice Stream Class (без змін) ---
class SoundDeviceStream(PullAudioInputStream):
    # ... (залишається як було) ...

# --- Main Logic ---

async def main():
    # --- 1. Парсинг аргументів ---
    parser = argparse.ArgumentParser(description="Real-time Voice Translator Client")
    parser.add_argument(
        "--profile", 
        type=str, 
        required=True, 
        choices=settings.profiles.keys(),
        help="Profile to run (e.g., 'understand' or 'answer')"
    )
    args = parser.parse_args()
    
    # Завантажуємо конфігурацію для обраного профілю
    try:
        profile = settings.profiles[args.profile]
        logger.info(f"Loading profile: [{args.profile.upper()}] - {profile['description']}")
    except KeyError:
        logger.error(f"Profile '{args.profile}' not found in config.py.")
        return

    # --- 2. Audio & Config Setup ---
    device_sr = settings.audio.get("sample_rate", 48000)
    in_name = profile["input_device"]
    output_device_name = profile["output_device"] # Потрібен для синтезу
    
    try:
        in_idx = find_device_index(
            in_name, 
            "input", 
            prefer_hostapi=settings.audio.get("prefer_hostapi")
        )
        # Перевіряємо вихідний пристрій одразу
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

    speech_config = SpeechConfig(subscription=speech_key, region=speech_region)
    
    # Налаштовуємо КОНКРЕТНИЙ переклад
    speech_config.add_target_language(profile["target_lang"]) 
    speech_config.set_property_by_name(f"SpeechSynthesisVoiceName.{profile['target_lang']}", profile["tts_voice"])
    speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)

    # --- 4. Audio Stream Setup (без змін) ---
    audio_format = AudioStreamFormat(
        samples_per_second=device_sr,
        bits_per_sample=16,
        channels=1,
        container_format=StreamContainerFormat.RAW_PCM
    )
    audio_stream_source = SoundDeviceStream(in_idx, device_sr, audio_format)
    audio_config = AudioConfig(stream=audio_stream_source)
    
    # --- 5. Обробники подій (визначені всередині main) ---
    
    def recognized(evt: SpeechRecognitionEventArgs):
        """ Обробник події, коли переклад завершено. """
        result = evt.result
        
        if result.reason == ResultReason.Translated:
            text_recognized = result.text
            text_translated = result.translation
            
            logger.info(f"==> [FROM {profile['source_lang'].upper()}] {text_recognized}")
            logger.success(f"==> [TO {profile['target_lang'].upper()}] {text_translated}")

        elif result.reason == ResultReason.RecognizedSpeech:
            logger.debug(f"[Recognizing] {result.text} (Intermediate)")
        elif result.reason == ResultReason.NoMatch:
            logger.debug("No speech could be recognized.")

    def synthesis_handler(evt: TranslationSynthesisEventArgs):
        """ Обробка події синтезу мови (коли приходить аудіо). """
        if evt.result.audio and evt.result.audio_length > 0:
            audio_data = evt.result.audio
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            tts_sample_rate = 24000 # Azure TTS Neural Voices
            
            # Відтворення аудіо на пристрій, вказаний у ПРОФІЛІ
            play_audio_blocking(
                audio_np, 
                sr=tts_sample_rate, 
                device_name=output_device_name # Використовуємо змінну з main()
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
    
    # Встановлюємо мову розпізнавання з профілю (надійніше, ніж auto-detect)
    recognizer.speech_recognition_language = profile["source_lang"]

    # Підписка на події
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
        pass # Захоплюємо Ctrl+C

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