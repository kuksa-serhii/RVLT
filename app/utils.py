"""
Utility functions for logging, timing, and audio debugging.
"""

import logging
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional, List
from collections import deque
import numpy as np
import wave


def setup_logger(
    name: str = "rt-ptt-translator",
    level: str = "INFO",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging with file rotation and console output.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (optional)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


class TimingStats:
    """
    Track timing statistics with percentile calculations.
    """
    
    def __init__(self, name: str, max_samples: int = 1000):
        """
        Initialize timing tracker.
        
        Args:
            name: Name of the timed operation
            max_samples: Maximum samples to keep for percentile calc
        """
        self.name = name
        self.max_samples = max_samples
        self.samples: deque[float] = deque(maxlen=max_samples)
        self.logger = logging.getLogger(__name__)
    
    def add_sample(self, duration_ms: float):
        """Add a timing sample in milliseconds."""
        self.samples.append(duration_ms)
    
    def get_stats(self) -> dict:
        """
        Get timing statistics.
        
        Returns:
            Dict with min, max, mean, p50, p95, p99
        """
        if not self.samples:
            return {}
        
        sorted_samples = sorted(self.samples)
        n = len(sorted_samples)
        
        return {
            "count": n,
            "min": sorted_samples[0],
            "max": sorted_samples[-1],
            "mean": sum(sorted_samples) / n,
            "p50": sorted_samples[int(n * 0.50)],
            "p95": sorted_samples[int(n * 0.95)] if n > 20 else sorted_samples[-1],
            "p99": sorted_samples[int(n * 0.99)] if n > 100 else sorted_samples[-1],
        }
    
    def log_stats(self):
        """Log current statistics."""
        stats = self.get_stats()
        if stats:
            self.logger.info(
                f"{self.name}: mean={stats['mean']:.1f}ms, "
                f"p50={stats['p50']:.1f}ms, p95={stats['p95']:.1f}ms, "
                f"min={stats['min']:.1f}ms, max={stats['max']:.1f}ms"
            )


class Timer:
    """Context manager for timing code blocks."""
    
    def __init__(self, name: str, stats: Optional[TimingStats] = None):
        """
        Initialize timer.
        
        Args:
            name: Name of timed operation
            stats: Optional TimingStats to record result
        """
        self.name = name
        self.stats = stats
        self.start_time = 0
        self.duration_ms = 0
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        self.duration_ms = (end_time - self.start_time) * 1000
        
        if self.stats:
            self.stats.add_sample(self.duration_ms)
        
        self.logger.debug(f"{self.name}: {self.duration_ms:.2f} ms")


def dump_audio_wav(
    audio_data: np.ndarray,
    sample_rate: int,
    filepath: str,
    description: str = ""
):
    """
    Dump audio to WAV file for debugging.
    
    Args:
        audio_data: int16 PCM audio
        sample_rate: Sample rate in Hz
        filepath: Output file path
        description: Optional description for logging
    """
    logger = logging.getLogger(__name__)
    
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
        
        logger.debug(f"Dumped audio to {filepath}: {len(audio_data)} samples @ {sample_rate} Hz {description}")
    
    except Exception as e:
        logger.error(f"Failed to dump audio: {e}")


def format_device_list(devices: List[dict]) -> str:
    """
    Format device list for display.
    
    Args:
        devices: List of device dicts
        
    Returns:
        Formatted string
    """
    lines = []
    lines.append("\nAvailable Audio Devices:")
    lines.append("-" * 80)
    
    for dev in devices:
        lines.append(
            f"  [{dev['index']}] {dev['name']}\n"
            f"      In: {dev['max_input_channels']} ch, Out: {dev['max_output_channels']} ch, "
            f"SR: {dev['default_samplerate']} Hz, API: {dev['hostapi']}"
        )
    
    lines.append("-" * 80)
    return "\n".join(lines)


def validate_audio_not_clipping(audio: np.ndarray, threshold: float = 0.95) -> bool:
    """
    Check if audio is clipping.
    
    Args:
        audio: int16 audio array
        threshold: Clipping threshold (0-1)
        
    Returns:
        True if no clipping detected
    """
    max_val = np.max(np.abs(audio))
    return max_val < (32767 * threshold)
