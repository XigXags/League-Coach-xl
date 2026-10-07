"""Build a mechanically checked coverage table from the numbered design notes."""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "JEV_DESIGN_NOTES.md"
OUT = Path(__file__).resolve().parents[1] / "NOTE_COVERAGE.csv"


def in_ranges(number: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(low <= number <= high for low, high in ranges)


def stage(number: int) -> str:
    if number in {25, 36}:
        return "owner-decision"
    if in_ranges(number, ((20, 31), (65, 65), (101, 121), (136, 139))):
        return "E-library-and-evidence"
    if in_ranges(number, ((32, 35), (47, 57), (66, 70), (79, 84), (132, 135), (153, 155))):
        return "C-split-ranker-and-state"
    if in_ranges(number, ((1, 19), (40, 46), (58, 64), (71, 78), (92, 97), (107, 112), (140, 141), (150, 151,))):
        return "D-routing-and-selected-LLM"
    if in_ranges(number, ((38, 39), (44, 44), (80, 81), (88, 91), (98, 100), (142, 149))):
        return "A-transport-and-observability"
    if in_ranges(number, ((41, 49), (116, 131), (144, 145), (152, 152))):
        return "E-library-and-evidence"
    return "B-evaluation-and-calibration"


def status(number: int) -> str:
    if number in {25, 36}:
        return "owner decision; interface only"
    if number in {38, 39, 44, 49, 62, 63, 64, 67, 70, 74, 80, 81, 88, 89, 90, 91, 98, 99, 100, 142, 146, 147, 149, 153, 154, 155, 156}:
        return "foundation or offline contract staged"
    if number in {43, 45, 87, 113, 114, 115, 125, 126, 127, 128, 132, 133, 134, 135, 136, 137, 138, 139}:
        return "later; disabled until evidence or owner decision"
    return "covered by staged plan; not live"


def resolution(number: int) -> str:
    special = {
        20: "Benchmark keyword/BM25 retrieval against later meaning-based two-pass Choice; do not assume both rankings are comparable.",
        25: "Feedback UI is intentionally unresolved; keep neutral label schema.",
        31: "Include none-fits and near misses; selected-answer fit gates speaking.",
        36: "Answer-library generation remains paused pending sourcing and review.",
        40: "Selected generative provider produces plain speech; Jev guards every line, including follow-ups.",
        70: "Move role guidance into documented instructions; reject undocumented sibling fields.",
        94: "Use option probabilities/top-two gap for selection; whole-answer confidence is a trust gate.",
        111: "Gate the selected answer's fit, not max fit over any candidate.",
        141: "Compound splitting is a separate validated extractor; no hidden action execution.",
        148: "Bound 429/529 retries by deadline; do not retry 401/422.",
        149: "Malformed successful replies fall back; never fill missing probabilities with zero.",
        152: "Review applicable agreements before setting retention policy.",
        156: "Keep deterministic order until option-permutation sensitivity is measured.",
    }
    return special.get(number, "See IMPLEMENTATION_PLAN.md; source Claude mentions mean the selected generative provider. Stage 0 adds profile switching independently of Jev.")


def main() -> None:
    found: dict[int, str] = {}
    for match in re.finditer(r"(?m)^\s*(\d+)\.\s+(.*)$", NOTES.read_text(encoding="utf-8")):
        number = int(match.group(1))
        if number in found:
            raise SystemExit(f"duplicate note number {number}")
        found[number] = " ".join(match.group(2).split())
    expected = set(range(1, 157))
    if set(found) != expected:
        raise SystemExit(f"coverage mismatch; missing={sorted(expected - set(found))}, extra={sorted(set(found) - expected)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("note", "primary_stage", "status", "note_excerpt", "resolution"))
        for number in range(1, 157):
            writer.writerow((number, stage(number), status(number), found[number], resolution(number)))
    print(f"wrote {OUT} ({len(found)} notes, all unique and covered)")


if __name__ == "__main__":
    main()
