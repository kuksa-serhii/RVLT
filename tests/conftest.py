"""
Pytest configuration and fixtures.
"""

import pytest
import os


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["SPEECH_KEY"] = "test_key_for_testing"
    os.environ["SPEECH_REGION"] = "westeurope"


@pytest.fixture
def mock_config():
    """Provide a mock configuration for testing."""
    from app.config import Config, AudioConfig, VoicemeeterConfig, SpeechConfig, PTTConfig
    
    return Config(
        audio=AudioConfig(),
        voicemeeter=VoicemeeterConfig(),
        speech=SpeechConfig(
            speech_key="test_key",
            speech_region="westeurope"
        ),
        ptt=PTTConfig()
    )
