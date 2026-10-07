"""LLM-backed question router with a closed set of local retrieval tools."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from local_questions import local_intent


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

LOCAL_INTENT_TO_TOOL = {
    "minimap": "visible_minimap",
    "clock": "game_clock",
    "roster": "match_roster",
    "score": "scoreboard",
    "self": "active_status",
    "champion": "active_champion",
    "gold": "team_gold_estimate",
}


@dataclass(frozen=True)
class Route:
    kind: str
    tools: tuple[str, ...] = ()
    clarification: str = ""
    source: str = "fallback"


def _fallback(question: str) -> Route:
    intent = local_intent(question)
    if intent:
        return Route("estimate" if intent == "gold" else "observe",
                     (LOCAL_INTENT_TO_TOOL[intent],), source="rules")
    return Route("decision", source="rules")


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
    """Ask a configured OpenAI-compatible chat model to choose retrieval tools.

    The model receives no game state and cannot name arbitrary tools. Invalid output or an unavailable
    router falls back to the conservative rule router.
    """
    url = os.getenv("COACH_ROUTER_URL", "").strip()
    model = os.getenv("COACH_ROUTER_MODEL", "").strip()
    if not url or not model:
        return _fallback(question)
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
    try:
        headers = {"Content-Type": "application/json"}
        key = _api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
        content = body["choices"][0]["message"]["content"]
        return _validate(_json_content(content))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _fallback(question)
