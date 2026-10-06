"""Role playbooks in lane_playbook/: mechanics for each lane, not patch facts.

Patch-specific timers and values live in MACRO_RESEARCH.md. Each role file has a
"## Summary" section that every briefing carries, and the full text that is sent
only for the role the active player is playing.
"""

from __future__ import annotations

import datetime
import re
from functools import lru_cache
from pathlib import Path

import champion_metadata


PLAYBOOK_ROOT = Path(__file__).with_name("lane_playbook")
ROLES = ("top", "jungle", "mid", "bot", "support")
FULL_TEXT_LIMIT = 9000


def _parse(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = "intro"
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[current] = "\n".join(lines).strip()
            current = line[3:].strip().casefold()
            lines = []
        else:
            lines.append(line)
    sections[current] = "\n".join(lines).strip()
    return sections


@lru_cache(maxsize=None)
def _file(name: str) -> str:
    path = PLAYBOOK_ROOT / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise FileNotFoundError(f"Playbook is empty: {path.name}")
    return text


def summary(role: str) -> str:
    """Short mechanics summary for any role; safe to send in every briefing."""
    return _parse(_file(role)).get("summary", "")


def full(role: str, limit: int = FULL_TEXT_LIMIT) -> str:
    """Full role playbook, trimmed at a section boundary when it is too long."""
    text = _file(role)
    if len(text) <= limit:
        return text
    cut = text.rfind("\n## ", 0, limit)
    return text[:cut].rstrip() if cut > 0 else text[:limit]


def fundamentals() -> str:
    """Cross-lane rules: phases, waves, trades, vision, objectives, death timers."""
    return _file("fundamentals")


def fundamentals_summary() -> str:
    return summary("fundamentals")


def _play(title: str, body: list[str]) -> dict[str, str]:
    def field(name: str) -> str:
        return next((line.split(":", 1)[1].strip() for line in body if line.startswith(f"{name}:")), "")
    text = "\n".join(body).strip()
    return {"title": title, "trigger": field("Trigger"), "summary": field("Summary"),
            "text": f"## {title}\n{text}"}


@lru_cache(maxsize=1)
def plays() -> tuple[dict[str, str], ...]:
    """Recognized macro plays from plays.md; each has a trigger name checked in coach.py."""
    found: list[dict[str, str]] = []
    title: str | None = None
    body: list[str] = []
    for line in _file("plays").splitlines():
        if line.startswith("## "):
            if title:
                found.append(_play(title, body))
            title, body = line[3:].strip(), []
        elif title:
            body.append(line)
    if title:
        found.append(_play(title, body))
    return tuple(play for play in found if play["trigger"])


def plays_for(triggers: tuple[str, ...] | list[str]) -> list[dict[str, str]]:
    return [play for play in plays() if play["trigger"] in triggers]


LESSON_FIELDS = {
    "applies to": "applies", "plan": "plan", "trigger": "trigger", "until": "until", "goal": "goal",
    "timeline": "timeline", "feed check": "feed_check", "player check": "player_check",
    "breaks it": "breaks", "say it like": "say", "source": "source",
    "offer at": "offer_at", "kind": "kind", "name": "name", "pick it with": "pick", "on track": "marks",
}
LESSON_PLANS = ("farm", "gank")
# "Offer at" stages: the jungle_clock stages, plus "lane" for laners before 14:00.
LESSON_STAGES = ("first_clear", "second_clear", "six_race", "six_behind", "six_first", "post_six",
                 "mid_game", "lane")
LESSON_KINDS = ("farm", "gank", "invade", "cover", "trade", "recover")
NAME_WORD_LIMIT = 5
SAY_WORD_LIMIT = 14
SAY_PLACEHOLDERS = ("level", "champion", "enemy", "enemy_level", "clock")
# Longest chat text taken from each field; a longer one is cut at a sentence end.
LESSON_TEXT_LIMITS = {"timeline": 300, "player_check": 200, "breaks": 200}
ROLE_WORDS = {**{role: role for role in ROLES}, "jungler": "jungle", "junglers": "jungle",
              "middle": "mid", "adc": "bot", "supports": "support"}


def _name(text: str | None) -> str:
    """Champion names compared without case, spaces or punctuation: "Bel'Veth" -> "belveth"."""
    return "".join(c for c in str(text or "").casefold() if c.isalnum())


def until_seconds(text: str | None) -> int | None:
    """ "25:00", "25" or "25 minutes" as seconds; None when it does not read as a game time."""
    found = re.fullmatch(r"(\d{1,3})(?::([0-5]\d))?\s*(?:m|min|mins|minutes?)?\.?", str(text or "").strip().casefold())
    return int(found[1]) * 60 + int(found[2] or 0) if found else None


def _lesson(title: str, body: list[str], fields: dict[str, str] = LESSON_FIELDS) -> dict[str, str]:
    lesson = {"title": title, **{key: "" for key in fields.values()}}
    current = None
    for line in body:
        head, separator, value = line.partition(":")
        # Dictated notes arrive as "- Goal: ..." or "**Goal:** ..." as often as plain "Goal: ...".
        key = fields.get(head.strip(" -*").casefold()) if separator else None
        if key:
            current = None if lesson[key] else key
            if current:
                lesson[key] = value.strip(" *")
        elif current and line.strip():
            # A wrapped or bulleted line belongs to the field above it.
            lesson[current] = f"{lesson[current]} {line.strip().lstrip('-* ')}".strip()
        else:
            current = None
    if "plan" in lesson:
        lesson["plan"] = lesson["plan"].casefold().strip(" .")
    if "trigger" in lesson:
        lesson["trigger"] = "_".join(re.findall(r"[a-z0-9]+", lesson["trigger"].casefold()))
    if "kind" in lesson:
        lesson["kind"] = lesson["kind"].casefold().strip(" .")
    text = "\n".join(body).strip()
    lesson["text"] = f"## {title}\n{text}"
    return lesson


@lru_cache(maxsize=8)
def _lessons(path: str, stamp, kind: str = "lesson") -> tuple[dict[str, str], ...] | None:
    fields = {"pro": PRO_FIELDS, "note": NOTE_FIELDS}.get(kind, LESSON_FIELDS)
    # stamp is the file's mtime, so an edit loads on the next answer without a restart.
    try:
        raw = Path(path).read_bytes()
        # Windows PowerShell 5.1 redirection writes UTF-16; Notepad adds a UTF-8 BOM.
        text = raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    found: list[dict[str, str]] = []
    title: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if title:
                found.append(_lesson(title, body, fields))
            title, body = line[3:].strip(), []
        elif title:
            body.append(line)
    if title:
        found.append(_lesson(title, body, fields))
    return tuple(found)


def lessons() -> tuple[dict[str, str], ...]:
    """The player's own long-term plans from lessons.md; a missing or blank file gives none."""
    path = PLAYBOOK_ROOT / "lessons.md"
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return ()
    return _lessons(str(path), stamp) or ()


def _targets(lesson: dict[str, str]) -> tuple[list[str], list[str]]:
    """Roles and champion names in "Applies to"; "Bel'Veth jungle" and "junglers" both read."""
    roles: list[str] = []
    champions: list[str] = []
    for token in lesson["applies"].split(","):
        words = [(word, ROLE_WORDS.get(word.casefold().strip("."))) for word in token.split()]
        roles += [role for _, role in words if role]
        champion = " ".join(word for word, role in words if not role)
        if _name(champion):
            champions.append(champion)
    return roles, champions


def _applies(lesson: dict[str, str], role: str | None, champion: str | None) -> bool:
    roles, champions = _targets(lesson)
    if not (roles or champions) or (roles and role not in roles):
        return False
    return not champions or _name(champion) in [_name(named) for named in champions]


def lessons_for(role: str | None, champion: str | None) -> list[dict[str, str]]:
    """Matching lessons, most specific first: one champion, then a champion list, then the whole role."""
    found = [lesson for lesson in lessons() if _applies(lesson, role, champion)]
    return sorted(found, key=lambda lesson: len(_targets(lesson)[1]) or 999)


def lesson_for(role: str | None, champion: str | None, trigger: str) -> dict[str, str] | None:
    return next((lesson for lesson in lessons_for(role, champion) if lesson["trigger"] == trigger), None)


def _tags(text: str) -> list[str]:
    """A comma list as names: "Six race, lane" -> ["six_race", "lane"]."""
    found = ("_".join(re.findall(r"[a-z0-9]+", part.casefold())) for part in str(text or "").split(","))
    return [name for name in found if name]


def plan_lessons(role: str | None, champion: str | None, stage: str, clock: float) -> list[dict[str, str]]:
    """Lessons that are plans of their own at this stage: "Offer at", no Trigger, Until not passed."""
    found = []
    for lesson in lessons_for(role, champion):
        until = until_seconds(lesson["until"])
        if (lesson["offer_at"] and not lesson["trigger"] and stage in _tags(lesson["offer_at"])
                and (until is None or clock < until)):
            found.append(lesson)
    return found[:2]


def _mark(clause: str) -> tuple | None:
    text = " ".join(clause.casefold().split()).strip(" .")
    found = re.fullmatch(r"level (\d{1,2}) by (\d{1,3}):([0-5]\d)", text)
    if found:
        return ("level", int(found[1]), int(found[2]) * 60 + int(found[3]))
    found = re.fullmatch(r"enemy under (\d{1,2}) until (\d{1,3}):([0-5]\d)", text)
    if found:
        return ("enemy_under", int(found[1]), int(found[2]) * 60 + int(found[3]))
    return ("no_deaths",) if text in ("no deaths", "no death") else None


def marks(lesson: dict[str, str]) -> tuple:
    """ "On track" as checks on observed level, time and deaths; unreadable clauses are skipped."""
    found = (_mark(clause) for clause in lesson.get("marks", "").split(";") if clause.strip())
    return tuple(mark for mark in found if mark)


def profile_for(champion: str | None) -> dict[str, str] | None:
    """The lesson with a Plan that names this champion; a single-champion entry beats a list."""
    wanted = _name(champion)
    found = [lesson for lesson in lessons() if lesson["plan"] and wanted
             and wanted in [_name(named) for named in _targets(lesson)[1]]]
    return min(found, key=lambda lesson: len(_targets(lesson)[1]), default=None)


def champion_lessons(champion: str | None) -> list[dict[str, str]]:
    """Lessons whose "Applies to" names this champion; role-wide lessons are not about a champion."""
    wanted = _name(champion)
    return [lesson for lesson in lessons()
            if wanted and wanted in [_name(named) for named in _targets(lesson)[1]]]


# champion_notes.md: the player's own sentences on how they play a champion, appended by the coach.
NOTE_FIELDS = {"role": "role", "note": "note", "added": "added"}
NOTE_CHAR_LIMIT = 200
NOTES_LIMIT = 3
NOTES_CHAR_LIMIT = 400
NOTES_HEADER = ("# Champion notes: my own words on how I play each champion\n\n"
                "The coach appends a block here when I tell it how I play a champion. Edit or delete freely.\n"
                "These are my own statements, not facts about any match.\n")


def _fold(text: str) -> str:
    """Letters and digits only, lower case: how two notes are compared."""
    return " ".join("".join(c if c.isalnum() else " " for c in str(text).casefold().replace("'", "")).split())


def note_text(text: str) -> str:
    """A note as it is stored: one line, no leading list or heading marks, 200 characters at most."""
    line = " ".join(str(text or "").split()).lstrip("#-* ").strip()
    if len(line) > NOTE_CHAR_LIMIT:
        cut = line[:NOTE_CHAR_LIMIT]
        line = (cut[:cut.rfind(" ")] if " " in cut else cut).rstrip()
    return line


def _notes(champion: str | None) -> list[dict[str, str]]:
    path = PLAYBOOK_ROOT / "champion_notes.md"
    try:
        status = path.stat()
    except OSError:
        return []
    # Two appends can land inside one tick of the file clock; the size always changes.
    stamp = (status.st_mtime_ns, status.st_size)
    wanted = _name(champion)
    return [entry for entry in _lessons(str(path), stamp, "note") or ()
            if wanted and _name(entry["title"]) == wanted and entry["note"]]


def champion_notes(champion: str | None) -> list[str]:
    """The player's own notes on this champion, newest first: three at most, 400 characters in total."""
    found: list[str] = []
    for entry in reversed(_notes(champion)):   # the file is append-only, so later is newer
        note = note_text(entry["note"])        # a hand-edited note is read at the length the coach stores
        # One that does not fit is passed over, so a long newest note cannot hide the others.
        if note and len(found) < NOTES_LIMIT and sum(map(len, found)) + len(note) <= NOTES_CHAR_LIMIT:
            found.append(note)
    return found


def add_champion_note(champion: str, role: str | None, text: str) -> str:
    """Append the player's sentence to champion_notes.md and return the text as stored.

    OSError when the file cannot be written, or cannot be read back as text: a note appended to a file
    the coach cannot read would be reported as saved and never used."""
    stored = note_text(text)
    if not stored or not _name(champion):
        return ""
    if any(_fold(entry["note"]) == _fold(stored) for entry in _notes(champion)):
        return stored   # said before: nothing is written twice
    path = PLAYBOOK_ROOT / "champion_notes.md"
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raw = b""
    # A file saved by Windows PowerShell 5.1 is UTF-16; the block is appended in the file's own encoding.
    encoding = {b"\xff\xfe": "utf-16-le", b"\xfe\xff": "utf-16-be"}.get(raw[:2], "utf-8")
    try:
        raw.decode("utf-16" if encoding != "utf-8" else "utf-8-sig")
    except UnicodeDecodeError as exc:
        raise OSError("champion_notes.md is not readable as text, so nothing was appended to it") from exc
    newline = "\n".encode(encoding)
    block = (f"\n## {' '.join(str(champion).split())}\nRole: {role or 'unknown'}\nNote: {stored}\n"
             f"Added: {datetime.date.today().isoformat()}\n")
    if not raw:
        block = NOTES_HEADER + block
    elif not raw.endswith(newline):
        block = "\n" + block
    with path.open("ab") as handle:   # append only: what is already in the file is never rewritten
        handle.write(block.encode(encoding))
    return stored


def lesson_problems(triggers) -> list[str]:
    """Readable faults in lessons.md for the log; a broken file must not stop the bot."""
    problems: list[str] = []
    try:
        path = PLAYBOOK_ROOT / "lessons.md"
        if path.exists() and _lessons(str(path), path.stat().st_mtime_ns) is None:
            return ["lessons.md could not be read as UTF-8 text, so no lessons are loaded"]
        for lesson in lessons():
            title, trigger, say = lesson["title"], lesson["trigger"], lesson["say"]
            roles, champions = _targets(lesson)
            if not (roles or champions):
                problems.append(f"'{title}' has no 'Applies to' line naming a role or champion, so it never applies")
            for named in champions:
                # Checked only when the champion data file loaded; without it every name would be flagged.
                if champion_metadata.known_champions() and _name(named) not in champion_metadata.known_champions():
                    problems.append(f"'{title}' applies to '{named}', which is not a role or champion name")
            if trigger and trigger not in triggers:
                problems.append(f"'{title}' has unknown Trigger '{trigger}'")
            if trigger and not say:
                problems.append(f"'{title}' has a Trigger but no 'Say it like' line")
            if len(say.split()) > SAY_WORD_LIMIT:
                problems.append(f"'{title}' has a 'Say it like' line over {SAY_WORD_LIMIT} words")
            unknown = [name for name in re.findall(r"\{([^}]*)\}", say) if name not in SAY_PLACEHOLDERS]
            if unknown or say.count("{") != say.count("}"):
                problems.append(f"'{title}' has a 'Say it like' placeholder the coach cannot fill"
                                f"{' ({' + unknown[0] + '})' if unknown else ''}; the built-in line is spoken instead")
            offer = _tags(lesson["offer_at"])
            for stage in offer:
                if stage not in LESSON_STAGES:
                    problems.append(f"'{title}' has unknown Offer at stage '{stage}'")
            if lesson["kind"] and lesson["kind"] not in LESSON_KINDS:
                problems.append(f"'{title}' has Kind '{lesson['kind']}'; use one of {', '.join(LESSON_KINDS)}")
            if offer and trigger:
                problems.append(f"'{title}' has both Offer at and Trigger; use one or the other")
            if offer and not lesson["goal"]:
                problems.append(f"'{title}' has Offer at but no Goal line, so it is never offered")
            if offer and not say:
                problems.append(f"'{title}' has Offer at but no 'Say it like' line")
            if len(lesson["name"].split()) > NAME_WORD_LIMIT:
                problems.append(f"'{title}' has a Name over {NAME_WORD_LIMIT} words")
            for clause in lesson["marks"].split(";"):
                if clause.strip() and _mark(clause) is None:
                    problems.append(f"'{title}' has an On track mark the coach cannot read ('{clause.strip()}'); "
                                    "write it like level 4 by 3:30")
            if lesson["plan"] and lesson["plan"] not in LESSON_PLANS:
                problems.append(f"'{title}' has Plan '{lesson['plan']}'; use farm or gank")
            if lesson["until"] and until_seconds(lesson["until"]) is None:
                problems.append(f"'{title}' has Until '{lesson['until']}'; write it like 25:00")
            for field, limit in LESSON_TEXT_LIMITS.items():
                if len(lesson[field]) > limit:
                    problems.append(f"'{title}' has a {field.replace('_', ' ')} over {limit} characters; "
                                    "chat shows only the first sentences")
    except Exception as exc:
        problems.append(f"lessons.md could not be checked ({type(exc).__name__})")
    return problems


_reported: tuple[str, int | None] | None = None


def fresh_lesson_problems(triggers) -> list[str]:
    """lesson_problems, once per saved version of the file, so a bad live edit shows in the log."""
    global _reported
    path = PLAYBOOK_ROOT / "lessons.md"
    try:
        stamp = (str(path), path.stat().st_mtime_ns)
    except OSError:
        stamp = (str(path), None)
    if stamp == _reported:
        return []
    _reported = stamp
    return lesson_problems(triggers)


# pro_lessons.md: tendencies paraphrased from professional games. They are background for the
# ranker only and never become a spoken option.
PRO_FIELDS = {
    "roles": "roles", "phase": "phase", "when": "when", "situation": "situation", "our side": "our",
    "their side": "their", "player check": "check", "seen in": "seen", "archetypes": "archetypes",
}
PRO_PHASES = ("early", "lane", "mid", "late")
# Data Dragon's champion tags; an "Archetypes:" line says which kinds of champion a principle is about.
PRO_ARCHETYPES = ("Fighter", "Tank", "Mage", "Assassin", "Marksman", "Support")
# Situations coach.situation_tags can observe; the last six are the PLAY_TRIGGERS names.
PRO_TAGS = (
    "ahead", "behind", "team_ahead", "team_behind", "numbers_up", "numbers_down", "objective_soon",
    "enemy_jungler_dead", "after_death", "after_kill", "after_objective", "tower_down", "gold_ready",
    "punished_split", "dive_setup", "objective_swap", "split_pressure", "baron_setup", "enemy_death_window",
)
PRO_FIELD_LIMIT = 300
PRO_ENTRY_LIMIT = 400
QUOTE_MARKS = '"\u201c\u201d\u201e\u201f'


def _pro_file() -> tuple[dict[str, str], ...] | None:
    """Parsed pro_lessons.md; () when it is missing or blank, None when it cannot be read."""
    path = PLAYBOOK_ROOT / "pro_lessons.md"
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return ()
    return _lessons(str(path), stamp, "pro")


def pro_lessons() -> tuple[dict[str, str], ...]:
    """Paraphrased pro principles; a missing, blank or unreadable file gives none."""
    return _pro_file() or ()


def _pro_roles(lesson: dict[str, str]) -> list[str]:
    return [ROLE_WORDS.get(name, name) for name in _tags(lesson["roles"])] or ["all"]


def pro_archetypes(lesson: dict[str, str]) -> list[str]:
    """Champion tags named on an "Archetypes:" line, as written apart from case: "tank, mage" -> Tank, Mage."""
    return [part.strip().title() for part in lesson.get("archetypes", "").split(",") if part.strip()]


def pro_archetype_match(role: str | None, tags) -> bool:
    """Whether a pro lesson for this role (or all) names one of these champion tags."""
    wanted = {str(tag).casefold() for tag in tags}
    for lesson in pro_lessons():
        roles = _pro_roles(lesson)
        if (role in roles or "all" in roles) and wanted.intersection(
                name.casefold() for name in pro_archetypes(lesson)):
            return True
    return False


def pro_matches(role: str | None, phase: str, tags) -> list[dict]:
    """Principles for this role, game phase and observed situation, best first, each with its shared tags."""
    tags = set(tags)
    scored = []
    for index, lesson in enumerate(pro_lessons()):
        roles = _pro_roles(lesson)
        phases = _tags(lesson["phase"]) or ["any"]
        when = _tags(lesson["when"]) or ["any"]
        shared = tags.intersection(when)
        if not lesson["situation"] or not (role in roles or "all" in roles):
            continue
        if not (phase in phases or "any" in phases) or not ("any" in when or shared):
            continue
        scored.append((-(2 * (role in roles) + len(shared)), index,
                       {**lesson, "shared": tuple(tag for tag in PRO_TAGS if tag in shared)}))
    return [lesson for _, _, lesson in sorted(scored, key=lambda entry: entry[:2])]


def pro_lessons_for(role: str | None, phase: str, tags, limit: int = 3, chars: int = 1200) -> list[str]:
    """The best-matching principles for this role, game phase and observed situation, as short texts."""
    found: list[str] = []
    for lesson in pro_matches(role, phase, tags):
        # The situation is a case the principle is about, never a statement about this match.
        entry = (f"{lesson['title']}: If this holds (not observed here): {lesson['situation']} "
                 f"Our side: {lesson['our']} Their side: {lesson['their']}")
        if lesson["check"]:
            entry += f" You check: {lesson['check']}"
        entry = entry[:PRO_ENTRY_LIMIT]
        if len(found) >= limit or sum(map(len, found)) + len(entry) > chars:
            break
        found.append(entry)
    return found


def pro_lesson_problems() -> list[str]:
    """Readable faults in pro_lessons.md for the log; a broken file must not stop the bot."""
    problems: list[str] = []
    try:
        found = _pro_file()
        if found is None:
            return ["pro_lessons.md could not be read as UTF-8 text, so no pro lessons are loaded"]
        for lesson in found:
            title = lesson["title"]
            for role in _pro_roles(lesson):
                if role != "all" and role not in ROLES:
                    problems.append(f"'{title}' has unknown role '{role}'")
            for phase in _tags(lesson["phase"]):
                if phase != "any" and phase not in PRO_PHASES:
                    problems.append(f"'{title}' has unknown Phase '{phase}'")
            for tag in _tags(lesson["when"]):
                if tag != "any" and tag not in PRO_TAGS:
                    problems.append(f"'{title}' has unknown When tag '{tag}'")
            for name in pro_archetypes(lesson):
                if name not in PRO_ARCHETYPES:
                    problems.append(f"'{title}' has unknown Archetypes value '{name}'; "
                                    f"use {', '.join(PRO_ARCHETYPES)}")
            for field, label in (("situation", "Situation"), ("our", "Our side"), ("their", "Their side")):
                if not lesson[field]:
                    problems.append(f"'{title}' has no {label} line")
            for field in PRO_FIELDS.values():
                if len(lesson[field]) > PRO_FIELD_LIMIT:
                    problems.append(f"'{title}' has a {field} field over {PRO_FIELD_LIMIT} characters")
            if any(mark in lesson["text"] for mark in QUOTE_MARKS):
                problems.append(f"'{title}' contains a quotation mark; pro lessons are written in our own words")
            if not re.fullmatch(r"\d+ games?", lesson["seen"].strip().casefold()):
                problems.append(f"'{title}' needs a 'Seen in' line like 6 games")
    except Exception as exc:
        problems.append(f"pro_lessons.md could not be checked ({type(exc).__name__})")
    return problems


_pro_reported: tuple[str, int | None] | None = None


def fresh_pro_lesson_problems() -> list[str]:
    """pro_lesson_problems, once per saved version of the file."""
    global _pro_reported
    path = PLAYBOOK_ROOT / "pro_lessons.md"
    try:
        stamp = (str(path), path.stat().st_mtime_ns)
    except OSError:
        stamp = (str(path), None)
    if stamp == _pro_reported:
        return []
    _pro_reported = stamp
    return pro_lesson_problems()


def validate() -> None:
    """Fail fast at startup if a role file is missing or has no summary."""
    for role in ROLES:
        if not summary(role):
            raise FileNotFoundError(f"lane_playbook/{role}.md needs a '## Summary' section")
    fundamentals()
