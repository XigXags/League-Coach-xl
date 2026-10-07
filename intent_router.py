"""LLM-backed question router with a closed set of local retrieval tools."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

TOOLS = {
    "active_champion": "The champion controlled by the local player.",
    "visible_minimap": "Champion icons confidently visible in the latest minimap frame.",
    "match_roster": "Champion rosters for both teams.",
    "game_clock": "Current in-game time.",
    "scoreboard": "Team kills and currently alive player counts.",
    "active_status": "The local player's level, health percentage, and unspent gold.",
    "team_gold_estimate": "A low-confidence team gold estimate derived from visible score statistics.",
}

ROUTE_SCHEMA = {
    "name": "league_coach_route",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["observe", "estimate", "decision", "clarify"]},
            "tools": {
                "type": "array",
                "items": {"type": "string", "enum": sorted(TOOLS)},
                "uniqueItems": True,
            },
            "clarification": {"type": "string"},
        },
        "required": ["kind", "tools", "clarification"],
        "additionalProperties": False,
    },
}

@dataclass(frozen=True)
class Route:
    kind: str
    tools: tuple[str, ...] = ()
    clarification: str = ""
    source: str = "llm"


class IntentRouterError(RuntimeError):
    """A question could not be authoritatively classified by the configured intent model."""


def _log(event: str, **details: object) -> None:
    stamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
    suffix = " ".join(f"{name}={value}" for name, value in details.items()
                      if value is not None and value != "")
    print(f"[{stamp}] [intent] {event}" + (f" {suffix}" if suffix else ""), flush=True)


def _api_key() -> str:
    key = os.getenv("COACH_ROUTER_API_KEY", "").strip()
    file_name = os.getenv("COACH_ROUTER_API_KEY_FILE", "").strip()
    if not key and file_name:
        key = Path(file_name).read_text(encoding="utf-8-sig").strip()
    return key


def _json_content(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("router response is not an object")
    return value


def _validate(value: dict) -> Route:
    kind = str(value.get("kind", "")).strip().casefold()
    if kind not in {"observe", "estimate", "decision", "clarify"}:
        raise ValueError("unsupported route kind")
    tools = tuple(dict.fromkeys(str(tool) for tool in value.get("tools", [])))
    if any(tool not in TOOLS for tool in tools):
        raise ValueError("router selected an unknown tool")
    if kind in {"observe", "estimate"} and not tools:
        raise ValueError("local route selected no tools")
    if kind in {"decision", "clarify"} and tools:
        raise ValueError("non-local route selected retrieval tools")
    clarification = str(value.get("clarification", "")).strip()
    if kind == "clarify" and not clarification:
        clarification = "Do you mean the match roster, or champions currently visible on the minimap?"
    return Route(kind, tools, clarification, source="llm")


def route_question(question: str, *, timeout: float = 8.0) -> Route:
    """Require the configured OpenAI model to choose retrieval tools.

    The model receives no game state and cannot name arbitrary tools. Failure raises IntentRouterError;
    callers must not silently bypass this layer or invoke the prediction engine.
    """
    url = os.getenv("COACH_ROUTER_URL", "").strip()
    model = os.getenv("COACH_ROUTER_MODEL", "").strip()
    request_id = uuid.uuid4().hex[:8]
    if not url or not model:
        missing = ",".join(name for name, value in (
            ("COACH_ROUTER_URL", url), ("COACH_ROUTER_MODEL", model)
        ) if not value)
        _log("configuration_failed", request_id=request_id, missing=missing)
        raise IntentRouterError(f"missing router configuration: {missing}")
    system = (
        "You route League of Legends player questions. Return exactly one JSON object with keys "
        "kind, tools, and clarification. kind is observe, estimate, decision, or clarify. "
        "Use decision only when the player asks for a recommendation, prediction, ranking, or future play. "
        "Use observe for direct facts, estimate for explicitly derived uncertain quantities, and clarify "
        "when the requested fact is ambiguous. Choose only from this tool catalog: "
        f"{json.dumps(TOOLS, sort_keys=True)}. Do not answer the question and do not invent tools."
    )
    payload = {
        "model": model,
        "reasoning_effort": "none",
        "max_completion_tokens": 128,
        "store": False,
        "response_format": {"type": "json_schema", "json_schema": ROUTE_SCHEMA},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
    }
    started = time.perf_counter()
    _log("request_start", request_id=request_id, provider="openai", model=model,
         endpoint=urlsplit(url).netloc, timeout_seconds=timeout, question_chars=len(question))
    try:
        headers = {"Content-Type": "application/json"}
        key = _api_key()
        if not key:
            raise ValueError("OpenAI API key is empty")
        headers["Authorization"] = f"Bearer {key}"
        _log("request_send", request_id=request_id, schema=ROUTE_SCHEMA["name"],
             allowed_tools=len(TOOLS), max_completion_tokens=payload["max_completion_tokens"])
        request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            response_headers = getattr(response, "headers", None)
            openai_request_id = response_headers.get("x-request-id") if response_headers else None
            body = json.load(response)
        usage = body.get("usage", {}) if isinstance(body, dict) else {}
        _log("response_received", request_id=request_id, status=status,
             openai_request_id=openai_request_id,
             latency_ms=round((time.perf_counter() - started) * 1000),
             prompt_tokens=usage.get("prompt_tokens"),
             completion_tokens=usage.get("completion_tokens"), total_tokens=usage.get("total_tokens"))
        content = body["choices"][0]["message"]["content"]
        route = _validate(_json_content(content))
        _log("classification_complete", request_id=request_id, kind=route.kind,
             tools=",".join(route.tools) or "none", clarification=bool(route.clarification))
        return route
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        status = getattr(error, "code", None)
        reason = getattr(error, "reason", None)
        _log("request_failed", request_id=request_id, error=type(error).__name__, status=status,
             reason=str(reason or error).replace("\r", " ").replace("\n", " ")[:160],
             latency_ms=round((time.perf_counter() - started) * 1000), action="blocked_before_jev")
        diagnostic = type(error).__name__ + (f" HTTP {status}" if status is not None else "")
        raise IntentRouterError(f"OpenAI intent classification failed ({diagnostic})") from error
