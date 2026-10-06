"""Coach-only push-to-talk from this PC's microphone (hold the - key by default)."""

from __future__ import annotations

import ctypes
import os
import threading
import time
from collections.abc import Callable

import sounddevice as sd


SAMPLE_RATE = 48_000
MAX_SECONDS = 12
MIN_SECONDS = 0.5


class HotkeyCapture:
    def __init__(self, on_press: Callable[[], None], on_release: Callable[[bytes], None],
                 *, device: int | None = None) -> None:
        self.on_press = on_press
        self.on_release = on_release
        self.device = device
        self.key = int(os.getenv("COACH_HOTKEY_VK", "0xBD"), 0)  # the - key between 0 and =
        self._running = threading.Event()
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._capturing = False
        self._pcm = bytearray()
        self._thread: threading.Thread | None = None
        self.error: Exception | None = None
        self.questions = 0

    def start(self) -> None:
        self._running.set()
        self._thread = threading.Thread(target=self._run, name="coach-hotkey", daemon=True)
        self._thread.start()
        if not self._ready.wait(5):
            self.stop()
            raise RuntimeError("Microphone did not open")
        if self.error:
            raise self.error

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)

    @property
    def active(self) -> bool:
        return self._running.is_set() and self._thread is not None and self._thread.is_alive()

    def _audio(self, indata, frames, time_info, status) -> None:
        with self._lock:
            if self._capturing:
                self._pcm.extend(indata.tobytes())
                if len(self._pcm) > SAMPLE_RATE * 2 * MAX_SECONDS:
                    del self._pcm[:len(self._pcm) - SAMPLE_RATE * 2 * MAX_SECONDS]

    def _run(self) -> None:
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                device=self.device, callback=self._audio):
                self._ready.set()
                down_before = False
                while self._running.is_set():
                    down = bool(ctypes.windll.user32.GetAsyncKeyState(self.key) & 0x8000)
                    if down and not down_before:
                        with self._lock:
                            self._pcm.clear()
                            self._capturing = True
                        self.on_press()
                    elif down_before and not down:
                        with self._lock:
                            self._capturing = False
                            pcm = bytes(self._pcm)
                            self._pcm.clear()
                        if len(pcm) >= SAMPLE_RATE * 2 * MIN_SECONDS:
                            self.questions += 1
                            self.on_release(pcm)
                    down_before = down
                    time.sleep(0.02)
        except Exception as exc:
            self.error = exc
            self._ready.set()
        finally:
            with self._lock:
                self._capturing = False
                self._pcm.clear()
            self._running.clear()


def input_devices() -> list[tuple[int, str]]:
    return [(index, device["name"]) for index, device in enumerate(sd.query_devices())
            if device["max_input_channels"] > 0]
