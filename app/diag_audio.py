import argparse
import sys
import time
import math
from contextlib import contextmanager

import numpy as np
import sounddevice as sd
from loguru import logger

# Using the NEW config.py with profiles
from app.config import settings

"""
Audio diagnostics helper (Windows-optimized, v3 - Profiles)
- Uses WASAPI shared mode by default to avoid WDM-KS blocking errors.
- Auto-selects sample rate (CLI > config > device default).
- Lists host APIs and devices.
- Tests audio devices directly from your 'config.py' profiles.

Usage:
  python -m app.diag_audio --hostapis
  python -m app.diag_audio --list
  python -m app.diag_audio --test-headphones  (Tests understand profile OUTPUT)
  python -m app.diag_audio --test-mic         (Tests answer profile INPUT)
  python -m app.diag_audio --test-zoom-in      (Tests understand profile INPUT)
  python -m app.diag_audio --full            (Tests headphones + mic)

Notes:
- This script reads device names directly from settings.profiles in 'app/config.py'.
"""

# ------------- host API helpers (Unchanged) -------------

def list_hostapis():
    print("\n=== Host APIs ===")
    for i, ha in enumerate(sd.query_hostapis()):
        name = ha.get("name", "")
        devs = ha.get("devices", [])
        print(f"[{i}] {name} | devices: {len(devs)}")
    print()


def _get_hostapi_index(prefer: str | None) -> int | None:
    if not prefer:
        return None
    prefer_l = prefer.lower()
    for i, ha in enumerate(sd.query_hostapis()):
        if prefer_l in ha.get("name", "").lower():
            return i
    return None

# ------------- device helpers (Unchanged) -------------

def _find_device_index(name: str, kind: str, prefer_hostapi: str | None = None) -> int:
    name = (name or "").lower()
    hostapi_idx = _get_hostapi_index(prefer_hostapi)
    devs = sd.query_devices()
    # 1) try preferred host API first
    if hostapi_idx is not None:
        for i, d in enumerate(devs):
            if d.get("hostapi") != hostapi_idx:
                continue
            dname = str(d.get("name", ""))
            if name in dname.lower() and d.get(f"max_{kind}_channels", 0) > 0:
                return i
    # 2) fallback: any host API
    for i, d in enumerate(devs):
        dname = str(d.get("name", ""))
        if name in dname.lower() and d.get(f"max_{kind}_channels", 0) > 0:
            return i
    raise RuntimeError(f"Audio device not found: {name!r} ({kind})")


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

# ------------- streams (Unchanged) -------------

@contextmanager
def _output_stream(idx: int, sr: int):
    wa = sd.WasapiSettings(exclusive=False)
    stream = sd.OutputStream(device=idx, channels=1, samplerate=sr, dtype="int16", extra_settings=wa)
    stream.start()
    try:
        yield stream
    finally:
        stream.stop(); stream.close()


@contextmanager
def _input_stream(idx: int, sr: int, blocksize: int):
    wa = sd.WasapiSettings(exclusive=False)
    stream = sd.InputStream(device=idx, channels=1, samplerate=sr, dtype="int16", blocksize=blocksize, extra_settings=wa)
    stream.start()
    try:
        yield stream
    finally:
        stream.stop(); stream.close()

# ------------- SR selection (Unchanged) -------------

def _pick_sample_rate(device_index: int, sr_cli: int | None, sr_cfg: int | None) -> int:
    """Choose sample rate priority: --sr > config.audio.sample_rate > device default."""
    if sr_cli:
        return int(sr_cli)
    if sr_cfg:
        return int(sr_cfg)
    dev_sr = int(sd.query_devices(device_index)["default_samplerate"]) or 48000
    return dev_sr

# ------------- actions (UPDATED) -------------

def play_tone(device_name: str, seconds: float = 3.0, sr_override: int | None = None):
    """
    Plays a test tone to the specified device.
    """
    prefer = settings.audio.get("prefer_hostapi", "Windows WASAPI")
    out_idx = _find_device_index(device_name, "output", prefer_hostapi=prefer)

    sr_cfg = settings.audio.get("sample_rate")
    sr = _pick_sample_rate(out_idx, sr_override, sr_cfg)

    logger.info(f"Playing 440 Hz tone for {seconds}s -> '{device_name}' (idx {out_idx}) @ {sr} Hz [WASAPI shared]")

    t = np.arange(int(seconds * sr)) / sr
    wave = (0.2 * np.sin(2 * math.pi * 440.0 * t)).astype(np.float32)
    wave_i16 = (np.clip(wave, -1.0, 1.0) * 32767.0).astype(np.int16)

    with _output_stream(out_idx, sr) as out:
        out.write(wave_i16)


