"""
Configuration module for RT Bilingual PTT Translator.

Loads configuration from .env and optional config.yaml using Pydantic models.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
import yaml


class AudioConfig(BaseModel):
    """Audio configuration parameters."""
    device_sr_in: int = Field(48000, description="Input device sample rate (Hz)")
    stt_sr: int = Field(16000, description="STT input sample rate (Hz)")
    tts_sr: int = Field(48000, description="TTS output sample rate (Hz)")
    frame_ms: int = Field(20, description="Audio frame duration (ms)")
    mic_device: Optional[str] = Field(None, description="Microphone device name")
    tts_device: Optional[str] = Field(None, description="TTS output device name")


class VoicemeeterConfig(BaseModel):
    """Voicemeeter routing configuration."""
    strip_mic: int = Field(0, description="Physical mic strip index")
    strip_tts: int = Field(1, description="Azure TTS strip index")
    bus_meeting: str = Field("B1", description="Meeting output bus")
    bus_headphones: str = Field("A1", description="Headphones output bus")


class SpeechConfig(BaseModel):
    """Azure Speech service configuration."""
    speech_key: str = Field(..., description="Azure Speech API key")
    speech_region: str = Field(..., description="Azure Speech region")
    stt_lang_ptt: str = Field("uk-UA", description="STT language for PTT (Ukrainian)")
    stt_lang_understand: str = Field("en-GB", description="STT language for understanding (English)")
    tts_voice_en: str = Field("en-GB-RyanNeural", description="English TTS voice")
    tts_voice_ua: str = Field("uk-UA-OstapNeural", description="Ukrainian TTS voice")
    
    @validator('speech_key')
    def validate_key(cls, v):
        if not v or v == "your_key_here":
            raise ValueError("SPEECH_KEY must be set to a valid Azure Speech key")
        return v


class PTTConfig(BaseModel):
    """Push-to-Talk configuration."""
    ptt_key: str = Field("F8", description="PTT hotkey")
    debounce_ms: int = Field(50, description="Debounce duration (ms)")
    vad_enabled: bool = Field(True, description="Enable Voice Activity Detection")
    vad_aggressiveness: int = Field(2, description="VAD aggressiveness (0-3)")


class LoggingConfig(BaseModel):
    """Logging and diagnostics configuration."""
    log_level: str = Field("INFO", description="Logging level")
    log_file: str = Field("logs/run.log", description="Log file path")
    dump_audio: bool = Field(False, description="Dump audio frames for debugging")
    dump_path: str = Field("debug_dumps", description="Audio dump directory")


class Config(BaseModel):
    """Main configuration model."""
    audio: AudioConfig = AudioConfig()
    voicemeeter: VoicemeeterConfig = VoicemeeterConfig()
    speech: SpeechConfig
    ptt: PTTConfig = PTTConfig()
    logging: LoggingConfig = LoggingConfig()


def load_config(env_file: Optional[str] = None, yaml_file: Optional[str] = None) -> Config:
    """
    Load configuration from environment and optional YAML file.
    
    Args:
        env_file: Path to .env file (default: .env in project root)
        yaml_file: Path to config.yaml (optional)
    
    Returns:
        Config: Validated configuration object
        
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Load environment variables
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()
    
    # Start with environment variables
    config_dict = {
        "speech": {
            "speech_key": os.getenv("SPEECH_KEY", ""),
            "speech_region": os.getenv("SPEECH_REGION", "westeurope"),
            "stt_lang_ptt": os.getenv("STT_LANG_PTT", "uk-UA"),
            "stt_lang_understand": os.getenv("STT_LANG_UNDERSTAND", "en-GB"),
            "tts_voice_en": os.getenv("TTS_VOICE_EN", "en-GB-RyanNeural"),
            "tts_voice_ua": os.getenv("TTS_VOICE_UA", "uk-UA-OstapNeural"),
        }
    }
    
    # Override with YAML if provided
    if yaml_file and Path(yaml_file).exists():
        with open(yaml_file, 'r') as f:
            yaml_config = yaml.safe_load(f) or {}
            # Deep merge
            for key, value in yaml_config.items():
                if key in config_dict and isinstance(value, dict):
                    config_dict[key].update(value)
                else:
                    config_dict[key] = value
    
    try:
        config = Config(**config_dict)
        return config
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}")


def validate_environment() -> list[str]:
    """
    Validate environment prerequisites.
    
    Returns:
        List of validation errors (empty if all OK)
    """
    errors = []
    
    # Check required environment variables
    if not os.getenv("SPEECH_KEY"):
        errors.append("SPEECH_KEY environment variable is required")
    
    if not os.getenv("SPEECH_REGION"):
        errors.append("SPEECH_REGION environment variable is required")
    
    # Check for Voicemeeter (Windows-only check)
    if os.name == 'nt':
        vm_paths = [
            r"C:\Program Files (x86)\VB\Voicemeeter",
            r"C:\Program Files\VB\Voicemeeter",
        ]
        if not any(Path(p).exists() for p in vm_paths):
            errors.append("Voicemeeter does not appear to be installed")
    
    return errors
