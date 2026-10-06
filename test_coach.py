import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lane_playbook
from coach import (LESSON_TRIGGERS, PLANS, PLAY_TRIGGERS, SAFE_KEYS, Option, Plan, _jungle_options,
                   candidate_options, coach, evidence, format_options, jungle_clock, plan_intent, plan_progress,
                   plan_snapshot, plan_table, situation_tags, summarize_game, two_options)
from coordinators import CoordinatorBoard, ROLES

import json
from copy import deepcopy
from dataclasses import replace
from datetime import date

import champion_metadata
import coach as coach_module
from coach import (CHAMPION_KITS_LIMIT, CHAT_LIMIT, EXPLAIN_NAMES, MORE_PHRASES, STOP_PHRASES, TAG_WORDS, Topic, _aloud,
                   _reason_parts, _role_options, _sentences, champion_kits, explain, is_noise, jev_rank,
                   note_intent, plan_knowledge, quick_intent)

SHIPPED_ROOT = lane_playbook.PLAYBOOK_ROOT


def game(*, gold=300, ally_dead=False, enemy_dead=False, dragon=False, baron=False, inhib=False):
    events = []
    if dragon:
        events.append({"EventName": "DragonKill", "EventTime": 850,
                       "KillerName": "Enemy", "DragonType": "Fire"})
    if baron:
        events.append({"EventName": "BaronKill", "EventTime": 880,
                       "KillerName": "Ally"})
    if inhib:
        events.append({"EventName": "InhibKilled", "EventTime": 860,
                       "KillerName": "Ally"})
    return {
        "gameData": {"gameTime": 900, "gameMode": "CLASSIC"},
        "activePlayer": {"riotId": "Ally", "currentGold": gold,
                         "championStats": {"currentHealth": 800, "maxHealth": 1000}},
        "allPlayers": [
            {"riotId": "Ally", "team": "ORDER", "championName": "Ashe",
             "level": 10, "isDead": ally_dead, "scores": {"kills": 3, "deaths": 1,
             "assists": 4, "creepScore": 90}, "items": [{"displayName": "B. F. Sword"}],
             "summonerSpells": {"summonerSpellOne": {"displayName": "Flash"},
                                "summonerSpellTwo": {"displayName": "Teleport"}}},
            {"riotId": "Enemy", "team": "CHAOS", "championName": "Jinx",
             "level": 10, "isDead": enemy_dead, "scores": {"kills": 2, "deaths": 3,
             "assists": 2, "creepScore": 86}, "items": []},
        ],
        "events": {"Events": events},
    }


class CoachTests(unittest.TestCase):
    def test_summary_uses_actual_gold_players_items_and_objective(self):
        state = summarize_game(game(gold=1800, enemy_dead=True, dragon=True))
        self.assertEqual(state["our_team"], "ORDER")
        self.assertEqual(state["active_gold"], 1800)
        self.assertEqual(state["teams"]["CHAOS"]["alive"], 0)
        self.assertEqual(state["players"][0]["items"], ["B. F. Sword"])
        self.assertEqual(state["players"][0]["summoner_spells"], ["Flash", "Teleport"])
        self.assertIn("Marksman", state["players"][0]["archetypes"])
        self.assertIn("dragon taken 0:50 ago by enemy team", evidence(state))
        self.assertNotIn("enemy_positions", state)

    def test_candidates_change_with_game_state(self):
        ahead = candidate_options(summarize_game(game(gold=1800, baron=True)), "What next?")
        behind = candidate_options(summarize_game(game(gold=100, dragon=True)), "What next?")
        self.assertIn("buy", {option.key for option in ahead})
        self.assertIn("baron_push", {option.key for option in ahead})
        self.assertNotIn("buy", {option.key for option in behind})
        self.assertIn("post_dragon", {option.key for option in behind})

    def test_specific_question_changes_options(self):
        state = summarize_game(game())
        dragon = candidate_options(state, "Should we take dragon?")
        lane = candidate_options(state, "Which lane?")
        self.assertIn("setup", {option.key for option in dragon})
        self.assertIn("mid_wave", {option.key for option in lane})

    def test_recent_inhibitor_changes_options(self):
        state = summarize_game(game(inhib=True))
        self.assertIn("inhib_pressure", {option.key for option in candidate_options(state, "What next?")})
        self.assertIn("last inhibitor taken", evidence(state))

    def test_grubs_vs_dragon_produces_two_executable_plans(self):
        match = game(gold=900)
        match["gameData"]["gameTime"] = 600
        state = summarize_game(match)
        options = candidate_options(state, "Should we take Grubs or Dragon?")
        self.assertEqual([option.key for option in options], ["take_grubs", "take_dragon"])
        self.assertIn("shoves mid", options[0].reason)
        self.assertIn("shove bot", options[1].reason)
        self.assertIn("sweeps lower river", options[1].reason)

    def test_recent_dragon_is_not_offered_as_available(self):
        match = game(dragon=True)
        match["gameData"]["gameTime"] = 900
        options = candidate_options(summarize_game(match), "Grubs or Dragon?")
        self.assertEqual(options[1].key, "dragon_setup")
        self.assertIn("Do not start an empty pit", options[1].reason)

    def test_first_dragon_has_not_spawned_yet(self):
        match = game()
        match["gameData"]["gameTime"] = 180
        options = candidate_options(summarize_game(match), "Grubs or Dragon?")
        self.assertEqual(options[1].key, "dragon_setup")
        self.assertIn("first Dragon", options[1].label)
        self.assertIn("not spawned yet", options[1].reason)
        self.assertNotIn("taken recently", options[1].reason)

    def test_future_event_is_not_presented_as_recent(self):
        match = game(dragon=True)
        match["gameData"]["gameTime"] = 180
        options = candidate_options(summarize_game(match), "Grubs or Dragon?")
        self.assertIn("not spawned yet", options[1].reason)

    def test_general_now_question_includes_lane_and_tower_options(self):
        match = game()
        match["gameData"]["gameTime"] = 1800
        keys = {option.key for option in candidate_options(summarize_game(match), "What's going on now?")}
        self.assertIn("mid_siege", keys)
        self.assertIn("side_pressure", keys)
        self.assertIn("hold_tempo", keys)
        self.assertNotIn("baron_window", keys)
        self.assertNotIn("dragon_setup", keys)
        self.assertNotIn("reset", keys)
        self.assertNotIn("waves", keys)

    def test_grubs_not_offered_after_early_window(self):
        match = game()
        match["gameData"]["gameTime"] = 1000
        options = candidate_options(summarize_game(match), "Grubs or Dragon?")
        self.assertEqual(options[0].key, "top_pit")
        self.assertIn("Herald", options[0].label)

    def test_roles_and_dragon_stakes_shape_the_plan(self):
        match = game()
        match["gameData"]["gameTime"] = 700
        match["allPlayers"] = []
        for team, champions in (("ORDER", ("Garen", "Vi", "Ahri", "Jinx", "Leona")),
                                ("CHAOS", ("Darius", "LeeSin", "Orianna", "Caitlyn", "Lulu"))):
            for role, champion in zip(("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"), champions):
                match["allPlayers"].append({
                    "riotId": "Ally" if champion == "Garen" else champion,
                    "team": team, "championName": champion, "position": role,
                    "level": 8, "isDead": champion == "LeeSin",
                    "scores": {"kills": 1, "deaths": 1, "assists": 1, "creepScore": 70},
                })
        match["activePlayer"]["riotId"] = "Ally"
        match["events"]["Events"] = [
            {"EventName": "DragonKill", "EventTime": 100, "KillerName": "Ally", "DragonType": "Fire"},
            {"EventName": "DragonKill", "EventTime": 400, "KillerName": "Vi", "DragonType": "Water"},
        ]
        state = summarize_game(match)
        options = candidate_options(state, "Grubs or Dragon?")
        self.assertIn("Ahri shoves mid", options[0].reason)
        self.assertIn("Leona sweeps lower river", options[1].reason)
        self.assertIn("Enemy jungler is dead", options[1].reason)
        self.assertIn("soul point", options[1].reason)

    def test_structure_champion_changes_grub_conversion(self):
        match = game()
        match["gameData"]["gameTime"] = 600
        match["allPlayers"][0]["championName"] = "Fiora"
        options = candidate_options(summarize_game(match), "Grubs or Dragon?")
        self.assertIn("Fiora is a strong structure-pressure pick", options[0].reason)

    def test_soul_changes_dragon_route_to_elder(self):
        match = game()
        match["gameData"]["gameTime"] = 1500
        match["events"]["Events"] = [
            {"EventName": "DragonKill", "EventTime": time, "KillerName": "Ally",
             "DragonType": "Fire"} for time in (100, 400, 700, 1000)
        ]
        options = candidate_options(summarize_game(match), "Grubs or Dragon?")
        self.assertIn("Elder Dragon", options[1].label)
        self.assertIn("execute buff", options[1].reason)

    def test_jev_scores_select_two_distinct_options(self):
        options = (Option("reset", "Reset", "a"), Option("waves", "Waves", "b"),
                   Option("buy", "Buy", "c"))
        first, second = two_options({"buy": .8, "waves": .6, "reset": .1}, options)
        self.assertEqual((first.key, second.key), ("buy", "waves"))

    def test_two_options_use_different_routes(self):
        options = (Option("mid_control", "Mid", "a"), Option("vision", "Mid vision", "b"),
                   Option("side_pressure", "Side", "c"))
        first, second = two_options({"mid_control": .9, "vision": .8, "side_pressure": .6}, options)
        self.assertEqual((first.key, second.key), ("mid_control", "side_pressure"))

    def test_coach_uses_live_facts_and_jev_rank(self):
        with patch("coach.read_live_game", return_value=game(gold=1800, baron=True)), \
             patch("coach.load_jev_key", return_value="secret"), \
             patch("coach.jev_rank", side_effect=lambda state, key, options: {
                 option.key: (1 if option.key == "baron_push" else .5 if option.key == "buy" else 0)
                 for option in options}):
            result = coach("What next?", "balanced")
        self.assertIn("1,800 unspent gold", result)
        self.assertIn("**Group with surviving Baron holders**", result)
        self.assertIn("**Spend your 1,800 gold on the next safe reset**", result)
        self.assertLess(result.index("Group with surviving Baron holders"), result.index("Spend your 1,800 gold"))
        self.assertIn("Otherwise: **Spend your 1,800 gold on the next safe reset**", result)
        self.assertTrue(result.startswith("Game read"))
        self.assertNotIn("Choose plan", result)
        self.assertNotIn("\n1. ", result)
        self.assertEqual(result.spoken,
                         "Group with surviving Baron holders. Or, Spend your 1,800 gold on the next safe reset.")

    def test_coach_passes_all_role_briefings_to_ranker(self):
        board = CoordinatorBoard({role: f"{role} guidance" for role in ROLES})
        captured = {}
        def rank(state, key, options):
            captured.update(state)
            return {option.key: 1 / (index + 1) for index, option in enumerate(options)}
        with patch("coach.read_live_game", return_value=game()), \
             patch("coach.load_jev_key", return_value="secret"), \
             patch("coach.jev_rank", side_effect=rank):
            coach("What next?", "balanced", coordinator_board=board)
        self.assertEqual(set(captured["coordinator_briefing"]), set(ROLES))
        self.assertEqual(captured["coordinator_briefing"]["top"]["guidance"], "top guidance")

    def test_early_general_call_prioritizes_lanes_over_neutral_pits(self):
        match = game()
        match["gameData"]["gameTime"] = 370
        keys = {option.key for option in candidate_options(summarize_game(match), "What's next?")}
        self.assertIn("lane_tempo", keys)
        self.assertIn("lane_reset", keys)
        self.assertNotIn("take_dragon", keys)
        self.assertNotIn("take_grubs", keys)

    def test_recent_pick_produces_specific_conversion(self):
        match = game(enemy_dead=True)
        match["events"]["Events"].append({"EventName": "ChampionKill", "EventTime": 890,
                                             "KillerName": "Ally", "VictimName": "Enemy"})
        options = candidate_options(summarize_game(match), "What next?")
        pick = next(option for option in options if option.key == "pick_convert")
        self.assertIn("tower", pick.reason)
        self.assertIn("before the respawn", pick.reason)

    def test_smite_identifies_unassigned_practice_jungler(self):
        match = game()
        match["allPlayers"][0]["championName"] = "Warwick"
        match["allPlayers"][0]["position"] = "NONE"
        match["allPlayers"][0]["summonerSpells"]["summonerSpellTwo"]["displayName"] = "Smite"
        state = summarize_game(match)
        options = candidate_options(state, "What next?")
        self.assertTrue(any("Warwick" in option.reason for option in options))

    def test_practice_tool_does_not_make_buy_plan_from_cheat_gold(self):
        match = game(gold=30000)
        match["gameData"]["gameMode"] = "PRACTICETOOL"
        state = summarize_game(match)
        self.assertIn("practice value", evidence(state))
        self.assertNotIn("buy", {option.key for option in candidate_options(state, "What next?")})

    def test_no_game_does_not_masquerade_as_live(self):
        with patch("coach.read_live_game", side_effect=OSError("offline")):
            result = coach("What next?", "balanced")
        self.assertIn("can't read a live League match", result)
        self.assertFalse(result.startswith("Game read"))

    def test_missing_jev_does_not_fake_a_rank(self):
        with patch("coach.read_live_game", return_value=game()), \
             patch("coach.load_jev_key", return_value=""):
            result = coach("What next?", "balanced")
        self.assertIn("Jev key missing", result)

    def test_voice_capability_question_gets_direct_answer(self):
        self.assertIn("/listen", coach("Can you hear me?", "balanced"))


def jungle_game(champion, level, time, enemy_level=None, enemy="Viego"):
    match = game()
    match["gameData"]["gameTime"] = time
    match["allPlayers"][0].update(championName=champion, level=level, position="JUNGLE")
    match["allPlayers"][1].update(championName=enemy)
    if enemy_level is not None:
        match["allPlayers"][1].update(level=enemy_level, position="JUNGLE")
    return match


# One fixture per jungle_clock stage: (level, game time, enemy level).
STAGES = {"first_clear": (3, 180, 3), "second_clear": (4, 270, 4), "six_race": (5, 340, 5),
          "six_behind": (5, 390, 6), "six_first": (6, 390, 5), "post_six": (6, 480, 6),
          "mid_game": (10, 900, 10)}


