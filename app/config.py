# app/config.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Завантажуємо .env для доступу до змінних середовища
load_dotenv()

# Корінь проекту
ROOT = Path(__file__).resolve().parent

# --- Словник профілів запуску ---
# Кожен профіль описує один потік перекладу

PROFILES: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    "understand": {
        "description": "🟢 Я СЛУХАЮ (EN -> UK). Слухає Zoom, перекладає мені в навушники.",
        # Вхід: Віртуальний кабель, куди Zoom/Teams надсилає аудіо
        # (Налаштовується в Zoom/Teams Output)
        "input_device": "CABLE Output (VB-Audio Virtual ",
        
        # Вихід: Ваші фізичні навушники
        # (Назва з вашого скріншоту image_199adc.png)
        "output_device": "Навушники (2- HD65)",
        
        # Мова, яку ми очікуємо почути (для розпізнавання)
        "source_lang": "en-GB", 
        
        # Мова, на яку перекладаємо
        "target_lang": "uk",
        
        # Голос для синтезу перекладу (український)
        "tts_voice": "uk-UA-AlinaNeural",
    },
    # -------------------------------------------------------------------------
    "answer": {
        "description": "🟣 Я ГОВОРЮ (UK -> EN). Слухає мій мікрофон, перекладає в Zoom/Teams.",
        
        # Вхід: Ваш фізичний мікрофон
        # (Назва з вашого скріншоту image_199adc.png)
        "input_device": "Головной телефон (2- HD65)",
        
        # Вихід: Віртуальний кабель "B", який Zoom слухає як мікрофон
        # (Потрібно встановити VB-CABLE B)
        "output_device": "CABLE-B Input (VB-Audio", 
        
        # Мова, якою ви говорите
        "source_lang": "uk-UA",
        
        # Мова, на яку перекладаємо
        "target_lang": "en",
        
        # Голос для синтезу перекладу (британський)
        "tts_voice": "en-GB-RyanNeural",
    }
    # -------------------------------------------------------------------------
}


class _Settings:
    """
    Легкий об'єкт налаштувань. Завантажує параметри з вбудованих значень
    та перезаписує їх змінними середовища (.env).
    """

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {
            "audio": {
                # Спільні налаштування
                "sample_rate": 48000,
                "frame_ms": 20,
                "prefer_hostapi": "Windows WASAPI"
            },
            
            # --- ПІДКЛЮЧЕННЯ ДО AZURE SPEECH SERVICE ---
            "azure": {
                "speech_key": os.getenv("AZURE_SPEECH_KEY", ""),
                "speech_region": os.getenv("AZURE_SPEECH_REGION", "uksouth"), #
            },
            
            # --- ЛОГУВАННЯ ---
            "logging": {
                "level": "INFO",
            },
        }
    
    # Додаємо профілі до об'єкта
    @property
    def profiles(self) -> Dict[str, Dict[str, Any]]:
        return PROFILES
        
    # --- public dict-like accessors ---
    @property
    def audio(self) -> Dict[str, Any]:
        return self._data["audio"]

    @property
    def logging(self) -> Dict[str, Any]:
        return self._data.get("logging", {})

    @property
    def azure(self) -> Dict[str, Any]:
        return self._data["azure"]

# Singleton-like settings instance
settings = _Settings()

__all__ = ["settings", "ROOT"]