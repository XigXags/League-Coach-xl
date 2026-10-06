"""Patch-pinned champion tags from Riot Data Dragon.

Tags are broad archetypes, not a matchup or lane-priority oracle.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


DATA_FILE = Path(__file__).with_name("champions-16.19.1.json")


def _normal(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


@lru_cache(maxsize=1)
def _tags() -> dict[str, list[str]]:
    try:
        with DATA_FILE.open(encoding="utf-8") as handle:
            champions = json.load(handle)["data"].values()
        return {_normal(champion["name"]): champion.get("tags", []) for champion in champions}
    except (OSError, ValueError, KeyError):
        return {}


def champion_tags(name: str | None) -> list[str]:
    return _tags().get(_normal(name or ""), [])


def known_champions() -> frozenset[str]:
    """Normalised champion names in the data file; empty when the file did not load."""
    return frozenset(_tags())


MOBILITY_FILE = Path(__file__).with_name("champion_mobility.json")


@lru_cache(maxsize=1)
def _mobility() -> dict[str, list[str]]:
    """Movement tags from build_mobility.py: heuristic possibilities, not observed positions."""
    try:
        with MOBILITY_FILE.open(encoding="utf-8") as handle:
            entries = json.load(handle)
        return {_normal(name): entry.get("movement", []) for name, entry in entries.items()}
    except (OSError, ValueError, AttributeError):
        return {}


def champion_movement(name: str | None) -> list[str]:
    return _mobility().get(_normal(name or ""), [])


KITS_FILE = Path(__file__).with_name("champion_kits.json")
KIT_SENTENCE_LIMIT = 80


@lru_cache(maxsize=1)
def _kits() -> dict[str, dict]:
    """Kit descriptions from build_champion_kits.py: what a champion can do, never what is ready now."""
    try:
        with KITS_FILE.open(encoding="utf-8") as handle:
            entries = json.load(handle)
        return {_normal(name): {**entry, "champion": name} for name, entry in entries.items()}
    except (OSError, ValueError, AttributeError, TypeError):
        return {}


def champion_kit(name: str | None) -> dict | None:
    return _kits().get(_normal(name or ""))


def _first_sentence(text: str, limit: int = KIT_SENTENCE_LIMIT) -> str:
    # "Dr. Mundo ..." is one sentence: the title's full stop does not end it.
    sentence = re.split(r"(?<!Dr\.)(?<=[.!?])\s+", str(text or "").strip(), maxsplit=1)[0]
    if not sentence:
        return ""
    if len(sentence) > limit:
        cut = sentence[:limit - 3]
        return (cut[:cut.rfind(" ")] if " " in cut else cut).rstrip(" ,;:.") + "..."
    return sentence if sentence[-1] in ".!?" else f"{sentence}."


def _kit_text(kit: dict, texts: int) -> str:
    """The summary line with the first `texts` abilities (passive, Q, W, E, R) described and the rest named."""
    resource = str(kit.get("resource") or "").strip()
    resource = "no resource" if resource.casefold() in ("", "none") else resource
    tags = ", ".join(kit["tags"]) if isinstance(kit.get("tags"), list) else ""
    parts = [f"{kit['champion']} ({'; '.join(part for part in (tags, resource) if part)})."]
    spells = kit.get("spells") or {}
    abilities = [("Passive", kit.get("passive") or {})] + [(key, spells[key]) for key in "QWER" if key in spells]
    for index, (label, ability) in enumerate(abilities):
        name = str(ability.get("name") or "").strip()
        text = _first_sentence(ability.get("text", "")) if index < texts else ""
        if name or text:
            parts.append(f"{label} {name}".rstrip() + (f": {text}" if text else "."))
    return " ".join(parts)


def kit_summary(name: str | None, limit: int = 420, *, names_only: bool = False) -> str:
    """One line on a champion's kit for the ranker; "" when the kit file or the champion is missing."""
    kit = champion_kit(name)
    if not kit:
        return ""
    try:
        # Over the limit, ability texts are dropped from R backwards and the names stay.
        for texts in range(0 if names_only else 5, -1, -1):
            line = _kit_text(kit, texts)
            if len(line) <= limit:
                return line
        return line[:limit]
    except (AttributeError, TypeError, KeyError):
        return ""   # a hand-edited entry of the wrong shape is no kit, not a crash
