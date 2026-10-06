import unittest

from coach import summarize_game
from coordinators import CoordinatorBoard, ROLES, load_role_reports
from test_coach import game


class CoordinatorTests(unittest.TestCase):
    def test_all_five_research_reports_load(self):
        reports = load_role_reports()
        self.assertEqual(set(reports), set(ROLES))
        self.assertTrue(all(len(report) > 1000 for report in reports.values()))

    def test_notes_follow_observed_changes_without_inventing_map_state(self):
        board = CoordinatorBoard({role: "Role guidance\n\nSix failure cases\n1. Never assume waves." for role in ROLES})
        first = game()
        first["allPlayers"][0]["position"] = "BOTTOM"
        board.observe(summarize_game(first))
        second = game(ally_dead=True)
        second["allPlayers"][0]["position"] = "BOTTOM"
        second["allPlayers"][0]["level"] = 11
        second["gameData"]["gameTime"] = 910
        board.observe(summarize_game(second))
        briefing = board.briefing()
        notes = briefing["bot"]["notes"]
        self.assertTrue(any("died" in note["text"] for note in notes))
        self.assertTrue(any("level 11" in note["text"] for note in notes))
        self.assertFalse(any("wave is pushed" in note["text"] for note in notes))
        self.assertEqual(board.briefing()["jungle"]["notes"], [])

    def test_new_match_clears_old_notes(self):
        board = CoordinatorBoard({role: "Guidance" for role in ROLES})
        first = game()
        first["allPlayers"][0]["position"] = "BOTTOM"
        board.observe(summarize_game(first))
        second = game()
        second["allPlayers"][0]["position"] = "BOTTOM"
        second["gameData"]["gameTime"] = 12
        board.observe(summarize_game(second))
        self.assertEqual(len(board.briefing()["bot"]["notes"]), 1)
        self.assertEqual(board.briefing()["bot"]["notes"][0]["game_second"], 12)

    def test_plan_memory_is_copied_out_and_cleared_with_the_match(self):
        board = CoordinatorBoard({role: "Guidance" for role in ROLES})
        first = game()
        board.observe(summarize_game(first))
        board.mark_plan(off=True)   # no plan yet: nothing happens
        self.assertEqual(board.plan_state(), (None, (), 0))
        board.choose({"id": "six_crab", "off": False})
        board.offered((("jungle_full_clear", "six_crab"), ("jungle_path", "gank")), 900)
        board.mark_plan(off=True)
        plan, offer, offer_at = board.plan_state()
        self.assertEqual((plan, offer_at), ({"id": "six_crab", "off": True}, 900))
        self.assertEqual(offer[1], ("jungle_path", "gank"))
        plan["id"] = "changed"
        self.assertEqual(board.plan["id"], "six_crab")
        later = game()
        later["gameData"]["gameTime"] = 890   # ten seconds back is jitter, not a new match
        board.observe(summarize_game(later))
        self.assertIsNotNone(board.plan)
        restarted = game()
        restarted["gameData"]["gameTime"] = 12
        board.observe(summarize_game(restarted))
        self.assertEqual((board.plan, board.offer, board.offer_at), (None, (), 0))
        board.choose({"id": "gank", "off": False})
        board.offered((("jungle_path", "gank"),), 20)
        other = game()
        other["gameData"]["gameTime"] = 30
        other["gameData"]["gameMode"] = "ARAM"   # a different match identity
        board.observe(summarize_game(other))
        self.assertEqual((board.plan, board.offer, board.offer_at), (None, (), 0))
        # A new match first seen with the clock further on: same player, side and mode, other opponents.
        board.choose({"id": "gank", "off": False})
        rematch = game()
        rematch["gameData"].update(gameTime=200, gameMode="ARAM")
        board.observe(summarize_game(rematch))
        self.assertIsNotNone(board.plan)
        rematch["allPlayers"][1]["riotId"] = "Someone else"
        board.observe(summarize_game(rematch))
        self.assertEqual((board.plan, board.offer, board.offer_at), (None, (), 0))

    def test_the_champion_ask_is_remembered_for_one_match(self):
        board = CoordinatorBoard({role: "Guidance" for role in ROLES})
        self.assertIsNone(board.champion_asked())
        board.observe(summarize_game(game()))
        board.mark_champion_asked(905.0)
        self.assertEqual(board.champion_asked(), 905)
        self.assertEqual(board.plan_state(), (None, (), 0))   # still the same three values
        later = game()
        later["gameData"]["gameTime"] = 950
        board.observe(summarize_game(later))
        self.assertEqual(board.champion_asked(), 905)
        restarted = game()
        restarted["gameData"]["gameTime"] = 12
        board.observe(summarize_game(restarted))
        self.assertIsNone(board.champion_ask_at)
        self.assertIsNone(board.champion_asked())

    def test_each_new_match_gets_its_own_serial_even_with_the_same_players(self):
        board = CoordinatorBoard({role: "Guidance" for role in ROLES})
        self.assertEqual(board.match_serial, 0)
        board.observe(summarize_game(game()))
        first_key = board.match_key
        later = game()
        later["gameData"]["gameTime"] = 950
        board.observe(summarize_game(later))
        self.assertEqual(board.match_serial, 1)            # the same match, further on
        restarted = game()
        restarted["gameData"]["gameTime"] = 12
        board.observe(summarize_game(restarted))
        self.assertEqual((board.match_serial, board.match_key), (2, first_key))

    def test_refresh_offer_moves_the_offer_time_only_when_there_is_an_offer(self):
        board = CoordinatorBoard({role: "Guidance" for role in ROLES})
        board.refresh_offer()                      # no match seen and nothing offered
        self.assertEqual(board.plan_state(), (None, (), 0))
        board.observe(summarize_game(game()))
        board.refresh_offer()                      # a match, but still nothing offered
        self.assertEqual(board.plan_state(), (None, (), 0))
        offer = (("jungle_full_clear", "six_crab"), ("jungle_path", "gank"))
        board.offered(offer, 900)
        board.choose({"id": "six_crab", "off": False})
        later = game()
        later["gameData"]["gameTime"] = 1030
        board.observe(summarize_game(later))
        board.refresh_offer()
        self.assertEqual(board.plan_state(), ({"id": "six_crab", "off": False}, offer, 1030))


if __name__ == "__main__":
    unittest.main()
