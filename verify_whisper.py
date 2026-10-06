"""Preload the local speech model and verify it can initialize on this PC."""

from faster_whisper import WhisperModel

model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
print("Local Whisper model ready")
