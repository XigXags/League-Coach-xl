import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import credentials
from credentials import load_discord_token, load_env, load_jev_key

ROOT = Path(__file__).parent


class EnvFileTests(unittest.TestCase):
    def env_file(self, text: str) -> Path:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / ".env"
        path.write_text(text, encoding="utf-8")
        return path

    def test_values_quotes_comments_and_blanks(self):
        path = self.env_file(
            "# comment\n\nDISCORD_BOT_TOKEN=abc.def\nTYPESAFE_API_KEY = \"quoted key\"\n"
            "COACH_VOICE_RATE=+30%  # inline note\nexport COACH_MOCK=1\nRIOT_API_KEY=\nnot a setting\n")
        with patch.dict(os.environ, {}, clear=True):
            load_env(path)
            self.assertEqual(dict(os.environ), {
                "DISCORD_BOT_TOKEN": "abc.def", "TYPESAFE_API_KEY": "quoted key",
                "COACH_VOICE_RATE": "+30%", "COACH_MOCK": "1"})

    def test_existing_environment_wins(self):
        path = self.env_file("DISCORD_BOT_TOKEN=from-file\n")
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "from-shell"}, clear=True):
            load_env(path)
            self.assertEqual(os.environ["DISCORD_BOT_TOKEN"], "from-shell")

    def test_missing_file_is_not_an_error(self):
        with patch.dict(os.environ, {}, clear=True):
            load_env(ROOT / "no-such-dir" / ".env")
            self.assertEqual(dict(os.environ), {})

    def test_loaders_read_the_env_file(self):
        path = self.env_file("DISCORD_BOT_TOKEN=token-value\nTYPESAFE_API_KEY=jev-value\n")
        with patch.dict(os.environ, {}, clear=True), patch.object(credentials, "ENV_FILE", path):
            self.assertEqual(load_discord_token(), "token-value")
            self.assertEqual(load_jev_key(), "jev-value")

    def test_missing_token_names_the_env_file_and_missing_jev_key_is_empty(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(credentials, "ENV_FILE", ROOT / "no-such.env"):
            with self.assertRaisesRegex(RuntimeError, r"\.env"):
                load_discord_token()
            self.assertEqual(load_jev_key(), "")


class ExampleFileTests(unittest.TestCase):
    def test_example_ships_no_values_for_secrets(self):
        with patch.dict(os.environ, {}, clear=True):
            load_env(ROOT / ".env.example")
            self.assertEqual(dict(os.environ), {})

    def test_env_is_ignored_and_example_is_not(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".env", ignored)
        self.assertNotIn(".env.example", ignored)


if __name__ == "__main__":
    unittest.main()
