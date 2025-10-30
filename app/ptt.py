"""
Push-to-Talk keyboard handler with debouncing.

Uses keyboard library for global hotkey detection.
"""

import time
import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    logger.warning("keyboard library not available - PTT disabled")


class PTTHandler:
    """
    Global keyboard hook for PTT with debouncing.
    
    Calls registered callbacks on press and release events.
    """
    
    def __init__(self, ptt_key: str = "F8", debounce_ms: int = 50):
        """
        Initialize PTT handler.
        
        Args:
            ptt_key: Key to use for PTT (e.g., 'F8', 'ctrl+space')
            debounce_ms: Debounce duration in milliseconds
        """
        self.ptt_key = ptt_key
        self.debounce_ms = debounce_ms
        self._pressed = False
        self._last_event_time = 0
        self._lock = threading.Lock()
        
        self.on_pressed: Optional[Callable[[], None]] = None
        self.on_released: Optional[Callable[[], None]] = None
        
        self._active = False
        
        if not KEYBOARD_AVAILABLE:
            logger.error("keyboard library not available - PTT will not work")
    
    def subscribe(
        self,
        on_pressed: Optional[Callable[[], None]] = None,
        on_released: Optional[Callable[[], None]] = None
    ):
        """
        Subscribe to PTT events.
        
        Args:
            on_pressed: Callback when PTT key is pressed
            on_released: Callback when PTT key is released
        """
        self.on_pressed = on_pressed
        self.on_released = on_released
        logger.info(f"PTT callbacks registered for key: {self.ptt_key}")
    
    def _handle_key_event(self, event):
        """Internal handler for keyboard events."""
        current_time = time.time() * 1000  # Convert to ms
        
        with self._lock:
            # Check debounce
            if current_time - self._last_event_time < self.debounce_ms:
                return
            
            self._last_event_time = current_time
            
            if event.event_type == 'down' and not self._pressed:
                # Key pressed
                self._pressed = True
                logger.debug(f"PTT pressed: {self.ptt_key}")
                if self.on_pressed:
                    try:
                        self.on_pressed()
                    except Exception as e:
                        logger.error(f"Error in on_pressed callback: {e}")
            
            elif event.event_type == 'up' and self._pressed:
                # Key released
                self._pressed = False
                logger.debug(f"PTT released: {self.ptt_key}")
                if self.on_released:
                    try:
                        self.on_released()
                    except Exception as e:
                        logger.error(f"Error in on_released callback: {e}")
    
    def start(self):
        """Start listening for PTT key events."""
        if not KEYBOARD_AVAILABLE:
            logger.error("Cannot start PTT - keyboard library not available")
            return
        
        if self._active:
            logger.warning("PTT handler already active")
            return
        
        try:
            keyboard.hook_key(self.ptt_key, self._handle_key_event)
            self._active = True
            logger.info(f"PTT handler started for key: {self.ptt_key}")
        except Exception as e:
            logger.error(f"Failed to start PTT handler: {e}")
    
    def stop(self):
        """Stop listening for PTT key events."""
        if not self._active:
            return
        
        try:
            keyboard.unhook_key(self.ptt_key)
            self._active = False
            self._pressed = False
            logger.info("PTT handler stopped")
        except Exception as e:
            logger.error(f"Error stopping PTT handler: {e}")
    
    def is_pressed(self) -> bool:
        """Check if PTT key is currently pressed."""
        with self._lock:
            return self._pressed
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
