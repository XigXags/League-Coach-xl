"""Validate answer-library files: python _validate.py [file.jsonl ...] (no args = every file here).

One JSON object per line. The coach filters entries by role, champion and phase, Jev picks the
intent from the player's question and then the best-fitting entry, and the coach speaks "say".
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent

INTENTS = {
    "clear_order", "pathing_next", "gank_choice", "invade", "counter_jungle", "track_enemy_jungler",
    "crab_and_level_six", "objective_setup", "objective_trade", "scaling_plan", "recall_and_buy",
    "wave_management", "trading_in_lane", "roam", "dive", "teamfight_role", "lead_conversion",
    "playing_from_behind", "split_push", "vision", "defend_or_give", "late_game_call", "matchup",
    "champion_identity", "power_spike", "plan_status",
}
ROLES = {"top", "jungle", "mid", "bot", "support", "any"}
PHASES = {"early", "lane", "mid", "late", "any"}
ARCHETYPES = {
    "farm_scaling", "early_gank", "engage_tank", "assassin", "skirmisher", "bruiser", "juggernaut",
    "control_mage", "burst_mage", "artillery", "marksman", "hypercarry", "enchanter", "engage_support",
    "poke", "split_pusher", "roamer", "objective_control", "any",
}
BASIS = ("pro:", "kit:", "rule", "written", "player:")
REQUIRED = ("id", "intent", "roles", "champions", "archetypes", "phase", "when", "asks", "say", "more",
            "check", "breaks", "basis")
SAY_WORDS = 26
MORE_WORDS = 40


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).casefold())


def known_champions() -> set[str]:
    data = json.loads((PROJECT / "champions-16.19.1.json").read_text(encoding="utf-8"))["data"]
    return {_norm(c["name"]) for c in data.values()} | {_norm(c["id"]) for c in data.values()}


def check_file(path: Path, champions: set[str]) -> tuple[int, list[str]]:
    problems: list[str] = []
    seen: set[str] = set()
    count = 0
    for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        where = f"{path.name}:{n}"
        try:
            e = json.loads(line)
        except ValueError as exc:
            problems.append(f"{where}: not JSON ({exc})")
            continue
        count += 1
        missing = [k for k in REQUIRED if k not in e]
        if missing:
            problems.append(f"{where}: missing {missing}")
            continue
        if e["id"] in seen:
            problems.append(f"{where}: duplicate id {e['id']}")
        seen.add(e["id"])
        if e["intent"] not in INTENTS:
            problems.append(f"{where}: unknown intent {e['intent']!r}")
        if not e["roles"] or not set(e["roles"]) <= ROLES:
            problems.append(f"{where}: roles must be a non-empty subset of {sorted(ROLES)}")
        if e["phase"] not in PHASES:
            problems.append(f"{where}: unknown phase {e['phase']!r}")
        if not isinstance(e["archetypes"], list) or not set(e["archetypes"]) <= ARCHETYPES:
            problems.append(f"{where}: archetypes must be a list within {sorted(ARCHETYPES)}")
        bad = [c for c in e["champions"] if _norm(c) not in champions]
        if bad:
            problems.append(f"{where}: unknown champions {bad}")
        if not isinstance(e["asks"], list) or not 3 <= len(e["asks"]) <= 6:
            problems.append(f"{where}: asks needs 3 to 6 example phrasings")
        if not isinstance(e["say"], str) or not 5 <= len(e["say"].split()) <= SAY_WORDS:
            problems.append(f"{where}: say must be 5 to {SAY_WORDS} words (has {len(str(e['say']).split())})")
        if not isinstance(e["more"], list) or not 1 <= len(e["more"]) <= 4:
            problems.append(f"{where}: more needs 1 to 4 follow-up lines")
        elif any(not isinstance(m, str) or len(m.split()) > MORE_WORDS for m in e["more"]):
            problems.append(f"{where}: each more line is at most {MORE_WORDS} words")
        if not str(e["basis"]).startswith(BASIS):
            problems.append(f"{where}: basis must start with one of {BASIS}")
        for field in ("when", "check", "breaks"):
            if not isinstance(e[field], str):
                problems.append(f"{where}: {field} must be text")
        if re.search(r"^\s*(1\.|2\.|option 1|choose plan)", str(e["say"]), re.I):
            problems.append(f"{where}: say must not be numbered")
    return count, problems


def main() -> int:
    files = [Path(a) for a in sys.argv[1:]] or sorted(HERE.glob("*.jsonl"))
    champions = known_champions()
    total = bad = 0
    for path in files:
        count, problems = check_file(path, champions)
        total += count
        bad += len(problems)
        print(f"{path.name}: {count} entries, {len(problems)} problems")
        for p in problems[:40]:
            print("  " + p)
    print(f"TOTAL {total} entries, {bad} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