class JungleClockTests(unittest.TestCase):
    def _clock(self, champion="Bel'Veth", level=4, time=270, enemy_level=4, **changes):
        match = jungle_game(champion, level, time, enemy_level)
        match["gameData"].update(changes)
        return jungle_clock(summarize_game(match))

    def test_non_jungler_has_no_clock(self):
        self.assertIsNone(jungle_clock(summarize_game(game())))

    def test_stage_follows_levels_and_game_time(self):
        for stage, (level, time, enemy_level) in STAGES.items():
            self.assertEqual(self._clock(level=level, time=time, enemy_level=enemy_level)["stage"], stage)

    def test_pace_is_relative_to_the_enemy_jungler_only(self):
        self.assertEqual(self._clock(level=5, time=390, enemy_level=6)["pace"], "behind")
        self.assertEqual(self._clock(level=6, time=390, enemy_level=5)["pace"], "ahead")
        self.assertEqual(self._clock()["pace"], "even")
        self.assertEqual(self._clock(enemy_level=None)["pace"], "unknown")
        self.assertEqual(self._clock(gameMode="PRACTICETOOL")["pace"], "unknown")

    def test_plan_comes_from_the_lessons_file(self):
        self.assertEqual(self._clock("Bel'Veth")["plan"], "farm")
        self.assertEqual(self._clock("Bel'Veth")["until"], 1500)
        self.assertEqual(self._clock("Lee Sin")["plan"], "gank")
        self.assertEqual(self._clock("Ashe")["plan"], "flex")
        self.assertEqual(self._clock("Ashe")["until"], 1200)


class JungleOptionTests(unittest.TestCase):
    def _options(self, champion, level, time, enemy_level, question="where should I path"):
        state = summarize_game(jungle_game(champion, level, time, enemy_level))
        return {option.key: option for option in candidate_options(state, question)}

    def _stage_options(self, champion="Bel'Veth"):
        for level, time, enemy_level in STAGES.values():
            state = summarize_game(jungle_game(champion, level, time, enemy_level))
            yield _jungle_options(state, time, "CHAOS", jungle_clock(state))

    def test_second_clear_offers_the_clear_and_a_gank_without_filler(self):
        options = self._options("Bel'Veth", 4, 270, 4)
        self.assertIn("jungle_full_clear", options)
        self.assertIn("jungle_path", options)
        for key in ("jungle_scale", "reset", "waves", "lane_tempo", "hold_tempo"):
            self.assertNotIn(key, options)
        self.assertIn("80 Lavender stacks", options["jungle_full_clear"].reason)
        self.assertIn("jungle: you level 4 vs Viego level 4, +4 CS",
                      evidence(summarize_game(jungle_game("Bel'Veth", 4, 270, 4))))

    def test_six_race_is_worded_as_a_check_not_an_observation(self):
        options = self._options("Bel'Veth", 5, 340, 5)
        race = options["jungle_six_race"]
        self.assertEqual(race.family, "farm")
        self.assertIn("You check", race.reason)
        self.assertIn("cannot see", race.reason)
        # "one crab is up" is the player's benchmark from lessons.md, not a statement about this match.
        stated = re.compile(r"(?<!if the )(?<!is the )(?<!one )crab is up", re.IGNORECASE)
        for option in options.values():
            self.assertIsNone(stated.search(option.reason), option.key)
            self.assertIsNone(stated.search(option.say), option.key)

    def test_scaling_plan_is_offered_only_to_farm_champions_at_six(self):
        self.assertIn("eighty", self._options("Bel'Veth", 8, 600, 8)["jungle_scale"].say)
        self.assertEqual(self._options("Master Yi", 8, 600, 8)["jungle_scale"].say,
                         "keep farming, Master Yi wins later")
        self.assertNotIn("jungle_scale", self._options("Lee Sin", 8, 600, 8))
        self.assertNotIn("jungle_scale", self._options("Bel'Veth", 12, 1560, 12))

    def test_built_in_wording_works_without_a_lessons_file(self):
        lane_playbook.plays()
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(lane_playbook, "PLAYBOOK_ROOT", Path(directory)):
            clear = self._options("Bel'Veth", 4, 270, 4)
            race = self._options("Bel'Veth", 5, 340, 5)
        self.assertIn("jungle_full_clear", clear)
        self.assertIn("jungle_path", clear)
        self.assertEqual(race["jungle_six_race"].label, "If a river crab is up, reach it first for level 6")
        self.assertIn("You check", race["jungle_six_race"].reason)

    def _taught(self, lesson, enemy_level=5):
        lane_playbook.plays()
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(lane_playbook, "PLAYBOOK_ROOT", Path(directory)):
            (Path(directory) / "lessons.md").write_text(
                "## Mine\nApplies to: jungle\nTrigger: six race\n" + lesson, encoding="utf-8")
            state = summarize_game(jungle_game("Bel'Veth", 5, 340, enemy_level))
            options = candidate_options(state, "where should I path")
            problems = lane_playbook.lesson_problems(LESSON_TRIGGERS)
        return {option.key: option for option in options}, state, problems

    def test_a_long_dictated_lesson_still_fits_one_discord_message(self):
        options, state, problems = self._taught(
            "Goal: Crab\nSay it like: Level {level}. Crab check\nTimeline: " + "Clear the camps in order. " * 80)
        race = options["jungle_six_race"]
        self.assertLess(len(race.reason), 700)
        self.assertTrue(race.reason.rstrip().endswith("."))
        self.assertTrue(any("timeline over 300" in problem for problem in problems), problems)
        bloated = Option("a", "A", "Word after word. " * 200)
        self.assertLess(len(format_options((bloated, bloated), source="live game", facts=evidence(state))), 2000)

    def test_a_say_line_the_coach_cannot_fill_falls_back_to_the_built_in(self):
        options, _, problems = self._taught("Say it like: go {enemy} {enemy_level} now", enemy_level=None)
        self.assertEqual(options["jungle_six_race"].say, "Level 5. If crab's up and you're a camp from six, get it first")
        self.assertEqual(problems, [])
        options, _, problems = self._taught("Say it like: You have {stacks} stacks")
        self.assertNotIn("{", options["jungle_six_race"].say)
        self.assertTrue(any("{stacks}" in problem for problem in problems), problems)

    def test_clock_describes_the_active_player_not_a_labelled_teammate(self):
        match = jungle_game("Bel'Veth", 3, 300, 4)
        match["allPlayers"][0]["position"] = "NONE"
        match["allPlayers"][0]["summonerSpells"]["summonerSpellTwo"]["displayName"] = "Smite"
        match["allPlayers"].append({"riotId": "Mate", "team": "ORDER", "championName": "Garen", "position": "JUNGLE",
                                    "level": 9, "isDead": False, "scores": {"creepScore": 200}})
        info = jungle_clock(summarize_game(match))
        self.assertEqual((info["champion"], info["level"], info["level_edge"], info["plan"]),
                         ("Bel'Veth", 3, -1, "farm"))

    def test_observed_levels_are_spoken_not_assumed_to_be_six(self):
        behind = self._options("Bel'Veth", 4, 400, 8)["jungle_six_behind"]
        self.assertIn("Viego is 8, you're 4", behind.say)
        first = self._options("Lee Sin", 9, 780, 5)["jungle_six_first"]
        self.assertIn("You're 9, Viego is 5", first.say)
        self.assertNotIn("ult", first.say)

    def test_a_jungler_always_hears_the_clear_or_scaling_plan(self):
        options = tuple(self._options("Bel'Veth", 8, 600, 8, "what should I do now").values())
        scores = {"jungle_objective": .9, "jungle_path": .8, "jungle_scale": .1}
        self.assertEqual([option.key for option in two_options(scores, options)],
                         ["jungle_objective", "jungle_scale"])
        scores = {"jungle_scale": .9, "jungle_objective": .8, "jungle_path": .1}
        self.assertEqual([option.key for option in two_options(scores, options)],
                         ["jungle_scale", "jungle_objective"])

    def test_two_options_do_not_pair_two_farm_plans(self):
        options = (Option("a", "A", "r", family="farm"), Option("b", "B", "r", family="farm"),
                   Option("c", "C", "r", family="gank"))
        first, second = two_options({"a": .9, "b": .8, "c": .1}, options)
        self.assertEqual((first.key, second.key), ("a", "c"))

    def test_spoken_lines_stay_short_and_carry_both_alternatives(self):
        for champion in ("Bel'Veth", "Lee Sin"):
            for options in self._stage_options(champion):
                for option in options:
                    self.assertLessEqual(len(option.say.split()), 14, option.key)
        pairs = [options[:2] for options in self._stage_options()]
        dead = jungle_game("Bel'Veth", 7, 500, 7)
        dead["allPlayers"][1]["isDead"] = True
        state = summarize_game(dead)
        pairs.append(_jungle_options(state, 500, "CHAOS", jungle_clock(state))[:2])
        for options in pairs:
            reply = format_options(options, source="live game", facts="x")
            self.assertLessEqual(len(reply.spoken.split()), 24, reply.spoken)
            self.assertIn(" Or, ", reply.spoken)
            self.assertTrue(reply.spoken[0].isupper(), reply.spoken)
            self.assertIn("\nOtherwise: **", reply)
            self.assertTrue(reply.endswith("Your call."))
        self.assertIn("Their jungler is dead. Or, ", reply.spoken)
        race = format_options(tuple(reversed(pairs[2])), source="live game", facts="x")
        self.assertNotIn("Or, Level", race.spoken)

    def test_long_plan_reaches_the_ranker_for_a_jungler_only(self):
        def ranked(match):
            captured = {}
            def rank(state, key, options):
                captured.update(state)
                return {option.key: 1 / (index + 1) for index, option in enumerate(options)}
            with patch("coach.read_live_game", return_value=match), \
                 patch("coach.load_jev_key", return_value="secret"), \
                 patch("coach.jev_rank", side_effect=rank):
                coach("What next?", "balanced")
            return captured
        jungler = ranked(jungle_game("Bel'Veth", 4, 270, 4))
        self.assertIn("game", jungler)
        self.assertEqual(jungler["long_plan"]["jungle_clock"]["stage"], "second_clear")
        self.assertTrue(any("80 stacks" in text for text in jungler["long_plan"]["lessons"]))
        self.assertNotIn("long_plan", ranked(game()))


ROSTERS = {"ORDER": ("Garen", "Bel'Veth", "Ahri", "Jinx", "Leona"),
           "CHAOS": ("Darius", "Viego", "Orianna", "Caitlyn", "Lulu")}


def team_game(time, level, enemy_level, *, enemy="Viego", cs=20, enemy_cs=20, deaths=0, edges=None,
              enemy_dead=False, respawn=0, me="JUNGLE"):
    """Five against five with the active player on Bel'Veth jungle; edges is {lane: (levels, cs)} for our laners.

    me moves the active player to another position; level, cs and enemy_level stay the junglers'."""
    edges = edges or {}
    players = []
    for team, roster in ROSTERS.items():
        for role, champion in zip(("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"), roster):
            ours, jungle = team == "ORDER", role == "JUNGLE"
            lane = {"TOP": "top", "MIDDLE": "mid", "BOTTOM": "bot"}.get(role)
            up, more = edges.get(lane, (0, 0)) if ours else (0, 0)
            players.append({
                "riotId": "Ally" if ours and role == me else f"{team}{role}", "team": team, "position": role,
                "championName": enemy if jungle and not ours else champion,
                "level": (level if ours else enemy_level) if jungle else 5 + up,
                "isDead": enemy_dead and jungle and not ours,
                "respawnTimer": respawn if jungle and not ours else 0,
                "scores": {"kills": 0, "deaths": deaths if ours and role == me else 0, "assists": 0,
                           "creepScore": (cs if ours else enemy_cs) if jungle else 40 + more},
                "summonerSpells": {"summonerSpellOne": {"displayName": "Smite" if jungle else "Flash"}},
            })
    return {"gameData": {"gameTime": time, "gameMode": "CLASSIC"},
            "activePlayer": {"riotId": "Ally", "currentGold": 300}, "allPlayers": players,
            "events": {"Events": []}}


INVADE = Plan("lesson_blue_into_an_invade", "blue into an invade", ("lesson_blue_into_an_invade",),
              ("invade", "blue into", "raptors"))
ON_MENU = {plan.id: plan for plan in (PLANS["six_crab"], PLANS["gank"], INVADE, PLANS["recover"], PLANS["trade"])}
OFFER = (("jungle_first_clear", "six_crab"), ("jungle_path", "gank"))
RECOVERY_SENTENCE = "this isn't working, is there a more conservative way to get back on track this game?"


class PlanIntentTests(unittest.TestCase):
    def _intent(self, question, offer=OFFER):
        return plan_intent(question, offer, ON_MENU, None)

    def test_a_commit_needs_a_commit_verb_or_a_fresh_offer(self):
        self.assertEqual(self._intent("Let's play for six on crab."), ("commit", "six_crab"))
        self.assertEqual(self._intent("going with the invade"), ("commit", "lesson_blue_into_an_invade"))
        self.assertEqual(self._intent("first one"), ("commit", "six_crab"))
        self.assertEqual(self._intent("the other one"), ("commit", "gank"))
        self.assertEqual(self._intent("first one", offer=()), ("ask", None))
        self.assertEqual(self._intent("this isn't working, switch to ganks"), ("commit", "gank"))

    def test_questions_and_reports_do_not_commit(self):
        for question in ("should I gank", "I got a kill, gank top", "What are our options now?",
                         "we are still going to lose this fight"):
            self.assertEqual(self._intent(question), ("ask", None), question)

    def test_recovery_menu_status_and_drop_are_recognised(self):
        self.assertEqual(self._intent(RECOVERY_SENTENCE), ("recover", None))
        self.assertEqual(self._intent("safer way back"), ("recover", None))
        self.assertEqual(self._intent("what else"), ("menu", "fresh"))
        self.assertEqual(self._intent("What are my options?"), ("menu", None))
        self.assertEqual(self._intent("am I on track"), ("status", None))
        self.assertEqual(self._intent("drop the plan"), ("drop", None))

    def test_a_plan_that_is_not_on_the_menu_is_not_committed(self):
        self.assertEqual(self._intent("let's go with baron"), ("unclear", None))
        self.assertEqual(plan_intent("first one", (("buy", ""), ("jungle_path", "gank")), ON_MENU, None),
                         ("unclear", None))


