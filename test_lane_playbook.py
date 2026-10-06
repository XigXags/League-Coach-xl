import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lane_playbook
from coach import LESSON_TRIGGERS, PLAY_TRIGGERS, active_role, candidate_options, recognized_plays, summarize_game
from coordinators import CoordinatorBoard, ROLES
from test_coach import game


class LanePlaybookTests(unittest.TestCase):
    def test_every_role_has_a_summary_and_the_core_sections(self):
        for role in ROLES:
            summary = lane_playbook.summary(role)
            self.assertTrue(summary, role)
            self.assertLess(len(summary), 1200, role)
            full = lane_playbook.full(role, limit=10_000)
            for heading in ("## Job", "## Mechanics", "## Early (lane phase)", "## Mid game",
                            "## Late game", "## Matchups", "## Reading the feed", "## Common mistakes",
                            "## What a useful call names"):
                self.assertIn(heading, full, f"{role} is missing {heading}")

    def test_full_playbook_is_trimmed_at_a_section_boundary(self):
        text = lane_playbook.full("jungle", limit=1500)
        self.assertLessEqual(len(text), 1500)
        self.assertFalse(text.rstrip().endswith("##"))

    def test_fundamentals_cover_waves_vision_and_objectives(self):
        text = lane_playbook.fundamentals()
        for term in ("## Waves", "## Vision and information", "## Objectives", "## Death and respawn"):
            self.assertIn(term, text)


