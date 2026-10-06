"""Smoke-test one live coach reply without printing API keys."""

from coach import coach

print(coach("What's the next play?", "balanced"))
