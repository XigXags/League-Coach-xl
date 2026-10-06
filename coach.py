"""Evidence-based coach that offers two alternatives from Riot's local live game data."""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from typing import Any

from credentials import load_jev_key
import lane_playbook
from champion_metadata import champion_movement, champion_tags, kit_summary
from coordinators import CoordinatorBoard


RIOT_URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
OBJECTIVE_EVENTS = {"DragonKill", "BaronKill", "HeraldKill", "TurretKilled", "InhibKilled", "AtakhanKill"}
STRUCTURE_SPECIALISTS = {"Yorick", "Fiora", "Tryndamere", "Ziggs", "Caitlyn"}
SCUTTLE_SPAWN = 175  # 2:55, patch 26.1
GRUBS_SPAWN = 480  # 8:00, patch 26.1; the feed has no Grub events to confirm it
BARON_SPAWN = 1200  # 20:00, patch 26.1
CHAT_LIMIT = 1900  # Discord rejects messages over 2000 characters
# lessons.md Trigger names -> the jungle option whose wording that lesson supplies.
LESSON_TRIGGERS = {
    "first_clear": "jungle_first_clear", "second_clear": "jungle_full_clear",
    "six_race": "jungle_six_race", "six_behind": "jungle_six_behind",
    "six_first": "jungle_six_first", "scaling": "jungle_scale",
}


@dataclass(frozen=True)
class Option:
    key: str
    label: str
    reason: str
    say: str = ""      # short spoken clause; speech falls back to the label
    family: str = ""   # two_options never fills both slots from one family
    plan: str = ""     # id of the plan this option is a step of


@dataclass(frozen=True)
class Plan:
    """Something the player can commit to for a stretch of the game, checked against observed marks."""
    id: str
    name: str                    # spoken, 2 to 5 words
    keys: tuple[str, ...]        # option keys that are steps of it, at any stage
    words: tuple[str, ...]       # phrases that pick it
    marks: tuple = ()            # ("level", n, seconds), ("enemy_under", n, seconds), ("no_deaths",)
    safe: bool = False


PLAN_QUESTION = "game plan"   # the broad question the plan menu is built from
SAFE_KEYS = {"jungle_recover", "jungle_trade", "jungle_counter", "lane_safe",
             "lane_reset", "survive", "loss_stabilize", "buy"}
PLANS = {plan.id: plan for plan in (
    # The two marks are the coach's reading of the player's benchmark; the lesson's "On track" line replaces them.
    Plan("six_crab", "six on crab", ("jungle_first_clear", "jungle_full_clear", "jungle_six_race"),
         ("six on crab", "second crab", "crab", "scuttle", "level six", "level 6", "six", "full clear",
          "farm", "farming", "clear"), (("level", 4, 210), ("level", 5, 350))),
    Plan("gank", "gank set-up lanes", ("jungle_path", "jungle_six_first"), ("gank", "ganks", "ganking")),
    Plan("steal", "steal a camp", ("jungle_steal",), ("steal a camp", "steal", "their side")),
    Plan("cover", "play through a lane", ("jungle_cover",), ("cover", "play through", "winning lane")),
    Plan("counter", "track and counter-gank", ("jungle_counter",),
         ("counter gank", "countergank", "track", "shadow"), safe=True),
    Plan("objective", "set up the objective", ("jungle_objective",),
         ("objective", "dragon", "drake", "grubs", "herald", "baron")),
    Plan("scale", "farm to scale", ("jungle_scale",),
         ("scale", "scaling", "stacks", "farm", "farming", "clear")),
    Plan("recover", "reset and recover", ("jungle_recover", "lane_safe"),
         ("recover", "reset and recover", "own side", "safer one", "safe one"), safe=True),
    Plan("trade", "give and trade", ("jungle_trade",),
         ("trade", "trade sides", "opposite side", "cross map"), safe=True),
    Plan("lane_reset", "reset and buy", ("lane_reset",), ("reset", "recall", "buy"), safe=True),
    Plan("top_hold", "hold the wave", ("top_wave",), ("hold", "freeze")),
    Plan("top_split", "split top", ("top_split",), ("split",)),
    Plan("mid_roam", "shove and roam", ("mid_roam_wave",), ("roam",)),
    Plan("mid_rotate", "rotate mid", ("mid_rotate",), ("rotate",)),
    Plan("bot_trade", "trade windows", ("bot_trade_window",), ("trade window",)),
    Plan("bot_group", "group bot", ("bot_group",), ("group",)),
    Plan("sup_vision", "river vision", ("support_vision",), ("ward", "vision")),
    Plan("sup_sweep", "sweep the pit", ("support_sweep",), ("sweep",)),
)}
PLAN_OF = {key: plan.id for plan in PLANS.values() for key in plan.keys}
# Spoken short forms for one-off plays that have no plan name, used only with plan memory on.
SHORT_NAMES = {"lane_tempo": "next wave with jungle cover", "side_pressure": "side-wave pressure",
               "mid_siege": "a mid-wave siege", "hold_tempo": "farm for now", "buy": "reset and spend",
               "numbers": "use the numbers window"}
# Spoken names an explanation uses for the remaining plays whose label is too long to say three times.
# They are kept apart from SHORT_NAMES so the first reply's spoken line does not change.
EXPLAIN_NAMES = {"grubs_setup": "set up Grubs", "take_grubs": "take Grubs", "dragon_setup": "set up dragon",
                 "take_dragon": "take dragon", "setup": "push mid, then set up", "trade": "cross-map push",
                 "fight": "fight on the river entrance", "pressure": "mid pressure",
                 "mid_wave": "shove mid into river", "side_wave": "top-side pressure",
                 "reset": "reset and regroup", "waves": "collect waves first",
                 "lane_lead": "play through the lane lead", "pick_convert": "convert the pick",
                 "loss_stabilize": "clear safely", "survive": "give space until respawns",
                 "baron_window": "check Baron", "downtime": "use the downtime",
                 "post_dragon": "play away from dragon", "inhib_pressure": "inhibitor lane pressure",
                 "vision": "river vision through mid", "jungle_six_behind": "farm to six first"}


class Reply(str):
    """Chat text that also carries the short line to speak."""
    spoken: str = ""
    topic = None      # a Topic on a fresh read: what "explain more" elaborates on
    commit = None     # with defer_board, the board and note writes to run once the reply is delivered
    layer: int = 0    # 1 to 4 on an explanation, 0 on anything else


@dataclass
class Topic:
    """The two alternatives of one delivered read, kept so "explain more" can elaborate without a new read."""
    match_key: tuple | None        # board.match_key when built; None without a board
    game_second: int
    source: str
    pair: tuple[Option, Option]
    more: tuple[str, ...]          # labels of extra menu options, chat only
    names: tuple[str, str]         # spoken names: a plan name, a short name or the label's first clause
    words: tuple[tuple[str, ...], tuple[str, ...]]   # normalised pick words per alternative, for focus
    lessons: tuple[dict | None, dict | None]         # the lessons.md entry behind each option
    background: dict               # {"profile": lesson|None, "principle": {...}|None, "note": str, "champion": str}
    layer: int = 0
    serial: int = 0                # board.match_serial when built: a restart with the same ten players is a new match


def read_live_game(timeout: float = 2.0) -> dict[str, Any]:
    """Read Riot's local endpoint on the PC running League."""
    request = urllib.request.Request(RIOT_URL, headers={"Accept": "application/json"})
    # Riot documents the local game client's self-signed certificate.
    with urllib.request.urlopen(request, timeout=timeout, context=ssl._create_unverified_context()) as response:
        return json.load(response)


