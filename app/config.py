from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Завантажуємо .env для доступу до змінних середовища
load_dotenv()

# Корінь проекту
ROOT = Path(__file__).resolve().parent


class _Settings:
    """
    Легкий об'єкт налаштувань. Завантажує параметри з вбудованих значень
    та перезаписує їх змінними середовища (.env).
    """

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {
            "audio": {
                "sample_rate": 48000, # Частота дискретизації пристрою (HD65)
                "frame_ms": 20,       # Розмір аудіофрейму для sounddevice
                
                # --- Аудіопристрої (Встановлюються відповідно до Voicemeeter/CABLE) ---
                # Клієнт слухає: CABLE Output (куди Voicemeeter злив мову співрозмовника та Ваш мікрофон)
                "input_remote": "CABLE Output (VB-Audio Virtual ", 
                # Клієнт відтворює переклад: CABLE Input (Teams/Zoom слухає це як мікрофон)
                "output_user_headphones": "CABLE Input (VB-Audio Virtual C", 
                "prefer_hostapi": "Windows WASAPI"
            },
            
            # --- ПІДКЛЮЧЕННЯ ДО AZURE SPEECH SERVICE ---
            "azure": {
                "speech_key": os.getenv("AZURE_SPEECH_KEY", ""), # Ключ для Speech Service
                "speech_region": os.getenv("AZURE_SPEECH_REGION", "westeurope"), # Регіон Azure
                # Високоякісні голоси для синтезу мови (TTS)
                "voice_uk": "uk-UA-AlinaNeural",  # Український голос
                "voice_en": "en-GB-RyanNeural",   # Британський голос
            },
            
            # --- КОНФІГУРАЦІЯ ПЕРЕКЛАДУ ---
            "translation": {
                # Мови, на які ми перекладаємо (для двостороннього перекладу)
                "target_languages": ["uk", "en"], 
                # Мова для розпізнавання: "auto-detect"
            },
            
            # --- ЛОГУВАННЯ ---
            "logging": {
                "level": "INFO", # Рівень логування: DEBUG | INFO | WARNING | ERROR
            },
        }
        
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
    
    @property
    def translation(self) -> Dict[str, Any]:
        return self._data.get("translation", {})

# Singleton-like settings instance
settings = _Settings()

__all__ = ["settings", "ROOT"]
