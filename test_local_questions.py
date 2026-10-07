import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import bot as coach_bot
from local_questions import answer_local_question, answer_tools, local_intent


def state():
    players = [
        {"name": "Me", "team": "ORDER", "champion": "Ashe", "level": 7},
        {"name": "Ally", "team": "ORDER", "champion": "Nami", "level": 6},
        {"name": "Enemy", "team": "CHAOS", "champion": "Jinx", "level": 7},
    ]
    return {
        "game_time_seconds": 372,
        "our_team": "ORDER",
        "active_player": "Me",
        "active_gold": 850,
        "active_health_percent": 64,
        "players": players,
        "teams": {
            "ORDER": {"kills": 4, "alive": 2},
            "CHAOS": {"kills": 3, "alive": 1},
        },
    }


class IntentTests(unittest.TestCase):
    def test_minimap_phrasings_are_local(self):
        for question in ("Who's on the minimap?", "Who can you see on the mini map?",
                         "Minimap, who is showing?", "Can you see the minimap?"):
            self.assertEqual(local_intent(question), "minimap")

    def test_tactical_question_falls_through(self):
        self.assertIsNone(local_intent("Who should we attack on the minimap?"))


class LocalAnswerTests(unittest.TestCase):
    def test_minimap_names_only_confident_sightings_and_marks_unclear_icons(self):
        sightings = [
            SimpleNamespace(team="ORDER", champion="Ashe", x=0.8, y=0.8, score=0.91),
            SimpleNamespace(team="CHAOS", champion="Jinx", x=0.2, y=0.2, score=0.88),
            SimpleNamespace(team="CHAOS", champion=None, x=0.5, y=0.5, score=0.4),
        ]
        answer = answer_local_question("minimap", state(), sightings, minimap_enabled=True)
        self.assertIn("ally Ashe near bottom-right", answer)
        self.assertIn("enemy Jinx near top-left", answer)
        self.assertIn("visible but unclear", answer)

    def test_empty_minimap_is_not_claimed_to_be_empty(self):
        answer = answer_local_question("minimap", state(), [], minimap_enabled=True)
        self.assertIn("don't have a fresh confident", answer)
        self.assertIn("does not mean nobody", answer)

    def test_disabled_minimap_is_explicit(self):
        self.assertIn("reading is off", answer_local_question(
            "minimap", state(), None, minimap_enabled=False))

    def test_other_local_facts(self):
        self.assertEqual(answer_local_question("champion", state()), "You're playing Ashe.")
        self.assertEqual(answer_local_question("clock", state()), "The game clock is 6:12.")
        self.assertIn("Allies: Ashe, Nami", answer_local_question("roster", state()))
        self.assertIn("Kills are 4 to 3", answer_local_question("score", state()))
        self.assertIn("850 unspent gold", answer_local_question("self", state()))

    def test_gold_difference_is_explicitly_low_confidence(self):
        sample = state()
        sample["players"][0].update(cs=80, kills=3, assists=2)
        sample["players"][1].update(cs=10, kills=0, assists=3)
        sample["players"][2].update(cs=50, kills=2, assists=1)
        answer = answer_local_question("gold", sample)
        self.assertIn("Low-confidence estimate", answer)
        self.assertIn("excludes plates", answer)

    def test_multiple_tools_are_combined(self):
        answer = answer_tools(("active_champion", "game_clock"), state())
        self.assertIn("playing Ashe", answer)
        self.assertIn("6:12", answer)


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_minimap_question_never_calls_jev_coach_path(self):
        watcher = SimpleNamespace(
            error=None,
            snapshot=Mock(return_value=[
                SimpleNamespace(team="ORDER", champion="Ashe", x=0.8, y=0.8, score=0.91)
            ]),
        )
        with patch.object(coach_bot.bot, "minimap", watcher), \
             patch.object(coach_bot.bot.coordinators, "last_state", state()), \
             patch.object(coach_bot, "coach") as jev_path:
            answer = await coach_bot.make_answer(1, "Who's on the minimap?")
        jev_path.assert_not_called()
        self.assertIn("ally Ashe", answer)


if __name__ == "__main__":
    unittest.main()
