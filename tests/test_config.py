"""
Unit tests for configuration loading and validation.
"""

import os
import tempfile
import pytest
from pathlib import Path
from app.config import load_config, validate_environment, Config


def test_load_config_from_env(monkeypatch):
    """Test loading configuration from environment variables."""
    # Set required env vars
    monkeypatch.setenv("SPEECH_KEY", "test_key_12345")
    monkeypatch.setenv("SPEECH_REGION", "westeurope")
    
    config = load_config()
    
    assert config.speech.speech_key == "test_key_12345"
    assert config.speech.speech_region == "westeurope"
    assert config.speech.stt_lang_ptt == "uk-UA"  # Default
    assert config.audio.device_sr_in == 48000  # Default


def test_load_config_missing_key(monkeypatch):
    """Test that missing API key raises error."""
    monkeypatch.delenv("SPEECH_KEY", raising=False)
    monkeypatch.setenv("SPEECH_REGION", "westeurope")
    
    with pytest.raises(ValueError, match="SPEECH_KEY"):
        load_config()


def test_load_config_invalid_key(monkeypatch):
    """Test that placeholder API key raises error."""
    monkeypatch.setenv("SPEECH_KEY", "your_key_here")
    monkeypatch.setenv("SPEECH_REGION", "westeurope")
    
    with pytest.raises(ValueError, match="SPEECH_KEY"):
        load_config()


def test_load_config_custom_values(monkeypatch):
    """Test loading custom configuration values."""
    monkeypatch.setenv("SPEECH_KEY", "custom_key")
    monkeypatch.setenv("SPEECH_REGION", "eastus")
    monkeypatch.setenv("STT_LANG_PTT", "en-US")
    monkeypatch.setenv("TTS_VOICE_EN", "en-US-JennyNeural")
    
    config = load_config()
    
    assert config.speech.speech_region == "eastus"
    assert config.speech.stt_lang_ptt == "en-US"
    assert config.speech.tts_voice_en == "en-US-JennyNeural"


def test_config_defaults():
    """Test default configuration values."""
    os.environ["SPEECH_KEY"] = "test_key"
    os.environ["SPEECH_REGION"] = "westeurope"
    
    config = load_config()
    
    # Audio defaults
    assert config.audio.device_sr_in == 48000
    assert config.audio.stt_sr == 16000
    assert config.audio.tts_sr == 48000
    assert config.audio.frame_ms == 20
    
    # Voicemeeter defaults
    assert config.voicemeeter.strip_mic == 0
    assert config.voicemeeter.strip_tts == 1
    assert config.voicemeeter.bus_meeting == "B1"
    
    # PTT defaults
    assert config.ptt.ptt_key == "F8"
    assert config.ptt.debounce_ms == 50
    
    # Logging defaults
    assert config.logging.log_level == "INFO"


def test_validate_environment_missing_key(monkeypatch):
    """Test environment validation with missing API key."""
    monkeypatch.delenv("SPEECH_KEY", raising=False)
    monkeypatch.delenv("SPEECH_REGION", raising=False)
    
    errors = validate_environment()
    
    assert len(errors) >= 1
    assert any("SPEECH_KEY" in err for err in errors)


def test_validate_environment_success(monkeypatch):
    """Test successful environment validation."""
    monkeypatch.setenv("SPEECH_KEY", "valid_key")
    monkeypatch.setenv("SPEECH_REGION", "westeurope")
    
    errors = validate_environment()
    
    # May have Voicemeeter warning on non-Windows or if not installed
    # but should not have env var errors
    env_errors = [e for e in errors if "SPEECH" in e]
    assert len(env_errors) == 0


def test_load_config_from_yaml(monkeypatch, tmp_path):
    """Test loading configuration from YAML file."""
    monkeypatch.setenv("SPEECH_KEY", "test_key")
    monkeypatch.setenv("SPEECH_REGION", "westeurope")
    
    # Create temporary YAML config
    yaml_content = """
ptt:
  ptt_key: "F9"
  debounce_ms: 100

audio:
  frame_ms: 30
"""
    
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml_content)
    
    config = load_config(yaml_file=str(yaml_file))
    
    # YAML values should override defaults
    assert config.ptt.ptt_key == "F9"
    assert config.ptt.debounce_ms == 100
    assert config.audio.frame_ms == 30
    
    # Env vars should still work
    assert config.speech.speech_key == "test_key"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
