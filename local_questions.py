"""Deterministic answers to factual live-game questions that do not need Jev."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any


MINIMAP_PATTERNS = (
    re.compile(r"\b(?:can|could|do) you (?:see|read|view)\b.*\bmini\s*map\b", re.I),
    re.compile(r"\bwho(?:'s| is| do you see| can you see).*\bmini\s*map\b", re.I),
    re.compile(r"\b(?:who|what).*\b(?:visible|showing|shown|on)\b.*\bmini\s*map\b", re.I),
    re.compile(r"\bmini\s*map\b.*\b(?:who|visible|showing|shown|see)\b", re.I),
)


def local_intent(question: str) -> str | None:
    """Return a supported factual intent; tactical questions deliberately fall through."""
    text = " ".join(question.casefold().replace("’", "'").split())
    if re.search(r"\b(?:should|attack|target|gank|fight|kill|focus|chase|contest)\b", text):
        return None
    if any(pattern.search(text) for pattern in MINIMAP_PATTERNS):
        return "minimap"
    if re.search(r"\b(?:what|which) champion am i (?:playing|on)\b", text):
        return "champion"
    if re.search(r"\b(?:estimated?|roughly|about).*\bgold (?:difference|diff|lead)\b", text) or \
            re.search(r"\bhow (?:far )?(?:ahead|behind).*\bgold\b", text):
        return "gold"
    if re.search(r"\b(?:what(?:'s| is) (?:the )?(?:game )?time|how long (?:has|have) .*game)", text):
        return "clock"
    if re.search(r"\b(?:who(?:'s| is) in (?:this|the) game|team comps?|champion roster)\b", text):
        return "roster"
    if re.search(r"\b(?:what(?:'s| is) (?:the )?(?:kill )?score|how many kills)\b", text):
        return "score"
    if re.search(r"\b(?:my|do i have)\b.*\b(?:health|hp|gold|level)\b", text):
        return "self"
    return None


def _clock(seconds: Any) -> str:
    try:
        total = max(0, round(float(seconds)))
    except (TypeError, ValueError):
        total = 0
    return f"{total // 60}:{total % 60:02d}"


def _position(x: float, y: float) -> str:
    vertical = "top" if y < 0.38 else "bottom" if y > 0.62 else "middle"
    horizontal = "left" if x < 0.38 else "right" if x > 0.62 else "center"
    if vertical == "middle" and horizontal == "center":
        return "near center"
    if vertical == "middle":
        return f"near {horizontal}"
    if horizontal == "center":
        return f"near {vertical}"
    return f"near {vertical}-{horizontal}"


def _minimap_answer(state: dict[str, Any] | None, sightings: Sequence[Any] | None,
                    *, enabled: bool, error: Exception | None) -> str:
    if not enabled:
        return "Minimap reading is off, so I can't say who is visible."
    if error is not None:
        return f"The minimap reader is unavailable ({type(error).__name__})."
    if not sightings:
        return ("I don't have a fresh confident minimap sighting. "
                "That does not mean nobody is visible.")

    our_team = state.get("our_team") if state else None
    # Keep one confident result per champion if ring detection briefly duplicates an icon.
    named: dict[tuple[str, str], Any] = {}
    unclear: dict[str, int] = {}
    for sighting in sightings:
        side = ("ally" if sighting.team == our_team else "enemy") if our_team else sighting.team.lower()
        if sighting.champion:
            key = (side, sighting.champion)
            previous = named.get(key)
            if previous is None or sighting.score > previous.score:
                named[key] = sighting
        else:
            unclear[side] = unclear.get(side, 0) + 1

    descriptions = [
        f"{side} {champion} {_position(sighting.x, sighting.y)}"
        for (side, champion), sighting in sorted(named.items())
    ]
    for side, count in sorted(unclear.items()):
        noun = "icon was" if count == 1 else "icons were"
        descriptions.append(f"{count} other {side} {noun} visible but unclear")
    if not descriptions:
        return ("I saw minimap rings in the latest frame but could not name them confidently. "
                "I won't guess.")
    return "Latest minimap frame: " + "; ".join(descriptions) + "."


def _enemy_team(state: dict[str, Any]) -> str | None:
    return next((team for team in state.get("teams", {}) if team != state.get("our_team")), None)


def answer_local_question(intent: str, state: dict[str, Any] | None,
                          sightings: Sequence[Any] | None = None, *, minimap_enabled: bool = False,
                          minimap_error: Exception | None = None) -> str:
    """Answer one classified intent from local observations only."""
    if intent == "minimap":
        return _minimap_answer(state, sightings, enabled=minimap_enabled, error=minimap_error)
    if not state or not state.get("players"):
        return "I can't read a live League match on this PC right now."
    if intent == "champion":
        me = next((p for p in state["players"] if p.get("name") == state.get("active_player")), {})
        champion = me.get("champion")
        return f"You're playing {champion}." if champion else "I can't identify your champion right now."
    if intent == "clock":
        return f"The game clock is {_clock(state.get('game_time_seconds'))}."
    if intent == "roster":
        ours = [p.get("champion") for p in state["players"] if p.get("team") == state.get("our_team")]
        enemy = _enemy_team(state)
        theirs = [p.get("champion") for p in state["players"] if p.get("team") == enemy]
        return f"Allies: {', '.join(filter(None, ours))}. Enemies: {', '.join(filter(None, theirs))}."
    if intent == "score":
        ours = state.get("teams", {}).get(state.get("our_team"), {})
        theirs = state.get("teams", {}).get(_enemy_team(state), {})
        return (f"Kills are {ours.get('kills', 0)} to {theirs.get('kills', 0)}. "
                f"Alive now: {ours.get('alive', 0)} allies and {theirs.get('alive', 0)} enemies.")
    if intent == "self":
        me = next((p for p in state["players"] if p.get("name") == state.get("active_player")), {})
        facts = []
        if me.get("level") is not None:
            facts.append(f"level {me['level']}")
        if state.get("active_health_percent") is not None:
            facts.append(f"{state['active_health_percent']} percent health")
        if state.get("active_gold") is not None:
            facts.append(f"{state['active_gold']} unspent gold")
        return "You have " + ", ".join(facts) + "." if facts else "Your current status is unavailable."
    if intent == "gold":
        ours = [p for p in state["players"] if p.get("team") == state.get("our_team")]
        theirs = [p for p in state["players"] if p.get("team") == _enemy_team(state)]

        def estimate(players: Sequence[dict[str, Any]]) -> float:
            # A deliberately rough score-derived estimate. Passive and starting gold cancel for equal
            # team sizes; plates, bounties, objectives, support income and sold items remain unknown.
            return sum(float(p.get("cs") or 0) * 20 + float(p.get("kills") or 0) * 300
                       + float(p.get("assists") or 0) * 75 for p in players)

        difference = round(estimate(ours) - estimate(theirs), -2)
        direction = "ahead" if difference >= 0 else "behind"
        return (f"Low-confidence estimate: your team is about {abs(int(difference)):,} gold {direction}. "
                "This uses score-derived averages for CS, kills, and assists; it excludes plates, "
                "bounties, objectives, support income, sold items, and unknown unspent gold.")
    raise ValueError(f"Unsupported local intent: {intent}")


TOOL_TO_INTENT = {
    "active_champion": "champion",
    "visible_minimap": "minimap",
    "match_roster": "roster",
    "game_clock": "clock",
    "scoreboard": "score",
    "active_status": "self",
    "team_gold_estimate": "gold",
}


def answer_tools(tools: Sequence[str], state: dict[str, Any] | None,
                 sightings: Sequence[Any] | None = None, *, minimap_enabled: bool = False,
                 minimap_error: Exception | None = None) -> str:
    """Execute validated retrieval tools and combine their factual outputs."""
    answers = [answer_local_question(
        TOOL_TO_INTENT[tool], state, sightings,
        minimap_enabled=minimap_enabled, minimap_error=minimap_error,
    ) for tool in tools]
    return " ".join(dict.fromkeys(answers))
