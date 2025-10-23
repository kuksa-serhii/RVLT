# app/rvlt_client.py
import asyncio
import sys
import numpy as np
import sounddevice as sd
import argparse
from queue import Queue
from loguru import logger

# Azure Speech SDK
from azure.cognitiveservices.speech import (
    SpeechConfig,
    ResultReason,
    CancellationReason,
)
from azure.cognitiveservices.speech.audio import (
    AudioConfig,
    PullAudioInputStream,
    PullAudioInputStreamCallback,
    AudioStreamFormat,
)
from azure.cognitiveservices.speech.translation import (
    SpeechTranslationConfig,
    TranslationRecognizer,
    TranslationSynthesisEventArgs,
)

from app.config import settings
from app.utils import find_device_index, play_audio_blocking


# --- Logging Setup ---
logger.add(
    "rvlt_run.log",
    rotation="10 MB",
    retention=5,
    level=settings.logging.get("level", "INFO"),
    enqueue=True,
)


class SoundDeviceCallback(PullAudioInputStreamCallback):
    """
    Callback для PullAudioInputStream: SDK викликає read(buffer) -> int,
    а ми підкладаємо туди байти з sounddevice.InputStream.
    """

    def __init__(self, device_idx: int, sr: int):
        self.device_idx = device_idx
        self.sr = sr
        self.queue: "Queue[bytes]" = Queue()
        self.blocksize = int(sr * settings.audio.get("frame_ms", 20) / 1000)
        self.stream: sd.InputStream | None = None

        logger.debug(f"Callback initialized. SR={sr}Hz, Blocksize={self.blocksize} samples.")

        wa_in = sd.WasapiSettings(exclusive=False)
        self.stream = sd.InputStream(
            samplerate=self.sr,
            channels=1,
            device=self.device_idx,
            dtype="int16",
            blocksize=self.blocksize,
            callback=self._on_audio,
            extra_settings=wa_in,
        )

    def _on_audio(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio stream status: {status}")
        # indata: int16 mono -> bytes
        self.queue.put(indata.tobytes())

    def start_stream(self):
        if self.stream and not self.stream.active:
            self.stream.start()
            logger.info(f"[Audio In] Started capture from index {self.device_idx} @ {self.sr} Hz (WASAPI shared)")

    def stop_stream(self):
        if self.stream and self.stream.active:
            self.stream.stop()
            self.stream.close()
            logger.info("[Audio In] Stopped capture stream.")

    # Обов’язковий метод для PullAudioInputStreamCallback
    def read(self, buffer: memoryview) -> int:
        """
        SDK надає буфер (memoryview). Потрібно записати туди байти і
        повернути КІЛЬКІСТЬ записаних байтів.
        """
        try:
            chunk = self.queue.get(timeout=0.05)  # bytes
        except Exception:
            # тиша як fallback
            chunk = b"\x00" * len(buffer)

        n = min(len(buffer), len(chunk))
        buffer[:n] = chunk[:n]
        if n < len(buffer):
            # доповнюємо тишею, щоб не рвати потік
            buffer[n:] = b"\x00" * (len(buffer) - n)
        return len(buffer)

    # Не обов’язково, але корисно для акуратного завершення
    def close(self):
        self.stop_stream()


async def main():
    # --- 1) CLI ---
    parser = argparse.ArgumentParser(description="Real-time Voice Translator Client")
    parser.add_argument(
        "--profile",
        type=str,
        required=True,
        choices=settings.profiles.keys(),
        help="Profile to run (e.g., 'understand' or 'answer')",
    )
    args = parser.parse_args()

    # --- 2) Load profile ---
    try:
        profile = settings.profiles[args.profile]
        logger.info(f"Loading profile: [{args.profile.upper()}] - {profile['description']}")
    except KeyError:
        logger.error(f"Profile '{args.profile}' not found in config.py.")
        return

    device_sr = int(profile["sample_rate"])
    in_name = profile["input_device"]
    out_name = profile["output_device"]

    try:
        in_idx = find_device_index(
            in_name, "input", prefer_hostapi=settings.audio.get("prefer_hostapi")
        )
        # fail-fast на вихідному пристрої
        find_device_index(
            out_name, "output", prefer_hostapi=settings.audio.get("prefer_hostapi")
        )
        logger.success(
            f"Audio devices OK: Input '{in_name}' -> Output '{out_name}' @ {device_sr}Hz"
        )
    except RuntimeError as e:
        logger.error(f"Device error: {e}. Check device names/SR in app/config.py.")
        return

    # --- 3) Azure Speech Config ---
    speech_key = settings.azure["speech_key"]
    speech_region = settings.azure["speech_region"]
    if not speech_key or not speech_region:
        raise RuntimeError("Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION in .env")

    speech_config = SpeechTranslationConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_recognition_language = profile["source_lang"] 
    speech_config.add_target_language(profile["target_lang"])
    speech_config.voice_name = profile["tts_voice"]

    # --- 4) Audio stream (PullAudioInputStream via callback) ---
    audio_format = AudioStreamFormat(
        samples_per_second=device_sr, bits_per_sample=16, channels=1
    )
    callback = SoundDeviceCallback(in_idx, device_sr)
    pull_stream = PullAudioInputStream(callback, audio_format)
    audio_config = AudioConfig(stream=pull_stream)

    # --- 5) Recognizer ---
    recognizer = TranslationRecognizer(
        translation_config=speech_config, audio_config=audio_config
    )


    # --- 6) Event handlers ---
    def recognized(evt):
        result = evt.result
        if result.reason == ResultReason.TranslatedSpeech:
            text_src = result.text
            text_dst = result.translations.get(profile["target_lang"], "")
            logger.info(f"==> [FROM {result.language.upper()}] {text_src}")
            logger.success(f"==> [TO {profile['target_lang'].upper()}] {text_dst}")
        elif result.reason == ResultReason.RecognizedSpeech:
            logger.debug(f"[Recognizing] {result.text}")
        elif result.reason == ResultReason.NoMatch:
            logger.debug("No speech could be recognized.")

    def synthesis_handler(evt: TranslationSynthesisEventArgs):
        # Відтворюємо озвучений переклад
        if evt.result.audio and len(evt.result.audio) > 0:
            audio_data = evt.result.audio
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            # Azure Neural TTS зазвичай 24000 Hz
            tts_sr = 24000
            play_audio_blocking(audio_np, sr=tts_sr, device_name=out_name)
            logger.debug(f"[TTS] Played {len(audio_data)} bytes.")

    def canceled(evt):
        # Якщо подія скасування
        details = evt.result.cancellation_details
        reason = details.reason if details else None
        if reason == CancellationReason.Error:
            err = details.error_details if details else "Unknown error"
            logger.error(f"[CANCELED] Reason=Error | Details: {err}")
        else:
            logger.error(f"[CANCELED] Reason: {reason}")
        sys.exit(1)

    def session_started(evt):
        logger.info(f"[SESSION] Started: {evt.session_id}")

    recognizer.recognized.connect(recognized)
    recognizer.synthesizing.connect(synthesis_handler)
    recognizer.canceled.connect(canceled)
    recognizer.session_started.connect(session_started)

    # --- 7) Run ---
    logger.info(f"Starting continuous recognition for profile [{args.profile.upper()}]...")
    callback.start_stream()
    recognizer.start_continuous_recognition_async()

    try:
        while True:
            await asyncio.sleep(0.5)
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        logger.info(f"Stopping recognition for profile [{args.profile.upper()}]...")
        recognizer.stop_continuous_recognition_async().get()
        callback.stop_stream()
        logger.info("Cleanup complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(e)
        sys.exit(1)