class PlanProgressTests(unittest.TestCase):
    def _verdict(self, level, time, enemy_level, deaths=1):
        start = summarize_game(jungle_game("Bel'Veth", 1, 40, 1))
        stored = plan_snapshot(PLANS["six_crab"], start, jungle_clock(start))
        match = jungle_game("Bel'Veth", level, time, enemy_level)
        match["allPlayers"][0]["scores"]["deaths"] = deaths   # the fixture starts on one death
        state = summarize_game(match)
        return plan_progress(stored, state, jungle_clock(state), {"jungle_full_clear"})

    def test_six_on_crab_is_judged_by_level_time_and_deaths(self):
        on_track = self._verdict(4, 208, 4)
        self.assertEqual(on_track["verdict"], "on_track")
        self.assertIn("on pace: level 4 at 3:28 against the mark of level 4 by 3:30; no deaths since",
                      on_track["chat"])
        self.assertEqual(on_track["lead"], "On pace, level 4 at 3:28")
        behind = self._verdict(4, 355, 4)
        self.assertEqual(behind["verdict"], "behind")
        self.assertIn("behind: level 4 at 5:55 against the mark of level 5 by 5:50", behind["chat"])
        self.assertEqual(self._verdict(4, 400, 4)["verdict"], "broken")
        self.assertEqual(self._verdict(5, 340, 6)["verdict"], "broken")
        self.assertEqual(self._verdict(6, 380, 5)["verdict"], "done")
        self.assertEqual(self._verdict(4, 208, 4, deaths=2)["verdict"], "behind")
        broken = self._verdict(4, 208, 4, deaths=3)
        self.assertEqual(broken["verdict"], "broken")
        self.assertIn("2 deaths since", broken["chat"])
        self.assertEqual(broken["lead"], "Six on crab is off")

    def test_progress_never_claims_camp_crab_or_stack_state(self):
        for level, time, enemy_level in ((4, 208, 4), (4, 355, 4), (4, 400, 5), (6, 380, 5)):
            found = self._verdict(level, time, enemy_level)
            for word in ("camp", "crab is up", "stack", "ward"):
                self.assertNotIn(word, (found["chat"] + found["lead"]).casefold())


class PlanPairTests(unittest.TestCase):
    OPTIONS = (Option("jungle_full_clear", "Clear", "r", "Level 4. Keep full clearing, level six is the payoff",
                      "farm", "six_crab"),
               Option("jungle_path", "Gank", "r", "gank only a set-up lane on your path", "gank", "gank"),
               Option("jungle_recover", "Recover", "r", "reset, buy, then clear only your own side", "recover",
                      "recover"),
               Option("jungle_cover", "Cover", "r", "top is ahead on score; path that side", "cover", "cover"))

    def test_a_must_key_leads_and_two_must_keys_are_the_pair(self):
        scores = {"jungle_full_clear": .9, "jungle_cover": .8, "jungle_path": .1}
        self.assertEqual([option.key for option in two_options(scores, self.OPTIONS, must=("jungle_path",))],
                         ["jungle_path", "jungle_full_clear"])
        self.assertEqual([option.key for option in
                          two_options(scores, self.OPTIONS, must=("jungle_full_clear", "jungle_recover"))],
                         ["jungle_full_clear", "jungle_recover"])
        self.assertEqual([option.key for option in two_options(scores, self.OPTIONS)],
                         ["jungle_full_clear", "jungle_cover"])

    def test_no_pair_shares_a_plan(self):
        options = (Option("a", "A", "r", plan="p"), Option("b", "B", "r", plan="p"), Option("c", "C", "r", plan="q"))
        first, second = two_options({"a": .9, "b": .8, "c": .1}, options)
        self.assertEqual((first.key, second.key), ("a", "c"))
        for stage_options in JungleOptionTests()._stage_options():
            listed = tuple(Option(o.key, o.label, o.reason, o.say, o.family, coach_plan(o)) for o in stage_options)
            for must in ((), (listed[-1].key,)):
                first, second = two_options({}, listed, must=must)
                self.assertFalse(first.plan and first.plan == second.plan, (first.key, second.key))

    def test_a_lead_opens_the_spoken_line_and_it_stays_short(self):
        names = {plan.id: plan.name for plan in PLANS.values()}
        for lead, short in (("On pace, level 4 at 3:28", "On pace"), ("Six on crab, locked", ""),
                            ("Behind the mark, level 4 at 5:55", "Behind")):
            for second in self.OPTIONS[1:]:
                reply = format_options((self.OPTIONS[0], second), source="live game", facts="x", lead=lead,
                                       short_lead=short, names=names)
                self.assertLessEqual(len(reply.spoken.split()), 24, reply.spoken)
                self.assertTrue(reply.spoken.startswith(lead), reply.spoken)
                self.assertIn(" Or, ", reply.spoken)
                self.assertNotIn("Level 4. Keep", reply.spoken)
                self.assertTrue(reply.startswith("Game read"))
        self.assertEqual(format_options(self.OPTIONS[:2], source="live game", facts="x", lead="On pace, level 4 at "
                                        "3:28", names=names).spoken,
                         "On pace, level 4 at 3:28. Keep full clearing, level six is the payoff. "
                         "Or, gank only a set-up lane on your path.")

    def test_a_long_second_half_falls_back_to_its_plan_name(self):
        wordy = Option("jungle_first_clear", "Clear", "r",
                       "Finish your camps, then crab if it's free; every camp counts for six", "farm", "six_crab")
        reply = format_options((wordy, self.OPTIONS[1]), source="live game", facts="x", lead="Six on crab, locked",
                               names={"gank": "gank set-up lanes"})
        self.assertEqual(reply.spoken, "Six on crab, locked. Finish your camps, then crab if it's free; every camp "
                                       "counts for six. Or, gank set-up lanes.")

    def test_more_adds_alternatives_in_chat_and_names_them_aloud(self):
        reply = format_options(self.OPTIONS[:2], source="live game", facts="x", more=self.OPTIONS[2:],
                               names={plan.id: plan.name for plan in PLANS.values()})
        self.assertTrue(reply.endswith("Your call."))
        self.assertEqual(reply.count("\nOtherwise: **"), 3)
        self.assertTrue(reply.spoken.startswith("Options: six on crab, gank set-up lanes,"), reply.spoken)
        self.assertTrue(reply.spoken.endswith("Your call."))
        self.assertLessEqual(len(reply.spoken.split()), 24)
        self.assertNotIn("\n1. ", reply)

    def test_without_a_lead_the_reply_is_what_it_was(self):
        plain = format_options(self.OPTIONS[:2], source="live game", facts="x")
        self.assertEqual(plain, "Game read (live game): x.\n**Clear** — r\nOtherwise: **Gank** — r\nYour call.")
        self.assertEqual(plain.spoken, "Level 4. Keep full clearing, level six is the payoff. "
                                       "Or, gank only a set-up lane on your path.")


def coach_plan(option):
    from coach import PLAN_OF
    return option.plan or PLAN_OF.get(option.key, "")


class PlanMemoryTests(unittest.TestCase):
    """Through coach() with a real board; the feed and the ranker are mocked."""

    def setUp(self):
        self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
        self.sent = []

    def _ask(self, question, match, board="own", fail=False):
        def rank(state, key, options):
            if fail:
                raise OSError("offline")
            self.sent.append(state)
            return {option.key: 1 / (index + 1) for index, option in enumerate(options)}
        with patch("coach.read_live_game", return_value=match), \
             patch("coach.load_jev_key", return_value="secret"), \
             patch("coach.jev_rank", side_effect=rank):
            return coach(question, "balanced", coordinator_board=self.board if board == "own" else board)

    def _commit(self):
        return self._ask("Let's play for six on crab.", team_game(125, 2, 2))

    def test_commit_stores_the_plan_and_still_offers_two(self):
        reply = self._commit()
        self.assertEqual(self.board.plan["id"], "six_crab")
        self.assertEqual(self.board.plan["marks"], (("level", 4, 210), ("level", 5, 350)))
        self.assertIn("plan set at 2:05: six on crab", reply)
        self.assertTrue(reply.startswith("Game read (live game)"))
        self.assertIn("\nOtherwise: **", reply)
        self.assertTrue(reply.spoken.startswith("Six on crab, locked. "), reply.spoken)
        self.assertEqual(self.board.offer[0], ("jungle_first_clear", "six_crab"))
        self.assertNotEqual(self.board.offer[1][1], "six_crab")

    def test_status_on_pace_keeps_the_plan_step_first(self):
        self._commit()
        reply = self._ask("am I on track", team_game(208, 4, 4))
        self.assertIn("plan: six on crab since 2:05, on pace: level 4 at 3:28", reply)
        self.assertEqual(self.board.offer[0][0], "jungle_full_clear")
        self.assertTrue(reply.spoken.startswith("On pace, level 4 at 3:28. Keep full clearing"), reply.spoken)
        self.assertEqual(self.board.plan["said"], "on_track")

    def test_behind_pairs_the_plan_step_with_a_safe_line(self):
        self._commit()
        reply = self._ask("am I on track", team_game(355, 4, 5, deaths=1))
        self.assertIn("behind: level 4 at 5:55 against the mark of level 5 by 5:50; 1 death since", reply)
        self.assertEqual(self.board.offer[0][0], "jungle_full_clear")
        self.assertIn(self.board.offer[1][0], SAFE_KEYS)
        self.assertTrue(reply.spoken.startswith("Behind"), reply.spoken)
        self.assertLessEqual(len(reply.spoken.split()), 24)

    def test_a_broad_question_repeats_the_verdict_only_when_it_changes(self):
        self._commit()
        first = self._ask("What are our options now?", team_game(208, 4, 4))
        again = self._ask("What are our options now?", team_game(215, 4, 4))
        self.assertTrue(first.spoken.startswith("On pace"), first.spoken)
        self.assertFalse(again.spoken.startswith("On pace"), again.spoken)
        self.assertIn("plan: six on crab since 2:05, on pace", again)
        late = self._ask("What are our options now?", team_game(356, 4, 4))
        self.assertTrue(late.spoken.startswith("Behind"), late.spoken)

    def test_recovery_request_gives_two_safe_lines_and_sets_the_plan_aside(self):
        self._commit()
        reply = self._ask(RECOVERY_SENTENCE, team_game(400, 5, 6))
        self.assertEqual(len(self.board.offer), 2)
        for key, _ in self.board.offer:
            self.assertIn(key, SAFE_KEYS)
        self.assertTrue(self.board.plan["off"])
        self.assertIn("plan: none active (six on crab set aside at 6:40)", reply)
        self.assertTrue(reply.spoken.startswith("Six on crab set aside. "), reply.spoken)
        self.assertNotIn(" is off", reply.spoken)
        self.assertIn(" Or, ", reply.spoken)
        self.assertLessEqual(len(reply.spoken.split()), 24)
        # A set-aside plan is not framed around again, but a status question still says where it went.
        later = self._ask("What are our options now?", team_game(420, 5, 6))
        self.assertNotIn("plan: ", later.splitlines()[0])
        self.assertEqual(later.spoken.count("Six on crab"), 0)
        self.assertIn("plan: none active (six on crab set aside at 6:40)",
                      self._ask("am I on track", team_game(425, 5, 6)))
        self.assertTrue(self.board.plan["off"])

    def test_recovery_without_a_plan_still_offers_two_safe_lines(self):
        match = game()
        match["allPlayers"][0]["position"] = "BOTTOM"
        match["gameData"]["gameTime"] = 500
        reply = self._ask("safer way back", match)
        self.assertEqual({key for key, _ in self.board.offer}, {"lane_safe", "lane_reset"})
        self.assertTrue(reply.spoken.startswith("Safer lines. "), reply.spoken)
        self.assertIsNone(self.board.plan)

    def test_a_ranker_failure_changes_nothing_on_the_board(self):
        reply = self._ask("Let's play for six on crab.", team_game(125, 2, 2), fail=True)
        self.assertIn("Jev is unavailable", reply)
        self.assertIsNone(self.board.plan)
        self.assertEqual(self.board.offer, ())
        self._commit()
        self._ask("drop the plan", team_game(130, 2, 2), fail=True)
        self.assertEqual(self.board.plan["id"], "six_crab")
        self.assertIn("Plan dropped", self._ask("drop the plan", team_game(131, 2, 2)).spoken)
        self.assertIsNone(self.board.plan)

    def test_current_plan_reaches_the_ranker_only_with_a_board(self):
        self._commit()
        self.assertNotIn("current_plan", self.sent[-1])
        with patch.object(lane_playbook, "pro_lessons", return_value=()):   # as with no pro_lessons.md
            self._ask("should I gank top", team_game(208, 4, 4))
        plan = self.sent[-1]["current_plan"]
        self.assertEqual((plan["name"], plan["verdict"], plan["set_aside"]), ("six on crab", "on_track", False))
        self.assertEqual(plan["marks"], ["level 4 by 3:30", "level 5 by 5:50"])
        self.assertEqual(self.sent[-1]["team_question"], "should I gank top")
        self.assertNotIn("pro_principles", self.sent[-1])
        plain = self._ask("Let's play for six on crab.", team_game(125, 2, 2), board=None)
        self.assertNotIn("current_plan", self.sent[-1])
        self.assertNotIn("plan set at", plain)
        self.assertNotIn("locked", plain.spoken)

    def test_menu_lists_more_alternatives_without_changing_the_plan(self):
        reply = self._ask("What are my options?", team_game(125, 2, 2, edges={"top": (1, 6), "bot": (0, -18)}))
        self.assertGreaterEqual(reply.count("\nOtherwise: **"), 2)
        self.assertTrue(reply.spoken.startswith("Options: "), reply.spoken)
        self.assertTrue(reply.endswith("Your call."))
        self.assertIsNone(self.board.plan)
        plans = [plan for _, plan in self.board.offer]
        self.assertEqual(len(plans), len(set(plans)))

    def test_pro_principles_reach_the_ranker_as_background_only(self):
        lane_playbook.plays()
        with tempfile.TemporaryDirectory() as directory:
            for name in ("lessons.md",):
                (Path(directory) / name).write_text("", encoding="utf-8")
            (Path(directory) / "pro_lessons.md").write_text(
                "## Trade the far side\nRoles: jungle\nPhase: any\nWhen: any\nSituation: Their jungler shows.\n"
                "Our side: Gains camps.\nTheir side: Gets the near side.\nSeen in: 4 games\n", encoding="utf-8")
            with patch.object(lane_playbook, "PLAYBOOK_ROOT", Path(directory)):
                reply = self._ask("What next?", team_game(208, 4, 4))
        self.assertTrue(self.sent[-1]["pro_principles"][0].startswith(
            "Trade the far side: If this holds (not observed here): Their jungler shows."))
        self.assertNotIn("Trade the far side", reply)
        self.assertNotIn("Trade the far side", reply.spoken)


