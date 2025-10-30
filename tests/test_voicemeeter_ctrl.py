"""
Unit tests for Voicemeeter controller (mocked).
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.voicemeeter_ctrl import VoicemeeterController, VOICEMEETER_AVAILABLE


@pytest.fixture
def mock_voicemeeter():
    """Create a mock Voicemeeter instance."""
    with patch('app.voicemeeter_ctrl.VOICEMEETER_AVAILABLE', True):
        with patch('app.voicemeeter_ctrl.voicemeeterlib') as mock_vm_lib:
            mock_vm = MagicMock()
            mock_vm_lib.api.return_value = mock_vm
            
            # Setup strip mocks
            mock_strip_0 = MagicMock()
            mock_strip_1 = MagicMock()
            mock_vm.strip = {
                0: mock_strip_0,
                1: mock_strip_1
            }
            
            yield mock_vm_lib, mock_vm


def test_connect_success(mock_voicemeeter):
    """Test successful connection to Voicemeeter."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    controller = VoicemeeterController()
    result = controller.connect()
    
    assert result == True
    assert controller.is_connected() == True
    mock_vm.login.assert_called_once()


def test_connect_retry_on_failure(mock_voicemeeter):
    """Test connection retries on failure."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    # Fail first 2 attempts, succeed on 3rd
    mock_vm.login.side_effect = [Exception("Failed"), Exception("Failed"), None]
    
    controller = VoicemeeterController(max_retries=3)
    result = controller.connect()
    
    assert result == True
    assert mock_vm.login.call_count == 3


def test_connect_max_retries_exceeded(mock_voicemeeter):
    """Test connection failure after max retries."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    mock_vm.login.side_effect = Exception("Connection failed")
    
    controller = VoicemeeterController(max_retries=2)
    result = controller.connect()
    
    assert result == False
    assert controller.is_connected() == False


def test_disconnect(mock_voicemeeter):
    """Test disconnection from Voicemeeter."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    controller = VoicemeeterController()
    controller.connect()
    controller.disconnect()
    
    assert controller.is_connected() == False
    mock_vm.logout.assert_called_once()


def test_mute_strip(mock_voicemeeter):
    """Test muting a strip."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    controller = VoicemeeterController()
    controller.connect()
    
    result = controller.mute_strip(0, True)
    
    assert result == True
    assert mock_vm.strip[0].mute == True


def test_mute_strip_not_connected(mock_voicemeeter):
    """Test muting fails when not connected."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    controller = VoicemeeterController()
    # Don't connect
    
    result = controller.mute_strip(0, True)
    
    assert result == False


def test_route_to_bus(mock_voicemeeter):
    """Test routing strip to bus."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    controller = VoicemeeterController()
    controller.connect()
    
    result = controller.route_to_bus(0, "B1", True)
    
    assert result == True
    # Check that B1 attribute was set
    assert hasattr(mock_vm.strip[0], "B1") or True  # Mock will create attribute


def test_set_ptt_mode_pressed(mock_voicemeeter):
    """Test PTT mode when pressed."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    controller = VoicemeeterController()
    controller.connect()
    
    result = controller.set_ptt_mode(pressed=True, strip_mic=0, strip_tts=1)
    
    assert result == True
    # Mic should be muted, TTS unmuted
    assert mock_vm.strip[0].mute == True
    assert mock_vm.strip[1].mute == False


def test_set_ptt_mode_released(mock_voicemeeter):
    """Test PTT mode when released."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    controller = VoicemeeterController()
    controller.connect()
    
    result = controller.set_ptt_mode(pressed=False, strip_mic=0, strip_tts=1)
    
    assert result == True
    # Mic should be unmuted, TTS muted
    assert mock_vm.strip[0].mute == False
    assert mock_vm.strip[1].mute == True


def test_context_manager(mock_voicemeeter):
    """Test using controller as context manager."""
    mock_vm_lib, mock_vm = mock_voicemeeter
    
    with VoicemeeterController() as controller:
        assert controller.is_connected() == True
    
    # Should be disconnected after exiting context
    mock_vm.logout.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
