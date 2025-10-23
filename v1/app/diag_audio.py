import argparse
import sys
import time
import math
from contextlib import contextmanager

import numpy as np
import sounddevice as sd
from loguru import logger

# Import profile-based settings
from app.config import settings
# Import the finder utility
from app.utils import find_device_index

"""
Audio diagnostics helper (Profile-based, v3)
- Reads device names and sample rates directly from app/config.py PROFILES.
- Uses WASAPI shared mode by default (as set in config).
- Lists all audio devices.
- Tests specific devices used by the translator profiles.

Usage:
  python -m app.diag_audio --list
  python -m app.diag_audio --test-headphones
  python -m app.diag_audio --test-mic
  python -m app.diag_audio --test-zoom-in
  python -m app.diag_audio --full
"""

# ------------- host API helpers (No change) -------------

def list_hostapis():
    print("\n=== Host APIs ===")
    for i, ha in enumerate(sd.query_hostapis()):
        name = ha.get("name", "")
        devs = ha.get("devices", [])
        print(f"[{i}] {name} | devices: {len(devs)}")
    print()

# ------------- device helpers (No change) -------------

def list_devices():
    print("\n=== Audio Devices ===")
    hostapis = sd.query_hostapis()
    devs = sd.query_devices()
    for i, d in enumerate(devs):
        ha_name = hostapis[d.get("hostapi", 0)].get("name", "?")
        print(
            f"[{i:02d}] {d['name']} | hostapi:{ha_name} | in:{d['max_input_channels']} out:{d['max_output_channels']} sr:{int(d['default_samplerate'])}"
        )
    print()

# ------------- streams (WASAPI shared) (No change) -------------

@contextmanager
def _output_stream(idx: int, sr: int):
    """Context manager for a WASAPI shared-mode output stream."""
    wa = sd.WasapiSettings(exclusive=False)
    stream = sd.OutputStream(device=idx, channels=1, samplerate=sr, dtype="int16", extra_settings=wa)
    stream.start()
    try:
        yield stream
    finally:
        stream.stop()
        stream.close()

@contextmanager
def _input_stream(idx: int, sr: int, blocksize: int):
    """Context manager for a WASAPI shared-mode input stream."""
    wa = sd.WasapiSettings(exclusive=False)
    stream = sd.InputStream(device=idx, channels=1, samplerate=sr, dtype="int16", blocksize=blocksize, extra_settings=wa)
    stream.start()
    try:
        yield stream
    finally:
        stream.stop()
        stream.close()

# ------------- SR selection (No change) -------------

def _pick_sample_rate(device_index: int, sr_cli: int | None, sr_cfg: int | None) -> int:
    """Choose sample rate priority: --sr > config.profile.sample_rate > device default."""
    if sr_cli:
        return int(sr_cli)
    if sr_cfg:
        return int(sr_cfg)
    # Fallback to device default
    dev_sr = int(sd.query_devices(device_index)["default_samplerate"]) or 48000
    return dev_sr

# ------------- ACTIONS (Updated for Profiles) -------------

def test_headphones(seconds: float = 3.0, sr_override: int | None = None):
    """Tests [understand] profile output device (your headphones)."""
    logger.info("Testing: [Profile: understand] -> Output (Headphones)")
    try:
        profile = settings.profiles["understand"]
        out_name = profile["output_device"]
        sr_cfg = profile["sample_rate"]
    except Exception as e:
        logger.error(f"Could not read 'understand' profile output from config.py: {e}")
        return

    prefer = settings.audio.get("prefer_hostapi")
    
    try:
        out_idx = find_device_index(out_name, "output", prefer_hostapi=prefer)
    except RuntimeError as e:
        logger.error(f"Device Error: {e}")
        return
        
    sr = _pick_sample_rate(out_idx, sr_override, sr_cfg)

    logger.info(f"Playing 440 Hz tone for {seconds}s -> '{out_name}' (idx {out_idx}) @ {sr} Hz")

    t = np.arange(int(seconds * sr)) / sr
    wave = (0.2 * np.sin(2 * math.pi * 440.0 * t)).astype(np.float32)
    wave_i16 = (np.clip(wave, -1.0, 1.0) * 32767.0).astype(np.int16)

    try:
        with _output_stream(out_idx, sr) as out:
            out.write(wave_i16)
    except Exception as e:
        logger.error(f"Failed to play audio to {out_name}: {e}")

