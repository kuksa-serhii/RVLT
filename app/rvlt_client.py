import asyncio
import sys
import numpy as np
import sounddevice as sd
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
    CancellationDetails
)

from app.config import settings
from app.utils import find_device_index, play_audio_blocking

# --- Налаштування логування ---
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
    Реалізує PullAudioInputStream для подачі аудіо-даних з sounddevice до Azure SDK.
    """
    def __init__(self, device_idx: int, sr: int, format: AudioStreamFormat):
        super().__init__(format)
        self.device_idx = device_idx
        self.sr = sr
        self.queue = Queue()
        # Блок, який читається sounddevice
        self.blocksize = int(sr * settings.audio.get("frame_ms", 20) / 1000)
        self.stream = None

    def read(self, size: int) -> bytes:
        """ SDK викликає цей метод, коли йому потрібні дані. """
        try:
            # Чекаємо на дані. Якщо черга порожня, повертаємо тишу (b'').
            chunk = self.queue.get(timeout=0.01) 
            return chunk if len(chunk) <= size else chunk[:size]
        except:
            # Якщо таймаут, повертаємо тишу відповідного розміру (для безперервності потоку)
            return b'\x00' * size

    def _callback(self, indata, frames, time, status):
        """ Callback для sounddevice InputStream. """
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        # PCM16, 1 канал. Відправляємо як байти.
        self.queue.put(indata.tobytes())

    def start_stream(self):
        """ Запуск потоку захоплення sounddevice. """
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
        """ Зупинка потоку. """
        if self.stream and self.stream.active:
            self.stream.stop(); self.stream.close()
        logger.info("[Audio In] Stopped capture stream.")


# --- Event Handlers ---

def recognized(evt: SpeechRecognitionEventArgs):
    """ Обробник події, коли переклад завершено. """
    result = evt.result
    
    if result.reason == ResultReason.Translated:
        lang_from = result.language
        lang_to = result.translation_target_language
        text_recognized = result.text
        text_translated = result.translation
        
        logger.info(f"==> [FROM {lang_from.upper()}] {text_recognized}")
        logger.success(f"==> [TO {lang_to.upper()}] {text_translated}")

    elif result.reason == ResultReason.RecognizedSpeech:
        logger.debug(f"[Recognizing] {result.text} (Intermediate)")
        
    elif result.reason == ResultReason.NoMatch:
        logger.debug("No speech could be recognized.")

def synthesis_handler(evt: TranslationSynthesisEventArgs):
    """ Обробка події синтезу мови (коли приходить аудіо). """
    if evt.result.audio and evt.result.audio_length > 0:
        audio_data = evt.result.audio
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        
        # Azure TTS Neural Voices зазвичай видають 24000 Гц
        tts_sample_rate = 24000 
        
        # Відтворення аудіо на пристрій, який слухає Teams/Zoom
        play_audio_blocking(
            audio_np, 
            sr=tts_sample_rate, 
            device_name=settings.audio.get("output_user_headphones")
        )
        logger.debug(f"[TTS] Played {evt.result.audio_length} bytes of audio.")

def canceled(evt: SpeechRecognitionEventArgs):
    logger.error(f"[CANCELED] Reason: {evt.result.cancellation_details.reason}")
    if evt.result.cancellation_details.reason == CancellationDetails.Reason.Error:
        logger.error(f"[CANCELED] Error Code: {evt.result.cancellation_details.error_details}")
    sys.exit(1)

def session_started(evt):
    logger.info(f"[SESSION] Started: {evt.session_id}")
    
# --- Main Logic ---

async def main():
    # --- 1. Audio & Config Setup ---
    device_sr = settings.audio.get("sample_rate", 48000)
    in_name = settings.audio.get("input_remote") 
    
    try:
        in_idx = find_device_index(in_name, "input", prefer_hostapi=settings.audio.get("prefer_hostapi"))
    except RuntimeError as e:
        logger.error(f"Device error: {e}. Check device names in app/config.py.")
        return

    # --- 2. Azure SDK Setup ---
    speech_key = settings.azure["speech_key"]
    speech_region = settings.azure["speech_region"]

    if not speech_key or not speech_region:
         raise RuntimeError("Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION in .env")

    speech_config = SpeechConfig(subscription=speech_key, region=speech_region)
    
    # Встановлення цільових мов для двостороннього перекладу
    for lang_code in settings.translation["target_languages"]:
        # Azure SDK використовує лише дволітерні коди ('uk', 'en') для таргетингу
        speech_config.add_target_language(lang_code) 
        
    # Встановлення голосів TTS для кожної цільової мови
    speech_config.set_property_by_name("SpeechSynthesisVoiceName.uk", settings.azure["voice_uk"])
    speech_config.set_property_by_name("SpeechSynthesisVoiceName.en", settings.azure["voice_en"])

    # Встановлення формату виводу TTS (24kHz PCM - стандарт для Neural)
    speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)

    # --- 3. Audio Stream Setup ---
    audio_format = AudioStreamFormat(
        samples_per_second=device_sr,
        bits_per_sample=16,
        channels=1,
        container_format=StreamContainerFormat.RAW_PCM
    )
    
    # Створюємо PullAudioInputStream для подачі аудіо-даних
    audio_stream_source = SoundDeviceStream(in_idx, device_sr, audio_format)
    # Передаємо SDK тільки AudioConfig з потоком вводу.
    audio_config = AudioConfig(stream=audio_stream_source)
    
    # --- 4. Translation Recognizer ---
    recognizer = TranslationRecognizer(
        translation_config=speech_config, 
        audio_config=audio_config
    )
    
    # Встановлення мови розпізнавання: автоматичне визначення
    recognizer.speech_recognition_language = "auto-detect"

    # Підписка на події
    recognizer.recognized.connect(recognized)
    recognizer.session_started.connect(session_started)
    recognizer.canceled.connect(canceled)
    recognizer.synthesis_event.connect(synthesis_handler)
    
    # --- 5. Run Continuous Recognition ---
    logger.info("Starting continuous recognition...")
    
    # Запускаємо захоплення аудіо та розпізнавання
    audio_stream_source.start_stream()
    recognizer.start_continuous_recognition()

    # Утримуємо головний потік, поки користувач не натисне Ctrl+C
    try:
        while True:
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass 
    except KeyboardInterrupt:
        pass # Захоплюємо Ctrl+C тут, щоб спрацювало finally

    finally:
        logger.info("Stopping recognition and cleaning up...")
        recognizer.stop_continuous_recognition()
        audio_stream_source.stop_stream()
        logger.info("Cleanup complete. Exiting.")


if __name__ == "__main__":
    try:
        # Для коректної роботи sounddevice та asyncio в Windows використовується вбудований loop
        asyncio.run(main())
    except Exception as e:
        logger.exception(e)
        sys.exit(1)
