import argparse
import sys
import time
import math
from contextlib import contextmanager

import numpy as np
import sounddevice as sd
from loguru import logger

from app.config import settings

"""
Audio diagnostics helper (Windows‑optimized, v2)
- Uses WASAPI shared mode by default to avoid WDM‑KS blocking errors
- Auto‑selects a safe sample rate from the device default (or --sr override)
- Lists host APIs and devices (with host API + default SR)
- Plays a 440 Hz test tone to your headphones
- Shows input RMS meter from remote/virtual line (e.g., VB‑CABLE Output)

Usage:
  python -m app.diag_audio --hostapis
  python -m app.diag_audio --list
  python -m app.diag_audio --test-out [--sr 48000]
  python -m app.diag_audio --test-in  [--sr 48000]
  python -m app.diag_audio --full     [--sr 48000]

Notes:
- If --sr is not provided, we try `config.audio.sample_rate`, else fall back to the device default.
- Ensure your meeting app routes audio to the device named in `config.yaml: audio.input_remote`.
"""

# ------------- host API helpers -------------

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

# ------------- device helpers -------------

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

# ------------- streams (WASAPI shared) -------------

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

# ------------- SR selection -------------

def _pick_sample_rate(device_index: int, sr_cli: int | None, sr_cfg: int | None) -> int:
    """Choose sample rate priority: --sr > config.yaml > device default."""
    if sr_cli:
        return int(sr_cli)
    if sr_cfg:
        return int(sr_cfg)
    dev_sr = int(sd.query_devices(device_index)["default_samplerate"]) or 48000
    return dev_sr

# ------------- actions -------------

def play_tone(seconds: float = 3.0, sr_override: int | None = None):
    out_name = settings.audio.get("output_user_headphones")
    prefer = settings.audio.get("prefer_hostapi", "Windows WASAPI")
    out_idx = _find_device_index(out_name, "output", prefer_hostapi=prefer)

    sr_cfg = settings.audio.get("sample_rate")
    sr = _pick_sample_rate(out_idx, sr_override, sr_cfg)

    logger.info(f"Playing 440 Hz tone for {seconds}s -> '{out_name}' (idx {out_idx}) @ {sr} Hz [WASAPI shared]")

    t = np.arange(int(seconds * sr)) / sr
    wave = (0.2 * np.sin(2 * math.pi * 440.0 * t)).astype(np.float32)
    wave_i16 = (np.clip(wave, -1.0, 1.0) * 32767.0).astype(np.int16)

    with _output_stream(out_idx, sr) as out:
        out.write(wave_i16)


def monitor_input(seconds: float = 5.0, sr_override: int | None = None):
    in_name = settings.audio.get("input_remote")
    prefer = settings.audio.get("prefer_hostapi", "Windows WASAPI")
    in_idx = _find_device_index(in_name, "input", prefer_hostapi=prefer)

    sr_cfg = settings.audio.get("sample_rate")
    sr = _pick_sample_rate(in_idx, sr_override, sr_cfg)

    frame_ms = int(settings.audio.get("frame_ms", 20))
    samples_per_frame = int(sr * frame_ms / 1000)

    logger.info(f"Monitoring input '{in_name}' (idx {in_idx}) for {seconds}s @ {sr} Hz | frame {frame_ms} ms [WASAPI shared]")
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
    print("\nStep 1/2: Output check → You should HEAR a 440 Hz tone in your headphones")
    play_tone(2.0, sr_override)
    time.sleep(0.5)
    print("\nStep 2/2: Input check → Speak or play any audio into your REMOTE/virtual line; meter should move")
    monitor_input(6.0, sr_override)
    print("Done. If the meter is flat, verify Windows Sound routing and app outputs.")

# ------------- CLI -------------

def main():
    parser = argparse.ArgumentParser(description="Audio diagnostics utility (WASAPI + auto SR)")
    parser.add_argument("--hostapis", action="store_true", help="List host APIs (WASAPI/WDM-KS/etc.)")
    parser.add_argument("--list", action="store_true", help="List audio devices with host API column")
    parser.add_argument("--test-out", action="store_true", help="Play a test tone to user headphones")
    parser.add_argument("--test-in", action="store_true", help="Show input RMS meter from the remote device")
    parser.add_argument("--full", action="store_true", help="Run output then input checks")
    parser.add_argument("--sr", type=int, default=None, help="Force sample rate (e.g., 48000)")
    args = parser.parse_args()

    try:
        if args.hostapis:
            list_hostapis()
        elif args.list:
            list_devices()
        elif args.test_out:
            play_tone(3.0, args.sr)
        elif args.test_in:
            monitor_input(8.0, args.sr)
        elif args.full or not any([args.hostapis, args.list, args.test_out, args.test_in]):
            full_check(args.sr)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
