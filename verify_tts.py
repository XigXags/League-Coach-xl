"""Check the coach's lower male neural voice is available."""

import asyncio
import io
import tempfile
from pathlib import Path

import discord
import edge_tts
import imageio_ffmpeg


async def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "voice.mp3"
        await edge_tts.Communicate(
            "Option one, take Dragon through bot and mid.",
            voice="en-US-ChristopherNeural", rate="+5%", pitch="-5Hz", volume="+8%",
        ).save(str(path))
        print("Lower male voice ready:", path.stat().st_size > 1000)
        source = discord.FFmpegOpusAudio(io.BytesIO(path.read_bytes()), pipe=True,
                                         executable=imageio_ffmpeg.get_ffmpeg_exe())
        try:
            print("In-memory playback ready:", bool(source.read()))
        finally:
            source.cleanup()


asyncio.run(main())