def _number(value: Any, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clock(seconds: float) -> str:
    total = max(0, round(seconds))
    return f"{total // 60}:{total % 60:02d}"


def summarize_game(data: dict[str, Any]) -> dict[str, Any]:
    """Keep facts relevant to decisions; never invent team gold or map vision."""
    game = data.get("gameData") or {}
    active = data.get("activePlayer") or {}
    raw_players = data.get("allPlayers") or []
    raw_events = (data.get("events") or {}).get("Events") or []
    active_name = active.get("riotId") or active.get("summonerName")
    name_to_team = {}
    for player in raw_players:
        for field in ("riotId", "summonerName"):
            if player.get(field):
                name_to_team[str(player[field]).casefold()] = player.get("team")
    our_team = name_to_team.get(str(active_name).casefold()) if active_name else None
    players = []
    for player in raw_players:
        scores = player.get("scores") or {}
        items = player.get("items") or []
        spells = player.get("summonerSpells") or {}
        players.append({
            "name": player.get("riotId") or player.get("summonerName"),
            "team": player.get("team"),
            "champion": player.get("championName"),
            "archetypes": champion_tags(player.get("championName")),
            # Possible reach from the kit's spell text (dash, leap, blink, charge, lunge), not a position.
            "movement_kit": champion_movement(player.get("championName")),
            "role": player.get("position"),
            "level": player.get("level"),
            "dead": player.get("isDead"),
            "respawn_seconds": round(_number(player.get("respawnTimer"))),
            "kills": scores.get("kills", 0),
            "deaths": scores.get("deaths", 0),
            "assists": scores.get("assists", 0),
            "cs": scores.get("creepScore", 0),
            "items": [item.get("displayName") for item in items if item.get("displayName")][:8],
            "summoner_spells": [spell.get("displayName") for spell in spells.values()
                                if isinstance(spell, dict) and spell.get("displayName")],
        })
    teams = {}
    for team in {p["team"] for p in players if p["team"]}:
        members = [p for p in players if p["team"] == team]
        teams[team] = {
            "players": len(members),
            "alive": sum(p["dead"] is False for p in members),
            "kills": sum(int(_number(p["kills"])) for p in members),
            "cs": sum(int(_number(p["cs"])) for p in members),
            "levels": sum(int(_number(p["level"])) for p in members),
        }
    objective_events = []
    recent_kills = []
    for event in raw_events:
        name = event.get("EventName")
        if name not in OBJECTIVE_EVENTS and name != "ChampionKill":
            continue
        event_time = round(_number(event.get("EventTime")))
        if event_time > _number(game.get("gameTime")) + 2:
            continue
        killer = event.get("KillerName")
        record = {
            "name": name,
            "time": event_time,
            "killer_team": name_to_team.get(str(killer).casefold()) if killer else None,
        }
        if name == "DragonKill":
            record["dragon_type"] = event.get("DragonType")
        if name == "ChampionKill":
            record["victim_team"] = name_to_team.get(str(event.get("VictimName")).casefold())
            recent_kills.append(record)
        else:
            objective_events.append(record)
    stats = active.get("championStats") or {}
    health = _number(stats.get("currentHealth"))
    max_health = _number(stats.get("maxHealth"))
    gold = active.get("currentGold")
    state = {
        "game_time_seconds": round(_number(game.get("gameTime"))),
        "mode": game.get("gameMode"),
        "practice_tool": str(game.get("gameMode", "")).upper() == "PRACTICETOOL",
        "our_team": our_team,
        "active_player": active_name,
        "active_gold": round(_number(gold)) if gold is not None else None,
        "active_health_percent": round(100 * health / max_health) if max_health > 0 else None,
        "players": players,
        "teams": teams,
        "objective_events": objective_events[-100:],
        "recent_champion_kills": recent_kills[-8:],
    }
    state["lane_edges"] = _lane_edges(state)
    return state


def _last_event(state: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((event for event in reversed(state["objective_events"]) if event["name"] == name), None)


def _role_player(state: dict[str, Any], team: str | None, role: str) -> dict[str, Any] | None:
    aliases = {
        "top": {"TOP"}, "jungle": {"JUNGLE"}, "mid": {"MIDDLE", "MID"},
        "bot": {"BOTTOM", "BOT"}, "support": {"UTILITY", "SUPPORT"},
    }
    assigned = next((player for player in state["players"]
                     if player["team"] == team and str(player["role"]).upper() in aliases[role]), None)
    if assigned or role != "jungle":
        return assigned
    # Practice Tool and some live feeds label the human jungler as NONE.
    # Smite is a useful fallback only when exactly one teammate has it.
    smite_users = [player for player in state["players"] if player["team"] == team
                   and any("smite" in spell.casefold() for spell in player["summoner_spells"])]
    return smite_users[0] if len(smite_users) == 1 else None


def _role_name(state: dict[str, Any], role: str) -> str:
    player = _role_player(state, state.get("our_team"), role)
    return player["champion"] if player and player.get("champion") else role


def _lane_edges(state: dict[str, Any]) -> dict[str, dict[str, int]]:
    our_team = state.get("our_team")
    enemies = next((team for team in state["teams"] if team != our_team), None)
    edges = {}
    for role in ("top", "mid", "bot", "jungle"):
        ally = _role_player(state, our_team, role)
        enemy = _role_player(state, enemies, role)
        if ally and enemy:
            edges[role] = {
                "level": int(_number(ally["level"]) - _number(enemy["level"])),
                "cs": int(_number(ally["cs"]) - _number(enemy["cs"])),
            }
    return edges


def _dragon_count(state: dict[str, Any], team: str | None) -> int:
    return sum(event["name"] == "DragonKill" and event["killer_team"] == team
               and event.get("dragon_type") != "Elder"
               for event in state["objective_events"])


def _dragon_due(state: dict[str, Any]) -> int | None:
    last = _last_event(state, "DragonKill")
    if last:
        soul_claimed = any(_dragon_count(state, team) >= 4 for team in state["teams"])
        return last["time"] + (360 if last.get("dragon_type") == "Elder" or soul_claimed else 300)
    return 300


ROLE_BY_POSITION = {
    "TOP": "top", "JUNGLE": "jungle", "MIDDLE": "mid", "MID": "mid",
    "BOTTOM": "bot", "BOT": "bot", "UTILITY": "support", "SUPPORT": "support",
}


def _active_player(state: dict[str, Any]) -> dict[str, Any] | None:
    return next((player for player in state["players"]
                 if player["name"] == state.get("active_player") and player["team"] == state.get("our_team")), None)


def active_role(state: dict[str, Any]) -> str | None:
    """The role the active player is playing, from the feed's position label."""
    me = _active_player(state)
    if me is None:
        return None
    role = ROLE_BY_POSITION.get(str(me.get("role")).upper())
    if role is None and any("smite" in str(spell).casefold() for spell in me.get("summoner_spells", [])):
        # Practice Tool and some feeds report the human jungler as NONE.
        return "jungle"
    return role


def active_champion(state: dict[str, Any]) -> str | None:
    """The champion the active player is on, from the feed."""
    return (_active_player(state) or {}).get("champion") or None


def _enemy_team(state: dict[str, Any]) -> str | None:
    teams = state.get("teams") or {}
    return next((team for team in teams if team != state.get("our_team")), None)


def _alive_edge(state: dict[str, Any]) -> int:
    teams = state.get("teams") or {}
    ours = teams.get(state.get("our_team"), {})
    theirs = teams.get(_enemy_team(state), {})
    return ours.get("alive", 0) - theirs.get("alive", 0) if ours and theirs else 0


def _within(events: list[dict[str, Any]], clock: float, seconds: float) -> list[dict[str, Any]]:
    return [event for event in events if 0 <= clock - event["time"] <= seconds]


# Each check reads only the observed feed: deaths, objectives, towers, alive counts, game time.
def _punished_split(state: dict[str, Any]) -> bool:
    enemy, our = _enemy_team(state), state.get("our_team")
    for death in state.get("recent_champion_kills", []):
        if death.get("victim_team") != our or not 0 <= state["game_time_seconds"] - death["time"] <= 90:
            continue
        if any(event["killer_team"] == enemy and death["time"] <= event["time"] <= death["time"] + 90
               and event["name"] in ("DragonKill", "TurretKilled", "HeraldKill", "BaronKill")
               for event in state["objective_events"]):
            return True
    return False


def _dive_setup(state: dict[str, Any]) -> bool:
    due = _dragon_due(state)
    return (_alive_edge(state) >= 1 and due is not None
            and 0 <= due - state["game_time_seconds"] <= 90)


def _objective_swap(state: dict[str, Any]) -> bool:
    recent = _within(state["objective_events"], state["game_time_seconds"], 150)
    towers = [e for e in recent if e["name"] == "TurretKilled" and e["killer_team"]]
    dragons = [e for e in recent if e["name"] == "DragonKill" and e["killer_team"]]
    return any(t["killer_team"] != d["killer_team"] and abs(t["time"] - d["time"]) <= 90
               for t in towers for d in dragons)


def _our_tower_within(state: dict[str, Any], seconds: float) -> bool:
    return any(e["name"] == "TurretKilled" and e["killer_team"] == state.get("our_team")
               for e in _within(state["objective_events"], state["game_time_seconds"], seconds))


def _split_pressure(state: dict[str, Any]) -> bool:
    return _alive_edge(state) >= 1 and _our_tower_within(state, 120)


def _baron_setup(state: dict[str, Any]) -> bool:
    return state["game_time_seconds"] >= 1200 and _our_tower_within(state, 180)


def _enemy_death_window(state: dict[str, Any]) -> bool:
    enemy = _enemy_team(state)
    recent = _within(state.get("recent_champion_kills", []), state["game_time_seconds"], 35)
    return _alive_edge(state) >= 1 and any(e.get("victim_team") == enemy for e in recent)


PLAY_TRIGGERS = {
    "punished_split": _punished_split,
    "dive_setup": _dive_setup,
    "objective_swap": _objective_swap,
    "split_pressure": _split_pressure,
    "baron_setup": _baron_setup,
    "enemy_death_window": _enemy_death_window,
}


def recognized_plays(state: dict[str, Any]) -> tuple[str, ...]:
    """Trigger names whose observed conditions hold in this snapshot."""
    return tuple(name for name, check in PLAY_TRIGGERS.items() if check(state))


def _trim(text: str, limit: int) -> str:
    """Cut at the last sentence end that fits."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(mark) for mark in (". ", "? ", "! "))
    return cut[:end + 1] if end > 0 else cut.rstrip() + "..."


# The stage uses only integer levels and game time; camps, crabs, XP within a level
# and passive stacks are not in the feed.
def jungle_clock(state: dict[str, Any]) -> dict[str, Any] | None:
    """Where the active jungler stands on the level 6 timeline, from observed levels, CS and time."""
    if active_role(state) != "jungle":
        return None
    # The active player's own record: a teammate can carry the JUNGLE label when ours reads NONE.
    me = _active_player(state)
    if me is None:
        return None
    clock = state["game_time_seconds"]
    enemy = _role_player(state, _enemy_team(state), "jungle")
    level = int(_number(me["level"]))
    cs = int(_number(me["cs"]))
    enemy_level = int(_number(enemy["level"])) if enemy else None
    compared = enemy is not None and not state.get("practice_tool")
    level_edge = level - enemy_level if compared else None
    cs_edge = cs - int(_number(enemy["cs"])) if compared else None
    if level_edge is None:
        pace = "unknown"
    elif level_edge <= -1 or (level_edge == 0 and cs_edge <= -20):
        pace = "behind"
    elif level_edge >= 1 or (level_edge == 0 and cs_edge >= 20):
        pace = "ahead"
    else:
        pace = "even"
    profile = lane_playbook.profile_for(me["champion"]) or {}
    if clock >= 840:
        stage = "mid_game"
    elif level < 6 and enemy_level is not None and enemy_level >= 6:
        stage = "six_behind"
    elif level >= 6 and enemy_level is not None and enemy_level < 6:
        stage = "six_first"
    elif level >= 6:
        stage = "post_six"
    elif level <= 3 and clock < 240:
        stage = "first_clear"
    elif level == 5:
        stage = "six_race"
    else:
        stage = "second_clear"
    return {
        "champion": me["champion"], "level": level, "cs": cs,
        "enemy_champion": enemy["champion"] if enemy else None, "enemy_level": enemy_level,
        "level_edge": level_edge, "cs_edge": cs_edge, "pace": pace,
        "plan": profile.get("plan") if profile.get("plan") in ("farm", "gank") else "flex",
        "until": lane_playbook.until_seconds(profile.get("until")) or 1200,
        "stage": stage,
    }


def _slug(title: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in title.casefold())


def _join(*parts: str) -> str:
    return " ".join(part for part in parts if part)


def _play_options(state: dict[str, Any]) -> tuple[Option, ...]:
    """Up to three recognized plays, offered only when their trigger is observed."""
    found = lane_playbook.plays_for(recognized_plays(state))[:3]
    return tuple(Option("play_" + _slug(play["title"]), play["title"], play["summary"]) for play in found)


def _lesson_reason(lesson: dict[str, str], seen: str, plan_note: str) -> str:
    # Dictated lessons can run long; each part is cut so the reply still fits one Discord message.
    timeline, check, breaks = (_trim(lesson[field], limit)
                               for field, limit in lane_playbook.LESSON_TEXT_LIMITS.items())
    return _join(seen,
                 f"By your own benchmark: {timeline}" if timeline else "",
                 f"You check: {check}" if check else "",
                 f"Breaks it: {breaks}" if breaks else "",
                 plan_note)


def _lesson_say(lesson: dict[str, str], fill: dict[str, Any]) -> str:
    say = lesson["say"]
    for name, value in fill.items():
        if value is not None:
            say = say.replace("{" + name + "}", str(value))
    if "{" in say:   # an unknown placeholder, or a level the feed did not give: never read it aloud
        say = ""
    return " ".join(say.split()[:14])


def _lesson_option(lesson: dict[str, str], seen: str, fill: dict[str, Any], plan_note: str) -> Option | None:
    """A lessons.md entry with "Offer at" as a plan of its own; its key is also its plan id."""
    goal = _trim(lesson["goal"], 90).rstrip(" .!?")
    if not goal:
        return None
    key = "lesson_" + _slug(lesson["title"])
    kind = lesson["kind"] if lesson["kind"] in lane_playbook.LESSON_KINDS else ""
    return Option(key, goal, _lesson_reason(lesson, seen, plan_note if kind == "farm" else ""),
                  _lesson_say(lesson, fill), kind, plan=key)


def _jungle_objective(state: dict[str, Any], enemy_team: str | None, note: str = "") -> Option:
    enemy_jungle = _role_player(state, enemy_team, "jungle")
    return Option("jungle_objective", "Set up the next neutral objective from your clear path",
                  f"You are the jungler. {note}Clear the camp that ends at the objective pit, with "
                  f"{_role_name(state, 'support')} placing vision "
                  "first. Start only when the adjacent lanes have pushed and the team can cover the entrance"
                  + (". The enemy jungler is dead, so the Smite fight is safer." if enemy_jungle and enemy_jungle["dead"] is True else "."),
                  "set up the next objective from your clear path")


def _jungle_options(state: dict[str, Any], clock: int, enemy_team: str | None,
                    info: dict[str, Any], *, recover: bool = False) -> tuple[Option, ...]:
    """The jungler's stage on the level 6 timeline, a gank alternative, the farm plan once 6,
    then the other plans whose trigger the feed shows."""
    join = _join

    champion = info["champion"] or "your champion"
    level, enemy_level, plan, stage = info["level"], info["enemy_level"], info["plan"], info["stage"]
    enemy = info["enemy_champion"] or "their jungler"
    time = _clock(clock)
    top, mid, bot = (_role_name(state, lane) for lane in ("top", "mid", "bot"))
    fill = {"level": level, "champion": champion, "enemy": enemy, "enemy_level": enemy_level, "clock": time}
    seen = (f"You are level {level} at {time}; {enemy} is level {enemy_level}." if info["enemy_champion"] else
            f"You are level {level} at {time}; the feed does not identify their jungler.")
    pace_note = {"behind": "You are behind their jungler on level or CS, so take camps before any river fight.",
                 "ahead": "You are ahead of their jungler on level or CS; keep the camps coming to hold it.",
                 }.get(info["pace"], "")
    plan_note = ""
    if plan == "farm":
        scaling = lane_playbook.lesson_for("jungle", info["champion"], "scaling") or {}
        goal = scaling.get("goal", "").rstrip(" .!?")
        plan_note = (f"On {champion} the same clears serve your longer plan: {goal}." if goal else
                     f"On {champion} the same clears serve your later power.")
    path_prefix = {"farm": f"On {champion} a gank is a detour from the farm plan. ",
                   "gank": f"{champion} is on your gank-first list, so set-up ganks are usually worth more than "
                           "an extra camp. ",
                   }.get(plan, "")
    built = {
        "jungle_first_clear": Option(
            "jungle_first_clear", "Finish the camps you have left, then a river crab if one is free",
            join(seen, "A full clear should put you about level 4, and the river crabs spawn at "
                       f"{_clock(SCUTTLE_SPAWN)} on patch 26.1 timings. "
                       "Every camp skipped now is experience you are missing when the level 6 race comes a few "
                       "minutes later. You check: which camps are left and whether a crab is free; the coach "
                       "cannot see camps or crabs.", plan_note),
            "Finish your camps, then crab if it's free; every camp counts for six", "farm"),
        "jungle_full_clear": Option(
            "jungle_full_clear", "Full clear again; level 6 is the payoff",
            join(seen, "Each skipped camp pushes level 6 back. Once both first crabs are dead only one crab is up "
                       "at a time, on a random river side, and being level 5 and on time is what lets you contest "
                       "it. You check: which camps are up and where the crab is; the coach cannot see either.",
                 pace_note, plan_note),
            f"Level {level}. Keep full clearing, level six is the payoff", "farm"),
        "jungle_six_race": Option(
            "jungle_six_race", "If a river crab is up, reach it first for level 6",
            join(seen, "By the player's own benchmark, two full clears plus a first crab leave a jungler about one "
                       "camp short of 6, so the next crab can be the level. You check: is the crab up, on which "
                       "side, and are you close to 6; the coach cannot see crabs, camps or experience. If you are "
                       "late or a camp short, give the crab and take a camp instead.", plan_note),
            f"Level {level}. If crab's up and you're a camp from six, get it first", "farm"),
        "jungle_six_behind": Option(
            "jungle_six_behind", f"Farm to 6 before you fight {enemy}",
            join(f"{enemy} is level {enemy_level} and you are level {level} at {time}, so they may have a level 6 "
                 "ultimate you do not have yet. Take camps away from the river until you are 6. You check: which "
                 f"camps are up and where {enemy} was last seen; the coach cannot see either.", plan_note),
            f"{enemy} is {enemy_level}, you're {level}. Camps first; don't fight in river alone", "farm"),
        "jungle_six_first": Option(
            "jungle_six_first", f"Use your level lead before {enemy} reaches 6",
            f"You are level {level} and {enemy} is level {enemy_level} at {time}. That gap closes once they reach "
            "6, so a gank or river fight is strongest while you hold the level lead. You check: is your "
            "ultimate up and is a lane set up; the coach cannot see cooldowns or waves. If nothing is set up, "
            "keep clearing.",
            f"You're {level}, {enemy} is {enemy_level}. Gank or fight while the level lead lasts", "gank"),
        "jungle_scale": Option(
            "jungle_scale", f"Keep full clearing; {champion} is strongest later",
            join(seen, f"{champion} is on your farm-first list, so camps taken now pay off later in the game. "
                       "You check: have you hit your item or power point yet; the coach cannot see passive stacks "
                       "or cooldowns. If you have, group instead."),
            f"keep farming, {champion} wins later", "farm"),
        "jungle_path": Option(
            "jungle_path",
            "Gank only a set-up lane next to your next camp" if plan == "farm" else
            "Gank the set-up lane next to your clear, then get back on camps",
            f"{path_prefix}A gank pays off now but costs camps. Take it only where your clear already ends and "
            f"{top}, {mid} or {bot} has the wave on their own side. You check: the wave and where their jungler "
            "was last seen; if that was the same side, it can be a trap. If it is not there, keep clearing.",
            "gank only a set-up lane on your path" if plan == "farm" else
            "gank a set-up lane by your clear", "gank"),
    }
    due = _dragon_due(state)
    dragon_note = (f"Dragon is due in {_clock(due - clock)} by the kill events. "
                   if stage == "post_six" and due is not None and due > clock else "")
    built["jungle_objective"] = _jungle_objective(state, enemy_team, dragon_note)

    def taught(option: Option) -> Option:
        # A matching lessons.md entry supplies the wording; the key and family never change.
        trigger = next((name for name, key in LESSON_TRIGGERS.items() if key == option.key), None)
        lesson = lane_playbook.lesson_for("jungle", info["champion"], trigger) if trigger else None
        if not lesson:
            return option
        reason = _lesson_reason(lesson, seen, "" if option.key == "jungle_scale" else plan_note)
        return Option(option.key, _trim(lesson["goal"], 90).rstrip(" .!?") or option.label, reason,
                      _lesson_say(lesson, fill) or option.say, option.family)

    lead = {"first_clear": "jungle_first_clear", "second_clear": "jungle_full_clear",
            "six_race": "jungle_six_race", "six_behind": "jungle_six_behind",
            "six_first": "jungle_six_first"}.get(stage, "jungle_objective")
    keys = [lead] + (["jungle_path"] if stage != "mid_game" else [])
    if stage in ("six_first", "post_six", "mid_game") and plan == "farm" and level >= 6 and clock < info["until"]:
        keys.append("jungle_scale")
    options = [taught(built[key]) for key in keys]

    # Extra plans, each only under a trigger the feed shows. Camps, crabs and positions stay "You check".
    me = _active_player(state) or {}
    practice = bool(state.get("practice_tool"))
    enemy_jungle = _role_player(state, enemy_team, "jungle")
    their = enemy[:1].upper() + enemy[1:]
    behind, dead = info["pace"] == "behind", me.get("dead") is True
    if recover or behind or dead:
        # "Until you are level" is said only when the feed shows a deficit; a forced safe line stays neutral.
        start = ("When you respawn, buy, then take" if dead else
                 "Recall when the camp you are on is done, spend your gold, and take")
        options.append(Option(
            "jungle_recover", "Reset, buy, then clear only your own side" + (" until you are level" if behind else ""),
            join(seen, pace_note if behind else "",
                 f"{start} your own-side camps away from the river "
                 f"{'until your level matches theirs' if behind else 'until your next item'}. "
                 "Give a contested crab or objective this time. "
                 f"You check: which of your own camps are up and where {enemy} was last seen; the coach cannot "
                 "see either. " + ("Once the feed shows you level, ask again and pick a plan." if behind else
                                   "Ask again when you want to pick a plan.")),
            "reset, buy, then clear only your own side", "recover"))
        options.append(Option(
            "jungle_trade", "Give the side their jungler shows on and take the opposite side",
            join(seen, f"Instead of contesting, answer on the other half of the map: when {enemy} appears on one "
                       "side, take camps or a lane play on the far side. You check: where "
                       f"{enemy} actually showed and which far-side camps are up; the coach cannot see positions "
                       "or camps. If they have not shown, stay on your own camps."),
            "trade sides: where they show, you take the opposite camps", "trade"))
    for lesson in lane_playbook.plan_lessons("jungle", info["champion"], stage, clock):
        option = _lesson_option(lesson, seen, fill, plan_note)
        if option:
            options.append(option)
    if (enemy_jungle and enemy_jungle["dead"] is True and enemy_jungle["respawn_seconds"] >= 25
            and clock < 840):
        options.append(Option(
            "jungle_steal", "Take one camp on their side while their jungler is dead",
            join(seen, f"{their} is dead with about {enemy_jungle['respawn_seconds']} seconds on the respawn "
                       "timer, and it keeps running. Whether that is enough for one camp on their side depends "
                       "on where you are. You check: how far you are, which of their camps is up and whether "
                       "their laners can collapse; the coach cannot see camps or positions. Leave before the "
                       "respawn; if nothing is up or it is too far, take your own camp instead."),
            "their jungler's dead; their camp if it's up and close, then out", "invade"))
    edges = {} if practice else {lane: edge for lane, edge in (state.get("lane_edges") or {}).items()
                                 if lane in ("top", "mid", "bot")}
    if clock < 840:
        # A lane with one signal up and the other down is mixed: neither ahead nor behind.
        ahead = {lane: edge for lane, edge in edges.items()
                 if (edge["level"] >= 1 and edge["cs"] > -15) or (edge["level"] >= 0 and edge["cs"] >= 15)}
        if ahead:
            lane = max(ahead, key=lambda name: (ahead[name]["level"], ahead[name]["cs"]))
            options.append(Option(
                "jungle_cover", f"Play through your {lane} lane's score lead",
                join(seen, f"Your {lane} lane ({_role_name(state, lane)}) is {ahead[lane]['level']:+d} levels and "
                           f"{ahead[lane]['cs']:+d} CS on the feed. Path so your clear ends on that side, then "
                           f"gank or cover its next wave. You check: where that wave is and where {enemy} was "
                           "last seen; a score lead is not wave priority and the coach cannot see either. If the "
                           "wave is not set, keep clearing."),
                f"{lane} is ahead on score; path there, gank a set wave", "cover"))
        listed = (lane_playbook.profile_for(info["enemy_champion"]) or {}).get("plan") == "gank"
        down = {lane: edge for lane, edge in edges.items()
                if (edge["level"] <= -1 and edge["cs"] < 15) or (edge["level"] <= 0 and edge["cs"] <= -15)}
        if info["enemy_champion"] and not practice and (listed or down):
            lane = min(down, key=lambda name: (down[name]["level"], down[name]["cs"])) if down else ""
            # Their intent and the wave are not observed: "in case they gank", and the lane is the player's check.
            lane_text = f"your {lane} lane" if lane else "whichever of your lanes is pushed up"
            opener = (f"{their} is on your gank-first list." if listed else
                      f"Your {lane} lane is behind on score, so it is the likelier target; that is a guess from "
                      "score, not a sighting.")
            options.append(Option(
                "jungle_counter", f"Track {enemy} and hold near a lane in case they gank",
                join(seen, opener,
                     f"Clear toward {lane_text} and wait a step behind it, so that if they gank it becomes a "
                     f"fight you join second. You check: where {enemy} was last seen and whether that wave is "
                     "pushed up; the coach cannot see positions or waves. If they show on the other side, take "
                     "what that opens on yours."),
                f"track {enemy}; hold near {f'your {lane} lane' if lane else 'a pushed-up lane'} in case they gank",
                "cover"))
    if stage in ("second_clear", "six_race", "six_behind", "six_first"):
        horizon = _next_horizon(state, clock)
        if horizon != "your next item":
            # Only a dragon respawn is computed from a kill event; first spawns are patch constants.
            basis = ("by the kill events and patch timers" if horizon.startswith("Dragon")
                     and _last_event(state, "DragonKill") else "by patch timers")
            options.append(_jungle_objective(state, enemy_team, f"{horizon}, {basis}. "))
    return tuple(options[:8])


def _role_options(state: dict[str, Any], role: str | None, clock: int, enemy_team: str | None,
                  *, recover: bool = False) -> tuple[Option, ...]:
    """One play for the active player's own lane job, chosen by game phase."""
    if role is None:
        return ()
    jungler = _role_name(state, "jungle")
    mid = _role_name(state, "mid")
    bot = _role_name(state, "bot")
    support = _role_name(state, "support")
    top = _role_name(state, "top")
    lane_phase = clock < 840
    if role == "top":
        if lane_phase:
            return (Option("top_wave", "Hold the top wave near your tower until your jungler can reach top",
                           f"You are top. Keep the wave on your side near your tower, trade only when the enemy top's "
                           f"key spell is down, and crash it only when {jungler} can reach top."),)
        return (Option("top_split", "Take the top side wave while mid and bot hold the centre",
                       f"You are top. If the enemy top is not in lane, push the top wave into their tower and watch "
                       f"the top river. A split needs {mid} and {bot} holding the centre and no enemy group on your side."),)
    if role == "jungle":
        info = jungle_clock(state)
        if info is None:   # keep today's single option
            if lane_phase:
                return (Option("jungle_path", "Path to the lane with the wave near its tower, then gank",
                               f"You are the jungler. Clear toward the lane whose wave is near its tower and arrive when "
                               f"{top}, {mid} or {bot} has the wave in place. Confirm vision first; if the enemy jungler "
                               "was last seen on that side, the gank is a trap."),)
            return (_jungle_objective(state, enemy_team),)
        return _jungle_options(state, clock, enemy_team, info, recover=recover)
    if role == "mid":
        if lane_phase:
            return (Option("mid_roam_wave", "Shove the mid wave to tower, then roam with a clear return",
                           f"You are mid. A wave that reaches the enemy tower and is cleared gives a short window; "
                           f"leave once it clears and return before the enemy responds. Agree the target with "
                           f"{jungler} and {support} before you move."),)
        return (Option("mid_rotate", "Rotate mid with the wave to the next objective",
                       f"You are mid. Crash the mid wave when the enemy mid is out of lane, then move with {jungler} "
                       "toward the objective. Return before the wave resets."),)
    if role == "bot":
        if lane_phase:
            return (Option("bot_trade_window", "Trade when the enemy support's key spell is down",
                           f"You are bot. Your trades depend on {support}'s level and the enemy support's spells. Keep "
                           "the wave pushed toward you while they are ready to engage, and trade once their key spell is spent."),)
        return (Option("bot_group", "Group bot with the team for the next objective",
                       f"You are bot. Rotate with {support} to the objective while the wave is pushed, then stand behind "
                       "the frontline. Leave the fight before the enemy resets."),)
    if role == "support":
        if lane_phase:
            return (Option("support_vision", "Ward the river and the jungler's route before the bot wave",
                           f"You are support. Place river vision before the lane pushes and stay with {bot} so the wave "
                           "is not free for the enemy. Do not walk far from the wave."),)
        return (Option("support_sweep", "Sweep the objective pit and entrance before the spawn",
                       f"You are support. Clear enemy vision on the pit and its entrance before the spawn, then stay "
                       f"with {jungler} to set it up. Do not engage without a follow-up."),)
    return ()


def _specific_objective_options(state: dict[str, Any], question: str) -> tuple[Option, ...]:
    """Build executable choices for an explicit objective-vs-objective question."""
    q = question.casefold()
    wants_grubs = "grub" in q
    wants_dragon = "dragon" in q or "drake" in q
    if not (wants_grubs and wants_dragon):
        return ()
    clock = state["game_time_seconds"]
    our_team = state.get("our_team")
    enemies = next((team for team in state["teams"] if team != our_team), None)
    our_jungle = _role_player(state, our_team, "jungle")
    enemy_jungle = _role_player(state, enemies, "jungle")
    jungler = _role_name(state, "jungle")
    mid = _role_name(state, "mid")
    top = _role_name(state, "top")
    bot = _role_name(state, "bot")
    support = _role_name(state, "support")
    specialists = [player["champion"] for player in state["players"]
                   if player["team"] == our_team and player["champion"] in STRUCTURE_SPECIALISTS]
    tower_conversion = (f"{specialists[0]} is a strong structure-pressure pick; "
                        "use the buff on the next pushed wave." if specialists else
                        "Convert the buff into turret damage on the next pushed wave.")
    gold = None if state.get("practice_tool") else state.get("active_gold")
    reset = (f"{gold:,} unspent gold on the active player: buy first, then "
             if gold is not None and gold >= 1300 else "")
    enemy_jungle_dead = enemy_jungle and enemy_jungle["dead"] is True
    our_jungle_dead = our_jungle and our_jungle["dead"] is True
    due = _dragon_due(state)
    dragon_down = due is not None and clock < due
    soul_claimed = any(_dragon_count(state, team) >= 4 for team in state["teams"])
    dragon_target = "Elder Dragon" if soul_claimed else "Dragon"
    dragon_stakes = ("Elder's execute buff can decide the next fight" if soul_claimed else
                     "This is your team's soul point" if _dragon_count(state, our_team) == 2 else
                     "This is your team's soul" if _dragon_count(state, our_team) == 3 else
                     "This adds a permanent dragon stack")
    if clock < 480:
        grubs = Option("grubs_setup", "Set up the 8:00 Grubs window",
                       f"{mid} and {top} prepare top-side waves; {jungler} paths toward the upper river. "
                       "Grubs have not spawned yet, so do not waste time in the pit now.")
    elif clock < 900:
        grubs = Option("take_grubs", "Take Grubs through top and mid",
                       f"{reset}{mid} shoves mid; {top} shoves top. {support} screens upper river; "
                       f"{jungler} checks the pit and takes remaining Grubs. {bot} stays bot. "
                       f"If empty, hit top tower. If taken, {tower_conversion}")
    else:
        target = "Herald" if clock < 1200 else "Baron"
        grubs = Option("top_pit", f"Play for {target}, not Grubs",
                       f"Grubs' one early window has passed. {mid} pushes mid; {top} holds the top-side wave; "
                       f"{support} clears upper-river vision and {jungler} checks {target} pit. "
                       "If it is empty, move the top wave into the tower.")
    if dragon_down:
        wait = _clock(due - clock)
        first_spawn = _last_event(state, "DragonKill") is None
        dragon = Option("dragon_setup", f"Set up {'first' if first_spawn else 'next'} {dragon_target} in {wait}",
                        f"{'Dragon has not spawned yet' if first_spawn else 'Dragon was taken recently'}. "
                        f"{bot} and {mid} push before the next spawn; "
                        f"{support} and {jungler} establish lower-river vision after a reset. Do not start an empty pit.")
    else:
        jungle_note = ("Enemy jungler is dead: start while Smite is uncontested. " if enemy_jungle_dead else
                       "Your jungler is dead: do not start a Smite fight; use the setup to threaten bot tower. "
                       if our_jungle_dead else "")
        dragon = Option("take_dragon", f"Take {dragon_target} through bot and mid",
                        f"{reset}{bot} and {support} shove bot; {mid} shoves mid. {support} sweeps lower river; "
                        f"{jungler} starts {dragon_target} while bot and mid cover entrances. "
                        f"{jungle_note}{dragon_stakes}.")
    return grubs, dragon


def evidence(state: dict[str, Any]) -> str:
    parts = [f"{_clock(state['game_time_seconds'])} game time"]
    clock = state["game_time_seconds"]
    parts.append("lane phase" if clock < 840 else "map transition" if clock < 1200 else "mid/late map")
    if state.get("practice_tool"):
        parts.append("Practice Tool; gold and scores may be altered")
    gold = state.get("active_gold")
    if gold is not None:
        suffix = " (practice value)" if state.get("practice_tool") else ""
        parts.append(f"you have {gold:,} unspent gold{suffix}")
    our_team = state.get("our_team")
    teams = state.get("teams") or {}
    enemy_team = next((name for name in teams if name != our_team), None)
    if our_team in teams and enemy_team:
        ours, theirs = teams[our_team], teams[enemy_team]
        parts.append(f"{ours['alive']} allies vs {theirs['alive']} enemies alive")
        if not state.get("practice_tool"):
            parts.append(f"kills {ours['kills']}-{theirs['kills']}")
    recent_deaths = [event for event in state.get("recent_champion_kills", [])
                     if 0 <= clock - event["time"] <= 35]
    if recent_deaths:
        ally_deaths = sum(event.get("victim_team") == our_team for event in recent_deaths)
        enemy_deaths = sum(event.get("victim_team") == enemy_team for event in recent_deaths)
        parts.append(f"last 35s deaths: {ally_deaths} allies, {enemy_deaths} enemies")
    if not state.get("practice_tool"):
        edges = state.get("lane_edges") or {}
        reads = [f"{role} {edge['level']:+d} levels/{edge['cs']:+d} CS"
                 for role, edge in edges.items() if role in ("top", "mid", "bot")]
        if reads:
            parts.append("lane score edges: " + ", ".join(reads))
        info = jungle_clock(state)
        if info and info["enemy_champion"] and info["cs_edge"] is not None:
            parts.append(f"jungle: you level {info['level']} vs {info['enemy_champion']} "
                         f"level {info['enemy_level']}, {info['cs_edge']:+d} CS")
    objectives = state.get("objective_events") or []
    if objectives:
        last = objectives[-1]
        event_name = {
            "DragonKill": "dragon", "BaronKill": "Baron", "HeraldKill": "Herald",
            "TurretKilled": "tower", "InhibKilled": "inhibitor",
            "AtakhanKill": "Atakhan",
        }.get(last["name"], "objective")
        age = _clock(state["game_time_seconds"] - last["time"])
        owner = "your team" if last["killer_team"] == our_team and our_team else (
            "enemy team" if last["killer_team"] and last["killer_team"] != our_team else "unknown team")
        parts.append(f"last {event_name} taken {age} ago by {owner}")
    return "; ".join(parts)


def _next_horizon(state: dict[str, Any], clock: int) -> str:
    """The next dated thing a quiet minute of farming is for."""
    due = _dragon_due(state)
    if due is not None and 0 < due - clock <= 120:
        return f"Dragon in {_clock(due - clock)}"
    if GRUBS_SPAWN - 120 <= clock < GRUBS_SPAWN:
        return f"Grubs at {_clock(GRUBS_SPAWN)}"
    if BARON_SPAWN - 120 <= clock < BARON_SPAWN:
        return f"Baron at {_clock(BARON_SPAWN)}"
    return "your next item"


def candidate_options(state: dict[str, Any], question: str, *, recover: str = "") -> tuple[Option, ...]:
    """Only propose plays whose stated trigger is present in the snapshot.

    recover "add" forces the safe options in; "only" keeps nothing but SAFE_KEYS."""
    specific = _specific_objective_options(state, question)
    if specific:
        return specific
    options: list[Option] = []
    seen: set[str] = set()

    def add(key: str, label: str, reason: str, say: str = "", family: str = "", plan: str = "") -> None:
        if key not in seen:
            seen.add(key)
            options.append(Option(key, label, reason, say, family, plan or PLAN_OF.get(key, "")))

    q = question.casefold()
    clock = state["game_time_seconds"]
    our_team = state.get("our_team")
    teams = state.get("teams") or {}
    enemy_team = next((name for name in teams if name != our_team), None)
    ours = teams.get(our_team, {})
    enemies = teams.get(enemy_team, {})
    alive_edge = ours.get("alive", 0) - enemies.get("alive", 0) if ours and enemies else 0
    gold = None if state.get("practice_tool") else state.get("active_gold")
    edges = {} if state.get("practice_tool") else state.get("lane_edges") or {}
    recent_kills = [event for event in state.get("recent_champion_kills", [])
                    if 0 <= clock - event["time"] <= 35]
    recent_enemy_deaths = [event for event in recent_kills if event.get("victim_team") == enemy_team]
    recent_ally_deaths = [event for event in recent_kills if event.get("victim_team") == our_team]
    role = active_role(state)
    for route in _role_options(state, role, clock, enemy_team, recover=bool(recover)):
        add(route.key, route.label, route.reason, route.say, route.family, route.plan)
    me = _active_player(state) or {}
    if role != "jungle":
        if role:
            fill = {"level": me.get("level"), "champion": me.get("champion"), "enemy": None,
                    "enemy_level": None, "clock": _clock(clock)}
            for lesson in lane_playbook.plan_lessons(role, me.get("champion"),
                                                     "lane" if clock < 840 else "mid_game", clock):
                taught = _lesson_option(lesson, "", fill, "")
                if taught:
                    add(taught.key, taught.label, taught.reason, taught.say, taught.family, taught.plan)
        edge = edges.get(role, {})
        if recover or edge.get("level", 0) <= -1 or edge.get("cs", 0) <= -20 or me.get("dead") is True:
            # The safe line follows the role and the phase: a support does not last-hit, and after lane
            # phase there is no lane to hold.
            if clock >= 840:
                add("lane_safe", "Catch waves on your own side and stay grouped behind vision",
                    "Take only the waves on your own half of the map, move with teammates behind your own wards, "
                    "and give an objective you cannot contest with numbers. You check: where the waves are and "
                    "who is missing on their side; the coach cannot see waves, wards or positions. Do not walk "
                    "into river alone.",
                    "catch waves on your side; stay grouped, give contested objectives", "recover")
            elif role == "support":
                add("lane_safe", "Stay with your carry behind the wave and ward your own side",
                    f"Stand behind the wave with {_role_name(state, 'bot')}, place wards on your own side of the "
                    "river, and do not roam alone until the next item. You check: where the wave is and whether "
                    "their jungler was seen near; the coach cannot see waves, wards or positions. Leave lane "
                    "only with a teammate.",
                    "stay with your carry; ward your own side, no roam alone", "recover")
            else:
                add("lane_safe", "Hold the wave at your tower and give what you cannot reach",
                    "Let the wave come to your tower, last-hit there, and give the CS and plates you cannot reach "
                    "safely until your next item. You check: where the wave is and whether their jungler was seen "
                    "near; the coach cannot see waves or positions. Leave lane only with a teammate.",
                    "hold at your tower; give what you can't reach", "recover")
        if recover:
            add("lane_reset", "Crash a wave, then reset together",
                f"{_role_name(state, 'mid')} and {_role_name(state, 'bot')} finish their next safe waves; "
                f"{_role_name(state, 'support')} covers the exit. Buy before looking for a roam or fight.")
    for play in _play_options(state):
        add(play.key, play.label, play.reason, play.say, play.family, play.plan)

    if gold is not None and gold >= 1300:
        add("buy", f"Spend your {gold:,} gold on the next safe reset",
            f"You have {gold:,} unspent gold. Clear the wave you can safely reach, recall, buy, "
            "then rejoin your team. Do not start a fight while holding the purchase.")
    if alive_edge >= 2:
        add("numbers", "Use the numbers window for a tower or enemy jungle entrance",
            f"It is {ours['alive']} versus {enemies['alive']} alive. Push the closest safe lane first; "
            "with the wave, hit its tower or enter the adjacent jungle together. Leave before respawns.")
    elif alive_edge <= -2:
        add("survive", "Give space and catch waves until respawns",
            f"It is {ours['alive']} versus {enemies['alive']} alive. Defend towers from behind the wave; "
            "do not enter river alone. Reassess when teammates respawn.")
    if recent_enemy_deaths and alive_edge > 0:
        add("pick_convert", "Turn the pick into nearby map space",
            "An enemy died in the last 35 seconds. Push the nearest lane as a group, then take "
            "its tower or a guarded jungle entrance before the respawn; avoid a blind chase.")
    if recent_ally_deaths and alive_edge < 0:
        add("loss_stabilize", "Clear safely after the lost fight",
            "A teammate died in the last 35 seconds. Catch the next safe wave under your tower, "
            "give up contested river space, and regroup on the respawn.")

    objective_words = {"dragon": "DragonKill", "baron": "BaronKill", "herald": "HeraldKill"}
    asked_objective = next((name for word, name in objective_words.items() if word in q), None)
    objective_question = asked_objective or any(word in q for word in ("objective", "grub", "atakhan"))
    broad_question = any(word in q for word in ("what next", "what's next", "whats next", "now", "next play", "going on", "what should", "game plan"))
    path_question = any(word in q for word in ("path", "farm", "clear", "camp", "gank", "where", "scuttle", "crab"))
    broad_question = broad_question or (role == "jungle" and path_question)
    if objective_question:
        for route in _specific_objective_options(state, "grubs or dragon"):
            add(route.key, route.label, route.reason)
    elif broad_question:
        if clock < 840:
            if role == "jungle":   # lane_tempo would duplicate jungle_path; the reset is the jungler's own
                add("lane_reset", "Recall and buy, then restart your clear",
                    "Finish the camp you are on, recall, spend your gold, and start the next clear from base. "
                    "You check: that no camp or crab you need is lost while you are away.",
                    "recall and buy, then restart your clear")
            else:
                add("lane_tempo", "Play for the next lane wave and jungle cover",
                    f"{_role_name(state, 'jungle')} paths toward the lane with the better matchup or "
                    "clearest wave; that laner handles the wave before moving. If the lane cannot move, "
                    "take a safe camp or reset instead of forcing river.")
            add("lane_reset", "Crash a wave, then reset together",
                f"{_role_name(state, 'mid')} and {_role_name(state, 'bot')} finish their next safe waves; "
                f"{_role_name(state, 'support')} covers the exit. Buy before looking for a roam or fight.")
        else:
            add("side_pressure", "Work a side wave into tower pressure",
                f"{_role_name(state, 'top')} takes the next safe side wave while four hold mid. "
                "Once the wave reaches tower, take damage there or rotate toward the defender. "
                "If enemies are missing, back off before the long lane becomes a trap.")
            add("mid_siege", "Bring a mid wave to the next tower",
                f"{_role_name(state, 'mid')} and {_role_name(state, 'bot')} escort the next mid wave; "
                f"{_role_name(state, 'support')} and {_role_name(state, 'jungle')} guard one flank. "
                "Hit the tower with the wave, then leave before the wave dies.")
        # A jungler who already has a farm option does not need a second one splitting the ranking.
        if alive_edge == 0 and not (role == "jungle" and any(option.family == "farm" for option in options)):
            horizon = _next_horizon(state, clock)
            add("hold_tempo", f"Nothing forced: farm toward {horizon}",
                "Both teams have equal numbers alive and nothing in the feed forces a fight. "
                f"What you take now is for {horizon}. Take the next safe wave or camp, then "
                "recheck after a death, item buy, or structure falls.",
                f"nothing in the feed forces a play; farm toward {horizon}", "farm")
        if clock >= 1200 and alive_edge >= 2:
            add("baron_window", "Use the pick to check Baron",
                f"With {alive_edge} more players alive, push mid first; support and jungle check "
                "top river together. Start Baron only if it is alive and the entrance is safe.")
        if not state.get("practice_tool"):
            lane = next((role for role in ("mid", "bot", "top")
                         if edges.get(role, {}).get("level", 0) >= 2 or
                         edges.get(role, {}).get("cs", 0) >= 25), None)
            if lane and not (role == "jungle" and "jungle_cover" in seen):
                edge = edges[lane]
                add("lane_lead", f"Play through your {lane} lane lead",
                    f"Your {lane} lane is up {edge['level']} levels and {edge['cs']} CS. "
                    f"{_role_name(state, 'jungle')} can cover its next wave and threaten that tower. "
                    "Check the actual wave and enemy positions before committing; score lead alone is not priority.")
    latest_asked = _last_event(state, asked_objective) if asked_objective else None
    recently_taken = latest_asked and 0 <= clock - latest_asked["time"] < 120
    if recently_taken:
        add("downtime", "Use the objective downtime for map pressure",
            f"That objective was taken {_clock(clock - latest_asked['time'])} ago; look for waves, towers, or a reset.")
    elif objective_question:
        target = asked_objective.replace("Kill", "").lower() if asked_objective else "the next objective"
        add("setup", f"Push mid and set up {target}",
            f"{_role_name(state, 'mid')} clears mid, {_role_name(state, 'support')} sweeps the river, "
            f"and {_role_name(state, 'jungle')} starts {target} after the adjacent lane moves.")
        add("trade", "Cross-map: push the far side and take a tower",
            f"Send {_role_name(state, 'top')} to the far side wave; {_role_name(state, 'jungle')} "
            "covers the route while the other three hold mid. Convert the wave into tower damage.")

    recent_baron = _last_event(state, "BaronKill")
    if recent_baron and recent_baron["killer_team"] == our_team and clock - recent_baron["time"] < 180:
        add("baron_push", "Group with surviving Baron holders",
            f"Your team took Baron {_clock(clock - recent_baron['time'])} ago; use the buff only if its holders are alive.")
    recent_dragon = _last_event(state, "DragonKill")
    if recent_dragon and clock - recent_dragon["time"] < 120:
        add("post_dragon", "Play away from dragon for now",
            f"Dragon was taken {_clock(clock - recent_dragon['time'])} ago; use the downtime for a wave, reset, or other objective.")
    recent_inhib = _last_event(state, "InhibKilled")
    if recent_inhib and clock - recent_inhib["time"] < 300:
        if recent_inhib["killer_team"] == our_team:
            add("inhib_pressure", "Use the opened inhibitor lane for pressure",
                "Your team took an inhibitor recently. Confirm the wave and surviving teammates before pushing farther.")
        elif recent_inhib["killer_team"]:
            add("inhib_defense", "Clear the exposed inhibitor lane",
                "The enemy took an inhibitor recently. Stabilize the incoming wave before leaving base.")
    recent_tower = _last_event(state, "TurretKilled")
    if recent_tower and clock - recent_tower["time"] < 150:
        if recent_tower["killer_team"] == our_team:
            add("tower_rotation", "Rotate after the tower take",
                "Your team took a tower recently. Check which nearby wave or objective is safe to move toward.")
        elif recent_tower["killer_team"]:
            add("tower_defense", "Regroup after losing a tower",
                "The enemy took a tower recently. Reassess the lane before fighting in the opened area.")

    if any(word in q for word in ("lane", "mid", "top", "bot side", "side lane")):
        add("mid_wave", "Shove mid, then move into river together",
            f"{_role_name(state, 'mid')} and {_role_name(state, 'bot')} clear mid; "
            f"{_role_name(state, 'support')} and {_role_name(state, 'jungle')} move first into river.")
        add("side_wave", "Create top-side pressure while four hold mid",
            f"{_role_name(state, 'top')} takes the top wave; the other four clear mid and wait "
            "for a response before rotating to the top river.")
    if any(word in q for word in ("fight", "engage", "aggressive", "aggression")):
        add("fight", "Shove mid and fight on the river entrance",
            f"{_role_name(state, 'mid')} clears mid; {_role_name(state, 'support')} and "
            f"{_role_name(state, 'jungle')} take the river entrance with the carries following.")
        add("pressure", "Shove mid and force an enemy response",
            f"{_role_name(state, 'mid')} and {_role_name(state, 'bot')} clear mid; "
            "hold the river entrance, then rotate toward the revealed defender.")

    if alive_edge > 0:
        add("pressure", "Shove mid during the numbers window",
            f"{_role_name(state, 'mid')} and {_role_name(state, 'bot')} clear mid; "
            f"{_role_name(state, 'support')} moves with {_role_name(state, 'jungle')} toward the next objective.")
    if clock >= 720 and (objective_question or alive_edge > 0):
        add("vision", "Move support and jungle through mid to river",
            f"{_role_name(state, 'mid')} pushes mid first; {_role_name(state, 'support')} "
            f"and {_role_name(state, 'jungle')} clear river wards together, then ping the entry route.")
    if not broad_question or not options:
        add("reset", "Reset, spend, and regroup through mid",
            f"{_role_name(state, 'mid')} catches the next mid wave; the team buys and leaves base "
            "together through mid toward the upcoming objective.")
        add("waves", "Collect mid and side waves before moving",
            f"{_role_name(state, 'mid')} catches mid, {_role_name(state, 'top')} catches top, "
            "then both join jungle and support at the river entrance.")
    if recover == "only":
        options = [option for option in options if option.key in SAFE_KEYS]
    return tuple(options[:12])


def jev_rank(state: dict[str, Any], api_key: str, options: tuple[Option, ...],
             timeout: float = 5.0) -> dict[str, float]:
    payload = {
        "model": "jev-latest",
        "state": state,
        "questions": {"next_play": {
            "type": "choice",
            "instructions": "Rank these concrete next-play plans for this League of Legends team. First resolve immediate deaths and safety, then a spendable item/reset window, then lane wave and jungle tempo, then structures, vision, or a neutral objective only when its window is actionable. An equal-number, no-trigger state can favor farming or waiting; do not force an objective fight. Use observed deaths, role assignments, lane level/CS edges, champion archetypes, items, listed summoner spells, objective history, question, and team style. A listed Teleport or global ability is a possibility, not proof it is ready. Lane score edges and archetypes are clues, not proof of lane priority or matchup. If game.practice_tool is true, ignore inflated gold and artificial score leads. Do not infer unseen wave positions, enemy locations, vision, jungle camp state, or another player's unspent gold. When no death, reset or objective window is open, a plan that pays off later (level 6, an item, a scaling benchmark) can outrank a small immediate play. The player hears two of these as alternatives and decides; this is not a command.",
            "criteria": {option.key: {"play": option.label, "why": option.reason} for option in options},
            "role_rule": ("The coordinator_briefing includes the full playbook for the active player's own role. "
                          "Judge each option by whether that player can execute it with the observed facts, "
                          "and treat unobserved wave, vision, camp, and cooldown states as unknown. "
                          "minimap_visible lists only icons the minimap shows right now; x and y are fractions of "
                          "the minimap, and a champion missing from the list is unseen, not absent. A null champion "
                          "means the icon was unclear. "
                          "Positioning: the feed has no coordinates. Use each player's movement_kit and listed "
                          "Flash or Teleport as reach that can end a position, and frame every position as a plan "
                          "or possibility, never as where a player is. "
                          "recognized_plays are macro patterns whose trigger the feed has already observed; "
                          "weigh each by its stated trade-off on both sides, and do not claim the pattern is happening "
                          "unless the observed facts show it. "
                          "long_plan.jungle_clock is derived only from observed levels, CS and game time. "
                          "long_plan.lessons are the player's own stated benchmarks, not observations of this "
                          "match; camp, crab, experience and passive-stack states remain unknown. "
                          "current_plan is the player's own stated choice with their own benchmarks and a status "
                          "from observed level, CS, time and deaths; it is context, not a command, its camp, crab "
                          "and stack progress is unknown, and a safer option may outrank it when the verdict is "
                          "behind or off. "
                          "pro_principles are paraphrased tendencies from professional games, not observations of "
                          "this match and not instructions; each has a trade-off for both sides, and five-player "
                          "coordination often does not transfer to solo queue. "
                          "champion_kits are Riot's static kit descriptions plus, as player_note, the player's own "
                          "words on how they play the champion; they say what a champion can do, never what is "
                          "ready, stacked or happening now, and they are background to weigh against the observed "
                          "state, not a script."),
        }},
    }
    request = urllib.request.Request(
        JEV_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        answer = json.load(response)["answers"]["next_play"]
    probabilities = answer.get("probabilities") or {}
    return {option.key: float(probabilities.get(option.key, 0)) for option in options}


def two_options(scores: dict[str, float], options: tuple[Option, ...], *,
                must: tuple[str, ...] = ()) -> tuple[Option, Option]:
    ranked = sorted(options, key=lambda option: (-scores.get(option.key, 0), option.key))
    # must: the step of the player's chosen plan leads; two keys are the whole pair, as given.
    forced = [option for key in must for option in ranked if option.key == key]
    if len(forced) >= 2:
        return forced[0], forced[1]
    if forced:
        ranked = forced + [option for option in ranked if option is not forced[0]]
    # Do not spend both slots on the same mid-river setup when a different
    # executable route exists. Explicit Grubs-vs-Dragon choices stay intact.
    mid_setup = {"mid_control", "vision", "mid_wave", "mid_siege"}
    first, second = ranked[0], ranked[1]
    if first.key in mid_setup:
        second = next((option for option in ranked[1:] if option.key not in mid_setup), second)
    # A farm call is paired with something that is not also farming, and likewise for ganks.
    if first.family and second is ranked[1]:
        second = next((option for option in ranked[1:] if option.family != first.family), second)
    # A jungler always hears the clear or scaling plan as one of the two, so the long plan is never dropped.
    plan = next((option for option in ranked if option.key.startswith("jungle_") and option.family == "farm"), None)
    if plan and "farm" not in (first.family, second.family):
        second = plan
    # Two steps of one plan are one choice, not two alternatives.
    if first.plan and second.plan == first.plan:
        second = next((option for option in ranked[1:] if option.plan != first.plan
                       and (not first.family or option.family != first.family)), second)
    return first, second


SPOKEN_WORD_LIMIT = 24


def _spoken(first: Option, second: Option, lead: str = "", short_lead: str = "", second_name: str = "",
            first_name: str = "") -> str:
    def words(option: Option) -> str:
        return (option.say or option.label).strip().rstrip(".!?")

    def clause(option: Option, other: Option, lead: bool) -> str:
        text = words(option)
        status, separator, rest = text.partition(". ")
        if not lead and option.say and separator and any(c.isdigit() for c in status):
            text = rest   # the level read is said once, up front, not after "Or,"
        reason = option.reason.casefold()
        critical = (". Their jungler is dead" if "enemy jungler is dead" in reason else
                    ". Your jungler is dead" if "your jungler is dead" in reason else "")
        if "jungler's dead" in words(other).casefold():
            critical = ""   # the other half already says it
        return f"{text}{critical}."

    def upper(text: str) -> str:
        return text[:1].upper() + text[1:]
    named = f"{second_name.strip().rstrip('.!?')}." if second_name.strip() else ""
    if not lead:
        plain = upper(f"{clause(first, second, True)} Or, {clause(second, first, False)}")
        # A line that fits is left as it was; a longer one names the second half by its plan.
        if named and len(plain.split()) > SPOKEN_WORD_LIMIT:
            return upper(f"{clause(first, second, True)} Or, {named}")
        return plain
    # The plan lead carries the status, so the first clause drops its own "Level N." read.
    opening = upper(clause(first, second, False))
    full = clause(second, first, False)
    brief = first_name.strip().rstrip(".!?")

    def short_first(opener: str) -> str:
        # The first half as its plan name, or nothing when the lead has just named that plan.
        if not brief:
            return f"{opening} "
        return "" if brief.casefold() in opener.casefold() else f"{upper(brief)}. "

    # Shorten in steps until the line fits: plan name for the second half, short lead, then the plan
    # name for the first half. The lead is never dropped: it is how a commit or a verdict is heard.
    lines = [f"{upper(lead)}. {opening} Or, {full}"]
    if named:
        lines.append(f"{upper(lead)}. {opening} Or, {named}")
    if short_lead:
        lines.append(f"{upper(short_lead)}. {opening} Or, {named or full}")
    lines.append(f"{upper(lead)}. {short_first(lead)}Or, {named or full}")
    if short_lead:
        lines.append(f"{upper(short_lead)}. {short_first(short_lead)}Or, {named or full}")
    return next((line for line in lines if len(line.split()) <= SPOKEN_WORD_LIMIT), lines[-1])


def format_options(options: tuple[Option, Option], *, source: str, facts: str, lead: str = "",
                   short_lead: str = "", more: tuple[Option, ...] = (),
                   names: dict[str, str] | None = None) -> Reply:
    """lead opens the spoken line with the plan's status; more adds up to two further alternatives."""
    first, second = options
    more = tuple(more)[:2]
    names = names or {}
    extra = "".join(f"Otherwise: **{option.label}** — {_trim(option.reason, 160)}\n" for option in more)
    reasons = [first.reason, second.reason]
    room = CHAT_LIMIT - len(facts) - len(first.label) - len(second.label) - len(extra)
    if sum(map(len, reasons)) > room:
        reasons = [_trim(reason, max(room // 2, 200)) for reason in reasons]
    reply = Reply(f"Game read ({source}): {facts}.\n"
                  f"**{first.label}** — {reasons[0]}\n"
                  f"Otherwise: **{second.label}** — {reasons[1]}\n"
                  f"{extra}"
                  "Your call.")
    def name(option: Option) -> str:
        # A plan's spoken name; "key:..." entries are short forms for one-off plays.
        return names.get(option.plan) or names.get("key:" + option.key) or ""

    if more:
        said = [(name(option) or option.label).strip().rstrip(".!?") for option in (first, second, *more)]
        opener = f"{lead.strip().rstrip('.!?')}. " if lead.strip() else ""
        while True:
            reply.spoken = f"{opener}Options: {', '.join(said[:-1])}, or {said[-1]}. Your call."
            if len(reply.spoken.split()) <= SPOKEN_WORD_LIMIT or len(said) <= 2:
                break
            said.pop()
    else:
        reply.spoken = _spoken(first, second, lead, short_lead, name(second), name(first))
    return reply


def _edges_now(state: dict[str, Any], info: dict[str, Any] | None) -> tuple[int | None, int | None]:
    """The active player's level and CS edge on their role opponent; None when the feed cannot compare."""
    if info:
        return info["level_edge"], info["cs_edge"]
    edge = None if state.get("practice_tool") else (state.get("lane_edges") or {}).get(active_role(state))
    return (edge["level"], edge["cs"]) if edge else (None, None)


def _pace(state: dict[str, Any], info: dict[str, Any] | None) -> str:
    """behind, even, ahead or unknown: the jungle clock's pace, or a laner's score edge."""
    if info:
        return info["pace"]
    level_edge, cs_edge = _edges_now(state, None)
    if level_edge is None:
        return "unknown"
    if level_edge <= -1 or cs_edge <= -15:
        return "behind"
    return "ahead" if level_edge >= 1 or cs_edge >= 15 else "even"


def situation_tags(state: dict[str, Any]) -> set[str]:
    """Observed situations that pro_lessons.md entries can ask for; every name is in lane_playbook.PRO_TAGS."""
    clock = state["game_time_seconds"]
    practice = bool(state.get("practice_tool"))
    our_team, enemy_team = state.get("our_team"), _enemy_team(state)
    teams = state.get("teams") or {}
    tags = set(recognized_plays(state))
    pace = _pace(state, jungle_clock(state))
    if pace in ("ahead", "behind"):
        tags.add(pace)
    if not practice and our_team in teams and enemy_team in teams:
        kills = teams[our_team]["kills"] - teams[enemy_team]["kills"]
        if abs(kills) >= 3:
            tags.add("team_ahead" if kills > 0 else "team_behind")
    alive = _alive_edge(state)
    if alive:
        tags.add("numbers_up" if alive > 0 else "numbers_down")
    if _next_horizon(state, clock) != "your next item":
        tags.add("objective_soon")
    enemy_jungle = _role_player(state, enemy_team, "jungle")
    if enemy_jungle and enemy_jungle["dead"] is True:
        tags.add("enemy_jungler_dead")
    recent = _within(state.get("recent_champion_kills", []), clock, 35)
    if any(event.get("victim_team") == our_team for event in recent):
        tags.add("after_death")
    if any(event.get("victim_team") == enemy_team for event in recent):
        tags.add("after_kill")
    if _within(state["objective_events"], clock, 120):
        tags.add("after_objective")
    if any(event["name"] == "TurretKilled" for event in _within(state["objective_events"], clock, 150)):
        tags.add("tower_down")
    gold = state.get("active_gold")
    if not practice and gold is not None and gold >= 1300:
        tags.add("gold_ready")
    return tags


def _phase(clock: float) -> str:
    return "early" if clock < 360 else "lane" if clock < 840 else "mid" if clock < 1500 else "late"


# Plan talk is matched on whole words of the normalised question, so "kill" never reads as "ill".
QUESTION_WORDS = {"what", "whats", "should", "can", "could", "would", "is", "are", "am", "do", "does", "did",
                  "how", "why", "which", "where", "when"}
# A question asked after the first word ("ok so should I ...") is still a question, not a choice.
QUESTION_TURNS = ("should i", "should we", "can i", "can we", "could i", "could we", "would i", "do i", "do we",
                  "is it", "is that", "is this", "what", "which", "how", "why", "where")
COMMIT_VERBS = ("lets", "go with", "going with", "ill", "i will", "we will", "were going", "play for",
                "playing for", "switch to", "stick with", "commit to", "lock in", "i pick", "i choose", "plan is",
                "im going to", "im gonna", "im going for", "i want to", "id rather")
# These are a choice only when they open the sentence: "take the crab", not "he will take the crab".
OPENING_VERBS = ("do the", "take the", "go for", "going for", "go back to", "back to")
# The only words allowed between a commit verb and the plan it names: "let's go with the invade".
BETWEEN_WORDS = {"the", "a", "an", "for", "to", "my", "with", "that", "this", "do", "go", "play", "take", "just",
                 "try", "back"}
# Spoken padding at either end of a sentence: "ok the first one", "second one please".
EDGE_WORDS = {"ok", "okay", "yeah", "yes", "um", "uh", "alright", "sure", "please", "then", "so", "and", "well",
              "hey", "coach", "actually", "right"}
OFFER_POSITIONS = (
    ("second one", "the second", "second option", "second plan", "other one", "the other", "otherwise",
     "the alternative", "number two", "option two"),
    ("first one", "the first", "first option", "first plan", "that one", "do that", "number one", "option one"),
)   # the second is checked first; index 0 below is offer[1]
FILLER_WORDS = ("the", "a", "an")
DROP_PHRASES = ("drop the plan", "forget the plan", "cancel the plan")
# A statement that the game is going badly, or an explicit request for the safe way: sets the plan aside.
RECOVER_PHRASES = ("not working", "isnt working", "is not working", "doesnt work", "didnt work", "plan failed",
                   "safer way", "safe way", "conservative", "get back on track", "way back on track",
                   "get back in", "get back into", "back in the game", "back into the game", "how do i come back",
                   "play safe", "play it safe", "playing safe", "im behind", "im losing", "far behind",
                   "fell behind", "were behind", "were losing", "keep dying", "getting destroyed", "bail",
                   "plan b", "abandon")
# Softer words: a request when stated, only a question about safety when asked ("is it safer to gank top").
RECOVER_HINTS = ("safer", "recover", "falling behind")
INTENT_PHRASES = (
    ("menu", "fresh", ("what else", "other ideas", "alternatives", "something else", "other options",
                       "different plan")),
    ("menu", None, ("my options", "all the options", "what plans", "which plans", "list the plans", "choices")),
    ("status", None, ("on track", "on pace", "how am i doing", "hows the plan", "how is the plan",
                      "is it working", "still good", "am i behind", "plan check", "stick with it", "stay on it",
                      "keep the plan", "hows it going", "hows my plan", "plan working", "is this working",
                      "whats my plan", "what plan", "am i ahead")),
)
BROAD_PHRASES = ("what next", "whats next", "what now", "next play", "what should i do", "our options",
                 "game plan")


def _norm(text: str) -> str:
    """Lower case, apostrophes removed, everything else that is not a letter or digit as one space."""
    text = str(text).casefold().replace("'", "").replace("’", "")
    return " ".join("".join(c if c.isalnum() else " " for c in text).split())


def _says(text: str, phrases) -> bool:
    padded = f" {text} "
    return any(f" {phrase} " in padded for phrase in phrases)


def _bare(text: str) -> str:
    return " ".join(word for word in text.split() if word not in FILLER_WORDS)


def _plan_words(plan: Plan) -> list[str]:
    return [word for word in (_norm(text) for text in (*plan.words, plan.name)) if word]


def _core(text: str) -> list[str]:
    """The words of a normalised sentence without the spoken padding at either end."""
    words = text.split()
    while words and words[0] in EDGE_WORDS:
        words = words[1:]
    while words and words[-1] in EDGE_WORDS:
        words = words[:-1]
    return words


def _next_phrase(words: list[str], index: int, phrases) -> tuple[str, int]:
    """The longest of phrases starting at index, or after up to three joining words; with the index after it."""
    for start in range(index, min(index + 4, len(words))):
        rest = " ".join(words[start:]) + " "
        found = max((phrase for phrase in phrases if rest.startswith(phrase + " ")), key=len, default="")
        if found:
            return found, start + len(found.split())
        if words[start] not in BETWEEN_WORDS:
            break
    return "", index


def plan_intent(question: str, offer: tuple[tuple[str, str], ...], plans: dict[str, Plan],
                stored: dict[str, Any] | None) -> tuple[str, str | None]:
    """What the player's sentence does to their plan: commit, drop, unclear, recover, menu, status or ask.

    offer is the last pair offered, or () once it is stale; plans are the plans on the menu right now.
    ("ask", "safe") is a question about safety: the safe lines are added and no plan is touched."""
    text = _norm(question)
    words = _core(text)
    if _says(text, DROP_PHRASES) or (len(words) <= 3 and _says(text, ("no plan",))):
        return "drop", None
    marked = str(question).strip().endswith("?")
    asking = marked or (bool(words) and words[0] in QUESTION_WORDS)

    # Each phrase belongs to the first plan on the menu that lists it.
    owner: dict[str, str] = {}
    for plan in plans.values():
        for word in _plan_words(plan):
            owner.setdefault(word, plan.id)
    off_menu = {word for plan in PLANS.values() if plan.id not in plans for word in _plan_words(plan)} - set(owner)
    slot = {phrase: index for index, phrases in zip((1, 0), OFFER_POSITIONS) for phrase in phrases}

    def positioned(index: int) -> tuple[str, str | None] | None:
        if index >= len(offer):
            return None
        target = offer[index][1]
        return ("commit", target) if target in plans else ("unclear", None)

    # A commit verb counts only in a statement, before any question turn, with the plan right after it.
    verbs = []
    for start in range(len(words)):
        for verb in (COMMIT_VERBS + OPENING_VERBS if start == 0 else COMMIT_VERBS):
            size = len(verb.split())
            if words[start:start + size] == verb.split() and not _says(" ".join(words[:start]), QUESTION_TURNS):
                verbs.append(start + size)
    if asking:
        verbs = []
    for end in verbs:
        phrase, after = _next_phrase(words, end, owner)
        if phrase and words[after:after + 1] != ["or"]:   # "the crab or gank" is weighing, not choosing
            return "commit", owner[phrase]
        phrase, _ = _next_phrase(words, end, slot)
        found = positioned(slot[phrase]) if phrase else None
        if found:
            return found
    # A short answer to a fresh offer: a position, or the name of a plan that was just offered.
    bare = _bare(" ".join(words))
    if bare and len(words) <= 5 and offer and not marked:
        found = next((positioned(index) for phrase, index in slot.items() if bare == _bare(phrase)), None)
        if found:
            return found
        offered = {plan for _, plan in offer}
        for plan in plans.values():
            if plan.id in offered and bare in {_bare(word) for word in _plan_words(plan)}:
                return "commit", plan.id
    if any(_next_phrase(words, end, off_menu)[0] for end in verbs):
        return "unclear", None
    if _says(text, RECOVER_PHRASES):
        return "recover", None
    if _says(text, RECOVER_HINTS):
        return ("ask", "safe") if asking else ("recover", None)
    for intent, target, phrases in INTENT_PHRASES:
        if _says(text, phrases):
            return intent, target
    return "ask", None


# Two commands that never reach the ranker. They are matched on the whole sentence, never on a phrase
# inside it, so "how do I stop the dive" and "one more camp" stay questions.
QUICK_PAD = {"just", "now", "oh", "no", "man", "bro", "dude", "god", "thanks"}
STOP_PHRASES = frozenset((
    "stop", "stopp", "stopped", "stop it", "stop that", "stop talking", "stop speaking", "quiet", "be quiet",
    "shut up", "shut it", "shush", "hush", "silence", "enough", "thats enough", "that is enough",
    "enough already", "no more", "never mind", "nevermind", "cancel", "cancel that", "forget it", "not now",
    "zip it", "can you stop", "can you stop talking", "i said stop"))
MORE_PHRASES = frozenset((
    "more", "more detail", "more details", "in more detail", "details", "explain", "explain more",
    "explained more", "explain that", "explain it", "explain both", "explain why", "tell me more", "say more",
    "go on", "goon", "go ahead", "keep going", "keep talking", "continue", "carry on", "elaborate", "expand",
    "expand on that", "break it down", "why", "why those", "why that", "why is that", "how come", "how so",
    "what do you mean", "what does that mean", "what do you mean by that", "explain again", "explain further",
    "can you explain", "can you explain more", "why though", "but why"))
# "why the second one", "explain gank": the longest head is tried first.
MORE_HEADS = ("tell me more about", "elaborate on", "more about", "more on", "explain", "why")
# After a head these point at the whole read, not at one alternative: "more on that", "why these two".
MORE_TAILS = frozenset(("that", "this", "it", "them", "both", "both of them", "these", "those", "these two",
                        "those two"))
# What Whisper tends to write for breath or silence; voice paths drop these without a reply.
NOISE_PHRASES = frozenset(("thank you", "thank you for watching", "thanks for watching", "you", "bye"))
QUICK_FOCUS_WORDS = 7
QUICK_STOP_WORDS = 12


def quick_forms(question: str) -> tuple[str, str, str]:
    """The sentence as said, without spoken padding, and with the quick-command padding stripped too."""
    words: list[str] = []
    for word in _norm(question).split():
        if not words or words[-1] != word:   # "stop stop" is "stop"
            words.append(word)
    plain = _core(" ".join(words))
    loose, pad = list(words), EDGE_WORDS | QUICK_PAD
    while loose and loose[0] in pad:
        loose = loose[1:]
    while loose and loose[-1] in pad:
        loose = loose[:-1]
    return " ".join(words), " ".join(plain), " ".join(loose)


def is_noise(question: str) -> bool:
    """A transcript with nothing in it but padding, or one of Whisper's silence phrases."""
    _, plain, loose = quick_forms(question)
    return not loose or plain in NOISE_PHRASES


def _only_stops(said: str) -> bool:
    """Nothing but stop phrases and spoken padding: "stop it, stop it", "stop, coach, stop", "stop. thank you".

    Every word must belong to a stop phrase or be padding, so "stop the plan" and "no plan" are not stops."""
    words = _bare(said).split()
    trimmed = True
    while trimmed:   # Whisper's silence phrases at either end, the longest first: "thank you" before "you"
        trimmed = False
        for noise in sorted((phrase.split() for phrase in NOISE_PHRASES), key=len, reverse=True):
            if len(words) > len(noise) and words[:len(noise)] == noise:
                words, trimmed = words[len(noise):], True
            elif len(words) > len(noise) and words[-len(noise):] == noise:
                words, trimmed = words[:-len(noise)], True
            if trimmed:
                break
    if len(words) > QUICK_STOP_WORDS:
        return False
    pad = EDGE_WORDS | QUICK_PAD
    longest = max(len(phrase.split()) for phrase in STOP_PHRASES)

    def rest(index: int, found: bool) -> bool:
        if index == len(words):
            return found
        if any(" ".join(words[index:index + size]) in STOP_PHRASES and rest(index + size, True)
               for size in range(min(longest, len(words) - index), 0, -1)):
            return True
        return words[index] in pad and rest(index + 1, found)

    return rest(0, False)


def quick_intent(question: str, topics: tuple[tuple[str, ...], tuple[str, ...]] = ((), ())
                 ) -> tuple[str, int | None] | None:
    """("stop", None), ("more", focus) or None. focus 0 or 1 is which remembered alternative opens."""
    said, plain, loose = quick_forms(question)
    # The sentence as said is tried too: "how so" ends in a padding word and "no more" starts with one.
    forms = {said, plain, loose}
    if forms & STOP_PHRASES or _only_stops(said):   # stop first, on every form: "no more" is a stop, not "more"
        return "stop", None
    if forms & MORE_PHRASES:
        return "more", None
    words = loose.split()
    if len(words) > QUICK_FOCUS_WORDS:
        return None
    for head in MORE_HEADS:
        size = len(head.split())
        if words[:size] != head.split() or len(words) == size:
            continue
        tail = _bare(" ".join(words[size:]))
        if not tail:
            return None
        if tail in MORE_TAILS:
            return "more", None
        for focus, phrases in zip((1, 0), OFFER_POSITIONS):
            if tail in {_bare(phrase) for phrase in phrases}:
                return "more", focus
        for last in (" plan", " one", " option"):   # "explain the gank plan" names the same thing as "explain gank"
            tail = tail.removesuffix(last)
        owners = [index for index in (0, 1) if tail in {_bare(_norm(word)) for word in topics[index]}]
        return ("more", owners[0]) if len(owners) == 1 else None
    return None


NOTE_OPENING = re.compile(r"^\W*(?:(?:ok|okay|hey|coach|so|and|please)\W+)*"
                          r"(note that|note|remember that|remember|my note|for the record)\b[\s,:;-]*",
                          re.IGNORECASE)
NOTE_CUES = ("i play", "i like", "i want", "i usually", "i go", "i look", "i try", "i farm", "i gank",
             "i full clear", "ill", "im going", "my plan", "plan is", "play it", "play for")
NOTE_BLOCKED_INTENTS = ("drop", "recover", "menu", "status", "unclear")
NOTE_SECONDS = 180       # how long after the coach's ask a plain sentence can be the answer to it
ASK_BEFORE = 900         # the coach asks how you play a champion only in the first fifteen minutes


def note_intent(question: str, champion: str | None, pending: bool, intent: str) -> str | None:
    """The player's own sentence on how they play this champion, or None.

    pending is true for a short while after the coach asked for one; "note that ..." works at any time."""
    text = " ".join(str(question).split())
    if not text or text.endswith("?") or quick_intent(text) is not None or intent in NOTE_BLOCKED_INTENTS:
        return None
    named = _norm(champion or "")
    cues = NOTE_CUES + ((named,) if named else ())
    opening = NOTE_OPENING.match(text)
    said = text[opening.end():].strip() if opening else ""
    # "Remember that their jungler is bot side" is about this match, not about how the champion is played:
    # the sentence must be in the first person or name the champion.
    if len(said.split()) >= 3 and _says(_norm(said), cues):
        return said
    if not pending:
        return None
    normal = _norm(text)
    words = _core(normal)
    if not 2 <= len(normal.split()) <= 40:
        return None
    if (words and words[0] in QUESTION_WORDS) or _says(normal, QUESTION_TURNS):
        return None
    if _says(normal, [phrase for phrases in OFFER_POSITIONS for phrase in phrases]):
        return None   # "the first one" answers the offer, not the ask
    # A bare pick ("full clear") only commits the plan; it is kept as a note when it also says how ("I'll farm").
    return text if _says(normal, cues) else None


def plan_knowledge(role: str | None, champion: str | None) -> bool:
    """Whether anything on file says how this champion is played: a lesson naming it, the player's own
    note, or a pro lesson for the role with an Archetypes line naming one of its Data Dragon tags."""
    if lane_playbook.champion_lessons(champion) or lane_playbook.champion_notes(champion):
        return True
    return lane_playbook.pro_archetype_match(role, champion_tags(champion))


def plan_table(menu: tuple[Option, ...], role: str | None, champion: str | None) -> dict[str, Plan]:
    """Every plan with a step on the menu, in menu order, with the player's own name, words and marks."""
    def taught(plan: Plan, lesson: dict[str, str], done: set[str]) -> Plan:
        name = " ".join(lesson["name"].split()[:lane_playbook.NAME_WORD_LIMIT])
        words = tuple(word.strip() for word in lesson["pick"].split(",") if word.strip())
        if words and plan.id in PLANS:
            # The player's own words are added to a built-in plan's; "full clear" and "farm" keep working.
            words = tuple(dict.fromkeys((*words, *plan.words)))
        marks = lane_playbook.marks(lesson)
        for field, value in (("name", name), ("words", words), ("marks", marks)):
            if value and field not in done:
                done.add(field)
                plan = replace(plan, **{field: value})
        return plan

    table: dict[str, Plan] = {}
    for option in menu:
        if not option.plan or option.plan in table:
            continue
        plan, done = PLANS.get(option.plan), set()
        if plan:
            for trigger, key in LESSON_TRIGGERS.items():
                lesson = lane_playbook.lesson_for(role, champion, trigger) if key in plan.keys else None
                if lesson:
                    plan = taught(plan, lesson, done)
        else:
            lesson = next((found for found in lane_playbook.lessons_for(role, champion)
                           if "lesson_" + _slug(found["title"]) == option.plan), None)
            if not lesson:
                continue
            title = " ".join(lesson["title"].casefold().split()[:lane_playbook.NAME_WORD_LIMIT])
            plan = taught(Plan(option.plan, title, (option.key,), (title,),
                               safe=lesson["kind"] in ("recover", "trade")), lesson, done)
        table[plan.id] = plan
    return table


def plan_snapshot(plan: Plan, state: dict[str, Any], info: dict[str, Any] | None) -> dict[str, Any]:
    """The plan as chosen, with the observed numbers at that moment to measure progress against."""
    me = _active_player(state) or {}
    level_edge, cs_edge = _edges_now(state, info)
    return {
        "id": plan.id, "name": plan.name, "marks": plan.marks, "safe": plan.safe,
        "chosen_at": state["game_time_seconds"],
        "level": int(_number(me.get("level"))), "cs": int(_number(me.get("cs"))),
        "deaths": int(_number(me.get("deaths"))),
        "kills_assists": int(_number(me.get("kills")) + _number(me.get("assists"))),
        "enemy_level": info["enemy_level"] if info else None,
        "level_edge": level_edge, "cs_edge": cs_edge, "said": None, "off": False,
    }


# Progress reads only level, CS, game time, deaths and the enemy jungler's level against the
# snapshot taken at the choice; camp, crab, stack and position progress is never claimed.
def plan_progress(stored: dict[str, Any], state: dict[str, Any], info: dict[str, Any] | None,
                  keys_now: set[str]) -> dict[str, str]:
    """on_track, behind, broken or done for the chosen plan, with the chat tag and the spoken leads."""
    me = _active_player(state) or {}
    clock = state["game_time_seconds"]
    level, cs = int(_number(me.get("level"))), int(_number(me.get("cs")))
    deaths = max(0, int(_number(me.get("deaths"))) - stored["deaths"])
    enemy_level = info["enemy_level"] if info else None
    pace = _pace(state, info)
    plan_id, name = stored["id"], stored["name"]
    marks = tuple(tuple(mark) for mark in stored.get("marks") or ())
    level_marks = [mark for mark in marks if mark[0] == "level"]
    missed = [mark for mark in level_marks if level < mark[1] and clock > mark[2]]
    broken_mark = (any(clock > mark[2] + 45 for mark in missed)
                   or any(mark[0] == "enemy_under" and enemy_level is not None and enemy_level >= mark[1]
                          and clock <= mark[2] for mark in marks)
                   or (("no_deaths",) in marks and deaths >= 1))
    timed = [mark[2] for mark in marks if len(mark) == 3]
    keys = PLANS[plan_id].keys if plan_id in PLANS else (plan_id,)
    closed = False                # the window shut, which is not the same as the plan being carried out
    if plan_id == "six_crab":     # these three have a finish line the feed shows
        done = level >= 6
    elif plan_id == "scale":
        done = clock >= (info["until"] if info else 1200)
    elif plan_id == "recover":
        done = pace in ("even", "ahead")   # unknown is not level: the feed cannot compare
    elif timed:
        done = closed = clock > max(timed) and not missed and not broken_mark
    else:
        done = closed = not any(key in keys_now for key in keys)
    level_edge, cs_edge = _edges_now(state, info)
    slipped = ((level_edge is not None and stored["level_edge"] is not None
                and level_edge <= stored["level_edge"] - 1)
               or (cs_edge is not None and stored["cs_edge"] is not None and cs_edge <= stored["cs_edge"] - 15))
    if done:
        verdict = "done"
    elif (broken_mark or deaths >= 2
          or (plan_id == "six_crab" and enemy_level is not None and enemy_level >= 6 and level < 6)):
        verdict = "broken"
    elif missed or deaths == 1 or (pace == "behind" and not stored["safe"]) or slipped:
        verdict = "behind"
    else:
        verdict = "on_track"
    since = "no deaths since" if not deaths else "1 death since" if deaths == 1 else f"{deaths} deaths since"
    at = f"level {level} at {_clock(clock)}"
    upcoming = next((mark for mark in level_marks if clock <= mark[2]), None)
    if missed or upcoming:
        mark = missed[0] if missed else upcoming
        detail = f"{at} against the mark of level {mark[1]} by {_clock(mark[2])}"
    elif level_marks:
        detail = f"{at}, past the last mark of level {level_marks[-1][1]} by {_clock(level_marks[-1][2])}"
    else:
        detail = f"level {stored['level']} to {level}, CS {stored['cs']} to {cs} since then"
    title = name[:1].upper() + name[1:]
    # Each wording names what the feed showed: a missed mark is "behind the mark", anything else its own cause.
    if verdict == "done":
        word, lead, short = (("window closed", f"{title}: the window has passed", "Window passed") if closed else
                             ("done", f"{title} is done", "Plan's done"))
    elif verdict == "broken":
        word, lead, short = "off", f"{title} is off", "Plan's off"
    elif verdict == "on_track":
        if upcoming:
            word, lead, short = "on pace", f"On pace, {at}", "On pace"
        elif level_marks:
            word, lead, short = "past the last mark", f"Past the last mark, {at}", "Past the last mark"
        elif level_edge is None:
            word, lead, short = "no score comparison on the feed", "No deaths since you chose it", "No deaths since"
        else:
            word, lead, short = "no setback", "No setback since you chose it", "No setback"
    elif missed:
        word, lead, short = "behind", f"Behind the mark, {at}", "Behind"
    elif deaths == 1:
        word, lead, short = "slipping (a death)", f"One death since, {at}", "One death since"
    elif pace == "behind" and not stored["safe"]:
        word, lead, short = (
            ("slipping (behind their jungler on level or CS)", f"Behind their jungler, {at}", "Behind their jungler")
            if info else
            ("slipping (behind your lane opponent on level or CS)", f"Behind in lane, {at}", "Behind in lane"))
    else:
        word, lead, short = ("slipping (score edge down since the choice)", "Score edge down since you chose it",
                             "Edge down")
    return {"verdict": verdict, "lead": lead, "short": short,
            "chat": f"plan: {name} since {_clock(stored['chosen_at'])}, {word}: {detail}; {since}"}


def _plan_turn(state: dict[str, Any], question: str, board: CoordinatorBoard) -> dict[str, Any]:
    """What this question does to the player's plan, decided before the ranker is asked.

    Nothing is written to the board here; "writes" run only after the ranker has answered."""
    now = state["game_time_seconds"]
    role, info, me = active_role(state), jungle_clock(state), _active_player(state) or {}
    stored, offer, offer_at = board.plan_state()
    offer = offer if now - offer_at <= 120 else ()
    gold = None if state.get("practice_tool") else state.get("active_gold")
    # Before a first clear there is nothing to recall for, unless the gold for an item is already there.
    no_reset = (role == "jungle" and int(_number(me.get("level"))) <= 1 and now < 180
                and not (gold is not None and gold >= 1300))

    def options_for(asked: str, recover: str = "") -> tuple[Option, ...]:
        found = candidate_options(state, asked, recover=recover)
        kept = tuple(option for option in found if option.key != "lane_reset")
        return kept if no_reset and len(kept) >= 2 else found

    menu = options_for(PLAN_QUESTION, "add")
    plans = plan_table(menu, role, me.get("champion"))
    intent, target = (("ask", None) if _specific_objective_options(state, question) else
                      plan_intent(question, offer, plans, stored))
    active = stored if stored and not stored["off"] else None
    progress = plan_progress(active, state, info, {option.key for option in menu}) if active else None
    verdict = progress["verdict"] if progress else None
    slipping = "add" if verdict in ("behind", "broken") else ""
    turn: dict[str, Any] = {
        "options": (), "step": "", "safe_pair": False, "lead": "", "short": "", "tag": "", "more": False,
        "writes": [], "stored": stored, "verdict": verdict, "intent": intent, "file_writes": [],
        "names": {**{plan.id: plan.name for plan in PLANS.values()},
                  **{plan.id: plan.name for plan in plans.values()},
                  **{f"key:{key}": name for key, name in SHORT_NAMES.items()}},
    }

    def step_in(options: tuple[Option, ...], plan_id: str) -> str:
        return next((option.key for option in options if option.plan == plan_id), "")

    def title(name: str) -> str:
        return name[:1].upper() + name[1:]

    def aside(plan: dict[str, Any], at: int) -> str:
        return f"plan: none active ({plan['name']} {plan.get('off_word') or 'set aside'} at {_clock(at)})"

    broad = intent == "ask" and active is not None and _says(_norm(question), BROAD_PHRASES)
    if intent == "commit":
        plan = plans[target]
        turn["options"] = options_for(PLAN_QUESTION, "add" if plan.safe else "")
        turn["step"] = step_in(turn["options"], plan.id)
        turn["lead"] = f"{title(plan.name)}, locked"
        turn["tag"] = f"plan set at {_clock(now)}: {plan.name}"
        turn["writes"].append(lambda: board.choose(plan_snapshot(plan, state, info)))
    elif intent == "status" or broad:
        if active is None:
            turn["options"] = options_for(PLAN_QUESTION)
            if stored:
                turn["tag"] = aside(stored, stored.get("off_at", now))
                turn["lead"] = f"{title(stored['name'])} is {'off' if stored.get('off_word') else 'set aside'}"
            else:
                turn["tag"], turn["lead"] = "no plan set this match", "No plan set"
        else:
            turn["tag"] = progress["chat"]
            # A broad question repeats the verdict aloud only when it has changed.
            if intent == "status" or verdict != active["said"]:
                turn["lead"], turn["short"] = progress["lead"], progress["short"]
            if verdict == "broken":
                # Said once, with the safe lines. The plan then goes off, so later questions get the
                # ordinary options instead of recovery lines for the rest of the game.
                turn["options"] = options_for(PLAN_QUESTION, "add" if _pace(state, info) == "ahead" else "only")
                turn["writes"].append(lambda: board.mark_plan(said=verdict, off=True, off_at=now,
                                                              off_word="went off"))
            elif verdict == "done":
                turn["options"] = options_for(question if broad else PLAN_QUESTION)
                turn["writes"].append(lambda: board.mark_plan(said=verdict, off=False))
            else:
                turn["options"] = options_for(PLAN_QUESTION, slipping)
                turn["step"] = step_in(turn["options"], active["id"])
                turn["safe_pair"] = verdict == "behind"
                turn["writes"].append(lambda: board.mark_plan(said=verdict, off=False))
    elif intent == "recover":
        turn["options"] = options_for(PLAN_QUESTION, "only")
        turn["lead"] = f"{title(active['name'])} set aside" if active else "Safer lines"
        if active:
            turn["tag"] = aside({"name": active["name"]}, now)
            turn["writes"].append(lambda: board.mark_plan(off=True, off_at=now, off_word=""))
    elif intent == "menu":
        options = options_for(PLAN_QUESTION, slipping)
        if target == "fresh":
            heard = {key for key, _ in offer}
            kept = tuple(option for option in options if option.key not in heard
                         and not (stored and option.plan == stored["id"]))
            if len(kept) >= 2:
                options = kept
            else:   # say so, rather than read the same list again as if it were new
                turn["lead"], turn["tag"] = "Nothing new on the feed", "no further options on the feed right now"
        turn["options"], turn["more"] = options, True
    elif intent == "drop":
        turn["options"] = options_for(PLAN_QUESTION)
        if stored:
            turn["lead"], turn["tag"] = "Plan dropped", "plan dropped"
            turn["writes"].append(lambda: board.choose(None))
        else:
            turn["tag"] = "no plan set this match"
    elif intent == "unclear":
        turn["options"] = options_for(question)
        turn["short"] = "No plan change"
        if offer and _says(_norm(question), [phrase for phrases in OFFER_POSITIONS for phrase in phrases]):
            turn["lead"], turn["short"] = "That one's a single play, not a plan", "That's a single play"
            turn["tag"] = "no plan change: that one is a single play, not a plan to hold"
        else:
            turn["lead"] = "No plan change, that plan isn't on offer"
            turn["tag"] = "no plan change: that plan is not on offer right now"
    else:
        # A question about safety adds the safe lines without touching the plan.
        turn["options"] = options_for(question, "add" if target == "safe" else slipping)
    return turn


def _current_plan(turn: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """The stored plan as ranker context: the player's choice, its marks and the observed numbers."""
    stored, me = turn["stored"], _active_player(state) or {}
    return {
        "name": stored["name"], "chosen_at": _clock(stored["chosen_at"]),
        "then": {key: stored[key] for key in ("level", "cs", "deaths")},
        "now": {key: int(_number(me.get(key))) for key in ("level", "cs", "deaths")},
        "marks": [f"level {mark[1]} by {_clock(mark[2])}" if mark[0] == "level" else
                  f"enemy under {mark[1]} until {_clock(mark[2])}" if mark[0] == "enemy_under" else "no deaths"
                  for mark in stored.get("marks") or ()],
        "verdict": turn["verdict"], "set_aside": bool(stored["off"]),
    }


def long_plan(state: dict[str, Any]) -> dict[str, Any]:
    """Observed jungle clock plus the player's own matching lessons; {} for other roles."""
    info = jungle_clock(state)
    if info is None:
        return {}
    return {"jungle_clock": info,
            "lessons": [lesson["text"][:900] for lesson in
                        lane_playbook.lessons_for("jungle", info["champion"])[:3]]}


def minimap_facts(sightings, our_team: str | None) -> list[dict[str, Any]]:
    """Icons the minimap shows right now, with each champion's possible reach. Unclear icons stay unnamed."""
    facts = []
    for sighting in sightings:
        facts.append({
            "side": "ally" if sighting.team == our_team else "enemy",
            "champion": sighting.champion,
            "x": sighting.x,
            "y": sighting.y,
            "movement_kit": champion_movement(sighting.champion) if sighting.champion else [],
        })
    return facts


CHAMPION_KITS_LIMIT = 1400
PLAYER_NOTE_LIMIT = 400


def champion_kits(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Riot's static kit text for the player, their role opponent and, for laners, the enemy jungler.

    This is ranker background only: it is never copied into an option, a spoken line or a chat line."""
    role, me = active_role(state), _active_player(state) or {}
    enemy_team = _enemy_team(state)
    found: dict[str, dict[str, Any]] = {}
    champion = me.get("champion")
    kit = kit_summary(champion)
    notes = lane_playbook.champion_notes(champion) if champion else []
    if kit:
        found["you"] = {"champion": champion, "role": role, "kit": kit}
        if notes:
            found["you"]["player_note"] = " ".join(notes)[:PLAYER_NOTE_LIMIT]
    opponent = _role_player(state, enemy_team, role) if role else None
    # A jungler's role opponent is the enemy jungler, so only laners get the separate entry.
    jungler = _role_player(state, enemy_team, "jungle") if role and role != "jungle" else None
    for name, player in (("role_opponent", opponent), ("enemy_jungler", jungler)):
        kit = kit_summary(player.get("champion")) if player else ""
        if kit:
            found[name] = {"champion": player["champion"], "kit": kit}

    def size() -> int:
        return sum(len(entry["kit"]) + len(entry.get("player_note", "")) for entry in found.values())

    if size() > CHAMPION_KITS_LIMIT:
        found.pop("enemy_jungler", None)
    if size() > CHAMPION_KITS_LIMIT and "role_opponent" in found:
        found["role_opponent"]["kit"] = kit_summary(found["role_opponent"]["champion"], names_only=True)
    return found


def _champion_turn(turn: dict[str, Any], state: dict[str, Any], question: str,
                   board: CoordinatorBoard) -> str:
    """Keep the player's sentence on how they play their champion, or ask for one once a match.

    Returns the champion a note was taken for, or "". Nothing is written here: the note is a file write
    and the ask a board write, and both run only when the reply is delivered."""
    now = state["game_time_seconds"]
    role, champion = active_role(state), (_active_player(state) or {}).get("champion")
    if not champion:
        return ""
    asked = board.champion_asked()
    pending = (asked is not None and 0 <= now - asked <= NOTE_SECONDS
               and not lane_playbook.champion_notes(champion))
    said = note_intent(question, champion, pending, turn["intent"])
    stored = lane_playbook.note_text(said) if said else ""
    if stored:
        turn["file_writes"].append(lambda: lane_playbook.add_champion_note(champion, role, stored))
        turn["lead"] = turn["lead"] or f"Noted for {champion}"
        saved = f'your note for {champion} saved: "{stored}" (edit lane_playbook\\champion_notes.md)'
        turn["tag"] = f"{turn['tag']}; {saved}" if turn["tag"] else saved
        return champion
    if (turn["intent"] == "ask" and not (turn["lead"] or turn["short"] or turn["more"])
            and turn["stored"] is None and now < ASK_BEFORE and asked is None
            and champion_tags(champion) and not plan_knowledge(role, champion)):
        turn["lead"] = f"No notes on {champion} yet, tell me how you play it"
        turn["short"] = f"No {champion} notes; what's your plan"
        turn["tag"] = f"no notes on {champion}: say one sentence on how you play it, or use /note"
        # A board write, so a ranker failure or a superseded reply does not use up the ask.
        turn["writes"].append(lambda: board.mark_champion_asked(now))
    return ""


# "Explain more": the reason already given, cut into what was seen, why, what to check and what breaks it.
SENTENCE_SPLIT = re.compile(r"(?<!Dr\.)(?<=[.?!])\s+")
REASON_MARKERS = (("By your own benchmark:", "why"), ("You check:", "check"), ("Breaks it:", "breaks"))
# The plan note and the pace note that _jungle_options appends after the checks.
REASON_NOTES = re.compile(r"^(?:On .+ the same clears serve|You are (?:behind|ahead of) their jungler)")
# A lesson's own fields are explained at greater length than the first reply had room for.
LESSON_EXPLAIN = (("By your own benchmark:", "timeline", 500), ("You check:", "player_check", 400),
                  ("Breaks it:", "breaks", 400))
EXPLAIN_WORD_LIMIT = 80
EXPLAIN_OPTION_WORDS = 32
EXPLAIN_TEXT_LIMIT = 700
EXPLAIN_PRO = True   # False keeps pro principles out of the background layer
EXPLAIN_TITLES = {1: "why these two", 2: "what to check and what breaks them",
                  3: "background, not a read of this game", 4: "nothing more on these two"}
EXPLAIN_EMPTY = "nothing more on the feed for this one."
# Past tense: an explanation describes the read it elaborates on, not the game as it is now.
TAG_WORDS = {
    "ahead": "you were ahead of your role opponent on level or CS",
    "behind": "you were behind your role opponent on level or CS",
    "team_ahead": "your team was three or more kills up",
    "team_behind": "your team was three or more kills down",
    "numbers_up": "more of your team was alive",
    "numbers_down": "more of their team was alive",
    "objective_soon": "by patch timers an objective spawn was within two minutes",   # not a feed reading
    "enemy_jungler_dead": "their jungler was dead",
    "after_death": "your team had just lost a player",
    "after_kill": "your team had just got a kill",
    "after_objective": "an objective had just been taken",
    "tower_down": "a tower had just fallen",
    "gold_ready": "you had 1,300 gold or more",
    **{name: f'the feed matched the "{name.replace("_", " ")}" pattern' for name in PLAY_TRIGGERS},
}


def _sentences(text: str) -> list[str]:
    return [sentence for sentence in SENTENCE_SPLIT.split(str(text).strip()) if sentence]


def _reason_parts(reason: str) -> dict[str, list[str]]:
    """Each sentence of an option's reason in exactly one of seen, why, check and breaks, in order."""
    parts: dict[str, list[str]] = {"seen": [], "why": [], "check": [], "breaks": []}
    mode = "why"
    for sentence in _sentences(reason):
        if sentence.startswith("You are level "):
            parts["seen"].append(sentence)
            continue
        marked = next((part for marker, part in REASON_MARKERS if sentence.startswith(marker)), None)
        if marked:
            mode = marked
        elif REASON_NOTES.match(sentence):
            mode = "why"
        parts[mode].append(sentence)
    return parts


def _explain_parts(option: Option, lesson: dict | None) -> dict[str, list[str]]:
    parts = _reason_parts(option.reason)
    fields = [f"{marker} {_trim(lesson[field], limit)}" for marker, field, limit in LESSON_EXPLAIN
              if lesson and lesson.get(field)]
    if not fields:
        return parts
    # A lesson-backed option: the lesson's own fields, with the observed read before and the notes after.
    sentences = _sentences(option.reason)
    notes = next((index for index, sentence in enumerate(sentences) if REASON_NOTES.match(sentence)),
                 len(sentences))
    return _reason_parts(_join(" ".join(parts["seen"]), *fields, " ".join(sentences[notes:])))


def _aloud(sentence: str) -> str:
    """A chat sentence as it is spoken: nothing in brackets, no symbols a voice reads badly."""
    text = re.sub(r"\s*\([^)]*\)", "", sentence).replace("**", "")
    text = text.replace("on patch 26.1 timings", "on this patch's timings")
    text = re.sub(r"(?<![\w.:])\+(\d)", r"plus \1", text)
    text = re.sub(r"(?<![\w.:])-(\d)", r"minus \1", text)
    text = re.sub(r";\s*(\w)", lambda found: f". {found[1].upper()}", text)
    return " ".join(text.split())


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]


def _ended(text: str) -> str:
    text = text.strip()
    return text if text[-1:] in ".!?" else f"{text}."


def _option_lesson(option: Option, role: str | None, champion: str | None) -> dict | None:
    """The lessons.md entry whose wording an option carries, or that it was built from."""
    trigger = next((name for name, key in LESSON_TRIGGERS.items() if key == option.key), None)
    found = lane_playbook.lesson_for(role, champion, trigger) if trigger else None
    return found or next((lesson for lesson in lane_playbook.lessons_for(role, champion)
                          if "lesson_" + _slug(lesson["title"]) == option.key), None)


def _topic(pair: tuple[Option, Option], more: tuple[Option, ...], state: dict[str, Any], source: str,
           board: CoordinatorBoard | None, turn: dict[str, Any] | None) -> Topic:
    """What "explain more" may draw on later: the pair as offered, the player's own lessons and note, and
    one pro principle with the observed tags it shares. Nothing here is a new read of the game."""
    role, champion = active_role(state), (_active_player(state) or {}).get("champion") or ""
    table = turn["names"] if turn else {}

    def name(option: Option) -> str:
        # A plan name or a short name; failing both, the label's first clause, never a label cut mid-phrase.
        text = (table.get(option.plan) or table.get("key:" + option.key) or EXPLAIN_NAMES.get(option.key)
                or re.split(r"[,;:]", option.label)[0]).strip().rstrip(".!?")
        return text[:1].lower() + text[1:]

    names = (name(pair[0]), name(pair[1]))
    if turn is None or names[0].casefold() == names[1].casefold():
        names = (pair[0].label.strip().rstrip(".!?"), pair[1].label.strip().rstrip(".!?"))
    plans = plan_table(pair, role, champion) if turn else {}
    words = tuple(tuple(_plan_words(plans[option.plan])) if option.plan in plans else () for option in pair)
    principle = None
    if turn is not None:
        matches = lane_playbook.pro_matches(role, _phase(state["game_time_seconds"]), situation_tags(state))
        # Only a principle that shares an observed tag with this read: without one there is nothing to weigh
        # it against, and the first entry in file order would be read back whatever was asked.
        found = next((match for match in matches if match["shared"]), None)
        if found:
            principle = {key: found[key] for key in ("title", "situation", "our", "their", "check", "shared")}
    notes = lane_playbook.champion_notes(champion) if champion else []
    # The champion's plan lesson is background only for the role it is written for and before its Until.
    profile = lane_playbook.profile_for(champion)
    until = lane_playbook.until_seconds(profile["until"]) if profile else None
    if profile and (profile not in lane_playbook.lessons_for(role, champion)
                    or (until is not None and state["game_time_seconds"] >= until)):
        profile = None
    return Topic(
        match_key=board.match_key if board is not None else None,
        game_second=state["game_time_seconds"], source=source, pair=(pair[0], pair[1]),
        more=tuple(option.label for option in more), names=names, words=(words[0], words[1]),
        lessons=(_option_lesson(pair[0], role, champion), _option_lesson(pair[1], role, champion)),
        background={"profile": profile, "principle": principle,
                    "note": notes[0] if notes else "", "champion": champion},
        serial=board.match_serial if board is not None else 0)


def _explain_chat(header: str, labels: list[str], texts: list[str], extra: list[str]) -> str:
    def build(shown: list[str]) -> str:
        return "\n".join([header, f"**{labels[0]}** — {shown[0] or EXPLAIN_EMPTY}",
                          f"Otherwise: **{labels[1]}** — {shown[1] or EXPLAIN_EMPTY}", *extra, "Your call."])

    texts = [_trim(text, EXPLAIN_TEXT_LIMIT) for text in texts]
    chat = build(texts)
    if len(chat) > CHAT_LIMIT:   # both are cut by the same amount, as format_options does
        room = CHAT_LIMIT - (len(chat) - sum(map(len, texts)))
        chat = build([_trim(text, max(room // 2, 200)) for text in texts])
    return chat


def _explain_speech(opener: str, names: list[str], sentences: list[list[str]]) -> str:
    """Whole sentences only, each alternative inside its own word budget; a long one stays in chat."""
    budget = min(EXPLAIN_OPTION_WORDS, (EXPLAIN_WORD_LIMIT - len(opener.split()) - 2) // 2)
    markers = tuple(marker for marker, _ in REASON_MARKERS)
    spoken = [opener]
    for name, listed in zip(names, sentences):
        head = f"{_capital(name)}."
        used, kept, cut, held = len(head.split()), [], False, False
        for sentence in listed:
            marked = sentence.startswith(markers)
            if marked or REASON_NOTES.match(sentence):
                held = False   # a new part starts here
            if held:
                continue
            aloud = _aloud(sentence)
            if aloud and used + len(aloud.split()) <= budget:
                kept.append(aloud)
                used += len(aloud.split())
            elif marked:
                # "By your own benchmark:" did not fit. Without it the rest of that part would be heard as
                # the coach's own claim, so the whole part stays in chat.
                held = cut = True
        rest = ("The detail on that one is in chat." if listed and (cut or not kept) else
                "" if kept else "Nothing more on the feed for that one.")
        if rest and used + len(rest.split()) <= budget:
            kept.append(rest)
        spoken.append(" ".join([head, *kept]))
    return " ".join([*spoken, "Your call."])


def _fit_sentence(principle: dict, stamp: str) -> str:
    """How the principle sits against the read, from observed tags only."""
    shared = [tag for tag in principle.get("shared") or () if tag in TAG_WORDS]
    seen = [TAG_WORDS[tag] for tag in shared if tag != "objective_soon"]
    parts = [f"At {stamp} the feed showed: {'; '.join(seen)}."] if seen else []
    if "objective_soon" in shared:   # a patch constant, or one applied to a kill event: not something the feed shows
        parts.append(f"At {stamp}, {TAG_WORDS['objective_soon']}.")
    return " ".join(parts) or "Nothing on the feed confirms it or rules it out."


def explain(topic: Topic, focus: int | None = None) -> Reply:
    """The next layer of explanation of a delivered read: why, then checks, then background, then done.

    Every layer names both alternatives and leaves the choice with the player. Nothing is read from the
    game and the topic is not changed; reply.layer says which layer this was."""
    order = (1, 0) if focus == 1 else (0, 1)
    pair = [topic.pair[index] for index in order]
    labels = [option.label for option in pair]
    first, second = (topic.names[index] for index in order)
    lessons = [topic.lessons[index] for index in order]
    parts = [_explain_parts(option, lesson) for option, lesson in zip(pair, lessons)]
    stamp = _clock(topic.game_second)
    background = topic.background or {}
    profile, note, champion = background.get("profile"), background.get("note") or "", background.get("champion")
    principle = background.get("principle") if EXPLAIN_PRO else None

    def header(layer: int) -> str:
        return f"Game read, continued ({topic.source}, as of {stamp}): {EXPLAIN_TITLES[layer]}."

    def opening(text: str) -> str:
        # The reasons carry what the feed showed then (a respawn timer, a score edge) in the present tense,
        # so a layer that speaks them says which read they are from, however recent it is.
        return f"From the {stamp} read: {text}"

    def reply(layer: int, chat: str, spoken: str) -> Reply:
        made = Reply(chat)
        made.spoken, made.layer = spoken, layer
        return made

    for layer in range(topic.layer + 1, 4):
        if layer in (1, 2):
            shown, said = ((("seen", "why"), ("why",)) if layer == 1 else
                           (("check", "breaks"), ("check", "breaks")))
            texts = [" ".join(sentence for key in shown for sentence in part[key]) for part in parts]
            if not any(texts):
                continue
            extra = ([f"Also offered: {'; '.join(label.rstrip('.!?') for label in topic.more)}."]
                     if layer == 1 and topic.more else [])
            opener = opening(f"{_capital(first)}, or {second}." if layer == 1 else
                             f"Before you pick {first} or {second}.")
            spoken = _explain_speech(opener, [first, second],
                                     [[sentence for key in said for sentence in part[key]] for part in parts])
            return reply(layer, _explain_chat(header(layer), labels, texts, extra), spoken)
        # Background: the player's own lessons and note, and one pro tendency, none of it a read of this game.
        # The champion's plan lesson stands behind a jungle option of its own family, and behind nothing else.
        behind = [lesson or (profile if profile and option.key.startswith("jungle_") and option.family
                             and option.family == profile.get("plan") else None)
                  for option, lesson in zip(pair, lessons)]
        if not (any(behind) or note or principle):
            continue
        texts = []
        for lesson in behind:
            if not lesson:
                texts.append("no lesson of yours behind this one.")
                continue
            source, check = _trim(lesson.get("source", ""), 300), _trim(lesson.get("feed_check", ""), 300)
            # The lesson's "Feed check" is its condition as written, never a statement about this read.
            texts.append(_join(f'Your lesson "{lesson["title"]}".',
                               f"Source, in your words: {_ended(source)}" if source else "",
                               f"Its condition, as your lesson states it (not checked against this read): "
                               f"{_ended(check)}" if check else ""))
        extra = [f"Your own note on {champion}: {_ended(note)}"] if note else []
        fit = _fit_sentence(principle, stamp) if principle else ""
        if principle:
            extra.append(_trim(_join(
                f"Pro tendency (background from pro games, not this match): {_ended(principle['title'])}",
                f"If this holds (not observed here): {principle['situation']}",
                f"Our side: {principle['our']}", f"Their side: {principle['their']}",
                f"You check: {principle['check']}" if principle.get("check") else ""), 900) + f" {fit}")
        opener = f"Background on {first} or {second}, not a read of this game."
        closing = f"Still {first} or {second}. Your call."
        room = EXPLAIN_WORD_LIMIT - len(opener.split()) - len(closing.split())
        spoken = [opener]

        def say(sentence: str) -> bool:
            nonlocal room
            if len(sentence.split()) > room:
                return False
            spoken.append(sentence)
            room -= len(sentence.split())
            return True

        # Only a lesson that stands behind one of the two alternatives is named aloud.
        for title in dict.fromkeys(lesson["title"] for lesson in behind if lesson):
            say(f"Your lesson {title} is from your own lessons file, not something I measured.")
        if note and not say(f"Your own note on {champion}: {_ended(note)}"):
            say(f"Your own note on {champion} is in chat.")
        # The principle's two sides stay in chat. Aloud it is a title with the fit, which is what weighs it
        # against the read, so the title is never spoken without it; the player's check follows if it fits.
        if principle:
            title = f"A pro tendency, as background only: {_ended(principle['title'])}"
            if len(title.split()) + len(fit.split()) <= room:
                say(title)
                say(fit)
                if principle.get("check"):
                    say(f"It depends on something I can't see: {principle['check']}")
            else:
                say("A pro tendency is in chat.")
        return reply(3, _explain_chat(header(3), labels, texts, extra), " ".join([*spoken, closing]))
    done = "\n".join([header(4), f"**{labels[0]}**", f"Otherwise: **{labels[1]}**", "Your call."])
    return reply(4, done, f"That's everything on {first} or {second}. Your call.")


NOTE_NOT_SAVED = "I could not write lane_playbook\\champion_notes.md, so your note was not saved."


def _note_writes(writes) -> str:
    """Run the note appends. A file that cannot be written never blocks the answer: the fault is logged
    and comes back as a line for the player, since the reply already says the note was saved."""
    try:
        for write in writes:
            write()
    except OSError as exc:
        print(f"Champion note not saved: {type(exc).__name__}: {exc}", flush=True)
        return NOTE_NOT_SAVED
    return ""


def coach(question: str, style: str, *, allow_demo_fallback: bool = False,
          coordinator_board: CoordinatorBoard | None = None, minimap=None,
          defer_board: bool = False, champion_ask: bool = False) -> str:
    q = question.casefold()
    if any(phrase in q for phrase in ("can you hear", "can you listen", "microphone", "voice input")):
        return ("I can listen to the Discord call after you run /listen in a text channel. "
                "Then say 'Coach, ...' followed by your question. Use /stoplisten to turn listening off.")
    source = "live game"
    try:
        game = read_live_game()
    except (OSError, ValueError, urllib.error.URLError):
        if not allow_demo_fallback:
            return "I can't read a live League match on this PC right now. Start a game here, then ask again."
        game = {"gameData": {"gameTime": 900, "gameMode": "CLASSIC"},
                "activePlayer": {"riotId": "Demo#NA1", "currentGold": 1400},
                "allPlayers": [{"riotId": "Demo#NA1", "team": "ORDER", "championName": "Ashe", "level": 9,
                                "isDead": False, "scores": {"kills": 2, "deaths": 1, "assists": 3}}],
                "events": {"Events": [{"EventName": "GameStart", "EventTime": 0}]}}
        source = "demo data"
    state = summarize_game(game)
    if source == "live game" and (not state["our_team"] or len(state["players"]) < 2):
        return "The live game feed is missing player or team data, so I can't make a grounded team call yet."
    # Plan memory lives on the board, so it exists only for a real match with coordinators running.
    live = coordinator_board is not None and source == "live game"
    if live:
        coordinator_board.observe(state)
    # lessons.md reloads live, so a bad edit is logged on the first answer after it is saved.
    for problem in lane_playbook.fresh_lesson_problems(LESSON_TRIGGERS):
        print(f"Lesson file: {problem}", flush=True)
    for problem in lane_playbook.fresh_pro_lesson_problems():
        print(f"Pro lesson file: {problem}", flush=True)
    turn = _plan_turn(state, question, coordinator_board) if live else None
    noted = _champion_turn(turn, state, question, coordinator_board) if turn and champion_ask else ""
    options = turn["options"] if turn else candidate_options(state, question)
    try:
        key = load_jev_key()
    except (OSError, RuntimeError):
        return "The Jev key file is invalid. Put only one key on one line in the configured file."
    if not key:
        return "Jev key missing; I won't present a fixed ranking as a live recommendation."
    try:
        ranking_state = {"game": state, "team_question": question[:500], "team_style": style}
        plan = long_plan(state)
        if plan:
            ranking_state["long_plan"] = plan
        kits = champion_kits(state)
        if kits:
            ranking_state["champion_kits"] = kits
        if live:
            if turn["stored"]:
                ranking_state["current_plan"] = _current_plan(turn, state)
            principles = lane_playbook.pro_lessons_for(active_role(state), _phase(state["game_time_seconds"]),
                                                       situation_tags(state))
            if principles:
                ranking_state["pro_principles"] = principles
            ranking_state["coordinator_briefing"] = coordinator_board.briefing(detail_role=active_role(state))
            ranking_state["lane_fundamentals"] = lane_playbook.fundamentals_summary()
            if minimap:
                ranking_state["minimap_visible"] = minimap_facts(minimap, state.get("our_team"))
            ranking_state["recognized_plays"] = [play["text"] for play in
                                                 lane_playbook.plays_for(recognized_plays(state))]
        scores = jev_rank(ranking_state, key, options)
    except (OSError, KeyError, ValueError, urllib.error.URLError):
        unavailable = "Jev is unavailable right now. I won't guess from incomplete data; try again shortly."
        if not noted:
            return unavailable
        # The player's sentence is theirs whether or not the ranker answered; the board stays untouched.
        kept = Reply(f"{unavailable} I kept your note on {noted}.")
        note_writes = list(turn["file_writes"])

        def keep() -> str:
            return _note_writes(note_writes)

        if defer_board:
            kept.commit = keep
            return kept
        problem = keep()
        return Reply(f"{unavailable} {problem}") if problem else kept
    if turn is None:
        pair = two_options(scores, options)
        reply = format_options(pair, source=source, facts=evidence(state))
        reply.topic = _topic(pair, (), state, source, coordinator_board, None)
        return reply
    ranked = sorted(options, key=lambda option: (-scores.get(option.key, 0), option.key))
    must: tuple[str, ...] = (turn["step"],) if turn["step"] else ()
    if must and turn["safe_pair"]:
        # Behind the mark: the plan's own step, next to the best-ranked safe line from another plan.
        safer = next((option.key for option in ranked if option.key in SAFE_KEYS and option.key != turn["step"]
                      and option.plan != turn["stored"]["id"]), None)
        must += (safer,) if safer else ()
    pair = two_options(scores, options, must=must)
    more: list[Option] = []
    if turn["more"]:
        named = {pair[0].plan, pair[1].plan}
        for option in ranked:
            if len(more) < 2 and option not in pair and option.plan and option.plan not in named:
                named.add(option.plan)
                more.append(option)
    # The ranker has answered. The board and the note file change in commit(): at once by default, or,
    # with defer_board, only when the caller has delivered the reply.
    pairs = tuple((option.key, option.plan) for option in (*pair, *more))
    key_at_build, now = (coordinator_board.match_key, coordinator_board.match_serial), state["game_time_seconds"]
    writes, file_writes = list(turn["writes"]), list(turn["file_writes"])

    def commit() -> str:
        with coordinator_board.lock:
            if (coordinator_board.match_key, coordinator_board.match_serial) != key_at_build:
                return ""                   # the match changed while this was computed
            for write in writes:
                write()
            coordinator_board.offered(pairs, now)
        return _note_writes(file_writes)    # the note append, outside the lock

    reply = format_options(pair, source=source, facts=evidence(state) + (f"; {turn['tag']}" if turn["tag"] else ""),
                           lead=turn["lead"], short_lead=turn["short"], more=tuple(more), names=turn["names"])
    reply.topic = _topic(pair, tuple(more), state, source, coordinator_board, turn)
    if defer_board:
        reply.commit = commit
    else:
        commit()
    return reply
