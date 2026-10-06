"""Local speech-to-text smoke test using the available Windows synthesizer."""

import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg

from bot import synthesize_windows
from voice_input import question_after_wake, transcribe_pcm

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "coach.wav"
    synthesize_windows("Coach, should we contest dragon?", path)
    pcm = subprocess.check_output([
        imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(path),
        "-f", "s16le", "-ac", "2", "-ar", "48000", "pipe:1",
    ])
    transcript = transcribe_pcm(pcm)
    print("Transcript:", transcript)
    print("Wake question:", question_after_wake(transcript))