def monitor_input(device_name: str, seconds: float = 5.0, sr_override: int | None = None):
    """
    Shows the input signal level (RMS) from the specified device.
    """
    prefer = settings.audio.get("prefer_hostapi", "Windows WASAPI")
    in_idx = _find_device_index(device_name, "input", prefer_hostapi=prefer)

    sr_cfg = settings.audio.get("sample_rate")
    sr = _pick_sample_rate(in_idx, sr_override, sr_cfg)

    frame_ms = int(settings.audio.get("frame_ms", 20))
    samples_per_frame = int(sr * frame_ms / 1000)

    logger.info(f"Monitoring input '{device_name}' (idx {in_idx}) for {seconds}s @ {sr} Hz | frame {frame_ms} ms [WASAPI shared]")
    print("RMS dBFS (approx):")

    def to_dbfs(block: np.ndarray) -> float:
        if block.size == 0:
            return -120.0
        rms = np.sqrt(np.mean((block.astype(np.float32) / 32768.0) ** 2) + 1e-12)
        return 20 * np.log10(rms + 1e-12)

    with _input_stream(in_idx, sr, samples_per_frame) as stream:
        t_end = time.time() + seconds
        while time.time() < t_end:
            data, _ = stream.read(samples_per_frame)
            db = to_dbfs(data)
            bar = int((db + 60) / 3)  # crude 0..20 scale for -60..0 dBFS
            bar = max(0, min(20, bar))
            print("[" + "#" * bar + " " * (20 - bar) + f"] {db:6.1f} dBFS", end="\r", flush=True)
        print()


def full_check(sr_override: int | None = None):
    """
    Performs a full check: output to headphones and input from microphone.
    """
    # 1. Test 'understand' profile output (your headphones)
    headphones_name = settings.profiles["understand"]["output_device"]
    print(f"\nStep 1/2: Output check (Profile: understand) -> '{headphones_name}'")
    print("         You should HEAR a 440 Hz tone in your headphones...")
    play_tone(headphones_name, 2.0, sr_override)
    time.sleep(0.5)

    # 2. Test 'answer' profile input (your microphone)
    mic_name = settings.profiles["answer"]["input_device"]
    print(f"\nStep 2/2: Input check (Profile: answer) -> '{mic_name}'")
    print("         Speak into your PHYSICAL MICROPHONE; the meter should move...")
    monitor_input(mic_name, 6.0, sr_override)
    
    print("\nDone. If tests failed, check device names in app/config.py and Windows settings.")

# ------------- CLI (UPDATED) -------------

def main():
    parser = argparse.ArgumentParser(description="Audio diagnostics utility (Profile-based)")
    parser.add_argument("--hostapis", action="store_true", help="List host APIs (WASAPI/WDM-KS/etc.)")
    parser.add_argument("--list", action="store_true", help="List all audio devices with host API")
    parser.add_argument("--test-headphones", action="store_true", help="Play test tone to headphones (understand profile OUTPUT)")
    parser.add_argument("--test-mic", action="store_true", help="Show input RMS meter from your mic (answer profile INPUT)")
    parser.add_argument("--test-zoom-in", action="store_true", help="Show input RMS from Zoom/Teams (understand profile INPUT)")
    parser.add_argument("--full", action="store_true", help="Run full check (headphones out + mic in)")
    parser.add_argument("--sr", type=int, default=None, help="Force sample rate (e.g., 48000)")
    args = parser.parse_args()

    try:
        if args.hostapis:
            list_hostapis()
        elif args.list:
            list_devices()
            
        elif args.test_headphones:
            out_name = settings.profiles["understand"]["output_device"]
            play_tone(out_name, 3.0, args.sr)
            
        elif args.test_mic:
            in_name = settings.profiles["answer"]["input_device"]
            monitor_input(in_name, 8.0, args.sr)
            
        elif args.test_zoom_in:
            in_name = settings.profiles["understand"]["input_device"]
            monitor_input(in_name, 8.0, args.sr)
            
        elif args.full or not any(vars(args).values()):
            # Run full check if --full is specified or if no flags are given
            full_check(args.sr)
            
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

