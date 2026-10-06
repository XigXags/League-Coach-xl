"""Small data contracts for provenance and cancellation. No live-state adapter yet."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Turn:
    session_id: str
    match_id: str
    match_serial: int
    request_version: int


def may_deliver(proposed: Turn, current: Turn, *, delivered: bool, already_committed: bool) -> bool:
    """Necessary preconditions, not an atomic send/commit implementation.

    The bot adapter must check under its session lock after awaiting Discord send.
    """
    return proposed == current and delivered and not already_committed


@dataclass(frozen=True)
class Fact:
    text: str
    source: Literal["observed", "player_report", "reference"]
    match_id: str | None
    observed_at: float | None
    expires_at: float | None
    source_id: str


def fresh_report(fact: Fact, *, match_id: str, game_second: float) -> bool:
    return (fact.source == "player_report" and fact.match_id == match_id
            and fact.observed_at is not None and fact.expires_at is not None
            and fact.observed_at <= game_second < fact.expires_at)
