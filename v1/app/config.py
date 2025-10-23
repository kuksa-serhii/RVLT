from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Load .env file for environment variables
load_dotenv()

# Project root
ROOT = Path(__file__).resolve().parent

# --- Profile Dictionary ---
# Each profile defines one translation stream (direction).
# We use partial names here, which app/utils.py will find.

PROFILES: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    "understand": {
        "description": "UNDERSTAND (EN -> UK). Listens to Zoom/Teams, speaks to headphones.",
        
        # Input: The virtual cable where Zoom/Teams sends its audio.
        # This is the "Recording" device from your WASAPI list [43].
        "input_device": "CABLE-A Output (VB-Audio Virtual Cable A)",
        
        # Output: Your physical headphones.
        # This is the "Playback" device from your WASAPI list [39].
        "output_device": "Наушники (2- HD65)",
        
        # Sample Rate: Must match what the WASAPI devices support.
        "sample_rate": 48000,
        
        # Language we expect to hear (recognition)
        "source_lang": "en-GB", 
        
        # Language to translate to
        "target_lang": "uk",
        
        # Voice for the synthesized translation (Ukrainian)
        "tts_voice": "uk-UA-PolinaNeural",
    },
    # -------------------------------------------------------------------------
    "answer": {
        "description": "ANSWER (UK -> EN). Listens to your mic, speaks to Zoom/Teams.",
        
        # Input: Your physical microphone.
        # This is your selected mic from the WASAPI list [42].
        "input_device": "Набор микрофонов (Realtek(R) Audio)",
        
        # Output: The virtual cable that Zoom/Teams listens to (as its mic).
        # This is the "Playback" device from your WASAPI list [36].
        "output_device": "CABLE-B Input (VB-Audio Virtual Cable B)", 
        
        # Sample Rate: Must match what the WASAPI devices support.
        "sample_rate": 48000,
        
        # Language you speak
        "source_lang": "uk-UA",
        
        # Language to translate to
        "target_lang": "en",
        
        # Voice for the synthesized translation (British English)
        "tts_voice": "en-GB-RyanNeural",
    }
    # -------------------------------------------------------------------------
}


class _Settings:
    """
    Lightweight settings object. Loads parameters from built-in values
    and overwrites them with environment variables (.env).
    """

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {
            "audio": {
                # Common audio settings
                "frame_ms": 20,
                "prefer_hostapi": "Windows WASAPI" # We MUST use WASAPI
            },
            
            # --- AZURE SPEECH SERVICE CONNECTION ---
            "azure": {
                "speech_key": os.getenv("AZURE_SPEECH_KEY", ""),
                "speech_region": os.getenv("AZURE_SPEECH_REGION", "uksouth"),
            },
            
            # --- LOGGING ---
            "logging": {
                "level": "INFO", # DEBUG | INFO | WARNING | ERROR
            },
        }
    
    # Add profiles to the settings object
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