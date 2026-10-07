"""Load settings and secrets from the project's single .env file without logging them."""

from __future__ import annotations

import os
from pathlib import Path


ENV_FILE = Path(__file__).with_name(".env")


def load_env(path: Path | None = None) -> None:
    """Copy KEY=VALUE lines from .env into the process environment.

    Variables already set in the environment win, and blank values are skipped, so an untouched
    line copied from .env.example behaves as if it were absent.
    """
    try:
        lines = (path or ENV_FILE).read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        if name and value:
            os.environ.setdefault(name, value)


def load_discord_token() -> str:
    load_env()
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Discord token not found. Set DISCORD_BOT_TOKEN in .env (see .env.example).")
    if any(c.isspace() for c in token):
        raise RuntimeError("DISCORD_BOT_TOKEN must be one token on one line.")
    return token


def load_jev_key() -> str:
    load_env()
    key = os.getenv("TYPESAFE_API_KEY", "").strip()
    if any(c.isspace() for c in key):
        raise RuntimeError("TYPESAFE_API_KEY must be one key on one line.")
    return key
