"""Build champion_mobility.json from Riot's Data Dragon spell text.

Run once per patch: .venv\\Scripts\\python -B build_mobility.py
Keyword matching is a heuristic over spell names and descriptions. It can miss
or over-tag a kit, so the coach treats these tags as possibilities, not facts.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path


DDRAGON_VERSION = "16.19.1"
CHAMPION_LIST = Path(__file__).with_name(f"champions-{DDRAGON_VERSION}.json")
OUTPUT = Path(__file__).with_name("champion_mobility.json")
DETAIL_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion/{id}.json"
MOVEMENT = {
    "dash": r"\bdash(?:es|ed|ing)?\b",
    "leap": r"\bleap(?:s|ed|ing)?\b|\bjump(?:s|ed|ing)?\b",
    "blink": r"\bblink(?:s|ed|ing)?\b|\bteleport(?:s|ed|ing)?\b",
    "charge": r"\bcharg(?:e|es|ed|ing)\b",
    "lunge": r"\blunge(?:s|d)?\b",
}


def classify(text: str) -> list[str]:
    lowered = text.casefold()
    return [label for label, pattern in MOVEMENT.items() if re.search(pattern, lowered)]


def build() -> dict[str, dict]:
    champions = json.loads(CHAMPION_LIST.read_text(encoding="utf-8"))["data"].values()
    result: dict[str, dict] = {}
    for champion in champions:
        url = DETAIL_URL.format(version=DDRAGON_VERSION, id=champion["id"])
        with urllib.request.urlopen(url, timeout=20) as response:
            detail = json.load(response)["data"][champion["id"]]
        spells = {}
        for key, spell in zip("QWER", detail.get("spells", [])):
            tags = classify(f"{spell.get('name', '')} {spell.get('description', '')}")
            if tags:
                spells[key] = tags
        movement = sorted({tag for tags in spells.values() for tag in tags})
        result[champion["name"]] = {"movement": movement, "spells": spells}
    return result


if __name__ == "__main__":
    data = build()
    OUTPUT.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    mobile = sum(1 for entry in data.values() if entry["movement"])
    print(f"Wrote {OUTPUT.name}: {len(data)} champions, {mobile} with movement tags.")
