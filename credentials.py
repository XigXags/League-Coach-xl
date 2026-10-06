"""Read the locally stored Discord bot token without logging it."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_TOKEN_FILE = Path.home() / "OneDrive" / "Desktop" / "DISCORD_BOT_TOKEN.txt"
DEFAULT_JEV_FILE = Path.home() / "OneDrive" / "Desktop" / "LaugeCoach_APIkey.txt"
PROJECT_JEV_FILE = Path(__file__).with_name("TYPESAFE_API_KEY.txt")


def load_discord_token() -> str:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        token_file = Path(os.getenv("DISCORD_BOT_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)))
        try:
            token = token_file.read_text(encoding="utf-8-sig").strip()
        except FileNotFoundError:
            raise RuntimeError("Discord token not found. Set DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN_FILE.") from None
    if token.startswith("DISCORD_BOT_TOKEN="):
        token = token.split("=", 1)[1].strip().strip('"').strip("'")
    if not token or any(c.isspace() for c in token):
        raise RuntimeError("Discord token file must contain one token on one line.")
    return token


def load_jev_key() -> str:
    key = os.getenv("TYPESAFE_API_KEY", "").strip()
    if not key:
        for candidate in (DEFAULT_JEV_FILE, PROJECT_JEV_FILE):
            if candidate.is_file():
                key = candidate.read_text(encoding="utf-8-sig").strip()
                break
    if key.startswith("TYPESAFE_API_KEY="):
        key = key.split("=", 1)[1].strip().strip('"').strip("'")
    if any(c.isspace() for c in key):
        raise RuntimeError("Jev key file must contain one key on one line.")
    return key
