import unittest
from pathlib import Path
from unittest.mock import patch

import bot as coach_bot
from coach import Reply


class SpeechFeedTests(unittest.TestCase):
    def test_read_returns_pushed_audio_in_order_until_finished(self):
        feed = coach_bot.SpeechFeed()
        feed.push(b"abc")
        feed.push(b"def")
        feed.finish()
        self.assertEqual(feed.read(4), b"abc")
        self.assertEqual(feed.read(4), b"def")
        self.assertEqual(feed.read(4), b"")
        self.assertEqual(feed.bytes_fed, 6)


class SpokenScriptTests(unittest.TestCase):
    def test_reply_supplies_its_own_spoken_line(self):
        reply = Reply("Game read (live game): x.\n**A** — r\nOtherwise: **B** — r\nYour call.")
        reply.spoken = "A. Or, B."
        self.assertEqual(coach_bot.spoken_script(reply), "A. Or, B.")

    def test_plain_text_falls_back_to_the_chat_labels(self):
        spoken = coach_bot.spoken_script("Game read (live game): x.\n**A** — r\nOtherwise: **B** — r\nYour call.")
        self.assertTrue(spoken)
        self.assertNotIn("**", spoken)
        self.assertIn("A", spoken)
        self.assertIn("B", spoken)

    def test_one_line_status_message_is_spoken(self):
        self.assertEqual(coach_bot.spoken_script("I can't read a live League match."),
                         "I can't read a live League match.")

    def test_one_line_status_message_is_capped_for_voice(self):
        self.assertLessEqual(len(coach_bot.spoken_script("word " * 100).split()), 80)


class SpeechStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_neural_chunks_reach_the_feed_as_they_arrive(self):
        class FakeCommunicate:
            def __init__(self, *args, **kwargs):
                pass

            async def stream(self):
                yield {"type": "WordBoundary", "data": None}
                yield {"type": "audio", "data": b"one"}
                yield {"type": "audio", "data": b"two"}

        feed = coach_bot.SpeechFeed()
        with patch.object(coach_bot.edge_tts, "Communicate", FakeCommunicate):
            await coach_bot.stream_speech("Hello.", feed)
        self.assertEqual(feed.read(10), b"one")
        self.assertEqual(feed.read(10), b"two")
        self.assertEqual(feed.read(10), b"")

    async def test_falls_back_to_windows_speech_when_no_neural_audio_arrives(self):
        class BrokenCommunicate:
            def __init__(self, *args, **kwargs):
                pass

            async def stream(self):
                raise OSError("offline")
                yield  # pragma: no cover

        def fake_windows(text: str, path: Path) -> None:
            path.write_bytes(b"RIFFwav")

        feed = coach_bot.SpeechFeed()
        with patch.object(coach_bot.edge_tts, "Communicate", BrokenCommunicate), \
                patch.object(coach_bot, "synthesize_windows", fake_windows):
            await coach_bot.stream_speech("Hello.", feed)
        self.assertEqual(feed.read(100), b"RIFFwav")
        self.assertEqual(feed.read(100), b"")


if __name__ == "__main__":
    unittest.main()
