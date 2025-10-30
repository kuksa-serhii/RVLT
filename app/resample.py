"""
Audio resampling utilities using pysoxr.

Provides high-quality sample rate conversion for int16 PCM audio.
"""

import numpy as np
import soxr
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def downsample_48k_to_16k_int16(audio_48k: np.ndarray) -> np.ndarray:
    """
    Downsample 48 kHz mono int16 audio to 16 kHz using pysoxr.
    
    Args:
        audio_48k: Mono int16 PCM at 48 kHz, shape (samples,)
        
    Returns:
        Mono int16 PCM at 16 kHz
    """
    if len(audio_48k) == 0:
        return np.array([], dtype=np.int16)
    
    # Convert to float32 for resampling
    audio_float = audio_48k.astype(np.float32) / 32768.0
    
    # Resample
    resampled = soxr.resample(
        audio_float,
        in_rate=48000,
        out_rate=16000,
        quality='HQ'  # High quality mode
    )
    
    # Convert back to int16
    audio_16k = (resampled * 32767.0).astype(np.int16)
    
    return audio_16k


def upsample_16k_to_48k_int16(audio_16k: np.ndarray) -> np.ndarray:
    """
    Upsample 16 kHz mono int16 audio to 48 kHz using pysoxr.
    
    Args:
        audio_16k: Mono int16 PCM at 16 kHz, shape (samples,)
        
    Returns:
        Mono int16 PCM at 48 kHz
    """
    if len(audio_16k) == 0:
        return np.array([], dtype=np.int16)
    
    # Convert to float32 for resampling
    audio_float = audio_16k.astype(np.float32) / 32768.0
    
    # Resample
    resampled = soxr.resample(
        audio_float,
        in_rate=16000,
        out_rate=48000,
        quality='HQ'
    )
    
    # Convert back to int16
    audio_48k = (resampled * 32767.0).astype(np.int16)
    
    return audio_48k


def upsample_24k_to_48k_int16(audio_24k: np.ndarray) -> np.ndarray:
    """
    Upsample 24 kHz mono int16 audio to 48 kHz using pysoxr.
    
    Args:
        audio_24k: Mono int16 PCM at 24 kHz, shape (samples,)
        
    Returns:
        Mono int16 PCM at 48 kHz
    """
    if len(audio_24k) == 0:
        return np.array([], dtype=np.int16)
    
    # Convert to float32 for resampling
    audio_float = audio_24k.astype(np.float32) / 32768.0
    
    # Resample (exact 2x)
    resampled = soxr.resample(
        audio_float,
        in_rate=24000,
        out_rate=48000,
        quality='HQ'
    )
    
    # Convert back to int16
    audio_48k = (resampled * 32767.0).astype(np.int16)
    
    return audio_48k


def resample_to_target_rate_int16(
    audio: np.ndarray,
    source_rate: int,
    target_rate: int
) -> np.ndarray:
    """
    Resample int16 audio from source rate to target rate.
    
    Args:
        audio: Mono int16 PCM at source_rate
        source_rate: Source sample rate in Hz
        target_rate: Target sample rate in Hz
        
    Returns:
        Mono int16 PCM at target_rate
    """
    if source_rate == target_rate:
        # No resampling needed
        return audio
    
    if len(audio) == 0:
        return np.array([], dtype=np.int16)
    
    logger.debug(f"Resampling from {source_rate} Hz to {target_rate} Hz")
    
    # Convert to float32 for resampling
    audio_float = audio.astype(np.float32) / 32768.0
    
    # Resample
    resampled = soxr.resample(
        audio_float,
        in_rate=source_rate,
        out_rate=target_rate,
        quality='HQ'
    )
    
    # Convert back to int16
    audio_resampled = (resampled * 32767.0).astype(np.int16)
    
    return audio_resampled


def validate_resample_ratio(source_rate: int, target_rate: int) -> bool:
    """
    Validate that resampling ratio is sensible.
    
    Args:
        source_rate: Source sample rate in Hz
        target_rate: Target sample rate in Hz
        
    Returns:
        True if ratio is valid
    """
    if source_rate <= 0 or target_rate <= 0:
        return False
    
    ratio = max(source_rate, target_rate) / min(source_rate, target_rate)
    
    # Allow ratios up to 8x
    return ratio <= 8.0
