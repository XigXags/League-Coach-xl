"""Five evidence-limited role coordinators for a live League match."""

from __future__ import annotations

from collections import deque
import copy
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

import lane_playbook

ROLES = ("top", "jungle", "mid", "bot", "support")
ROLE_ALIASES = {
    "top": {"TOP"}, "jungle": {"JUNGLE"}, "mid": {"MIDDLE", "MID"},
    "bot": {"BOTTOM", "BOT"}, "support": {"UTILITY", "SUPPORT"},
}
REPORT_ROOT = Path(__file__).with_name("artifacts") / "role-research"


@dataclass(frozen=True)
class Note:
    role: str
    game_second: int
    kind: str
    text: str
    confidence: str = "observed"


def load_role_reports(root: Path = REPORT_ROOT) -> dict[str, str]:
    """Load every role report once when Coach starts; reject an incomplete set."""
    runs = sorted((path for path in root.iterdir() if path.is_dir()), reverse=True) if root.exists() else []
    for run in runs:
        if all((run / f"{role}.md").is_file() for role in ROLES):
            reports = {role: (run / f"{role}.md").read_text(encoding="utf-8") for role in ROLES}
            if all(reports.values()):
                return reports
    raise FileNotFoundError("Five complete role reports are required in artifacts/role-research")


def _role_player(state: dict[str, Any], role: str) -> dict[str, Any] | None:
    team = state.get("our_team")
    players = [p for p in state.get("players", []) if p.get("team") == team]
    assigned = next((p for p in players if str(p.get("role")).upper() in ROLE_ALIASES[role]), None)
    if assigned or role != "jungle":
        return assigned
    smite = [p for p in players if any("smite" in str(spell).casefold()
                                     for spell in p.get("summoner_spells", []))]
    return smite[0] if len(smite) == 1 else None


def _compact_guidance(report: str) -> str:
    """Use the research's thesis and failure checks without sending entire reports to Jev."""
    paragraphs = [part.strip() for part in report.split("\n\n") if part.strip()]
    thesis = next((part for part in paragraphs[:3] if "central decision" in part or
                   "should manage" in part or "should connect" in part or
                   "job in a five-stack" in part or "should coordinate" in part),
                  paragraphs[0] if paragraphs else "")
    heading = next((i for i, line in enumerate(report.splitlines())
                    if "Six failure cases" in line), None)
    failures = []
    if heading is not None:
        lines = report.splitlines()[heading + 1:]
        failures = [line.strip() for line in lines if line.lstrip().startswith(("1.", "2.", "3."))][:3]
    return " ".join([thesis[:400], *failures])[:900]


