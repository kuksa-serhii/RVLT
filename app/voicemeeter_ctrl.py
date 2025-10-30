"""
Voicemeeter Remote API control wrapper.

Provides strip muting, bus routing, and PTT mode switching.
"""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import voicemeeterlib
    VOICEMEETER_AVAILABLE = True
except ImportError:
    VOICEMEETER_AVAILABLE = False
    logger.warning("voicemeeterlib not available - Voicemeeter control disabled")


class VoicemeeterController:
    """
    Thin wrapper over Voicemeeter Remote API.
    
    Handles connection, strip muting, bus routing, and PTT mode.
    """
    
    def __init__(self, kind: str = "banana", max_retries: int = 3):
        """
        Initialize Voicemeeter controller.
        
        Args:
            kind: Voicemeeter type ('basic', 'banana', 'potato')
            max_retries: Maximum connection retry attempts
        """
        self.kind = kind
        self.max_retries = max_retries
        self.vm: Optional[object] = None
        self._connected = False
        
        if not VOICEMEETER_AVAILABLE:
            logger.error("Voicemeeter library not available")
    
    def connect(self) -> bool:
        """
        Connect to Voicemeeter with retries.
        
        Returns:
            True if connected successfully
        """
        if not VOICEMEETER_AVAILABLE:
            logger.error("Cannot connect - voicemeeterlib not installed")
            return False
        
        for attempt in range(self.max_retries):
            try:
                self.vm = voicemeeterlib.api(self.kind)
                self.vm.login()
                self._connected = True
                logger.info(f"Connected to Voicemeeter {self.kind}")
                return True
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                time.sleep(0.5)
        
        logger.error("Failed to connect to Voicemeeter after retries")
        return False
    
    def disconnect(self):
        """Disconnect from Voicemeeter."""
        if self.vm and self._connected:
            try:
                self.vm.logout()
                self._connected = False
                logger.info("Disconnected from Voicemeeter")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to Voicemeeter."""
        return self._connected
    
    def mute_strip(self, index: int, mute: bool) -> bool:
        """
        Mute or unmute a strip.
        
        Args:
            index: Strip index (0-based)
            mute: True to mute, False to unmute
            
        Returns:
            True if successful
        """
        if not self._connected:
            logger.error("Not connected to Voicemeeter")
            return False
        
        try:
            strip = self.vm.strip[index]
            strip.mute = mute
            logger.debug(f"Strip {index} mute={mute}")
            return True
        except Exception as e:
            logger.error(f"Failed to mute strip {index}: {e}")
            return False
    
    def route_to_bus(self, strip_index: int, bus: str, on: bool) -> bool:
        """
        Route strip to a bus.
        
        Args:
            strip_index: Strip index (0-based)
            bus: Bus identifier (e.g., 'A1', 'B1')
            on: True to enable routing, False to disable
            
        Returns:
            True if successful
        """
        if not self._connected:
            logger.error("Not connected to Voicemeeter")
            return False
        
        try:
            strip = self.vm.strip[strip_index]
            setattr(strip, bus, on)
            logger.debug(f"Strip {strip_index} -> {bus} = {on}")
            return True
        except Exception as e:
            logger.error(f"Failed to route strip {strip_index} to {bus}: {e}")
            return False
    
    def set_ptt_mode(self, pressed: bool, strip_mic: int, strip_tts: int) -> bool:
        """
        Switch Voicemeeter strips for PTT mode.
        
        When pressed: mute mic strip, unmute TTS strip
        When released: unmute mic strip, mute TTS strip
        
        Args:
            pressed: True if PTT pressed, False if released
            strip_mic: Physical mic strip index
            strip_tts: Azure TTS strip index
            
        Returns:
            True if successful
        """
        if not self._connected:
            logger.error("Not connected to Voicemeeter")
            return False
        
        try:
            if pressed:
                # PTT pressed: mute mic, unmute TTS
                self.mute_strip(strip_mic, True)
                self.mute_strip(strip_tts, False)
                logger.info("PTT mode: MIC muted, TTS unmuted")
            else:
                # PTT released: unmute mic, mute TTS
                self.mute_strip(strip_mic, False)
                self.mute_strip(strip_tts, True)
                logger.info("PTT mode: MIC unmuted, TTS muted")
            
            return True
        except Exception as e:
            logger.error(f"Failed to set PTT mode: {e}")
            return False
    
    def get_strip_levels(self, index: int) -> Optional[tuple[float, float]]:
        """
        Get strip audio levels (L, R) in dB.
        
        Args:
            index: Strip index
            
        Returns:
            Tuple of (left_db, right_db) or None if error
        """
        if not self._connected:
            return None
        
        try:
            strip = self.vm.strip[index]
            # This is a placeholder - actual API may vary
            return (strip.levels.prefader[0], strip.levels.prefader[1])
        except Exception as e:
            logger.error(f"Failed to get levels for strip {index}: {e}")
            return None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