def _monitor_input_logic(in_name: str, sr_cfg: int, seconds: float, sr_override: int | None):
    """Helper function to run the RMS meter logic."""
    prefer = settings.audio.get("prefer_hostapi")
    
    try:
        in_idx = find_device_index(in_name, "input", prefer_hostapi=prefer)
    except RuntimeError as e:
        logger.error(f"Device Error: {e}")
        return

    sr = _pick_sample_rate(in_idx, sr_override, sr_cfg)

    frame_ms = int(settings.audio.get("frame_ms", 20))
    samples_per_frame = int(sr * frame_ms / 1000)

    logger.info(f"Monitoring input '{in_name}' (idx {in_idx}) for {seconds}s @ {sr} Hz")
    print("RMS dBFS (approx):")

    def to_dbfs(block: np.ndarray) -> float:
        if block.size == 0:
            return -120.0
        rms = np.sqrt(np.mean((block.astype(np.float32) / 32768.0) ** 2) + 1e-12)
        return 20 * np.log10(rms + 1e-12)

    try:
        with _input_stream(in_idx, sr, samples_per_frame) as stream:
            t_end = time.time() + seconds
            while time.time() < t_end:
                data, _ = stream.read(samples_per_frame)
                db = to_dbfs(data)
                bar = int((db + 60) / 3)  # crude 0..20 scale for -60..0 dBFS
                bar = max(0, min(20, bar))
                print("[" + "#" * bar + " " * (20 - bar) + f"] {db:6.1f} dBFS", end="\r", flush=True)
            print()
    except Exception as e:
        logger.error(f"Failed to monitor audio from {in_name}: {e}")

def test_mic(seconds: float = 5.0, sr_override: int | None = None):
    """Tests [answer] profile input device (your physical mic)."""
    logger.info("Testing: [Profile: answer] -> Input (Your Microphone)")
    try:
        profile = settings.profiles["answer"]
        in_name = profile["input_device"]
        sr_cfg = profile["sample_rate"]
    except Exception as e:
        logger.error(f"Could not read 'answer' profile input from config.py: {e}")
        return
    _monitor_input_logic(in_name, sr_cfg, seconds, sr_override)

def test_zoom_in(seconds: float = 5.0, sr_override: int | None = None):
    """Tests [understand] profile input device (the CABLE-A output)."""
    logger.info("Testing: [Profile: understand] -> Input (Zoom/Teams Audio via CABLE-A)")
    try:
        profile = settings.profiles["understand"]
        in_name = profile["input_device"]
        sr_cfg = profile["sample_rate"]
    except Exception as e:
        logger.error(f"Could not read 'understand' profile input from config.py: {e}")
        return
    _monitor_input_logic(in_name, sr_cfg, seconds, sr_override)


def full_check(sr_override: int | None = None):
    """Runs the two primary tests: headphones and mic."""
    print("\nStep 1/2: Output check (Headphones) -> You should HEAR a 440 Hz tone.")
    test_headphones(2.0, sr_override)
    time.sleep(0.5)
    print("\nStep 2/2: Input check (Microphone) -> Speak into your mic; meter should move.")
    test_mic(6.0, sr_override)
    print("\nDone. If tests pass, your primary devices are configured correctly.")
    print("If audio from Zoom/Teams is not translated, run: python -m app.diag_audio --test-zoom-in")

# ------------- CLI (Updated) -------------

def main():
    parser = argparse.ArgumentParser(description="Audio diagnostics utility (Profile-based)")
    parser.add_argument("--hostapis", action="store_true", help="List host APIs (MME/WASAPI/etc.)")
    parser.add_argument("--list", action="store_true", help="List all audio devices")
    parser.add_argument("--test-headphones", action="store_true", help="Tests [understand] profile output (plays tone)")
    parser.add_argument("--test-mic", action="store_true", help="Tests [answer] profile input (monitors your mic)")
    parser.add_argument("--test-zoom-in", action="store_true", help="Tests [understand] profile input (monitors CABLE-A)")
    parser.add_argument("--full", action="store_true", help="Runs --test-headphones then --test-mic")
    parser.add_argument("--sr", type=int, default=None, help="Force sample rate (e.g., 48000)")
    args = parser.parse_args()

    try:
        if args.hostapis:
            list_hostapis()
        elif args.list:
            list_devices()
        elif args.test_headphones:
            test_headphones(3.0, args.sr)
        elif args.test_mic:
            test_mic(8.0, args.sr)
        elif args.test_zoom_in:
            test_zoom_in(8.0, args.sr)
        elif args.full or not any([args.hostapis, args.list, args.test_headphones, args.test_mic, args.test_zoom_in]):
            full_check(args.sr)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()