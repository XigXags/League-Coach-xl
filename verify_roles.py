"""Print only non-sensitive role and mode fields from the local match."""

from coach import read_live_game, summarize_game

state = summarize_game(read_live_game())
print(state["mode"], state["game_time_seconds"])
print([(player["champion"], player["role"]) for player in state["players"]])
