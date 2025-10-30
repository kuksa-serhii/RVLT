"""
Audio device enumeration and stream management using sounddevice.

Handles WASAPI device queries, stream creation at 48 kHz, and stereo→mono downmixing.
"""

import numpy as np
import sounddevice as sd
from typing import Optional, Callable, List, Tuple
import logging

logger = logging.getLogger(__name__)


def list_audio_devices() -> List[dict]:
    """
    Enumerate all available WASAPI audio devices.
    
    Returns:
        List of device dictionaries with name, index, channels, sample rate
    """
    devices = []
    for idx, dev in enumerate(sd.query_devices()):
        devices.append({
            "index": idx,
            "name": dev['name'],
            "max_input_channels": dev['max_input_channels'],
            "max_output_channels": dev['max_output_channels'],
            "default_samplerate": dev['default_samplerate'],
            "hostapi": sd.query_hostapis(dev['hostapi'])['name']
        })
    return devices


def find_device_by_name(name: str, input_device: bool = True) -> Optional[int]:
    """
    Find device index by name (case-insensitive substring match).
    
    Args:
        name: Device name or substring
        input_device: True for input, False for output
        
    Returns:
        Device index or None if not found
    """
    devices = list_audio_devices()
    name_lower = name.lower()
    
    for dev in devices:
        if name_lower in dev['name'].lower():
            if input_device and dev['max_input_channels'] > 0:
                return dev['index']
            elif not input_device and dev['max_output_channels'] > 0:
                return dev['index']
    
    return None


def downmix_stereo_to_mono_int16(stereo_frames: np.ndarray) -> np.ndarray:
    """
    Downmix stereo int16 PCM to mono using (L+R)/2 with overflow protection.
    
    Args:
        stereo_frames: Shape (frames, 2) int16 array
        
    Returns:
        Shape (frames,) int16 mono array
    """
    if stereo_frames.ndim == 1:
        # Already mono
        return stereo_frames
    
    if stereo_frames.shape[1] == 1:
        # Single channel
        return stereo_frames.flatten()
    
    # Convert to int32 to avoid overflow during addition
    left = stereo_frames[:, 0].astype(np.int32)
    right = stereo_frames[:, 1].astype(np.int32)
    
    # Average and cast back to int16
    mono = ((left + right) // 2).astype(np.int16)
    return mono


class AudioInputStream:
    """
    Manages an input audio stream at 48 kHz with configurable frame size.
    
    Automatically handles stereo→mono downmixing.
    """
    
    def __init__(
        self,
        device: Optional[int] = None,
        samplerate: int = 48000,
        frame_ms: int = 20,
        channels: int = 1,
        callback: Optional[Callable[[np.ndarray], None]] = None
    ):
        """
        Initialize audio input stream.
        
        Args:
            device: Device index (None for default)
            samplerate: Sample rate in Hz (default 48000)
            frame_ms: Frame duration in milliseconds (default 20)
            channels: Number of channels to request (1 or 2)
            callback: Function called with mono int16 frames
        """
        self.device = device
        self.samplerate = samplerate
        self.frame_ms = frame_ms
        self.blocksize = int(samplerate * frame_ms / 1000)
        self.channels = channels
        self.callback = callback
        self.stream: Optional[sd.InputStream] = None
        
        logger.info(
            f"AudioInputStream: device={device}, sr={samplerate}, "
            f"frame_ms={frame_ms}, blocksize={self.blocksize}"
        )
    
    def _stream_callback(self, indata, frames, time_info, status):
        """Internal callback for sounddevice stream."""
        if status:
            logger.warning(f"Stream status: {status}")
        
        # Convert to int16
        audio_int16 = (indata * 32767).astype(np.int16)
        
        # Downmix to mono if needed
        mono = downmix_stereo_to_mono_int16(audio_int16)
        
        if self.callback:
            self.callback(mono)
    
    def start(self):
        """Start the input stream."""
        if self.stream is not None:
            logger.warning("Stream already started")
            return
        
        self.stream = sd.InputStream(
            device=self.device,
            channels=self.channels,
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            dtype=np.float32,
            callback=self._stream_callback
        )
        self.stream.start()
        logger.info("Input stream started")
    
    def stop(self):
        """Stop and close the input stream."""
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            logger.info("Input stream stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class AudioOutputStream:
    """
    Manages an output audio stream for playback at 48 kHz.
    """
    
    def __init__(
        self,
        device: Optional[int] = None,
        samplerate: int = 48000,
        channels: int = 1
    ):
        """
        Initialize audio output stream.
        
        Args:
            device: Device index (None for default)
            samplerate: Sample rate in Hz (default 48000)
            channels: Number of output channels (default 1)
        """
        self.device = device
        self.samplerate = samplerate
        self.channels = channels
        self.stream: Optional[sd.OutputStream] = None
        
        logger.info(f"AudioOutputStream: device={device}, sr={samplerate}, ch={channels}")
    
    def start(self):
        """Start the output stream."""
        if self.stream is not None:
            logger.warning("Stream already started")
            return
        
        self.stream = sd.OutputStream(
            device=self.device,
            channels=self.channels,
            samplerate=self.samplerate,
            dtype=np.int16
        )
        self.stream.start()
        logger.info("Output stream started")
    
    def write(self, audio_data: np.ndarray):
        """
        Write audio data to the stream.
        
        Args:
            audio_data: int16 PCM data (mono or multi-channel)
        """
        if self.stream is None:
            raise RuntimeError("Stream not started")
        
        # Reshape for mono if needed
        if audio_data.ndim == 1 and self.channels == 1:
            audio_data = audio_data.reshape(-1, 1)
        
        self.stream.write(audio_data)
    
    def stop(self):
        """Stop and close the output stream."""
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            logger.info("Output stream stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