class NewOptionTests(unittest.TestCase):
    def _keys(self, match, question="where should I path", recover=""):
        return {option.key: option for option in
                candidate_options(summarize_game(match), question, recover=recover)}

    def test_new_jungle_options_appear_only_under_their_observed_triggers(self):
        quiet = self._keys(team_game(310, 4, 4))   # no dated objective inside two minutes
        for key in ("jungle_recover", "jungle_trade", "jungle_steal", "jungle_cover", "jungle_counter",
                    "jungle_objective", "lane_safe"):
            self.assertNotIn(key, quiet)
        behind = self._keys(team_game(270, 4, 5))
        self.assertEqual((behind["jungle_recover"].family, behind["jungle_trade"].family), ("recover", "trade"))
        self.assertEqual(behind["jungle_recover"].plan, "recover")
        steal = self._keys(team_game(270, 4, 4, enemy_dead=True, respawn=30))["jungle_steal"]
        self.assertIn("depends on where you are", steal.reason)
        self.assertNotIn("That is time", steal.reason)
        self.assertNotIn("jungle_steal", self._keys(team_game(270, 4, 4, enemy_dead=True, respawn=20)))
        self.assertNotIn("jungle_steal", self._keys(team_game(900, 9, 9, enemy_dead=True, respawn=30)))
        lanes = self._keys(team_game(270, 4, 4, edges={"top": (1, 6), "bot": (0, -18)}), "what should I do now")
        self.assertIn("Your top lane (Garen) is +1 levels and +6 CS", lanes["jungle_cover"].reason)
        self.assertIn("Your bot lane is behind on score", lanes["jungle_counter"].reason)
        self.assertIn("not a sighting", lanes["jungle_counter"].reason)
        self.assertNotIn("lane_lead", lanes)
        listed = self._keys(team_game(270, 4, 4, enemy="Nunu & Willump"))
        self.assertIn("Nunu & Willump is on your gank-first list", listed["jungle_counter"].reason)
        self.assertIn("jungle_objective", self._keys(team_game(380, 5, 5)))   # Grubs at 8:00 are two minutes out

    def test_recover_modes_force_and_filter_the_safe_options(self):
        match = team_game(270, 4, 4)
        self.assertIn("jungle_recover", self._keys(match, recover="add"))
        self.assertIn("jungle_full_clear", self._keys(match, recover="add"))
        only = self._keys(match, "game plan", recover="only")
        self.assertTrue({"jungle_recover", "jungle_trade"} <= set(only))
        self.assertTrue(set(only) <= SAFE_KEYS)
        for position in ("TOP", "UTILITY", None):
            laner = game()
            laner["gameData"]["gameTime"] = 500
            if position:
                laner["allPlayers"][0]["position"] = position
            only = self._keys(laner, "game plan", recover="only")
            self.assertTrue({"lane_safe", "lane_reset"} <= set(only), position)
            self.assertTrue(set(only) <= SAFE_KEYS)
            self.assertNotIn("lane_safe", self._keys(laner, "What next?"))
        dead = game(ally_dead=True)
        self.assertEqual(self._keys(dead, "What next?")["lane_safe"].family, "recover")

    def test_new_options_stay_short_and_state_nothing_unseen(self):
        stated = re.compile(r"(?<!if the )(?<!is the )(?<!one )crab is up", re.IGNORECASE)
        seen_keys = set()
        for enemy in ("Viego", "Nunu & Willump"):
            for time, level, enemy_level in ((60, 1, 1), (270, 4, 5), (340, 5, 5), (380, 5, 6), (380, 6, 5)):
                state = summarize_game(team_game(time, level, enemy_level, enemy=enemy, enemy_dead=True, respawn=25,
                                                 edges={"top": (2, 30), "bot": (-1, -20)}))
                options = _jungle_options(state, time, "CHAOS", jungle_clock(state), recover=True)
                self.assertLessEqual(len(options), 8)
                laner = candidate_options(summarize_game(game(ally_dead=True)), "game plan", recover="add")
                for option in (*options, *laner):
                    seen_keys.add(option.key)
                    self.assertIsNone(stated.search(option.reason), option.key)
                    self.assertIsNone(stated.search(option.say), option.key)
                    if option.key in ("jungle_recover", "jungle_trade", "jungle_steal", "jungle_cover",
                                      "jungle_counter", "lane_safe") or option.key.startswith("lesson_"):
                        self.assertLessEqual(len(option.say.split()), 14, option.key)
                        self.assertIn("You check", option.reason, option.key)
                        self.assertIn("cannot see", option.reason, option.key)
                        self.assertNotIn("enemy jungler is dead", option.reason.casefold())
                        self.assertNotIn("your jungler is dead", option.reason.casefold())
        for key in ("jungle_recover", "jungle_trade", "jungle_steal", "jungle_cover", "jungle_counter",
                    "lesson_blue_into_an_invade", "lane_safe"):
            self.assertIn(key, seen_keys)

    def test_a_lesson_with_offer_at_becomes_its_own_plan_until_it_expires(self):
        lane_playbook.plays()
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(lane_playbook, "PLAYBOOK_ROOT", Path(directory)):
            (Path(directory) / "lessons.md").write_text(
                "## Red then dive\nApplies to: jungle\nOffer at: first_clear\nUntil: 1:30\nKind: gank\n"
                "Name: red into a dive\nPick it with: dive, red start\nGoal: Start red and dive bot at level 3\n"
                "Player check: Is the wave under their tower? The coach cannot see waves.\n"
                "On track: level 3 by 2:45\nSay it like: red, then dive bot at three\n"
                "## No goal\nApplies to: jungle\nOffer at: first_clear\nSay it like: go\n", encoding="utf-8")
            early = summarize_game(team_game(40, 1, 1))
            options = {option.key: option for option in candidate_options(early, "game plan")}
            plans = plan_table(tuple(options.values()), "jungle", "Bel'Veth")
            late = {option.key for option in candidate_options(summarize_game(team_game(100, 2, 2)), "game plan")}
        taught = options["lesson_red_then_dive"]
        self.assertEqual((taught.family, taught.plan), ("gank", "lesson_red_then_dive"))
        self.assertEqual(taught.label, "Start red and dive bot at level 3")
        self.assertEqual(taught.say, "red, then dive bot at three")
        self.assertIn("You check: Is the wave under their tower?", taught.reason)
        self.assertNotIn("lesson_no_goal", options)
        plan = plans["lesson_red_then_dive"]
        self.assertEqual((plan.name, plan.words, plan.marks),
                         ("red into a dive", ("dive", "red start"), (("level", 3, 165),)))
        self.assertEqual(plan_intent("I'll take the dive", (), plans, None), ("commit", "lesson_red_then_dive"))
        self.assertFalse(any(key.startswith("lesson_") for key in late))

    def test_the_shipped_lessons_name_the_crab_plan_and_offer_the_invade(self):
        early = candidate_options(summarize_game(team_game(40, 1, 1)), "game plan")
        self.assertEqual([option.key for option in early[:2]], ["jungle_first_clear", "jungle_path"])
        invade = next(option for option in early if option.key == "lesson_blue_into_an_invade")
        self.assertEqual(invade.family, "invade")
        plans = plan_table(early, "jungle", "Bel'Veth")
        self.assertEqual(plans["six_crab"].name, "six on crab")
        self.assertEqual(plans["six_crab"].marks, (("level", 4, 210), ("level", 5, 350)))
        self.assertEqual(plans["lesson_blue_into_an_invade"].name, "blue into an invade")
        reply = format_options((early[0], invade), source="live game", facts="x", lead="Six on crab, locked",
                               names={plan.id: plan.name for plan in plans.values()})
        self.assertEqual(reply.spoken, "Six on crab, locked. Finish your camps, then crab if it's free; every camp "
                                       "counts for six. Or, blue into an invade.")
        plain = format_options((early[0], invade), source="live game", facts="x")
        self.assertEqual(plain.spoken, "Finish your camps, then crab if it's free; every camp counts for six. "
                                       "Or, blue into one enemy camp, back out, then full clear.")
        self.assertLessEqual(len(plain.spoken.split()), 24)

    def test_situation_tags_are_all_known_to_the_pro_lesson_file(self):
        self.assertTrue(set(PLAY_TRIGGERS) <= set(lane_playbook.PRO_TAGS))
        matches = [game(), game(gold=1800, enemy_dead=True, dragon=True, baron=True, inhib=True),
                   game(ally_dead=True), team_game(270, 4, 5), team_game(380, 6, 5, enemy_dead=True, respawn=20)]
        kill = game(enemy_dead=True)
        kill["events"]["Events"] += [
            {"EventName": "ChampionKill", "EventTime": 890, "KillerName": "Ally", "VictimName": "Enemy"},
            {"EventName": "TurretKilled", "EventTime": 880, "KillerName": "Ally"}]
        found = set()
        for match in matches + [kill]:
            tags = situation_tags(summarize_game(match))
            self.assertTrue(tags <= set(lane_playbook.PRO_TAGS), tags)
            found |= tags
        for tag in ("behind", "ahead", "numbers_up", "numbers_down", "gold_ready", "after_kill", "tower_down",
                    "after_objective", "enemy_jungler_dead", "objective_soon"):
            self.assertIn(tag, found)
        self.assertEqual(situation_tags(summarize_game(game())), set())


class PlanTalkTests(unittest.TestCase):
    """plan_intent against the real early Bel'Veth menu, with the shipped lessons.md."""

    def setUp(self):
        menu = candidate_options(summarize_game(team_game(125, 2, 2)), "game plan", recover="add")
        self.plans = plan_table(menu, "jungle", "Bel'Veth")

    def _intent(self, question, offer=OFFER):
        return plan_intent(question, offer, self.plans, None)

    def test_a_question_that_names_a_plan_is_not_a_choice(self):
        for question in ("Hey, should I take the crab?", "If I gank top I'll lose my camps, is that worth it?",
                         "I'll be six soon, what then?", "tell me, do the enemies have six?",
                         "so should I do the full clear or gank", "I'll kill him, then should I recall?",
                         "ok should I take the crab", "okay should I go with the gank or keep farming",
                         "so do I take the crab or gank", "and should I do the scuttle", "I'll die if I gank",
                         "gank?", "six?", "the crab?", "he will take the crab", "I'll take the crab or gank"):
            for offer in ((), OFFER):
                self.assertEqual(self._intent(question, offer), ("ask", None), question)

    def test_ordinary_ways_of_stating_a_choice_commit(self):
        for question in ("Let's full clear", "I'll farm", "let's clear", "let's go with the full clear",
                         "I'll play for level 6", "switch to farming", "actually let's farm", "I'm gonna farm",
                         "I'm going for the crab", "go for six on crab", "go back to six on crab", "take the crab"):
            self.assertEqual(self._intent(question, ()), ("commit", "six_crab"), question)
        for question in ("I'm going to gank", "I'm gonna gank", "I want to gank", "I'd rather gank"):
            self.assertEqual(self._intent(question, ()), ("commit", "gank"), question)
        for question, plan in (("ok the first one", "six_crab"), ("yeah the first one", "six_crab"),
                               ("um, the second one", "gank"), ("second one please", "gank"),
                               ("yeah do that", "six_crab"), ("number two", "gank"), ("option two", "gank"),
                               ("let's do the second one", "gank"), ("gank", "gank"), ("six on crab", "six_crab")):
            self.assertEqual(self._intent(question), ("commit", plan), question)
            self.assertEqual(self._intent(question, ())[0], "ask", question)

    def test_a_short_answer_only_picks_a_plan_that_was_just_offered(self):
        for question in ("reset", "recall", "buy", "trade"):
            self.assertEqual(self._intent(question), ("ask", None), question)
        self.assertEqual(self._intent("safer"), ("recover", None))
        safe_offer = (("jungle_recover", "recover"), ("jungle_trade", "trade"))
        self.assertEqual(self._intent("the safer one", safe_offer), ("commit", "recover"))
        self.assertEqual(self._intent("trade", safe_offer), ("commit", "trade"))

    def test_recovery_status_and_drop_follow_what_was_meant(self):
        for question in ("how do I get back into the game", "I need to play safe", "play it safe", "I keep dying",
                         "that didn't work", "the plan failed", "we're losing", "I fell behind",
                         "I'm getting destroyed", "is there a safer way"):
            self.assertEqual(self._intent(question), ("recover", None), question)
        for question in ("is it safer to gank top or bot", "are we falling behind?", "how do I recover from this"):
            self.assertEqual(self._intent(question), ("ask", "safe"), question)
        for question in ("am I back on track", "how's it going", "how's my plan", "is the plan working",
                         "what's my plan", "am I ahead"):
            self.assertEqual(self._intent(question), ("status", None), question)
        self.assertEqual(self._intent("no plan"), ("drop", None))
        self.assertEqual(self._intent("I have no plan"), ("ask", None))
        self.assertEqual(self._intent("there's no plan B"), ("recover", None))