class CoordinatorBoard:
    def fork(self):
        """Detached evaluation board with the current notes/plan and its own lock."""
        with self.lock:
            board = CoordinatorBoard(copy.deepcopy(self.reports))
            for name, value in self.__dict__.items():
                if name != "lock":
                    setattr(board, name, copy.deepcopy(value))
        return board

    def __init__(self, reports: dict[str, str] | None = None) -> None:
        self.reports = reports if reports is not None else load_role_reports()
        if any(not self.reports.get(role) for role in ROLES):
            raise ValueError("A report is required for each League role")
        lane_playbook.validate()
        self.guidance = {role: _compact_guidance(self.reports[role]) for role in ROLES}
        self.lock = RLock()
        self.notes: dict[str, deque[Note]] = {role: deque(maxlen=30) for role in ROLES}
        self.last_state: dict[str, Any] | None = None
        self.match_key: tuple | None = None
        # Counts new matches, so a restart with the same ten players (same match_key) is still told apart.
        self.match_serial: int = 0
        # The player's chosen plan and the last two alternatives offered, for this match only.
        self.plan: dict[str, Any] | None = None
        self.offer: tuple[tuple[str, str], ...] = ()   # (option key, plan id) in reply order
        self.offer_at: int = 0
        # Game second the coach asked how the player plays a champion it has no notes on; once per match.
        self.champion_ask_at: int | None = None

    def plan_state(self) -> tuple[dict[str, Any] | None, tuple[tuple[str, str], ...], int]:
        """Copies of the chosen plan, the last offer and the game second it was made."""
        with self.lock:
            return (dict(self.plan) if self.plan else None), tuple(self.offer), self.offer_at

    def choose(self, plan: dict[str, Any] | None) -> None:
        with self.lock:
            self.plan = dict(plan) if plan else None

    def offered(self, pairs: tuple[tuple[str, str], ...], now: int) -> None:
        with self.lock:
            self.offer, self.offer_at = tuple(pairs), int(now)

    def refresh_offer(self) -> None:
        """Keep the last offer answerable ("the first one") after an explanation of it was delivered."""
        with self.lock:
            if self.offer and self.last_state:
                self.offer_at = int(self.last_state["game_time_seconds"])

    def champion_asked(self) -> int | None:
        with self.lock:
            return self.champion_ask_at

    def mark_champion_asked(self, now: int) -> None:
        with self.lock:
            self.champion_ask_at = int(now)

    def mark_plan(self, **changes: Any) -> None:
        """Update the chosen plan's record; nothing happens when no plan is set."""
        with self.lock:
            if self.plan:
                self.plan.update(changes)

    def observe(self, state: dict[str, Any]) -> None:
        """Take notes on verified changes; no inferred wave, vision or position facts."""
        if not state.get("our_team") or not state.get("players"):
            return
        now = int(state.get("game_time_seconds", 0))
        # The ten player names are part of the match: a new game that starts unobserved, with the clock
        # already past the old one, still has a different roster.
        roster = tuple(sorted(str(player.get("name")) for player in state["players"]))
        identity = (state.get("active_player"), state.get("our_team"), state.get("mode"), roster)
        with self.lock:
            if self.match_key != identity or (self.last_state and
                                             now + 15 < self.last_state.get("game_time_seconds", 0)):
                self.notes = {role: deque(maxlen=30) for role in ROLES}
                self.last_state = None
                self.match_key = identity
                self.match_serial += 1
                self.plan, self.offer, self.offer_at = None, (), 0
                self.champion_ask_at = None
            old =self.last_state or {}
            for role in ROLES:
                player = _role_player(state, role)
                if not player:
                    continue
                previous = _role_player(old, role) if old else None
                champion = player.get("champion") or role
                if previous is None:
                    self.notes[role].append(Note(role, now, "roster",
                                                 f"{champion} is assigned to {role}."))
                else:
                    if player.get("dead") != previous.get("dead"):
                        self.notes[role].append(Note(role, now, "status",
                                                     f"{champion} {'died' if player.get('dead') else 'respawned'}."))
                    if player.get("level") != previous.get("level"):
                        self.notes[role].append(Note(role, now, "level",
                                                     f"{champion} reached level {player.get('level')}."))
                    new_items = [item for item in player.get("items", [])
                                 if item not in previous.get("items", [])]
                    if new_items:
                        self.notes[role].append(Note(role, now, "items",
                                                     f"{champion} gained {', '.join(new_items[:2])}."))
                edge = (state.get("lane_edges") or {}).get(role)
                old_edge = (old.get("lane_edges") or {}).get(role)
                if edge and not state.get("practice_tool") and (old_edge is None or
                    (abs(edge.get("cs", 0)) >= 20 and abs(edge.get("cs", 0) - old_edge.get("cs", 0)) >= 10) or
                    (abs(edge.get("level", 0)) >= 2 and edge.get("level") != old_edge.get("level"))):
                    self.notes[role].append(Note(role, now, "lane_score",
                        f"{champion} is {edge['cs']:+d} CS and {edge['level']:+d} levels versus the role opponent; "
                        "this is a strength clue, not proof of wave priority.", "inferred"))
            self.last_state = state

    def briefing(self, roles: tuple[str, ...] = ROLES, detail_role: str | None = None) -> dict[str, Any]:
        """Notes and guidance for every role; the full playbook only for the active player's role."""
        with self.lock:
            briefing = {role: {"guidance": self.guidance[role],
                               "playbook": lane_playbook.summary(role),
                               "notes": [note.__dict__ for note in list(self.notes[role])[-5:]]}
                        for role in roles if role in ROLES}
        if detail_role in briefing:
            briefing[detail_role]["full_playbook"] = lane_playbook.full(detail_role)
        return briefing

    def display(self, role: str | None = None) -> str:
        roles = (role,) if role in ROLES else ROLES
        with self.lock:
            lines = []
            for current in roles:
                latest = list(self.notes[current])[-3:]
                lines.append(f"**{current.title()}**: " + ("; ".join(n.text for n in latest)
                             if latest else "No live notes yet."))
            return "\n".join(lines)
