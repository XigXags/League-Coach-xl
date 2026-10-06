"""One-off Jev schema check; prints only non-secret ranking scores."""

from coach import candidate_options, evidence, jev_rank, summarize_game
from credentials import load_jev_key
from test_coach import game

match = game()
match["gameData"]["gameTime"] = 600
state = summarize_game(match)
question = "Should we take Grubs or Dragon?"
options = candidate_options(state, question)
print(evidence(state))
print([option.label for option in options])
scores = jev_rank({"game": state, "team_question": question,
                   "team_style": "balanced"}, load_jev_key(), options)
print(scores)