class PlanWordingTests(unittest.TestCase):
    """What the coach says about a plan names only what the feed showed."""

    def _progress(self, plan, level, time, enemy_level, deaths=1, keys=("jungle_path",)):
        start = summarize_game(jungle_game("Bel'Veth", 1, 40, 1 if enemy_level is not None else None))
        stored = plan_snapshot(PLANS[plan], start, jungle_clock(start))
        match = jungle_game("Bel'Veth", level, time, enemy_level)
        match["allPlayers"][0]["scores"]["deaths"] = deaths   # the fixture starts on one death
        state = summarize_game(match)
        return plan_progress(stored, state, jungle_clock(state), set(keys))

    def test_behind_the_mark_is_said_only_for_a_missed_mark(self):
        death = self._progress("six_crab", 4, 208, 4, deaths=2)
        self.assertEqual((death["verdict"], death["lead"]), ("behind", "One death since, level 4 at 3:28"))
        self.assertIn("slipping (a death): level 4 at 3:28 against the mark of level 4 by 3:30", death["chat"])
        enemy_up = self._progress("six_crab", 4, 200, 5)
        self.assertEqual((enemy_up["verdict"], enemy_up["lead"]), ("behind", "Behind their jungler, level 4 at 3:20"))
        self.assertNotIn("mark,", enemy_up["lead"] + death["lead"])
        missed = self._progress("six_crab", 4, 355, 4)
        self.assertEqual(missed["lead"], "Behind the mark, level 4 at 5:55")

    def test_on_pace_needs_a_mark_still_ahead(self):
        late = self._progress("six_crab", 5, 480, 5)
        self.assertEqual((late["verdict"], late["lead"]), ("on_track", "Past the last mark, level 5 at 8:00"))
        self.assertIn("past the last mark: level 5 at 8:00, past the last mark of level 5 by 5:50", late["chat"])
        gank = self._progress("gank", 3, 300, 3)
        self.assertEqual((gank["verdict"], gank["lead"], gank["short"]),
                         ("on_track", "No setback since you chose it", "No setback"))
        self.assertNotIn("pace", (late["chat"] + late["lead"] + gank["chat"]).casefold())
        unknown = self._progress("gank", 3, 300, None)
        self.assertEqual(unknown["lead"], "No deaths since you chose it")
        self.assertIn("no score comparison on the feed", unknown["chat"])

    def test_done_is_said_only_for_a_finish_the_feed_shows(self):
        closed = self._progress("gank", 3, 300, 3, keys=())
        self.assertEqual((closed["verdict"], closed["lead"], closed["short"]),
                         ("done", "Gank set-up lanes: the window has passed", "Window passed"))
        self.assertIn("window closed", closed["chat"])
        self.assertNotIn("done", closed["chat"] + closed["lead"])
        self.assertEqual(self._progress("six_crab", 6, 380, 5)["lead"], "Six on crab is done")
        self.assertEqual(self._progress("recover", 4, 300, 4)["verdict"], "done")
        self.assertNotEqual(self._progress("recover", 4, 300, None)["verdict"], "done")

    def test_recover_says_until_you_are_level_only_when_behind(self):
        def recover(match):
            return {option.key: option for option in
                    candidate_options(summarize_game(match), "game plan", recover="add")}["jungle_recover"]
        ahead = recover(team_game(300, 5, 4))
        self.assertEqual(ahead.label, "Reset, buy, then clear only your own side")
        self.assertIn("until your next item", ahead.reason)
        for claim in ("matches theirs", "ahead of their jungler", "shows you level"):
            self.assertNotIn(claim, ahead.reason)
        behind = recover(team_game(300, 4, 5))
        self.assertEqual(behind.label, "Reset, buy, then clear only your own side until you are level")
        self.assertIn("until your level matches theirs", behind.reason)
        dead = team_game(300, 4, 4)
        next(player for player in dead["allPlayers"] if player["riotId"] == "Ally")["isDead"] = True
        self.assertIn("When you respawn, buy, then take", recover(dead).reason)
        self.assertNotIn("Recall when the camp you are on", recover(dead).reason)

    def test_a_mixed_lane_is_neither_ahead_nor_behind(self):
        keys = {option.key for option in candidate_options(
            summarize_game(team_game(200, 3, 3, edges={"top": (1, -15)})), "what should I do now")}
        self.assertNotIn("jungle_cover", keys)
        self.assertNotIn("jungle_counter", keys)

    def test_counter_and_objective_do_not_state_intent_waves_or_kill_events(self):
        options = {option.key: option for option in candidate_options(
            summarize_game(team_game(250, 4, 4, enemy="Lee Sin")), "what should I do now")}
        counter = options["jungle_counter"]
        self.assertEqual(counter.label, "Track Lee Sin and hold near a lane in case they gank")
        self.assertEqual(counter.say, "track Lee Sin; hold near a pushed-up lane in case they gank")
        self.assertIn("whichever of your lanes is pushed up", counter.reason)
        self.assertNotIn("your pushed-up lane", counter.reason + counter.say)
        self.assertIn("Dragon in 0:50, by patch timers.", options["jungle_objective"].reason)

    def test_the_safe_lane_line_follows_role_and_phase(self):
        def safe(position, time):
            match = game()
            match["gameData"]["gameTime"] = time
            match["allPlayers"][0]["position"] = position
            return {option.key: option for option in
                    candidate_options(summarize_game(match), "game plan", recover="only")}["lane_safe"]
        self.assertIn("last-hit", safe("MIDDLE", 500).reason)
        support = safe("UTILITY", 500)
        self.assertTrue(support.label.startswith("Stay with your carry"), support.label)
        self.assertNotIn("last-hit", support.reason)
        late = safe("UTILITY", 1000)
        self.assertTrue(late.label.startswith("Catch waves on your own side"), late.label)
        self.assertEqual(safe("MIDDLE", 1000).label, late.label)
        for option in (support, late, safe("MIDDLE", 500)):
            self.assertLessEqual(len(option.say.split()), 14)
            self.assertIn("You check", option.reason)
            self.assertIn("cannot see", option.reason)

    def test_a_long_plain_line_names_the_second_half_and_says_dead_once(self):
        state = summarize_game(team_game(125, 2, 2, edges={"top": (1, 6)}, enemy_dead=True, respawn=30))
        options = {option.key: option for option in candidate_options(state, "game plan")}
        names = {plan.id: plan.name for plan in PLANS.values()}
        pair = (options["jungle_cover"], options["jungle_first_clear"])
        plain = format_options(pair, source="live game", facts="x")
        self.assertEqual(plain.spoken, "Top is ahead on score; path there, gank a set wave. Or, Finish your camps, "
                                       "then crab if it's free; every camp counts for six.")
        named = format_options(pair, source="live game", facts="x", names=names)
        self.assertEqual(named.spoken, "Top is ahead on score; path there, gank a set wave. Or, six on crab.")
        short = format_options((options["jungle_path"], options["jungle_cover"]), source="live game", facts="x",
                               names=names)
        self.assertIn("Or, top is ahead on score", short.spoken)   # it fits, so it is left as it was
        late = {option.key: option for option in candidate_options(
            summarize_game(team_game(380, 5, 5, enemy_dead=True, respawn=30)), "game plan")}
        both = format_options((late["jungle_steal"], late["jungle_objective"]), source="live game", facts="x",
                              names=names)
        self.assertEqual(both.spoken.casefold().count("dead"), 1, both.spoken)
        self.assertLessEqual(len(both.spoken.split()), 24, both.spoken)


class PlanReviewTests(unittest.TestCase):
    """Through coach() with a real board; the feed and the ranker are mocked."""
    setUp = PlanMemoryTests.setUp
    _ask = PlanMemoryTests._ask
    _commit = PlanMemoryTests._commit

    def test_the_shipped_pick_words_add_to_the_built_in_ones(self):
        reply = self._ask("Let's full clear", team_game(125, 2, 2))
        self.assertEqual(self.board.plan["id"], "six_crab")
        self.assertNotIn("not on offer", reply)
        self.assertTrue(reply.spoken.startswith("Six on crab, locked. "), reply.spoken)

    def test_a_question_does_not_overwrite_the_plan(self):
        self._commit()
        for question in ("Hey, should I take the gank?", "ok so should I go with the gank or keep farming"):
            reply = self._ask(question, team_game(130, 2, 2))
            self.assertEqual(self.board.plan["id"], "six_crab", question)
            self.assertNotIn("locked", reply.spoken)

    def test_a_broken_plan_is_said_once_and_then_set_aside(self):
        self._ask("I'll gank", team_game(125, 2, 2))
        self.assertEqual(self.board.plan["id"], "gank")
        ahead = dict(cs=120, enemy_cs=90, deaths=2)
        first = self._ask("What are our options now?", team_game(600, 8, 7, **ahead))
        self.assertTrue(first.spoken.startswith("Gank set-up lanes is off. "), first.spoken)
        self.assertTrue(self.board.plan["off"])
        self.assertNotIn("matches theirs", first)
        self.assertFalse({key for key, _ in self.board.offer} <= SAFE_KEYS)   # ahead on the feed: real options too
        again = self._ask("what should I do", team_game(610, 8, 7, **ahead))
        self.assertFalse({key for key, _ in self.board.offer} <= SAFE_KEYS)
        self.assertNotIn("plan: ", again.splitlines()[0])
        self.assertNotIn("until you are level", again)
        status = self._ask("am I on track", team_game(620, 8, 7, **ahead))
        self.assertIn("plan: none active (gank set-up lanes went off at 10:00)", status)
        self.assertTrue(status.spoken.startswith("Gank set-up lanes is off. "), status.spoken)

    def test_a_broken_plan_while_behind_gets_only_the_safe_lines_that_once(self):
        self._ask("I'll gank", team_game(125, 2, 2))
        self._ask("what now", team_game(300, 4, 5, deaths=2))
        self.assertTrue({key for key, _ in self.board.offer} <= SAFE_KEYS)
        self.assertTrue(self.board.plan["off"])

    def test_a_laner_hears_the_lock_and_the_verdict(self):
        match = team_game(300, 4, 4, me="TOP")
        reply = self._ask("I'll hold", match)
        self.assertEqual(self.board.plan["id"], "top_hold")
        self.assertTrue(reply.spoken.startswith("Hold the wave, locked. "), reply.spoken)
        self.assertIn(" Or, ", reply.spoken)
        self.assertLessEqual(len(reply.spoken.split()), 24, reply.spoken)
        status = self._ask("am I on track", team_game(310, 4, 4, me="TOP"))
        self.assertTrue(status.spoken.startswith("No setback"), status.spoken)
        self.assertLessEqual(len(status.spoken.split()), 24, status.spoken)
        self.assertIn("no setback: level 5 to 5, CS 40 to 40 since then", status)

    def test_a_refused_choice_is_heard(self):
        mid = team_game(250, 4, 4, me="MIDDLE")
        self._ask("What next?", mid)
        self.assertEqual(self.board.offer, (("mid_roam_wave", "mid_roam"), ("lane_tempo", "")))
        single = self._ask("the second one", mid)
        self.assertIsNone(self.board.plan)
        self.assertIn("no plan change: that one is a single play, not a plan to hold", single)
        self.assertNotIn("not on offer", single)
        self.assertTrue(single.spoken.startswith("That's a single play. "), single.spoken)
        self.assertLessEqual(len(single.spoken.split()), 24, single.spoken)
        absent = self._ask("let's go with baron", mid)
        self.assertTrue(absent.spoken.startswith("No plan change"), absent.spoken)
        self.assertIn(" Or, ", absent.spoken)

    def test_a_safety_question_or_a_status_question_keeps_the_plan(self):
        self._commit()
        safety = self._ask("is it safer to gank top or bot", team_game(130, 2, 2))
        self.assertFalse(self.board.plan["off"])
        self.assertNotIn("set aside", safety + safety.spoken)
        status = self._ask("am I back on track", team_game(208, 4, 4))
        self.assertFalse(self.board.plan["off"])
        self.assertTrue(status.spoken.startswith("On pace, level 4 at 3:28. "), status.spoken)

    def test_status_without_a_plan_says_so_aloud(self):
        self.assertTrue(self._ask("am I on track", team_game(208, 4, 4)).spoken.startswith("No plan set. "))
        self._commit()
        self._ask(RECOVERY_SENTENCE, team_game(400, 5, 6))
        later = self._ask("am I on track", team_game(425, 5, 6))
        self.assertTrue(later.spoken.startswith("Six on crab is set aside. "), later.spoken)

    def test_the_menu_does_not_offer_a_recall_before_the_first_clear(self):
        early = self._ask("What are my options?", team_game(50, 1, 1))
        self.assertNotIn("lane_reset", {key for key, _ in self.board.offer})
        self.assertNotIn("reset and buy", early.spoken)
        self.assertTrue(early.spoken.startswith("Options: six on crab, "), early.spoken)

    def test_what_else_with_nothing_new_says_so(self):
        support = team_game(200, 3, 3, me="UTILITY")
        self._ask("what are my options", support)
        again = self._ask("what else", support)
        self.assertTrue(again.spoken.startswith("Nothing new on the feed. "), again.spoken)
        self.assertIn("no further options on the feed right now", again)
        self.assertLessEqual(len(again.spoken.split()), 24, again.spoken)


class QuickIntentTests(unittest.TestCase):
    """ "stop" and "more" are whole sentences, never a phrase inside a question."""

    def test_every_listed_phrase_is_recognised(self):
        for phrase in STOP_PHRASES:
            self.assertEqual(quick_intent(phrase), ("stop", None), phrase)
        for phrase in MORE_PHRASES:
            self.assertEqual(quick_intent(phrase), ("more", None), phrase)
        self.assertFalse(STOP_PHRASES & MORE_PHRASES)

    def test_padded_stops_and_mores_are_recognised(self):
        for question in ("Stop.", "Ok, stop.", "Stop! Stop!", "no stop", "coach shut up please", "stop right now",
                         "no more", "that's enough"):
            self.assertEqual(quick_intent(question), ("stop", None), question)
        for question in ("keep going", "so why", "explain more", "what do you mean?"):
            self.assertEqual(quick_intent(question), ("more", None), question)

    def test_a_stop_said_twice_or_with_filler_is_still_a_stop(self):
        for question in ("Stop it, stop it.", "Shut up, shut up.", "Stop. Thank you.", "Can you stop?",
                         "I said stop.", "Stop! Enough!", "Stop talking, stop.", "Stop it. Stop.",
                         "Stop please stop", "Stop, coach, stop", "Stop. Bye.", "stop the coach", "Shut up, coach.",
                         "Thank you. Stop."):
            self.assertEqual(quick_intent(question), ("stop", None), question)
        # Every word has to be part of a stop phrase or padding.
        for question in ("how do I stop their jungler", "should I stop farming", "Should I stop?", "stop farming",
                         "stop the plan", "stop it, their jungler is top", "no", "thanks", "you", "right now",
                         "enough ganks", "no more camps"):
            self.assertIsNone(quick_intent(question), question)

    def test_more_can_point_at_the_whole_read(self):
        topics = (("six on crab", "crab", "farm"), ("gank", "ganks", "invade"))
        for question in ("tell me more about that", "more on that", "why these two", "why those two",
                         "explain them", "explain this", "explain both of them", "explain again", "explain further",
                         "can you explain more", "Can you explain?", "why though", "but why",
                         "what do you mean by that"):
            self.assertEqual(quick_intent(question, topics), ("more", None), question)
        self.assertEqual(quick_intent("explain the gank plan", topics), ("more", 1))
        self.assertEqual(quick_intent("explain the invade plan", topics), ("more", 1))
        self.assertEqual(quick_intent("why the crab one", topics), ("more", 0))
        self.assertIsNone(quick_intent("tell me more about dragon", topics))
        self.assertIsNone(quick_intent("explain the baron plan", topics))

    def test_questions_that_only_contain_the_words_are_left_alone(self):
        for question in ("stop their jungler", "how do I stop the dive", "stop the plan", "cancel the plan",
                         "is that enough", "why is their top ahead", "more ganks", "one more camp", "what else",
                         "other options", "top", "no plan", ""):
            self.assertIsNone(quick_intent(question), question)
        # The plan words are untouched: these still mean what they meant.
        self.assertEqual(plan_intent("cancel the plan", OFFER, ON_MENU, None), ("drop", None))
        self.assertEqual(plan_intent("what else", OFFER, ON_MENU, None), ("menu", "fresh"))
        self.assertEqual(plan_intent("other options", OFFER, ON_MENU, None), ("menu", "fresh"))

    def test_focus_names_one_remembered_alternative(self):
        topics = (("six on crab", "crab", "farm"), ("gank", "ganks", "gank set up lanes"))
        self.assertEqual(quick_intent("why the second one"), ("more", 1))
        self.assertEqual(quick_intent("explain the first one", topics), ("more", 0))
        self.assertEqual(quick_intent("why gank", topics), ("more", 1))
        self.assertEqual(quick_intent("tell me more about the crab", topics), ("more", 0))
        self.assertIsNone(quick_intent("why gank"))
        self.assertIsNone(quick_intent("why gank", (("gank",), ("gank",))))
        self.assertIsNone(quick_intent("why baron", topics))

    def test_noise_is_only_padding_or_a_silence_phrase(self):
        for heard in ("Thank you.", "thanks", "you", "Bye.", "ok", "Thanks for watching!", ""):
            self.assertTrue(is_noise(heard), heard)
        for heard in ("stop", "what now", "more", "thank you for the gank"):
            self.assertFalse(is_noise(heard), heard)


def champion_game(champion, time, level, me="JUNGLE"):
    """team_game with the active player on another champion."""
    match = team_game(time, level, level, me=me)
    next(player for player in match["allPlayers"] if player["riotId"] == "Ally")["championName"] = champion
    return match


