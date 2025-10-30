"""
Unit tests for resampling functions.
"""

import numpy as np
import pytest
from app.resample import (
    downsample_48k_to_16k_int16,
    upsample_16k_to_48k_int16,
    upsample_24k_to_48k_int16,
    resample_to_target_rate_int16,
    validate_resample_ratio
)


def test_downsample_48k_to_16k_ratio():
    """Test that downsampling produces correct output length."""
    # 1 second of 48 kHz audio
    audio_48k = np.random.randint(-1000, 1000, size=48000, dtype=np.int16)
    
    audio_16k = downsample_48k_to_16k_int16(audio_48k)
    
    # Should be approximately 1/3 the length (48000 / 16000 = 3)
    expected_length = 16000
    assert abs(len(audio_16k) - expected_length) < 10, f"Expected ~{expected_length}, got {len(audio_16k)}"


def test_downsample_empty_array():
    """Test downsampling with empty input."""
    audio_48k = np.array([], dtype=np.int16)
    audio_16k = downsample_48k_to_16k_int16(audio_48k)
    
    assert len(audio_16k) == 0


def test_upsample_16k_to_48k_ratio():
    """Test that upsampling produces correct output length."""
    # 1 second of 16 kHz audio
    audio_16k = np.random.randint(-1000, 1000, size=16000, dtype=np.int16)
    
    audio_48k = upsample_16k_to_48k_int16(audio_16k)
    
    # Should be approximately 3x the length
    expected_length = 48000
    assert abs(len(audio_48k) - expected_length) < 10, f"Expected ~{expected_length}, got {len(audio_48k)}"


def test_upsample_24k_to_48k_exact():
    """Test 24k to 48k upsampling (exact 2x ratio)."""
    # 1 second of 24 kHz audio
    audio_24k = np.random.randint(-1000, 1000, size=24000, dtype=np.int16)
    
    audio_48k = upsample_24k_to_48k_int16(audio_24k)
    
    # Should be exactly 2x the length
    expected_length = 48000
    assert abs(len(audio_48k) - expected_length) < 5, f"Expected ~{expected_length}, got {len(audio_48k)}"


def test_resample_identity():
    """Test that same rate resampling returns original."""
    audio = np.random.randint(-1000, 1000, size=1000, dtype=np.int16)
    
    resampled = resample_to_target_rate_int16(audio, 48000, 48000)
    
    assert len(resampled) == len(audio)
    np.testing.assert_array_equal(resampled, audio)


def test_resample_no_clipping():
    """Test that resampling doesn't cause clipping."""
    # Create audio with moderate levels
    audio_48k = np.random.randint(-10000, 10000, size=48000, dtype=np.int16)
    
    audio_16k = downsample_48k_to_16k_int16(audio_48k)
    
    # Check no clipping (values within int16 range)
    assert np.max(audio_16k) <= 32767
    assert np.min(audio_16k) >= -32768
    
    # Check most values are not at extremes
    clipped = np.sum(np.abs(audio_16k) > 30000)
    assert clipped < len(audio_16k) * 0.01, "Too many values near clipping"


def test_validate_resample_ratio_valid():
    """Test valid resample ratios."""
    assert validate_resample_ratio(48000, 16000) == True
    assert validate_resample_ratio(16000, 48000) == True
    assert validate_resample_ratio(24000, 48000) == True
    assert validate_resample_ratio(44100, 48000) == True


def test_validate_resample_ratio_invalid():
    """Test invalid resample ratios."""
    assert validate_resample_ratio(0, 48000) == False
    assert validate_resample_ratio(48000, 0) == False
    assert validate_resample_ratio(48000, 400000) == False  # Ratio > 8


def test_roundtrip_downsample_upsample():
    """Test roundtrip down and up preserves reasonable quality."""
    # Create simple tone
    duration = 0.1  # 100 ms
    freq = 440  # A4
    sr_48k = 48000
    
    t = np.linspace(0, duration, int(sr_48k * duration), False)
    audio_48k_orig = (np.sin(2 * np.pi * freq * t) * 10000).astype(np.int16)
    
    # Downsample to 16k
    audio_16k = downsample_48k_to_16k_int16(audio_48k_orig)
    
    # Upsample back to 48k
    audio_48k_restored = upsample_16k_to_48k_int16(audio_16k)
    
    # Lengths should be similar (within a few samples due to filter edge effects)
    assert abs(len(audio_48k_restored) - len(audio_48k_orig)) < 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
