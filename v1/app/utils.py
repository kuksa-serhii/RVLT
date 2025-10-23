import numpy as np
import sounddevice as sd
from loguru import logger
from typing import Dict, Any

from app.config import settings

"""
Утиліти для пошуку пристроїв та відтворення аудіо.
Перевикористовується логіка знаходження пристроїв для Windows WASAPI.
"""

def _get_hostapi_index(prefer: str | None) -> int | None:
    """Знаходить індекс Host API за назвою."""
    if not prefer:
        return None
    prefer_l = prefer.lower()
    for i, ha in enumerate(sd.query_hostapis()):
        if prefer_l in ha.get("name", "").lower():
            return i
    return None

def find_device_index(name: str, kind: str, prefer_hostapi: str | None = None) -> int:
    """Знаходить індекс аудіопристрою за частковою назвою та типом (input/output)."""
    hostapi_idx = _get_hostapi_index(prefer_hostapi)
    name_l = (name or "").lower()
    devs = sd.query_devices()
    
    # 1. Спроба знайти у пріоритетному Host API (наприклад, WASAPI)
    if hostapi_idx is not None:
        for i, d in enumerate(devs):
            if d.get("hostapi") == hostapi_idx and d.get(f"max_{kind}_channels", 0) > 0:
                if name_l in str(d.get("name", "")).lower():
                    return i
    
    # 2. Пошук серед усіх Host API
    for i, d in enumerate(devs):
        if name_l in str(d.get("name", "")).lower() and d.get(f"max_{kind}_channels", 0) > 0:
            return i
            
    raise RuntimeError(f"Audio device not found: {name!r} ({kind})")

def play_audio_blocking(pcm: np.ndarray, sr: int, device_name: str):
    """
    Відтворює PCM16 numpy масив на вказаний вихідний пристрій (блокуючий).
    Використовується для відтворення перекладу.
    """
    if pcm.size == 0:
        logger.warning("Empty PCM array; nothing to play.")
        return
        
    out_idx = find_device_index(device_name, "output", prefer_hostapi=settings.audio.get("prefer_hostapi"))
    
    # Налаштування WASAPI shared mode для уникнення блокувань
    wa = sd.WasapiSettings(exclusive=False)
    
    try:
        # Аудіо від Azure TTS зазвичай 24kHz. Використовуємо його як SR.
        with sd.OutputStream(device=out_idx, channels=1, samplerate=sr, dtype="int16", extra_settings=wa) as stream:
            stream.write(pcm)
    except Exception as e:
        logger.error(f"Failed to play audio to {device_name} (idx {out_idx}): {e}")

__all__ = ["find_device_index", "play_audio_blocking"]