class FlaggedCase(unittest.TestCase):
    """coach() with the bot's two opt-in flags; the feed and the ranker are mocked."""

    def setUp(self):
        lane_playbook.plays()
        self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
        self.sent = []

    def _root(self, **files):
        """A playbook folder with the shipped lessons and no champion notes, unless given."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for name in ("lessons.md", "pro_lessons.md"):
            (root / name).write_bytes((SHIPPED_ROOT / name).read_bytes())
        for name, text in files.items():
            (root / f"{name}.md").write_text(text, encoding="utf-8")
        patcher = patch.object(lane_playbook, "PLAYBOOK_ROOT", root)
        patcher.start()
        self.addCleanup(patcher.stop)
        return root

    def _ask(self, question, match, *, fail=False, board="own", **flags):
        def rank(state, key, options):
            if fail:
                raise OSError("offline")
            self.sent.append(state)
            return {option.key: 1 / (index + 1) for index, option in enumerate(options)}
        with patch("coach.read_live_game", return_value=match), \
             patch("coach.load_jev_key", return_value="secret"), \
             patch("coach.jev_rank", side_effect=rank):
            return coach(question, "balanced", coordinator_board=self.board if board == "own" else board, **flags)


class ReasonPartTests(unittest.TestCase):
    def _options(self):
        for champion in ("Bel'Veth", "Lee Sin", "Ashe"):
            for level, time, enemy_level in STAGES.values():
                state = summarize_game(jungle_game(champion, level, time, enemy_level))
                yield from _jungle_options(state, time, "CHAOS", jungle_clock(state), recover=True)
        state = summarize_game(team_game(270, 4, 5, enemy_dead=True, respawn=30,
                                         edges={"top": (2, 30), "bot": (-1, -20)}))
        yield from _jungle_options(state, 270, "CHAOS", jungle_clock(state), recover=True)
        for role in ROLES:
            for time in (400, 1000):
                yield from _role_options(summarize_game(team_game(time, 5, 5)), role, time, "CHAOS")

    def test_every_sentence_lands_in_exactly_one_part(self):
        seen = 0
        for option in self._options():
            parts = _reason_parts(option.reason)
            self.assertEqual(set(parts), {"seen", "why", "check", "breaks"})
            placed = [sentence for part in parts.values() for sentence in part]
            self.assertEqual(sorted(placed), sorted(_sentences(option.reason)), option.key)
            self.assertEqual(len(placed), len(set(placed)), option.key)
            self.assertEqual(" ".join(_sentences(option.reason)), option.reason, option.key)
            seen += 1
        self.assertGreater(seen, 60)

    def test_the_plan_note_and_the_pace_note_are_reasons_not_checks(self):
        state = summarize_game(team_game(270, 4, 5))
        clear = _jungle_options(state, 270, "CHAOS", jungle_clock(state))[0]
        parts = _reason_parts(clear.reason)
        self.assertEqual(parts["seen"], ["You are level 4 at 4:30; Viego is level 5."])
        self.assertIn("You are behind their jungler on level or CS, so take camps before any river fight.",
                      parts["why"])
        self.assertTrue(parts["why"][-1].startswith("On Bel'Veth the same clears serve your longer plan"))
        self.assertEqual(parts["check"], ["You check: which camps are up and where the crab is; the coach cannot "
                                          "see either."])
        ahead = summarize_game(team_game(270, 4, 4, cs=60, enemy_cs=20))
        pace = _reason_parts(_jungle_options(ahead, 270, "CHAOS", jungle_clock(ahead))[0].reason)
        self.assertTrue(any(sentence.startswith("You are ahead of their jungler") for sentence in pace["why"]))

    def test_a_lesson_keeps_its_own_markers(self):
        state = summarize_game(jungle_game("Bel'Veth", 5, 340, 5))
        race = _jungle_options(state, 340, "CHAOS", jungle_clock(state))[0]
        parts = _reason_parts(race.reason)
        self.assertTrue(parts["why"][0].startswith("By your own benchmark:"))
        self.assertTrue(parts["check"][0].startswith("You check:"))
        self.assertTrue(parts["breaks"][0].startswith("Breaks it:"))
        self.assertTrue(parts["why"][-1].startswith("On Bel'Veth the same clears serve"))

    def test_a_title_in_a_champion_name_does_not_split_the_sentence(self):
        state = summarize_game(jungle_game("Bel'Veth", 4, 270, 4, enemy="Dr. Mundo"))
        clear = _jungle_options(state, 270, "CHAOS", jungle_clock(state))[0]
        self.assertEqual(_reason_parts(clear.reason)["seen"], ["You are level 4 at 4:30; Dr. Mundo is level 4."])
        self.assertEqual(_sentences("Dr. Mundo is level 4. He is big."), ["Dr. Mundo is level 4.", "He is big."])

    def test_aloud_drops_brackets_and_reads_symbols(self):
        self.assertEqual(_aloud("Your top lane (Garen) is +1 levels and -6 CS; path there."),
                         "Your top lane is plus 1 levels and minus 6 CS. Path there.")
        self.assertEqual(_aloud("The crabs spawn at 2:55 on patch 26.1 timings."),
                         "The crabs spawn at 2:55 on this patch's timings.")
        self.assertEqual(_aloud("Gank a **set-up** lane at 5:25."), "Gank a set-up lane at 5:25.")


class ExplainTests(FlaggedCase):
    """ "Explain more" elaborates on the two alternatives already given; it never becomes one play."""
    FIRST = "Full clear again; level 6 is the payoff"
    SECOND = "Gank only a set-up lane next to your next camp"

    def setUp(self):
        super().setUp()
        self._root()   # the shipped lessons, and no notes of the player's own unless a test adds one

    def _topic(self, match=None, question="what next", **flags):
        return self._ask(question, match or team_game(208, 4, 4), **flags).topic

    def _layers(self, topic, **options):
        found = []
        for _ in range(6):
            found.append(explain(replace(topic, layer=found[-1].layer if found else topic.layer), **options))
            if found[-1].layer == 4:
                break
        return found

    def test_the_topic_remembers_the_pair_as_offered(self):
        topic = self._topic()
        self.assertEqual([option.label for option in topic.pair], [self.FIRST, self.SECOND])
        self.assertEqual(topic.names, ("six on crab", "gank set-up lanes"))
        self.assertEqual((topic.game_second, topic.source, topic.match_key, topic.layer),
                         (208, "live game", self.board.match_key, 0))
        self.assertIn("crab", topic.words[0])
        self.assertIn("gank", topic.words[1])
        self.assertEqual(topic.background["profile"]["title"], "Bel'Veth farms to 80 stacks")
        # No pro principle shares an observed tag with this quiet read, so none is attached.
        self.assertEqual(lane_playbook.pro_matches("jungle", "early", set())[0]["title"],
                         "Gank when your camps are down")
        self.assertIsNone(topic.background["principle"])
        self.assertEqual((topic.lessons, topic.more, topic.background["note"]), ((None, None), (), ""))
        self.assertEqual(topic.serial, self.board.match_serial)

    def test_spoken_names_are_whole_phrases(self):
        cases = (("grubs or dragon", team_game(600, 8, 8, me="TOP"), ("take Grubs", "take dragon")),
                 ("should we fight or take dragon", team_game(1000, 10, 10, me="TOP"),
                  ("split top", "play for Herald")))
        for question, match, names in cases:
            self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
            topic = self._topic(match, question)
            self.assertEqual(topic.names, names)
            for reply in self._layers(topic):
                self.assertIn(f"{names[0]} or {names[1]}".casefold(), reply.spoken.casefold().replace(",", ""))
        # No name ends on a joining word left over from a cut label.
        for name in EXPLAIN_NAMES.values():
            self.assertNotIn(name.split()[-1], ("and", "an", "on", "into", "through", "four", "the"), name)
            self.assertLessEqual(len(name.split()), 5, name)

    def test_the_champion_plan_lesson_is_background_only_for_its_role_and_before_its_until(self):
        self.assertEqual(self._topic().background["profile"]["title"], "Bel'Veth farms to 80 stacks")
        self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
        late = self._topic(team_game(1570, 12, 12), "what should I do now")   # 26:10, past Until: 25:00
        self.assertIsNone(late.background["profile"])
        self.assertEqual([reply.layer for reply in self._layers(late)][-2:], [1, 4])
        self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
        mid = self._topic(champion_game("Diana", 400, 5, me="MIDDLE"))        # on the farm-first jungler list
        self.assertIsNone(mid.background["profile"])
        for reply in self._layers(mid):
            self.assertNotIn("Farm-first junglers", reply + reply.spoken)

    def test_layers_come_in_order_and_each_keeps_both_alternatives(self):
        topic = self._topic()
        before = deepcopy(topic)
        layers = self._layers(topic)
        self.assertEqual([reply.layer for reply in layers], [1, 2, 3, 4])
        self.assertEqual(topic, before)   # explain never changes the topic; the bot does, on delivery
        titles = ("why these two", "what to check and what breaks them", "background, not a read of this game",
                  "nothing more on these two")
        for reply, title in zip(layers, titles):
            self.assertTrue(reply.startswith(f"Game read, continued (live game, as of 3:28): {title}.\n"), reply)
            self.assertTrue(reply.endswith("\nYour call."))
            self.assertIn(f"**{self.FIRST}**", reply)
            self.assertIn(f"\nOtherwise: **{self.SECOND}**", reply)
            self.assertLessEqual(len(reply), CHAT_LIMIT)
            self.assertLessEqual(len(reply.spoken.split()), 80, reply.spoken)
            self.assertTrue(reply.spoken.endswith("Your call."))
            opening = re.split(r"(?<=[.!?])\s+", reply.spoken)[0]
            self.assertIn("six on crab", opening.casefold())
            self.assertIn("gank set-up lanes", opening)
            self.assertIsNone(reply.topic)
            self.assertIsNone(reply.commit)
        self.assertEqual(explain(replace(topic, layer=4)).layer, 4)
        self.assertEqual(explain(replace(topic, layer=4)), layers[3])

    def test_the_first_two_layers_say_what_the_reply_already_gave(self):
        why, check = self._layers(self._topic())[:2]
        self.assertEqual(why.spoken,
                         "From the 3:28 read: Six on crab, or gank set-up lanes. Six on crab. Each skipped camp "
                         "pushes level 6 back. "
                         "On Bel'Veth the same clears serve your longer plan: Keep full clearing toward 40, then 80 "
                         "Lavender stacks. Gank set-up lanes. On Bel'Veth a gank is a detour from the farm plan. A "
                         "gank pays off now but costs camps. Your call.")
        self.assertIn("You are level 4 at 3:28; Viego is level 4. Each skipped camp pushes level 6 back. Once both "
                      "first crabs are dead", why)
        self.assertNotIn("You check", why)
        self.assertEqual(check.spoken,
                         "From the 3:28 read: Before you pick six on crab or gank set-up lanes. Six on crab. You "
                         "check: which camps are up and where the crab is. The coach cannot see either. Gank set-up "
                         "lanes. You check: the "
                         "wave and where their jungler was last seen. If that was the same side, it can be a trap. "
                         "If it is not there, keep clearing. Your call.")
        self.assertNotIn("Each skipped camp", check)

    def test_every_spoken_sentence_comes_from_the_reason_the_lesson_or_a_template(self):
        for match in (team_game(208, 4, 4), team_game(340, 5, 5), team_game(600, 8, 8), team_game(270, 4, 5)):
            topic = self._topic(match)
            first, second = topic.names
            allowed = {_aloud(sentence) for option in topic.pair for sentence in _sentences(option.reason)}
            for lesson in topic.lessons:
                for marker, field in (("By your own benchmark:", "timeline"), ("You check:", "player_check"),
                                      ("Breaks it:", "breaks")):
                    allowed |= {_aloud(sentence) for sentence in _sentences(f"{marker} {(lesson or {}).get(field)}")}
            templates = [f"From the {topic.game_second // 60}:{topic.game_second % 60:02d} read:",
                         f"{first[:1].upper()}{first[1:]}, or {second}.", f"Before you pick {first} or {second}.",
                         f"{first[:1].upper()}{first[1:]}.", f"{second[:1].upper()}{second[1:]}.", "Your call.",
                         "Nothing more on the feed for that one.", "The detail on that one is in chat."]
            for reply in self._layers(topic)[:2]:
                left = reply.spoken
                for known in sorted([*allowed, *templates], key=len, reverse=True):
                    left = left.replace(known, "")
                self.assertEqual(left.strip(), "", reply.spoken)

    def test_focus_puts_the_named_alternative_first_and_keeps_the_other(self):
        topic = self._topic()
        for reply in self._layers(topic, focus=1):
            self.assertLess(reply.index(self.SECOND), reply.index(self.FIRST))
            self.assertIn(f"\nOtherwise: **{self.FIRST}**", reply)
            self.assertIn("six on crab", reply.spoken)
        self.assertTrue(explain(topic, 1).spoken.startswith(
            "From the 3:28 read: Gank set-up lanes, or six on crab. Gank set-up lanes. "))
        self.assertEqual(explain(topic, 0), explain(topic))

    def test_what_the_feed_showed_is_always_spoken_as_the_read_it_came_from(self):
        # The reasons are in the present tense; a respawn timer is out of date within seconds.
        match = team_game(270, 4, 4, enemy_dead=True, respawn=30)
        topic, state = self._topic(match), summarize_game(match)
        steal = next(option for option in _jungle_options(state, 270, "CHAOS", jungle_clock(state))
                     if option.key == "jungle_steal")
        dead = replace(topic, pair=(steal, topic.pair[0]), names=("steal a camp", topic.names[0]))
        told =[reply for reply in self._layers(dead) if "is dead with about 30 seconds" in reply.spoken]
        self.assertTrue(told)
        for reply in self._layers(dead):
            self.assertIn("as of 4:30", reply)
            self.assertLessEqual(len(reply.spoken.split()), 80)
            if reply.layer in (1, 2):   # the layers that speak sentences from the read
                self.assertTrue(reply.spoken.startswith("From the 4:30 read: "), reply.spoken)
        for reply in told:
            self.assertIn(reply.layer, (1, 2))

    def test_a_lesson_part_is_never_spoken_without_its_marker(self):
        topic = self._topic(team_game(340, 5, 5))   # the six race, worded by the shipped "Scuttle for six" lesson
        self.assertEqual(topic.lessons[0]["title"], "Scuttle for six")
        why = explain(topic)
        self.assertIn("By your own benchmark: Full clear all six camps", why)
        self.assertIn("Be level 5 and about a camp short of 6", why)
        # The marker sentence is over the budget, so the benchmark's second sentence is not said on its own.
        self.assertNotIn("Be level 5", why.spoken)
        self.assertNotIn("benchmark", why.spoken)
        self.assertIn("Six on crab. On Bel'Veth the same clears serve your longer plan: Keep full clearing toward "
                      "40, then 80 Lavender stacks. The detail on that one is in chat. Gank set-up lanes.", why.spoken)
        for reply in self._layers(topic)[:2]:
            for sentence in re.split(r"(?<=[.!?])\s+", reply.spoken):
                if sentence in ("A skipped camp, a slow clear, a death, a gank on you mid-clear, or an early invade "
                                "of your camps, for example by their mid laner.", "Then give the crab and take a camp."):
                    self.fail(f"a 'Breaks it' sentence was spoken without its marker: {sentence}")

    def test_a_layer_with_nothing_in_it_is_skipped_and_one_empty_side_is_still_named(self):
        plain = Topic(None, 600, "live game",
                      (Option("a", "Alpha", "Push the wave."), Option("b", "Beta", "Reset now.")),
                      (), ("alpha", "beta"), ((), ()), (None, None), {})
        self.assertEqual([reply.layer for reply in self._layers(plain)], [1, 4])
        done = explain(replace(plain, layer=1))
        self.assertEqual(done, "Game read, continued (live game, as of 10:00): nothing more on these two.\n"
                               "**Alpha**\nOtherwise: **Beta**\nYour call.")
        self.assertEqual(done.spoken, "That's everything on alpha or beta. Your call.")
        lopsided = replace(plain, pair=(plain.pair[0], Option("b", "Beta", "You check: the wave.")), more=("Gamma",))
        why = explain(lopsided)
        self.assertIn("Otherwise: **Beta** — nothing more on the feed for this one.", why)
        self.assertIn("\nAlso offered: Gamma.\nYour call.", why)
        self.assertEqual(why.spoken, "From the 10:00 read: Alpha, or beta. Alpha. Push the wave. Beta. Nothing more on "
                                     "the feed for that one. Your call.")
        self.assertEqual(explain(replace(lopsided, layer=1)).layer, 2)

    def test_background_is_the_players_own_and_a_pro_tendency_framed_as_neither(self):
        topic = self._topic(team_game(270, 4, 5))   # a level behind: one shipped principle shares that tag
        principle = topic.background["principle"]
        self.assertEqual((principle["title"], principle["shared"]),
                         ("A jungler who is behind has few places to go", ("behind",)))
        background = self._layers(topic)[2]
        self.assertIn('Your lesson "Bel\'Veth farms to 80 stacks". Source, in your words: 40 and 80 are patch 26.15',
                      background)
        # The lesson's "Feed check" is quoted as the lesson's condition, never as a fact about this read.
        self.assertNotIn("Feed check", background)
        self.assertIn("Its condition, as your lesson states it (not checked against this read): You are on Bel'Veth "
                      "and it is before 25:00.", background)
        self.assertIn(f"Otherwise: **{self.SECOND}** — no lesson of yours behind this one.", background)
        self.assertIn("\nPro tendency (background from pro games, not this match): A jungler who is behind has few "
                      "places to go. If this holds (not observed here): ", background)
        self.assertIn(f"Our side: {principle['our']}", background)
        self.assertIn(f"Their side: {principle['their']}", background)
        fit = "At 4:30 the feed showed: you were behind your role opponent on level or CS."
        self.assertIn(fit, background)
        spoken = background.spoken
        # Aloud the tendency's title is followed at once by how it sits against the read.
        self.assertTrue(spoken.startswith("Background on six on crab or gank set-up lanes, not a read of this game. "
                                          "Your lesson Bel'Veth farms to 80 stacks is from your own lessons file, "
                                          "not something I measured. A pro tendency, as background only: A jungler "
                                          f"who is behind has few places to go. {fit} "), spoken)
        self.assertTrue(spoken.endswith(" Still six on crab or gank set-up lanes. Your call."), spoken)
        for chat_only in (principle["our"], principle["their"], principle["situation"], "40 and 80 are patch",
                          "it is before 25:00"):
            self.assertNotIn(chat_only, spoken)
        with patch("coach.EXPLAIN_PRO", False):
            quiet = self._layers(topic)[2]
        self.assertEqual(quiet.layer, 3)
        self.assertNotIn("Pro tendency", quiet)
        self.assertNotIn("pro tendency", quiet.spoken)
        self.assertNotIn("A jungler who is behind", quiet + quiet.spoken)

    def test_a_tendency_is_spoken_with_its_fit_or_not_at_all(self):
        topic = self._topic(team_game(270, 4, 5))
        wordy = replace(topic, background={**topic.background, "principle": {
            **topic.background["principle"], "title": "A very long title " * 12}})
        spoken = next(reply for reply in self._layers(wordy) if reply.layer == 3).spoken
        self.assertNotIn("A very long title", spoken)
        self.assertIn(" A pro tendency is in chat. Still six on crab or gank set-up lanes. Your call.", spoken)
        self.assertLessEqual(len(spoken.split()), 80)

    def test_only_a_lesson_behind_one_of_the_two_is_named_aloud(self):
        race = self._topic(team_game(340, 5, 5))   # the crab lesson words the first option; the profile neither
        spoken = next(reply for reply in self._layers(race) if reply.layer == 3).spoken
        self.assertIn("Your lesson Scuttle for six is from your own lessons file, not something I measured.", spoken)
        self.assertNotIn("80 stacks", spoken)
        self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
        listed = self._topic(champion_game("Master Yi", 270, 4))
        background = next(reply for reply in self._layers(listed) if reply.layer == 3)
        self.assertIn('Your lesson "Farm-first junglers". Source, in your words: community consensus', background)
        self.assertNotIn("benchmark", background.spoken)

    def test_an_objective_timer_is_not_called_a_feed_reading(self):
        self.assertEqual(coach_module._fit_sentence({"shared": ("behind", "objective_soon")}, "6:40"),
                         "At 6:40 the feed showed: you were behind your role opponent on level or CS. At 6:40, by "
                         "patch timers an objective spawn was within two minutes.")
        self.assertEqual(coach_module._fit_sentence({"shared": ("objective_soon",)}, "6:40"),
                         "At 6:40, by patch timers an objective spawn was within two minutes.")
        self.assertEqual(coach_module._fit_sentence({"shared": ()}, "6:40"),
                         "Nothing on the feed confirms it or rules it out.")

    def test_the_fit_sentence_uses_only_observed_tags(self):
        self._root(pro_lessons="## Camps before river\nRoles: jungle\nPhase: any\nWhen: behind, tower_down\n"
                               "Situation: Their jungler is up a level.\nOur side: Gains camps.\n"
                               "Their side: Gets river.\nSeen in: 4 games\n")
        topic = self._topic(team_game(270, 4, 5))
        self.assertEqual(topic.background["principle"]["shared"], ("behind",))
        background = next(reply for reply in self._layers(topic) if reply.layer == 3)
        fit = "At 4:30 the feed showed: you were behind your role opponent on level or CS."
        self.assertIn(fit, background)
        self.assertIn(fit, background.spoken)
        self.assertNotIn("tower", background.spoken)
        self.assertTrue(set(lane_playbook.PRO_TAGS) <= set(TAG_WORDS))

    def test_the_players_note_is_part_of_the_background(self):
        self._root(champion_notes="## Bel'Veth\nRole: jungle\nNote: I full clear until six, then look for dives\n"
                                  "Added: 2026-10-06\n")
        topic = self._topic()
        self.assertEqual(topic.background["note"], "I full clear until six, then look for dives")
        background = self._layers(topic)[2]
        self.assertIn("\nYour own note on Bel'Veth: I full clear until six, then look for dives.\n", background)
        self.assertIn("Your own note on Bel'Veth: I full clear until six, then look for dives.", background.spoken)
        self.assertLessEqual(len(background.spoken.split()), 80)

    def test_no_kit_text_reaches_a_reply_or_an_explanation(self):
        reply = self._ask("what next", team_game(208, 4, 4))
        self.assertIn("Void Surge", self.sent[-1]["champion_kits"]["you"]["kit"])
        texts = [reply, reply.spoken]
        for layer in self._layers(reply.topic):
            texts += [layer, layer.spoken]
        checked = 0
        for champion in ("Bel'Veth", "Viego"):
            kit = champion_metadata.champion_kit(champion)
            for ability in (kit["passive"], *kit["spells"].values()):
                for part in filter(None, (ability["name"], ability["text"])):
                    checked += 1
                    for text in texts:
                        self.assertNotIn(part, text)
        self.assertEqual(checked, 20)

    def test_long_reasons_still_fit_one_message_and_eighty_words(self):
        wordy = Option("a", "Alpha", "By your own benchmark: " + "Clear the camps in order. " * 120)
        topic = Topic(None, 60, "live game", (wordy, wordy), (), ("alpha plan", "beta plan"), ((), ()),
                      (None, None), {})
        for reply in self._layers(topic):
            self.assertLessEqual(len(reply), CHAT_LIMIT)
            self.assertLessEqual(len(reply.spoken.split()), 80)


class DeferredBoardTests(FlaggedCase):
    def test_defaults_write_the_board_at_once(self):
        reply = self._ask("Let's play for six on crab.", team_game(125, 2, 2))
        self.assertIsNone(reply.commit)
        self.assertEqual(reply.layer, 0)
        self.assertEqual(self.board.plan["id"], "six_crab")
        self.assertEqual(self.board.offer[0], ("jungle_first_clear", "six_crab"))
        self.assertIsInstance(reply.topic, Topic)

    def test_a_deferred_reply_writes_nothing_until_it_is_committed(self):
        reply = self._ask("Let's play for six on crab.", team_game(125, 2, 2), defer_board=True)
        self.assertTrue(reply.spoken.startswith("Six on crab, locked. "), reply.spoken)
        self.assertEqual(self.board.plan_state(), (None, (), 0))
        reply.commit()
        plan, offer, offer_at = self.board.plan_state()
        self.assertEqual((plan["id"], offer[0], offer_at), ("six_crab", ("jungle_first_clear", "six_crab"), 125))

    def test_a_commit_after_the_match_changed_does_nothing(self):
        reply = self._ask("Let's play for six on crab.", team_game(125, 2, 2), defer_board=True)
        rematch = team_game(130, 2, 2)
        rematch["allPlayers"][0]["riotId"] = "Someone else"   # another roster: a different match
        self.board.observe(summarize_game(rematch))
        self.assertNotEqual(self.board.match_key, reply.topic.match_key)
        reply.commit()
        self.assertEqual(self.board.plan_state(), (None, (), 0))

    def test_the_topic_is_attached_with_and_without_a_board(self):
        plain = self._ask("What next?", game(), board=None)
        self.assertIsNone(plain.commit)
        self.assertIsNone(plain.topic.match_key)
        self.assertEqual(plain.topic.names, tuple(option.label for option in plain.topic.pair))
        self.assertIsNone(plain.topic.background["principle"])
        self.assertEqual(explain(plain.topic).layer, 1)
        live = self._ask("What next?", team_game(208, 4, 4), defer_board=True)
        self.assertEqual(live.topic.match_key, self.board.match_key)
        self.assertEqual(live.topic.pair[0].key, "jungle_full_clear")


class ChampionAskTests(FlaggedCase):
    """Once a match, a champion with nothing on file gets one question; the answer is the player's own."""
    ON = dict(champion_ask=True)
    SENTENCE = "I play Zac for ganks from level four, I don't full clear."

    def setUp(self):
        super().setUp()
        self.root = self._root()

    def _notes(self):
        path = self.root / "champion_notes.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def test_the_ask_is_made_once_a_match(self):
        first = self._ask("what's my first clear", champion_game("Zac", 65, 1), **self.ON)
        self.assertEqual(first.spoken, "No Zac notes; what's your plan. Finish your camps, then crab if it's free; "
                                       "every camp counts for six. Or, gank set-up lanes.")
        self.assertTrue(first.splitlines()[0].endswith(
            "; no notes on Zac: say one sentence on how you play it, or use /note."), first)
        self.assertIn(" Or, ", first.spoken)
        self.assertLessEqual(len(first.spoken.split()), 24)
        self.assertIn("\nOtherwise: **", first)
        self.assertEqual(self.board.champion_asked(), 65)
        again = self._ask("what's my first clear", champion_game("Zac", 75, 1), **self.ON)
        self.assertNotIn("notes", again + again.spoken)
        self.board.observe(summarize_game(champion_game("Zac", 12, 1)))   # the clock restarted: a new match
        self.assertIsNone(self.board.champion_asked())
        self.assertIn("No Zac notes", self._ask("what now", champion_game("Zac", 65, 1), **self.ON).spoken)

    def test_a_long_champion_name_still_fits_the_spoken_line(self):
        for champion in ("Nunu & Willump", "Aurelion Sol", "Zac"):
            self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
            reply = self._ask("where should I path", champion_game(champion, 200, 3), **self.ON)
            if champion != "Nunu & Willump":   # Nunu is on the shipped gank-first list
                self.assertIn(f"no notes on {champion}", reply)
                self.assertTrue(reply.spoken.startswith("No "), reply.spoken)
            self.assertIn(" Or, ", reply.spoken)
            self.assertLessEqual(len(reply.spoken.split()), 24, reply.spoken)

    def test_the_ask_is_not_used_up_by_a_ranker_failure_or_an_undelivered_reply(self):
        self._ask("what now", champion_game("Zac", 65, 1), fail=True, **self.ON)
        self.assertIsNone(self.board.champion_asked())
        held = self._ask("what now", champion_game("Zac", 70, 1), defer_board=True, **self.ON)
        self.assertIn("No Zac notes", held.spoken)
        self.assertIsNone(self.board.champion_asked())
        again = self._ask("what now", champion_game("Zac", 75, 1), defer_board=True, **self.ON)
        self.assertIn("No Zac notes", again.spoken)
        again.commit()
        self.assertEqual(self.board.champion_asked(), 75)

    def test_the_ask_is_left_out_when_something_is_known_or_the_turn_is_about_a_plan(self):
        def asked(question, match, **flags):
            self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
            reply = self._ask(question, match, **{**self.ON, **flags})
            return "notes" in reply.casefold() or "notes" in reply.spoken.casefold()
        self.assertTrue(asked("what now", champion_game("Zac", 65, 1)))
        self.assertTrue(asked("what now", champion_game("Zac", 400, 5, me="TOP")))
        for champion in ("Bel'Veth", "Master Yi", "Lee Sin"):
            self.assertFalse(asked("what now", champion_game(champion, 65, 1)), champion)
        self.assertFalse(asked("what now", champion_game("Zac", 900, 10)))            # after 15:00
        self.assertFalse(asked("I'll farm", champion_game("Zac", 65, 1)))             # a commit turn
        self.assertFalse(asked("What are my options?", champion_game("Zac", 65, 1)))  # a menu turn
        self.assertFalse(asked("what now", champion_game("Zac", 65, 1), champion_ask=False))
        self.assertFalse(asked("what now", champion_game("Zac", 65, 1), board=None))
        self.board = CoordinatorBoard({role: "guidance" for role in ROLES})
        self._ask("I'll farm", champion_game("Zac", 65, 1))                           # a stored plan
        self.assertNotIn("notes", self._ask("what now", champion_game("Zac", 70, 1), **self.ON).casefold())
        (self.root / "champion_notes.md").write_text("## zac\nNote: ganks first\n", encoding="utf-8")
        self.assertFalse(asked("what now", champion_game("Zac", 65, 1)))              # a stored note
        self.assertTrue(plan_knowledge("jungle", "Zac"))

    def test_plan_knowledge_reads_lessons_notes_and_archetype_lines(self):
        self.assertTrue(plan_knowledge("jungle", "Bel'Veth"))
        self.assertTrue(plan_knowledge("jungle", "Kindred"))
        self.assertFalse(plan_knowledge("jungle", "Zac"))      # the role-wide crab lesson does not count
        self.assertFalse(plan_knowledge("top", "Garen"))
        self._root(pro_lessons="## Tanks start fights\nRoles: jungle\nArchetypes: tank, Mage\n"
                               "Situation: A fight is near.\nOur side: Engage.\nTheir side: Kite.\n"
                               "Seen in: 3 games\n")
        self.assertTrue(plan_knowledge("jungle", "Zac"))
        self.assertFalse(plan_knowledge("top", "Zac"))
        self.assertFalse(plan_knowledge("jungle", "Viego"))

    def test_note_intent_takes_a_statement_and_never_a_question_or_a_command(self):
        self.assertEqual(note_intent("Coach, note that I play Zac for early ganks", "Zac", False, "ask"),
                         "I play Zac for early ganks")
        self.assertEqual(note_intent("remember: I full clear, then gank bot", "Zac", False, "ask"),
                         "I full clear, then gank bot")
        self.assertEqual(note_intent("for the record, Zac wants fights at six", "Zac", False, "ask"),
                         "Zac wants fights at six")
        self.assertIsNone(note_intent("note that", "Zac", False, "ask"))
        # About this match, not about how the champion is played: nothing in the first person, no champion.
        for question in ("Remember that their jungler is bot side", "note the enemy jungler is top side",
                         "Remember when I died top lane", "Remember to ping me dragon",
                         "for the record this team is bad", "remember: full clear, then gank bot"):
            self.assertIsNone(note_intent(question, "Zac", False, "ask"), question)
            self.assertIsNone(note_intent(question, "Zac", True, "ask"), question)
        # A bare pick in the pending window commits the plan and is not kept as the standing note.
        for question in ("full clear", "let's gank", "going with ganks"):
            self.assertIsNone(note_intent(question, "Zac", True, "commit"), question)
        self.assertEqual(note_intent(self.SENTENCE, "Zac", True, "ask"), self.SENTENCE)
        self.assertIsNone(note_intent(self.SENTENCE, "Zac", False, "ask"))
        self.assertEqual(note_intent("I'll farm", "Zac", True, "commit"), "I'll farm")
        self.assertEqual(note_intent("Zac wants fights at six", "Zac", True, "ask"), "Zac wants fights at six")
        for question, intent in (("the first one", "commit"), ("I'll take the first one", "commit"),
                                 ("should I play it for ganks?", "ask"), ("do I play it for ganks", "ask"),
                                 ("I play it for ganks, is that right?", "ask"), ("stop", "ask"),
                                 ("keep going", "ask"), ("this isn't working, I play it badly", "recover"),
                                 ("I want to drop the plan", "drop"), ("I play", "status"), ("ganks", "ask"),
                                 ("a kill top just now", "ask")):
            self.assertIsNone(note_intent(question, "Zac", True, intent), question)

    def test_the_answer_to_the_ask_is_kept_once_delivered(self):
        self._ask("what's my first clear", champion_game("Zac", 65, 1), **self.ON)
        reply = self._ask(self.SENTENCE, champion_game("Zac", 80, 1), defer_board=True, **self.ON)
        self.assertEqual(reply.spoken, "Noted for Zac. Finish your camps, then crab if it's free; every camp counts "
                                       "for six. Or, gank a set-up lane by your clear.")
        self.assertTrue(reply.splitlines()[0].endswith(
            f'; your note for Zac saved: "{self.SENTENCE}" (edit lane_playbook\\champion_notes.md).'), reply)
        self.assertEqual(self._notes(), "")          # nothing is written before delivery
        reply.commit()
        self.assertTrue(self._notes().startswith("# Champion notes: my own words"))
        self.assertTrue(self._notes().endswith(
            f"\n## Zac\nRole: jungle\nNote: {self.SENTENCE}\nAdded: {date.today().isoformat()}\n"))
        self.assertEqual(lane_playbook.champion_notes("Zac"), [self.SENTENCE])
        later = self._ask("what now", champion_game("Zac", 90, 1), **self.ON)
        self.assertNotIn("notes", later.casefold())
        self.assertEqual(self.sent[-1]["champion_kits"]["you"]["player_note"], self.SENTENCE)
        self.assertIn(f"Your own note on Zac: {self.SENTENCE}", explain(replace(later.topic, layer=2)).spoken)

    def test_a_choice_made_in_the_answer_is_both_kept_and_committed(self):
        self._ask("what now", champion_game("Zac", 65, 1), **self.ON)
        reply = self._ask("I'll farm", champion_game("Zac", 80, 1), **self.ON)
        self.assertEqual(self.board.plan["id"], "six_crab")
        self.assertTrue(reply.spoken.startswith("Six on crab, locked. "), reply.spoken)
        self.assertIn('plan set at 1:20: six on crab; your note for Zac saved: "I\'ll farm"', reply)
        self.assertEqual(lane_playbook.champion_notes("Zac"), ["I'll farm"])

    def test_nothing_is_kept_outside_the_window_or_without_the_flag(self):
        self._ask("what now", champion_game("Zac", 65, 1), **self.ON)
        late = self._ask(self.SENTENCE, champion_game("Zac", 65 + 181, 3), **self.ON)
        self.assertNotIn("saved", late)
        self.assertEqual(self._notes(), "")
        self.assertNotIn("saved", self._ask("the first one", champion_game("Zac", 250, 3), **self.ON))
        self.assertNotIn("saved", self._ask("note that I play Zac for ganks", champion_game("Zac", 255, 3)))
        self.assertEqual(self._notes(), "")
        explicit = self._ask("note that I play Zac for ganks", champion_game("Zac", 260, 3), **self.ON)
        self.assertIn('your note for Zac saved: "I play Zac for ganks"', explicit)
        self.assertTrue(explicit.spoken.startswith("Noted for Zac. "), explicit.spoken)
        self.assertIn(" Or, ", explicit.spoken)
        self.assertEqual(lane_playbook.champion_notes("Zac"), ["I play Zac for ganks"])

    def test_a_ranker_failure_keeps_the_note_and_leaves_the_board_alone(self):
        self._ask("what now", champion_game("Zac", 65, 1), **self.ON)
        before = (self.board.plan_state(), self.board.champion_asked())
        reply = self._ask("I'll farm", champion_game("Zac", 80, 1), fail=True, defer_board=True, **self.ON)
        self.assertEqual(reply, "Jev is unavailable right now. I won't guess from incomplete data; try again "
                                "shortly. I kept your note on Zac.")
        self.assertFalse(reply.startswith("Game read"))
        self.assertIsNone(reply.topic)
        self.assertEqual(self._notes(), "")
        reply.commit()
        self.assertEqual(lane_playbook.champion_notes("Zac"), ["I'll farm"])
        self.assertEqual((self.board.plan_state(), self.board.champion_asked()), before)
        at_once = self._ask("note that I gank at three", champion_game("Zac", 85, 1), fail=True, **self.ON)
        self.assertIn("I kept your note on Zac", at_once)
        self.assertIsNone(at_once.commit)
        self.assertEqual(lane_playbook.champion_notes("Zac"), ["I gank at three", "I'll farm"])
        plain = self._ask("what now", champion_game("Zac", 90, 1), fail=True, **self.ON)
        self.assertEqual(plain, "Jev is unavailable right now. I won't guess from incomplete data; try again shortly.")

    def test_a_note_file_that_cannot_be_written_never_blocks_the_answer(self):
        self._ask("what now", champion_game("Zac", 65, 1), **self.ON)
        failing = patch.object(lane_playbook, "add_champion_note", side_effect=PermissionError("read-only"))
        with failing, patch("builtins.print") as logged:
            held = self._ask(self.SENTENCE, champion_game("Zac", 80, 1), defer_board=True, **self.ON)
            self.assertEqual(held.commit(), coach_module.NOTE_NOT_SAVED)   # the line the bot posts after it
            self.assertEqual(self.board.offer[0][0], "jungle_first_clear")   # the board write still happened
            at_once = self._ask(self.SENTENCE, champion_game("Zac", 85, 1), **self.ON)
            self.assertTrue(at_once.startswith("Game read"))
            lost = self._ask(self.SENTENCE, champion_game("Zac", 90, 1), fail=True, **self.ON)
        self.assertEqual(lost, "Jev is unavailable right now. I won't guess from incomplete data; try again "
                               f"shortly. {coach_module.NOTE_NOT_SAVED}")
        self.assertIn("Champion note not saved: PermissionError", logged.call_args_list[0].args[0])
        self.assertEqual(self._notes(), "")
        kept = self._ask(self.SENTENCE, champion_game("Zac", 95, 1), defer_board=True, **self.ON)
        self.assertEqual(kept.commit(), "")
        self.assertEqual(lane_playbook.champion_notes("Zac"), [self.SENTENCE])

    def test_a_restart_with_the_same_players_is_a_new_match_for_a_held_reply(self):
        held = self._ask("Let's play for six on crab.", champion_game("Zac", 600, 8), defer_board=True)
        self.board.observe(summarize_game(champion_game("Zac", 20, 1)))   # same ten names, the clock restarted
        self.assertEqual(self.board.match_key, held.topic.match_key)
        self.assertNotEqual(self.board.match_serial, held.topic.serial)
        held.commit()
        self.assertEqual(self.board.plan_state(), (None, (), 0))