class LessonTests(unittest.TestCase):
    def test_lessons_file_parses_and_passes_its_own_checks(self):
        found = lane_playbook.lessons()
        self.assertGreaterEqual(len(found), 4)
        for lesson in found:
            if lesson["trigger"]:
                self.assertIn(lesson["trigger"], LESSON_TRIGGERS, lesson["title"])
        self.assertEqual(lane_playbook.lesson_problems(LESSON_TRIGGERS), [])

    def test_profile_matches_champion_names_loosely(self):
        self.assertEqual(lane_playbook.profile_for("Bel'Veth")["plan"], "farm")
        self.assertEqual(lane_playbook.profile_for("belveth"), lane_playbook.profile_for("Bel'Veth"))
        self.assertEqual(lane_playbook.profile_for("LeeSin")["plan"], "gank")
        self.assertIsNone(lane_playbook.profile_for("Ashe"))

    def test_role_wide_lesson_applies_to_any_jungler(self):
        self.assertEqual(lane_playbook.lesson_for("jungle", "Viego", "six_race")["title"], "Scuttle for six")
        self.assertIsNone(lane_playbook.lesson_for("top", "Viego", "six_race"))
        self.assertIsNone(lane_playbook.lesson_for("jungle", "Viego", "scaling"))

    def test_missing_or_broken_file_never_raises(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(lane_playbook, "PLAYBOOK_ROOT", Path(directory)):
            self.assertEqual(lane_playbook.lessons(), ())
            (Path(directory) / "lessons.md").write_text(
                "## Bad\nApplies to: jungle\nTrigger: nonsense\nPlan: objective\n", encoding="utf-8")
            self.assertEqual(len(lane_playbook.lesson_problems(LESSON_TRIGGERS)), 3)

    def _file(self, text, encoding="utf-8"):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        (Path(directory.name) / "lessons.md").write_text(text, encoding=encoding)
        patcher = patch.object(lane_playbook, "PLAYBOOK_ROOT", Path(directory.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dictated_formatting_still_parses(self):
        self._file("## Crab\n- Applies to: Bel'Veth jungle\n**Trigger:** Six race.\nUntil: 22 minutes\n"
                   "Plan: farm\nSay it like: go\nTimeline: first line\nwrapped second line\n", encoding="utf-8-sig")
        lesson = lane_playbook.lesson_for("jungle", "Bel'Veth", "six_race")
        self.assertEqual(lesson["title"], "Crab")
        self.assertEqual(lesson["timeline"], "first line wrapped second line")
        self.assertEqual(lane_playbook.until_seconds(lesson["until"]), 1320)
        self.assertIsNone(lane_playbook.lesson_for("jungle", "Viego", "six_race"))
        self.assertEqual(lane_playbook.lesson_problems(LESSON_TRIGGERS), [])

    def test_utf16_file_from_powershell_loads(self):
        self._file("## Crab\nApplies to: junglers\nTrigger: six_race\nSay it like: go\n", encoding="utf-16")
        self.assertEqual(lane_playbook.lesson_for("jungle", "Viego", "six_race")["title"], "Crab")

    def test_the_most_specific_lesson_wins_wherever_it_sits(self):
        self._file("## Any\nApplies to: jungle\nTrigger: six_race\nSay it like: a\n"
                   "## List\nApplies to: jungle, Master Yi, Kayn\nPlan: farm\n"
                   "## Yi\nApplies to: jungle, Master Yi\nPlan: farm\nUntil: 22:00\nTrigger: six_race\nSay it like: b\n")
        self.assertEqual(lane_playbook.lesson_for("jungle", "Master Yi", "six_race")["title"], "Yi")
        self.assertEqual(lane_playbook.lesson_for("jungle", "Kayn", "six_race")["title"], "Any")
        self.assertEqual(lane_playbook.profile_for("MasterYi")["until"], "22:00")

    def test_silent_failures_are_reported(self):
        self._file("## A\nTrigger: six_race\nSay it like: go\n"
                   "## B\nApplies to: jungle, Belvith\nPlan: farm\nUntil: late\n")
        problems = " | ".join(lane_playbook.lesson_problems(LESSON_TRIGGERS))
        for expected in ("'A' has no 'Applies to'", "'Belvith'", "Until 'late'"):
            self.assertIn(expected, problems)
        self.assertEqual(lane_playbook.fresh_lesson_problems(LESSON_TRIGGERS) != [],
                         lane_playbook.fresh_lesson_problems(LESSON_TRIGGERS) == [])
        (lane_playbook.PLAYBOOK_ROOT / "lessons.md").write_bytes(b"\x80\x81 not text")
        self.assertIn("could not be read", lane_playbook.lesson_problems(LESSON_TRIGGERS)[0])
        self.assertEqual(lane_playbook.lessons(), ())


class MovementTests(unittest.TestCase):
    def test_movement_kit_is_attached_to_players(self):
        match = game()
        match["allPlayers"][1]["championName"] = "Yasuo"
        state = summarize_game(match)
        enemy = next(p for p in state["players"] if p["team"] == "CHAOS")
        self.assertIn("dash", enemy["movement_kit"])

    def test_positioning_rule_is_in_the_fundamentals(self):
        self.assertIn("## Positioning and movement", lane_playbook.fundamentals())


class ActiveRoleTests(unittest.TestCase):
    def test_position_label_maps_to_role(self):
        match = game()
        match["allPlayers"][0]["position"] = "UTILITY"
        self.assertEqual(active_role(summarize_game(match)), "support")

    def test_smite_identifies_jungle_when_position_is_missing(self):
        match = game()
        match["allPlayers"][0]["summonerSpells"]["summonerSpellOne"] = {"displayName": "Smite"}
        self.assertEqual(active_role(summarize_game(match)), "jungle")

    def test_unknown_position_gives_no_role(self):
        self.assertIsNone(active_role(summarize_game(game())))


class RoleOptionTests(unittest.TestCase):
    def _keys(self, position: str, game_time: int) -> set[str]:
        match = game(gold=300)
        match["allPlayers"][0]["position"] = position
        match["gameData"]["gameTime"] = game_time
        return {option.key for option in candidate_options(summarize_game(match), "What next?")}

    def test_lane_phase_offers_the_players_own_lane_job(self):
        self.assertIn("top_wave", self._keys("TOP", 400))
        self.assertIn("jungle_path", self._keys("JUNGLE", 400))
        self.assertIn("mid_roam_wave", self._keys("MIDDLE", 400))
        self.assertIn("bot_trade_window", self._keys("BOTTOM", 400))
        self.assertIn("support_vision", self._keys("UTILITY", 400))

    def test_mid_game_switches_to_objective_and_side_jobs(self):
        self.assertIn("top_split", self._keys("TOP", 1000))
        self.assertIn("jungle_objective", self._keys("JUNGLE", 1000))
        self.assertIn("mid_rotate", self._keys("MIDDLE", 1000))
        self.assertIn("bot_group", self._keys("BOTTOM", 1000))
        self.assertIn("support_sweep", self._keys("UTILITY", 1000))

    def test_other_roles_do_not_get_the_players_role_options(self):
        keys = self._keys("TOP", 400)
        self.assertNotIn("bot_trade_window", keys)
        self.assertNotIn("support_vision", keys)


class RecognizedPlayTests(unittest.TestCase):
    def test_play_library_parses_with_triggers_that_exist(self):
        found = lane_playbook.plays()
        self.assertGreaterEqual(len(found), 10)
        for play in found:
            self.assertIn(play["trigger"], PLAY_TRIGGERS, play["title"])
            self.assertTrue(play["summary"], play["title"])

    def test_turret_for_dragon_is_recognized_after_an_isolated_death(self):
        match = game(gold=300)
        match["events"]["Events"] += [
            {"EventName": "ChampionKill", "EventTime": 850, "VictimName": "Ally", "KillerName": "Enemy"},
            {"EventName": "DragonKill", "EventTime": 880, "KillerName": "Enemy", "DragonType": "Water"},
        ]
        match["gameData"]["gameTime"] = 900
        self.assertIn("punished_split", recognized_plays(summarize_game(match)))

    def test_swapped_tower_and_dragon_are_recognized(self):
        match = game(gold=300)
        match["events"]["Events"] += [
            {"EventName": "TurretKilled", "EventTime": 800, "KillerName": "Ally"},
            {"EventName": "DragonKill", "EventTime": 850, "KillerName": "Enemy", "DragonType": "Fire"},
        ]
        match["gameData"]["gameTime"] = 900
        self.assertIn("objective_swap", recognized_plays(summarize_game(match)))

    def test_quiet_even_game_recognizes_no_play(self):
        self.assertEqual(recognized_plays(summarize_game(game(gold=300))), ())

    def test_recognized_play_becomes_an_option_and_a_briefing_text(self):
        match = game(gold=300)
        match["events"]["Events"] += [
            {"EventName": "ChampionKill", "EventTime": 850, "VictimName": "Ally", "KillerName": "Enemy"},
            {"EventName": "DragonKill", "EventTime": 880, "KillerName": "Enemy", "DragonType": "Water"},
        ]
        match["gameData"]["gameTime"] = 900
        keys = {option.key for option in candidate_options(summarize_game(match), "What next?")}
        self.assertTrue(any(key.startswith("play_punished_split") for key in keys), keys)


class BriefingTests(unittest.TestCase):
    def test_only_the_active_role_gets_the_full_playbook(self):
        board = CoordinatorBoard()
        briefing = board.briefing(detail_role="bot")
        self.assertIn("## Mechanics", briefing["bot"]["full_playbook"])
        self.assertNotIn("full_playbook", briefing["top"])
        self.assertEqual(briefing["top"]["playbook"], lane_playbook.summary("top"))

    def test_every_role_carries_its_playbook_summary(self):
        board = CoordinatorBoard({role: "Thesis.\n\nSix failure cases\n1. Check." for role in ROLES})
        briefing = board.briefing()
        for role in ROLES:
            self.assertEqual(briefing[role]["playbook"], lane_playbook.summary(role))


PLAN_LESSON = ("## Red then dive\nApplies to: jungle\nOffer at: first_clear, second clear\nUntil: 4:00\n"
               "Kind: gank\nName: red into a dive\nGoal: Dive bot\nSay it like: dive bot\n")
PRO_LESSON = ("## {title}\nRoles: {roles}\nPhase: {phase}\nWhen: {when}\nSituation: {situation}\n"
              "Our side: Gains tempo.\nTheir side: Gives the far side.\nPlayer check: Look at the wave.\n"
              "Seen in: 6 games\n")


def pro(title, roles="all", phase="any", when="any", situation="A lane is pushed."):
    return PRO_LESSON.format(title=title, roles=roles, phase=phase, when=when, situation=situation)


class PlanLessonTests(unittest.TestCase):
    def _files(self, **files):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for name, text in files.items():
            (Path(directory.name) / f"{name}.md").write_text(text, encoding="utf-8")
        patcher = patch.object(lane_playbook, "PLAYBOOK_ROOT", Path(directory.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_shipped_file_has_five_lessons_and_no_problems(self):
        self.assertEqual([lesson["title"] for lesson in lane_playbook.lessons()],
                         ["Scuttle for six", "Blue into an invade", "Bel'Veth farms to 80 stacks",
                          "Farm-first junglers", "Gank-first junglers"])
        self.assertEqual(lane_playbook.lesson_problems(LESSON_TRIGGERS), [])
        crab = lane_playbook.lesson_for("jungle", "Viego", "six_race")
        self.assertEqual((crab["name"], crab["goal"]), ("six on crab", "If a river crab is up, reach it first for "
                                                                       "level 6"))
        self.assertEqual(crab["say"], "Level {level}. If crab's up and you're a camp from six, get it first")
        self.assertFalse((lane_playbook.PLAYBOOK_ROOT.parent / "lesson_inbox.md").exists())

    def test_marks_read_levels_enemy_levels_and_deaths(self):
        lesson = {"marks": "Level 4 by 3:30; enemy under 6 until 6:10; no deaths; be quick; level 5 by 5:50."}
        self.assertEqual(lane_playbook.marks(lesson), (("level", 4, 210), ("enemy_under", 6, 370), ("no_deaths",),
                                                       ("level", 5, 350)))
        self.assertEqual(lane_playbook.marks({"marks": ""}), ())
        self._files(lessons=PLAN_LESSON + "On track: level 4 by 3:30; be quick\n")
        problems = lane_playbook.lesson_problems(LESSON_TRIGGERS)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("'be quick'", problems[0])

    def test_plan_lessons_follow_stage_role_and_until(self):
        self._files(lessons=PLAN_LESSON + "## Reworded\nApplies to: jungle\nTrigger: six_race\nSay it like: go\n"
                    "## Yi only\nApplies to: jungle, Master Yi\nOffer at: first_clear\nGoal: Farm\n"
                    "Say it like: farm\n## Third\nApplies to: jungle\nOffer at: first_clear\nGoal: C\n"
                    "Say it like: c\n")
        self.assertEqual(lane_playbook.lesson_problems(LESSON_TRIGGERS), [])
        titles = lambda *args: [lesson["title"] for lesson in lane_playbook.plan_lessons(*args)]
        self.assertEqual(titles("jungle", "Viego", "first_clear", 60), ["Red then dive", "Third"])
        self.assertEqual(titles("jungle", "Master Yi", "first_clear", 60), ["Yi only", "Red then dive"])
        self.assertEqual(titles("jungle", "Viego", "second_clear", 200), ["Red then dive"])
        self.assertEqual(titles("jungle", "Viego", "second_clear", 240), [])
        self.assertEqual(titles("jungle", "Viego", "six_race", 60), [])
        self.assertEqual(titles("top", "Garen", "first_clear", 60), [])

    def test_each_plan_lesson_fault_is_reported_once(self):
        cases = {"Trigger: six_race\n": "both Offer at and Trigger", "Kind: sneaky\n": "Kind 'sneaky'"}
        for extra, expected in cases.items():
            self._files(lessons=PLAN_LESSON.replace("Kind: gank\n", "") + extra)
            problems = lane_playbook.lesson_problems(LESSON_TRIGGERS)
            self.assertEqual(len(problems), 1, problems)
            self.assertIn(expected, problems[0])
        for text, expected in ((PLAN_LESSON.replace("Say it like: dive bot\n", ""), "no 'Say it like'"),
                               (PLAN_LESSON.replace("Goal: Dive bot\n", ""), "no Goal"),
                               (PLAN_LESSON.replace("first_clear", "third clear"), "Offer at stage 'third_clear'"),
                               (PLAN_LESSON.replace("red into a dive", "red buff into a bot dive"), "Name over 5")):
            self._files(lessons=text)
            problems = lane_playbook.lesson_problems(LESSON_TRIGGERS)
            self.assertEqual(len(problems), 1, problems)
            self.assertIn(expected, problems[0])

    def test_pro_lessons_are_optional(self):
        self._files()
        self.assertEqual(lane_playbook.pro_lessons(), ())
        self.assertEqual(lane_playbook.pro_lessons_for("jungle", "early", {"behind"}), [])
        self.assertEqual(lane_playbook.pro_lesson_problems(), [])
        self._files(pro_lessons="  \n")
        self.assertEqual(lane_playbook.pro_lessons(), ())
        self._files()   # a fresh folder, so the unreadable file is not a cached read of the blank one
        (lane_playbook.PLAYBOOK_ROOT / "pro_lessons.md").write_bytes(b"\x80\x81 not text")
        self.assertEqual(lane_playbook.pro_lessons(), ())
        self.assertIn("could not be read", lane_playbook.pro_lesson_problems()[0])

    def test_pro_lessons_are_chosen_by_role_phase_and_situation(self):
        self._files(pro_lessons=pro("Everyone") + pro("Junglers behind", "jungle, support", "early, lane", "behind")
                    + pro("Late only", "all", "late") + pro("Top only", "top")
                    + pro("Needs a tower", "all", "any", "tower_down, after_kill"))
        self.assertEqual(lane_playbook.pro_lesson_problems(), [])
        first = lambda *args: [text.split(":")[0] for text in lane_playbook.pro_lessons_for(*args)]
        self.assertEqual(first("jungle", "early", {"behind"}), ["Junglers behind", "Everyone"])
        self.assertEqual(first("jungle", "early", set()), ["Everyone"])
        self.assertEqual(first("jungle", "mid", {"behind"}), ["Everyone"])
        self.assertEqual(first("top", "late", {"tower_down", "after_kill"}),
                         ["Top only", "Needs a tower", "Everyone"])
        self.assertEqual(first(None, "late", set()), ["Everyone", "Late only"])
        entry = lane_playbook.pro_lessons_for("jungle", "early", {"behind"})[0]
        self.assertEqual(entry, "Junglers behind: If this holds (not observed here): A lane is pushed. Our side: "
                                "Gains tempo. Their side: Gives the far side. You check: Look at the wave.")

    def test_pro_lessons_sent_to_the_ranker_are_capped(self):
        self._files(pro_lessons="".join(pro(f"Rule {n}", situation="Long. " * 49) for n in range(6)))
        found = lane_playbook.pro_lessons_for("mid", "lane", set())
        self.assertEqual(len(found), 3)
        self.assertTrue(all(len(entry) <= 400 for entry in found))
        self.assertLessEqual(sum(map(len, found)), 1200)
        self.assertEqual(len(lane_playbook.pro_lessons_for("mid", "lane", set(), limit=5, chars=900)), 2)

    def test_pro_lesson_faults_are_reported(self):
        self._files(pro_lessons=pro("Quoted", situation='They said "go" and went.')
                    + pro("Curly", situation="They said \u201cgo\u201d.")
                    + pro("Bad names", "jungle, coach", "dawn", "winning")
                    + "## Thin\nRoles: all\nSeen in: many\n")
        problems = " | ".join(lane_playbook.pro_lesson_problems())
        for expected in ("'Quoted' contains a quotation mark", "'Curly' contains a quotation mark",
                         "unknown role 'coach'", "unknown Phase 'dawn'", "unknown When tag 'winning'",
                         "'Thin' has no Situation", "'Thin' has no Our side", "'Thin' has no Their side",
                         "'Thin' needs a 'Seen in' line"):
            self.assertIn(expected, problems)
        self.assertEqual(len(lane_playbook.pro_lesson_problems()), 9)
        self.assertEqual(lane_playbook.fresh_pro_lesson_problems() != [],
                         lane_playbook.fresh_pro_lesson_problems() == [])

    def test_pro_matches_carry_the_shared_tags_and_feed_the_same_ranker_text(self):
        self._files(pro_lessons=pro("Everyone") + pro("Junglers behind", "jungle, support", "early, lane", "behind")
                    + pro("Needs a tower", "all", "any", "tower_down, after_kill, behind"))
        found = lane_playbook.pro_matches("jungle", "early", {"behind", "after_kill", "gold_ready"})
        self.assertEqual([(lesson["title"], lesson["shared"]) for lesson in found],
                         [("Junglers behind", ("behind",)), ("Needs a tower", ("behind", "after_kill")),
                          ("Everyone", ())])
        self.assertEqual((found[0]["our"], found[0]["their"], found[0]["check"]),
                         ("Gains tempo.", "Gives the far side.", "Look at the wave."))
        self.assertEqual(lane_playbook.pro_matches("top", "late", set())[0]["title"], "Everyone")
        self.assertEqual(lane_playbook.pro_matches("top", "late", {"gold_ready"})[0]["shared"], ())

    def test_the_shipped_pro_lessons_reach_the_ranker_as_they_did(self):
        def before(role, phase, tags, limit=3, chars=1200):
            """pro_lessons_for as it was before pro_matches existed, kept here as the reference."""
            tags = set(tags)
            scored = []
            for index, lesson in enumerate(lane_playbook.pro_lessons()):
                roles = lane_playbook._pro_roles(lesson)
                phases = lane_playbook._tags(lesson["phase"]) or ["any"]
                when = lane_playbook._tags(lesson["when"]) or ["any"]
                shared = len(tags.intersection(when))
                if not lesson["situation"] or not (role in roles or "all" in roles):
                    continue
                if not (phase in phases or "any" in phases) or not ("any" in when or shared):
                    continue
                scored.append((-(2 * (role in roles) + shared), index, lesson))
            found = []
            for _, _, lesson in sorted(scored, key=lambda entry: entry[:2]):
                entry = (f"{lesson['title']}: If this holds (not observed here): {lesson['situation']} "
                         f"Our side: {lesson['our']} Their side: {lesson['their']}")
                if lesson["check"]:
                    entry += f" You check: {lesson['check']}"
                entry = entry[:lane_playbook.PRO_ENTRY_LIMIT]
                if len(found) >= limit or sum(map(len, found)) + len(entry) > chars:
                    break
                found.append(entry)
            return found

        compared = 0
        for role in (*ROLES, None):
            for phase in lane_playbook.PRO_PHASES:
                for tags in (set(), {"behind"}, {"ahead", "after_kill"}, {"tower_down", "numbers_up", "gold_ready"},
                             set(lane_playbook.PRO_TAGS)):
                    self.assertEqual(lane_playbook.pro_lessons_for(role, phase, tags), before(role, phase, tags))
                    self.assertEqual(lane_playbook.pro_lessons_for(role, phase, tags, limit=5, chars=900),
                                     before(role, phase, tags, 5, 900))
                    compared += bool(before(role, phase, tags))
        self.assertGreater(compared, 60)
        first = lane_playbook.pro_lessons_for("jungle", "early", set())[0]
        self.assertTrue(first.startswith("Gank when your camps are down: If this holds (not observed here): Your "
                                         "clear is finished"), first)
        self.assertEqual(lane_playbook.pro_lesson_problems(), [])
        self.assertEqual(len(lane_playbook.pro_lessons()), 50)
        self.assertFalse(any(lesson["archetypes"] for lesson in lane_playbook.pro_lessons()))

    def test_archetypes_are_parsed_and_checked(self):
        self._files(pro_lessons=pro("Front line", "jungle, top") + "Archetypes: tank, Fighter\n"
                    + pro("Typo") + "Archetypes: Tank, Bruiser\n" + pro("Plain"))
        tanks, typo, plain = lane_playbook.pro_lessons()
        self.assertEqual(lane_playbook.pro_archetypes(tanks), ["Tank", "Fighter"])
        self.assertEqual(lane_playbook.pro_archetypes(plain), [])
        self.assertEqual(lane_playbook.pro_lesson_problems(),
                         ["'Typo' has unknown Archetypes value 'Bruiser'; use Fighter, Tank, Mage, Assassin, "
                          "Marksman, Support"])
        self.assertTrue(lane_playbook.pro_archetype_match("jungle", ["Tank"]))
        self.assertTrue(lane_playbook.pro_archetype_match("mid", ["Mage", "Tank"]))     # "Typo" is for all roles
        self.assertFalse(lane_playbook.pro_archetype_match("mid", ["Fighter"]))
        self.assertFalse(lane_playbook.pro_archetype_match("jungle", ["Mage"]))
        self.assertFalse(lane_playbook.pro_archetype_match("jungle", []))
        # The line is the player's reading aid and a plan-knowledge signal; the ranker text does not change.
        self.assertNotIn("Archetypes", lane_playbook.pro_lessons_for("jungle", "early", set())[0])


class ChampionNoteTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "champion_notes.md"
        patcher = patch.object(lane_playbook, "PLAYBOOK_ROOT", Path(directory.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_shipped_file_is_a_header_with_no_notes(self):
        shipped = Path(lane_playbook.__file__).with_name("lane_playbook") / "champion_notes.md"
        self.assertTrue(lane_playbook.NOTES_HEADER.startswith(
            "# Champion notes: my own words on how I play each champion\n"))
        # A file the coach creates opens the same way as the shipped one; my own notes may follow it.
        self.assertTrue(shipped.read_text(encoding="utf-8").startswith(lane_playbook.NOTES_HEADER))

    def test_a_note_is_appended_as_one_dated_block(self):
        self.assertEqual(lane_playbook.champion_notes("Zac"), [])
        stored = lane_playbook.add_champion_note("Zac", "jungle", "I play Zac for ganks from level four.")
        self.assertEqual(stored, "I play Zac for ganks from level four.")
        today = __import__("datetime").date.today().isoformat()
        self.assertEqual(self.path.read_text(encoding="utf-8"), lane_playbook.NOTES_HEADER +
                         f"\n## Zac\nRole: jungle\nNote: I play Zac for ganks from level four.\nAdded: {today}\n")
        self.assertEqual(lane_playbook.champion_notes("zac"), ["I play Zac for ganks from level four."])
        self.assertEqual(lane_playbook.champion_notes("Garen"), [])
        self.assertEqual(lane_playbook.champion_notes(None), [])

    def test_what_is_already_in_the_file_is_never_rewritten(self):
        mine = "# My notes\n\n## Bel'Veth\nNote: farm to eighty\n\nsome text of my own, no newline at the end"
        self.path.write_text(mine, encoding="utf-8")
        lane_playbook.add_champion_note("Bel'Veth", None, "dive at six")
        text = self.path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(mine + "\n\n## Bel'Veth\nRole: unknown\nNote: dive at six\nAdded: "), text)
        self.assertEqual(lane_playbook.champion_notes("BelVeth"), ["dive at six", "farm to eighty"])

    def test_a_note_is_one_line_without_list_marks_and_two_hundred_characters_at_most(self):
        stored = lane_playbook.add_champion_note("Zac", "jungle", "  - ## gank\n early,\tthen\r\nfarm  ")
        self.assertEqual(stored, "gank early, then farm")
        long = lane_playbook.add_champion_note("Zac", "jungle", "word " * 80)
        self.assertEqual(long, " ".join(["word"] * 40))   # 199 characters: cut at the last space that fits
        self.assertLessEqual(len(long), lane_playbook.NOTE_CHAR_LIMIT)
        self.assertEqual(lane_playbook.note_text("x" * 250), "x" * 200)
        self.assertEqual(lane_playbook.add_champion_note("Zac", "jungle", " -- \n"), "")
        self.assertEqual(self.path.read_text(encoding="utf-8").count("## Zac"), 2)
        for line in self.path.read_text(encoding="utf-8").splitlines():
            self.assertLessEqual(len(line), 206)

    def test_a_note_said_twice_is_stored_once(self):
        lane_playbook.add_champion_note("Zac", "jungle", "I gank from level four.")
        self.assertEqual(lane_playbook.add_champion_note("zac", "jungle", "i gank, from level FOUR"),
                         "i gank, from level FOUR")
        lane_playbook.add_champion_note("Garen", "top", "I gank from level four.")   # another champion: kept
        text = self.path.read_text(encoding="utf-8")
        self.assertEqual((text.count("## Zac"), text.count("## Garen"), text.count("Note:")), (1, 1, 2))

    def test_a_utf16_file_from_powershell_is_appended_in_its_own_encoding(self):
        self.path.write_text("# Notes\n\n## Zac\nNote: first\n", encoding="utf-16")
        self.assertEqual(lane_playbook.champion_notes("Zac"), ["first"])
        lane_playbook.add_champion_note("Zac", "jungle", "second, with a dash — and Bel'Veth")
        self.assertEqual(self.path.read_bytes()[:2], "﻿".encode("utf-16-le"))
        text = self.path.read_text(encoding="utf-16")
        self.assertTrue(text.startswith("# Notes\n\n## Zac\nNote: first\n\n## Zac\nRole: jungle\nNote: second, "), text)
        self.assertEqual(lane_playbook.champion_notes("Zac"), ["second, with a dash — and Bel'Veth", "first"])

    def test_notes_come_newest_first_three_at_most_and_four_hundred_characters(self):
        for number in range(5):
            lane_playbook.add_champion_note("Zac", "jungle", f"note number {number}")
        self.assertEqual(lane_playbook.champion_notes("Zac"), ["note number 4", "note number 3", "note number 2"])
        for number in range(2):
            lane_playbook.add_champion_note("Garen", "top", f"{'spin ' * 39}{number}")
        lane_playbook.add_champion_note("Garen", "top", "short and newest")
        found = lane_playbook.champion_notes("Garen")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0], "short and newest")
        self.assertLessEqual(sum(map(len, found)), 400)

    def test_a_long_hand_edited_note_does_not_hide_the_others(self):
        self.path.write_text(f"## Zac\nNote: short and old\n\n## Zac\nNote: {'word ' * 96}\n", encoding="utf-8")
        found = lane_playbook.champion_notes("Zac")
        self.assertEqual(found, [" ".join(["word"] * 40), "short and old"])   # read at the stored length
        self.path.write_text(f"## Zac\nNote: ok\n\n## Zac\nNote: {'x' * 199}\n\n## Zac\nNote: {'y' * 199}\n"
                             f"\n## Zac\nNote: {'z' * 199}\n", encoding="utf-8")
        # The third-newest is over the 400 characters and is passed over; the older short one still fits.
        self.assertEqual(lane_playbook.champion_notes("Zac"), ["z" * 199, "y" * 199, "ok"])

    def test_nothing_is_appended_to_a_file_that_cannot_be_read_back(self):
        broken = b"# Notes\n\n## Zac\nNote: caf\xe9 \xff\xfe ganks\n"
        self.path.write_bytes(broken)
        self.assertEqual(lane_playbook.champion_notes("Zac"), [])
        with self.assertRaises(OSError):
            lane_playbook.add_champion_note("Zac", "jungle", "I gank early")
        self.assertEqual(self.path.read_bytes(), broken)
        self.path.unlink()
        with patch.object(lane_playbook, "PLAYBOOK_ROOT", self.path.parent / "no-such-folder"):
            with self.assertRaises(OSError):
                lane_playbook.add_champion_note("Zac", "jungle", "I gank early")

    def test_champion_lessons_are_the_ones_that_name_the_champion(self):
        (self.path.parent / "lessons.md").write_text(
            "## Any\nApplies to: jungle\nTrigger: six_race\nSay it like: a\n"
            "## List\nApplies to: jungle, Master Yi, Bel'Veth\nPlan: farm\n"
            "## Hers\nApplies to: Bel'Veth jungle\nTrigger: scaling\nSay it like: b\n", encoding="utf-8")
        titles = lambda champion: [lesson["title"] for lesson in lane_playbook.champion_lessons(champion)]
        self.assertEqual(titles("belveth"), ["List", "Hers"])
        self.assertEqual(titles("Master Yi"), ["List"])
        self.assertEqual(titles("Zac"), [])
        self.assertEqual(titles(None), [])


if __name__ == "__main__":
    unittest.main()
