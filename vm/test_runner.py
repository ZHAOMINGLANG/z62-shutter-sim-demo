#!/usr/bin/env python3
"""
Automated VM tests:
- single_shot_test: press shutter once, expect play_count +1
- burst_shot_test: five quick triggers, expect first-mode to allow 1 actual play
- every_n mode: every N trigger plays once
"""
from pathlib import Path
import wave
import struct
import time
from vm.test_shutter import ShutterSoundManager, ShutterSoundConfig


def create_demo_sdcard(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "SHUTTER").mkdir(parents=True, exist_ok=True)

    sr = 8000
    frames = sr // 2
    data = bytearray()
    for i in range(frames):
        v = int(12000 * (1 if i % 20 < 10 else -1))
        data.extend(struct.pack('<h', v))

    p = root / "SHUTTER.WAV"
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bytes(data))
    print("[demo] created", p)


def single_shot_test(mgr):
    pre = mgr.play_count
    out = mgr.trigger()
    print("[single] ->", out)
    post = mgr.play_count
    assert post - pre == 1, f"expected play +1, got {post - pre}"
    print("[single] OK")


def burst_first_mode_test(mgr, n=5, interval_s=0.02):
    pre = mgr.play_count
    for i in range(n):
        out = mgr.trigger()
        print(f"[burst-first] {i + 1}/{n} ->", out)
        time.sleep(interval_s)
    post = mgr.play_count
    print(f"[burst-first] actual plays: {post - pre}")
    assert post - pre == 1, f"expected first-mode burst to play once, got {post - pre}"
    print("[burst-first] OK")


def burst_every_n_test(mgr, n=5, interval_s=0.02):
    pre = mgr.play_count
    for i in range(n):
        out = mgr.trigger()
        print(f"[burst-every_n] {i + 1}/{n} ->", out)
        time.sleep(interval_s)
    post = mgr.play_count
    print(f"[burst-every_n] actual plays: {post - pre}")
    assert post - pre == 2, f"expected every_n=3 to play 2 times in 5 triggers, got {post - pre}"
    print("[burst-every_n] OK")


def main():
    sd = Path("demo_sdcard")
    if not sd.exists():
        create_demo_sdcard(sd)

    first_mgr = ShutterSoundManager(sd, play_mode="first", min_interval_ms=60)
    first_mgr.config = ShutterSoundConfig(enabled=True, selected="SHUTTER.WAV", volume=90)
    print("Preview:", first_mgr.preview_sound())
    print("\nSingle shot test")
    single_shot_test(first_mgr)
    print("\nBurst first-mode test")
    burst_first_mode_test(first_mgr, n=5, interval_s=0.02)

    every_mgr = ShutterSoundManager(sd, play_mode="every_n", every_n=3)
    every_mgr.config = ShutterSoundConfig(enabled=True, selected="SHUTTER.WAV", volume=90)
    print("\nBurst every_n-mode test")
    burst_every_n_test(every_mgr, n=5, interval_s=0.02)

    print("\nAll passed.")


if __name__ == "__main__":
    main()