class ChampionKitPayloadTests(FlaggedCase):
    def test_a_jungler_gets_their_own_kit_and_their_opponents(self):
        self._root()
        self._ask("what next", team_game(208, 4, 4))
        kits = self.sent[-1]["champion_kits"]
        self.assertEqual(set(kits), {"you", "role_opponent"})
        self.assertEqual((kits["you"]["champion"], kits["you"]["role"]), ("Bel'Veth", "jungle"))
        self.assertTrue(kits["you"]["kit"].startswith("Bel'Veth (Fighter; no resource). Passive Death in Lavender"))
        self.assertNotIn("player_note", kits["you"])
        self.assertEqual(set(kits["role_opponent"]), {"champion", "kit"})
        self.assertEqual(kits["role_opponent"]["champion"], "Viego")

    def test_a_laner_also_gets_the_enemy_jungler_and_the_total_is_capped(self):
        root = self._root()
        self._ask("what next", team_game(300, 4, 4, me="TOP"))
        kits = self.sent[-1]["champion_kits"]
        self.assertEqual(set(kits), {"you", "role_opponent", "enemy_jungler"})
        self.assertEqual([kits[name]["champion"] for name in ("you", "role_opponent", "enemy_jungler")],
                         ["Garen", "Darius", "Viego"])
        (root / "champion_notes.md").write_text(
            "".join(f"## Garen\nNote: {'spin to win ' * 16}{n}\n" for n in range(3)), encoding="utf-8")
        note = " ".join(lane_playbook.champion_notes("Garen"))
        self.assertTrue(300 < len(note) <= 400, len(note))
        # Exactly room for the player and the role opponent: the enemy jungler goes first.
        room = len(note) + sum(len(champion_metadata.kit_summary(name)) for name in ("Garen", "Darius"))
        with patch("coach.CHAMPION_KITS_LIMIT", room):
            self._ask("what next", team_game(305, 4, 4, me="TOP"))
        kits = self.sent[-1]["champion_kits"]
        self.assertEqual(kits["you"]["player_note"], note)
        self.assertNotIn("enemy_jungler", kits)
        self.assertEqual(kits["role_opponent"]["kit"], champion_metadata.kit_summary("Darius"))
        with patch("coach.CHAMPION_KITS_LIMIT", room - 1):   # one character short: the opponent's kit is names only
            self._ask("what next", team_game(310, 4, 4, me="TOP"))
        short = self.sent[-1]["champion_kits"]["role_opponent"]["kit"]
        self.assertEqual(short, champion_metadata.kit_summary("Darius", names_only=True))
        self.assertNotIn(":", short)

    def test_the_cap_holds_for_every_champion_with_the_longest_notes(self):
        note = "x" * 400
        longest = sorted(champion_metadata._kits(), key=lambda name: -len(champion_metadata.kit_summary(name)))[:3]
        match = team_game(300, 4, 4, me="TOP")
        for player in match["allPlayers"]:
            if player["position"] == "TOP":
                player["championName"] = longest[0 if player["team"] == "ORDER" else 1]
            elif player["position"] == "JUNGLE" and player["team"] == "CHAOS":
                player["championName"] = longest[2]
        with patch.object(lane_playbook, "champion_notes", return_value=[note]):
            kits = champion_kits(summarize_game(match))
        self.assertEqual(kits["you"]["player_note"], note)
        self.assertEqual(CHAMPION_KITS_LIMIT, 1400)
        self.assertLessEqual(sum(len(entry["kit"]) + len(entry.get("player_note", "")) for entry in kits.values()),
                             CHAMPION_KITS_LIMIT)

    def test_an_unknown_champion_or_a_missing_file_sends_nothing(self):
        self._root()
        self._ask("what next", champion_game("Not A Champion", 208, 4))
        self.assertEqual(set(self.sent[-1]["champion_kits"]), {"role_opponent"})
        with patch.object(champion_metadata, "KITS_FILE", Path("missing-kits.json")):
            champion_metadata._kits.cache_clear()
            try:
                self._ask("what next", team_game(208, 4, 4))
            finally:
                champion_metadata._kits.cache_clear()
        self.assertNotIn("champion_kits", self.sent[-1])
        self._ask("What next?", game(), board=None)
        self.assertEqual(set(self.sent[-1]["champion_kits"]), {"you"})

    def test_the_ranker_is_told_what_a_kit_is(self):
        captured = {}

        class Answer:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, *args):
                return b'{"answers": {"next_play": {"probabilities": {"a": 0.7}}}}'

        def fake_open(request, timeout=None):
            captured.update(json.loads(request.data))
            return Answer()

        with patch("coach.urllib.request.urlopen", side_effect=fake_open):
            scores = jev_rank({"game": {}}, "secret", (Option("a", "A", "r"), Option("b", "B", "r")))
        self.assertEqual(scores, {"a": 0.7, "b": 0.0})
        rule = captured["questions"]["next_play"]["role_rule"]
        self.assertTrue(rule.endswith(
            "champion_kits are Riot's static kit descriptions plus, as player_note, the player's own words on how "
            "they play the champion; they say what a champion can do, never what is ready, stacked or happening "
            "now, and they are background to weigh against the observed state, not a script."), rule)


if __name__ == "__main__":
    unittest.main()
