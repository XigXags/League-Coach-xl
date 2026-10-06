"""Opt-in Discord voice capture and local Whisper transcription."""

from __future__ import annotations

import audioop
import re
import threading
from collections.abc import Callable

import numpy as np
from discord.ext import voice_recv
from faster_whisper import WhisperModel


_model: WhisperModel | None = None
_model_lock = threading.Lock()
WAKE = re.compile(r"\b(?:hey\s+)?(?:league\s+)?coach\b[\s,.:;!?-]*", re.IGNORECASE)


def load_model() -> WhisperModel:
    global _model
    with _model_lock:
        if _model is None:
            _model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        return _model


def question_after_wake(transcript: str) -> str | None:
    match = WAKE.search(transcript)
    if not match:
        return None
    question = transcript[match.end():].strip(" .,!?:;-\n\t")
    return question or None


def transcribe_pcm(pcm: bytes, channels: int = 2) -> str:
    """Transcribe 48 kHz signed 16-bit Discord stereo or local mono PCM."""
    mono = audioop.tomono(pcm, 2, 0.5, 0.5) if channels == 2 else pcm
    converted, _ = audioop.ratecv(mono, 2, 1, 48000, 16000, None)
    audio = np.frombuffer(converted, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = load_model().transcribe(
        audio, language="en", beam_size=1, best_of=1,
        condition_on_previous_text=False, vad_filter=True,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


class CoachSink(voice_recv.AudioSink):
    """Collect one speaker's short utterance and send it to the async bot."""

    def __init__(self, submit: Callable[[int, str, bytes], None]) -> None:
        super().__init__()
        self.submit = submit
        self.buffers: dict[int, bytearray] = {}
        self.names: dict[int, str] = {}
        self.timers: dict[int, threading.Timer] = {}
        self.lock = threading.Lock()
        self.pcm_bytes = 0
        self.completed_segments = 0

    def wants_opus(self) -> bool:
        return False

    def write(self, user, data: voice_recv.VoiceData) -> None:
        if user is None or user.bot or not data.pcm:
            return
        user_id = user.id
        pcm = data.pcm
        with self.lock:
            self.pcm_bytes += len(pcm)
            timer = self.timers.pop(user_id, None)
            if timer:
                timer.cancel()
            buffer = self.buffers.setdefault(user_id, bytearray())
            buffer.extend(pcm)
            self.names[user_id] = user.display_name
            if len(buffer) >= 48000 * 2 * 2 * 12:
                self._finish_locked(user_id)

    @voice_recv.AudioSink.listener()
    def on_voice_member_speaking_stop(self, member) -> None:
        with self.lock:
            if member.id not in self.buffers:
                return
            timer = threading.Timer(0.35, self._finish, args=(member.id,))
            self.timers[member.id] = timer
            timer.start()

    def _finish(self, user_id: int) -> None:
        with self.lock:
            self._finish_locked(user_id)

    def _finish_locked(self, user_id: int) -> None:
        timer = self.timers.pop(user_id, None)
        if timer:
            timer.cancel()
        pcm = bytes(self.buffers.pop(user_id, b""))
        name = self.names.pop(user_id, "Player")
        if len(pcm) >= 48000 * 2 * 2 // 2 and audioop.rms(pcm, 2) > 150:
            self.completed_segments += 1
            self.submit(user_id, name, pcm)

    def cleanup(self) -> None:
        with self.lock:
            for timer in self.timers.values():
                timer.cancel()
            self.timers.clear()
            self.buffers.clear()
            self.names.clear()
