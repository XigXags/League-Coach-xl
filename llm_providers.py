"""Native async HTTP adapters. No SDK, implicit model choice or raw output logs."""
from __future__ import annotations
import asyncio
import json
import os
import time
from email.utils import parsedate_to_datetime
from dataclasses import dataclass
import aiohttp


@dataclass(frozen=True)
class Generation:
    text: str
    model: str
    usage: dict
    seconds: float
    request_id: str | None = None
    retries: int = 0


async def post_json(url, headers, payload, timeout):
    started = time.monotonic()
    async with asyncio.timeout(timeout):
        async with aiohttp.ClientSession() as session:
            for attempt in range(2):
                async with session.post(url, headers=headers, json=payload, allow_redirects=False) as response:
                    if response.status in {429, 500, 502, 503, 504, 529} and attempt == 0:
                        await response.read()
                        delay = .2
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = max(0, float(retry_after))
                            except ValueError:
                                try:
                                    delay = max(0, parsedate_to_datetime(retry_after).timestamp() - time.time())
                                except (ValueError, TypeError, OverflowError):
                                    pass
                        if delay >= timeout - (time.monotonic() - started):
                            raise RuntimeError("Provider retry exceeds deadline")
                        await asyncio.sleep(delay)
                        continue
                    if response.status != 200:
                        # Response bodies can contain user prompts or credentials; never include them.
                        raise RuntimeError(f"Provider HTTP {response.status}")
                    data = await response.json()
                    if not isinstance(data, dict):
                        raise ValueError("Provider response must be an object")
                    data["_coach_transport"] = {"request_id": response.headers.get("x-request-id") or response.headers.get("request-id"),
                                                 "retries": attempt}
                    return data
    raise RuntimeError("Provider unavailable")


async def generate(profile: dict, system: str, brief: dict) -> Generation:
    started = time.monotonic()
    provider = profile["provider"]
    key = os.getenv(profile.get("api_key_env") or "", "")
    if profile.get("api_key_env") and not key:
        raise ValueError("API key missing")
    model = profile.get("model")
    if not model:
        raise ValueError("Model ID missing")
    user = json.dumps(brief, ensure_ascii=False, allow_nan=False)
    headers = {"Content-Type": "application/json"}
    budget = profile["max_output_tokens"]
    if provider == "openai_responses":
        url = (profile.get("base_url") or "https://api.openai.com/v1").rstrip("/") + "/responses"
        headers["Authorization"] = f"Bearer {key}"
        payload = {"model": model, "instructions": system, "input": user,
                   "max_output_tokens": budget, "store": False}
    elif provider == "anthropic_messages":
        url = (profile.get("base_url") or "https://api.anthropic.com/v1").rstrip("/") + "/messages"
        headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        payload = {"model": model, "system": system, "max_tokens": budget,
                   "messages": [{"role": "user", "content": user}]}
    elif provider == "chat_completions":
        url = profile["base_url"].rstrip("/") + "/chat/completions"
        if key:
            headers["Authorization"] = f"Bearer {key}"
        payload = {"model": model, "max_tokens": budget,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    else:
        raise ValueError("Profile does not generate text")
    data = await post_json(url, headers, payload, profile["timeout_seconds"])
    if provider == "openai_responses":
        if data.get("status") != "completed":
            raise ValueError("Incomplete or refused generation")
        blocks = [part for item in data.get("output", []) if item.get("type") == "message"
                  for part in item.get("content", [])]
        if any(part.get("type") == "refusal" for part in blocks):
            raise ValueError("Refused generation")
        text = " ".join(part["text"] for part in blocks if part.get("type") == "output_text")
    elif provider == "anthropic_messages":
        if data.get("stop_reason") not in {"end_turn", "stop_sequence"}:
            raise ValueError("Incomplete or refused generation")
        text = " ".join(part["text"] for part in data.get("content", []) if part.get("type") == "text")
    else:
        choice = data["choices"][0]
        if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
            raise ValueError("Incomplete or refused generation")
        text = choice["message"]["content"]
    if not isinstance(text, str) or not text.strip() or len(text) > 3000:
        raise ValueError("Empty or oversized generation")
    if not isinstance(data.get("model"), str) or not data["model"]:
        raise ValueError("Resolved model missing")
    usage = data.get("usage", {})
    if not isinstance(usage, dict):
        raise ValueError("Malformed usage metadata")
    metadata = data.get("_coach_transport", {})
    return Generation(text.strip(), data["model"], usage, time.monotonic() - started,
                      metadata.get("request_id"), metadata.get("retries", 0))
