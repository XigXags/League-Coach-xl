"""Validated, non-secret provider profiles and atomic per-server selections."""
from __future__ import annotations

import copy
import json
import math
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).parent
PROVIDERS = {"builtin", "openai_responses", "anthropic_messages", "chat_completions"}


class Profiles:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.revision: dict[int, int] = {}
        self.reload()
        path = root / "model_selections.json"
        try:
            self.selections = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(self.selections, dict):
                raise ValueError("Selections must be an object")
        except FileNotFoundError:
            self.selections = {}

    def reload(self):
        path = self.root / "coach_models.json"
        if not path.exists():
            path = self.root / "jev_implementation" / "profiles.example.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("profiles"), dict):
            raise ValueError("Invalid model config schema")
        profiles = data["profiles"]
        jev = data.get("jev", {})
        if (jev.get("model") != "jev-1.13.0" or jev.get("question_revision") != "coach-staged-v1" or
                jev.get("credential_source") != "existing_jev_loader"):
            raise ValueError("Jev model/question revision must match this evaluated wire contract")
        for name, profile in profiles.items():
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", name):
                raise ValueError("Invalid profile ID")
            if profile.get("provider") not in PROVIDERS or type(profile.get("enabled")) is not bool:
                raise ValueError(f"Invalid provider/enabled: {name}")
            for field, low, high in (("timeout_seconds", .1, 60), ("max_output_tokens", 16, 8192)):
                value = profile.get(field)
                if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                    raise ValueError(f"Invalid {field}: {name}")
            if type(profile["max_output_tokens"]) is not int:
                raise ValueError("max_output_tokens must be an integer")
            if profile.get("model") and profile.get("model_env"):
                raise ValueError(f"Use model OR model_env: {name}")
            if profile.get("model") is not None and (not isinstance(profile["model"], str) or not profile["model"].strip()):
                raise ValueError(f"Invalid model ID: {name}")
            for field in ("model_env", "api_key_env"):
                if profile.get(field) and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", profile[field]):
                    raise ValueError(f"Invalid environment reference: {name}")
            url = profile.get("base_url")
            if url:
                parsed = urlsplit(url)
                if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
                    raise ValueError(f"Invalid endpoint: {name}")
                if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}):
                    raise ValueError("Remote endpoints require HTTPS")
            if profile.get("provider") == "chat_completions" and not url:
                raise ValueError(f"Explicit endpoint required: {name}")
            visited = {name}
            target = profile.get("fallback_profile")
            while target:
                if target in visited or target not in profiles or not profiles[target].get("enabled"):
                    raise ValueError(f"Invalid fallback chain: {name}")
                visited.add(target)
                target = profiles[target].get("fallback_profile")
        default = data.get("default_profile")
        if default not in profiles or not profiles[default]["enabled"]:
            raise ValueError("Default profile must be enabled")
        deadline = data.get("turn_deadline_seconds", 10)
        if type(deadline) not in (int, float) or not math.isfinite(deadline) or not 1 <= deadline <= 60:
            raise ValueError("Invalid turn deadline")
        self.data = data

    def frozen(self, name: str) -> dict:
        if name not in self.data["profiles"]:
            raise ValueError("Unknown model profile")
        profile = copy.deepcopy(self.data["profiles"][name])
        profile["id"] = name
        profile["model"] = profile.get("model") or os.getenv(profile.get("model_env") or "", "") or None
        return profile

    def frozen_chain(self, name: str) -> list[dict]:
        chain = []
        while name:
            profile = self.frozen(name)
            chain.append(profile)
            name = profile.get("fallback_profile")
        return chain

    def readiness(self, name: str) -> str:
        profile = self.frozen(name)
        if not profile["enabled"]:
            return "disabled"
        if profile["provider"] == "builtin":
            return "ready"
        if not profile["model"]:
            return "model ID missing"
        if profile.get("api_key_env") and not os.getenv(profile["api_key_env"]):
            return "API key missing"
        return "ready"

    def selected(self, guild_id: int) -> str:
        name = self.selections.get(str(guild_id), self.data["default_profile"])
        return name if name in self.data["profiles"] else self.data["default_profile"]

    def select(self, guild_id: int, name: str | None):
        name = name or self.data["default_profile"]
        if self.readiness(name) != "ready":
            raise ValueError(f"{name}: {self.readiness(name)}")
        updated = {**self.selections, str(guild_id): name}
        target = self.root / "model_selections.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(updated, indent=2), encoding="utf-8")
        os.replace(temporary, target)
        self.selections = updated
        self.revision[guild_id] = self.revision.get(guild_id, 0) + 1
        return name
