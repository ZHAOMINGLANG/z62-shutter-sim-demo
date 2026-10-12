#!/usr/bin/env python3
"""
Z62 shutter sound simulator for VM validation.
- resolve SD card SHUTTER.WAV or SHUTTER/1.WAV..4.WAV
- supports preview and trigger
- if simpleaudio available, will try to play actual PCM; otherwise simulates
- supports burst policy:
    - "every": every trigger plays
    - "first": only first trigger in a burst plays
    - "every_n": every Nth trigger plays
"""
import wave
import time
import json
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class ShutterSoundConfig:
    enabled: bool = False
    selected: str = "NONE"
    volume: int = 80


class ShutterSoundManager:
    def __init__(self, sound_root, play_mode="first", min_interval_ms=60, every_n=3):
        self.sound_root = Path(sound_root)
        self.config = ShutterSoundConfig()
        self.play_count = 0
        self.last_played = None
        self._sa = None
        try:
            import simpleaudio as _sa
            self._sa = _sa
        except Exception:
            self._sa = None

        self.play_mode = play_mode
        self.min_interval_ms = int(min_interval_ms)
        self.every_n = max(1, int(every_n))
        self._last_play_time = 0.0
        self._since_last_play_triggers = 0

    def load_config(self, cfg_path):
        path = Path(cfg_path)
        if not path.exists():
            self.config = ShutterSoundConfig()
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.config.enabled = bool(data.get("enabled", False))
            self.config.selected = str(data.get("selected", "NONE"))
            self.config.volume = int(data.get("volume", 80))
        except Exception:
            self.config = ShutterSoundConfig()

    def save_config(self, cfg_path):
        Path(cfg_path).write_text(
            json.dumps(asdict(self.config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def resolve_sound_file(self):
        if not self.config.enabled:
            return None

        root = self.sound_root / "SHUTTER.WAV"
        if root.exists() and self.config.selected in ("SHUTTER.WAV", "NONE"):
            return root

        sdir = self.sound_root / "SHUTTER"
        if self.config.selected.startswith("SHUTTER/"):
            p = self.sound_root / self.config.selected
            if p.exists():
                return p

        if self.config.selected in {"1.WAV", "2.WAV", "3.WAV", "4.WAV"}:
            p = sdir / self.config.selected
            if p.exists():
                return p

        if root.exists():
            return root

        for n in range(1, 5):
            p = sdir / f"{n}.WAV"
            if p.exists():
                return p
        return None

    def describe_wav(self, path):
        try:
            with wave.open(str(path), "rb") as wf:
                return f"{wf.getframerate()}Hz {wf.getnchannels()}ch {wf.getsampwidth()*8}bit {wf.getnframes()}frames"
        except Exception:
            return "invalid wav"

    def _should_play_now(self):
        import time as _time
        now = _time.monotonic()

        if self.play_mode == "every":
            return True

        if self.play_mode == "first":
            if (now - self._last_play_time) * 1000.0 >= self.min_interval_ms:
                return True
            return False

        if self.play_mode == "every_n":
            self._since_last_play_triggers += 1
            if self._since_last_play_triggers >= self.every_n:
                self._since_last_play_triggers = 0
                return True
            return False

        return True

    def _record_play(self):
        import time as _time
        self._last_play_time = _time.monotonic()
        self._since_last_play_triggers = 0

    def _play_pcm(self, path):
        self.last_played = path
        self.play_count += 1
        print(f"[play] {path} ({self.describe_wav(path)}) vol={self.config.volume}")
        self._record_play()

        if self._sa:
            try:
                with wave.open(str(path), "rb") as wf:
                    frames = wf.readframes(wf.getnframes())
                    self._sa.play_buffer(frames, wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
                time.sleep(0.05)
            except Exception as e:
                print("[play] playback failed:", e)
        else:
            time.sleep(0.02)

    def preview_sound(self):
        p = self.resolve_sound_file()
        if not p:
            return "No sound selected"
        return f"Previewing: {p} ({self.describe_wav(p)})"

    def trigger(self):
        if not self.config.enabled:
            return "Shutter sound disabled"

        p = self.resolve_sound_file()
        if not p:
            return "No valid shutter sound found"

        if not self._should_play_now():
            print("[trigger] skipped due to burst policy")
            return f"Triggered sound (skipped): {p.name}"

        self._play_pcm(p)
        return f"Triggered sound: {p.name}"
