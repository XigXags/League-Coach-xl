"""Build champion_kits.json from Riot's Data Dragon ability descriptions.

Run once per patch: .venv\\Scripts\\python -B build_champion_kits.py
Only names and Riot's own short descriptions are kept: no cooldowns, ranges or costs.
A kit says what a champion can do, never what is ready, stacked or happening in a match.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from build_mobility import CHAMPION_LIST, DDRAGON_VERSION, DETAIL_URL


OUTPUT = Path(__file__).with_name("champion_kits.json")


def clean(text: str, limit: int = 220) -> str:
    """Plain text from Data Dragon markup, cut at the last sentence end that fits."""
    text = re.sub(r"<br\s*/?>", " ", str(text or ""), flags=re.IGNORECASE)
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\{\{.*?\}\}", "", text)
    text = re.sub(r"%i:\w+%", "", text)   # icon placeholders such as %i:OnHit%
    text = " ".join(html.unescape(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # "Dr. Mundo" is not a sentence end.
    end = max((found.start() for found in re.finditer(r"(?<!Dr)[.!?] ", cut)), default=-1)
    if end > 0:
        return cut[:end + 1]
    return cut[:cut.rfind(" ")] if " " in cut else cut


def fetch(champion_id: str) -> dict:
    """One champion's detail file; one retry."""
    url = DETAIL_URL.format(version=DDRAGON_VERSION, id=champion_id)
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                return json.load(response)["data"][champion_id]
        except (OSError, ValueError, KeyError):
            if attempt:
                raise
    raise OSError(champion_id)


def kit(detail: dict) -> dict:
    def ability(entry: dict) -> dict[str, str]:
        # Text comes from "description"; "tooltip" carries the numbers this file leaves out.
        return {"name": clean(entry.get("name", "")), "text": clean(entry.get("description", ""))}

    return {
        "tags": list(detail.get("tags") or []),
        "resource": detail.get("partype", ""),
        "passive": ability(detail.get("passive") or {}),
        "spells": {key: ability(spell) for key, spell in zip("QWER", detail.get("spells") or [])},
    }


def build() -> dict[str, dict]:
    champions = json.loads(CHAMPION_LIST.read_text(encoding="utf-8"))["data"].values()
    return {champion["name"]: kit(fetch(champion["id"])) for champion in champions}


if __name__ == "__main__":
    try:
        data = build()
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f"Nothing written: a champion could not be fetched ({type(exc).__name__}: {exc}).")
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, OUTPUT)
    print(f"Wrote {OUTPUT.name}: {len(data)} champions from Data Dragon {DDRAGON_VERSION}.")
