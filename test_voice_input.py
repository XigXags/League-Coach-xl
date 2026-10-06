import unittest
from types import SimpleNamespace

from voice_input import CoachSink, question_after_wake


class VoiceInputTests(unittest.TestCase):
    def test_wake_word_extracts_question(self):
        self.assertEqual(question_after_wake("Hey League Coach, should we contest dragon?"),
                         "should we contest dragon")
        self.assertIsNone(question_after_wake("Should we contest dragon?"))
        self.assertIsNone(question_after_wake("Coach."))

    def test_sink_collects_one_user_and_ignores_bot(self):
        received = []
        sink = CoachSink(lambda user_id, name, pcm: received.append((user_id, name, pcm)))
        pcm = b"\x00\x10" * 48000 * 2
        sink.write(SimpleNamespace(id=1, bot=False, display_name="Player"),
                   SimpleNamespace(pcm=pcm))
        sink.write(SimpleNamespace(id=2, bot=True, display_name="Bot"),
                   SimpleNamespace(pcm=pcm))
        sink._finish(1)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][:2], (1, "Player"))
        self.assertEqual(received[0][2], pcm)
        sink.cleanup()


if __name__ == "__main__":
    unittest.main()
