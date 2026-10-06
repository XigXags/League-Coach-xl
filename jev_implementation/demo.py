"""An offline response-validation demonstration. Never opens a network connection."""

from foundation.contracts import ContractError, PINNED_MODEL, validate_response
from foundation.policy import selected_answer_fit
from foundation.questions import QUESTION_REVISION

request = {"model": PINNED_MODEL, "state": "Give me options without guessing the enemy location.",
           "questions": {"answer": {"type": "choice", "instructions": "Which candidate answers the player's question?",
                                     "criteria": {"check_wave": "Check the wave or reset", "none": "No candidate fits"}}}}
good = {"model": PINNED_MODEL, "usage": {"input_tokens": 123, "output_tokens": 9},
        "answers": {"answer": {"type": "choice", "choice": "check_wave", "confidence": .9,
                               "probabilities": {"check_wave": .95, "none": .05}}}}
validated = validate_response(request, good)
print("OFFLINE SYNTHETIC DEMO: no API calls, no Coach writes")
print("Valid envelope retained model and usage:", validated["model"], validated["usage"])
decision = selected_answer_fit("check_wave", {"check_wave": .95}, none_id="none", policy=None,
                               model=PINNED_MODEL, revision=QUESTION_REVISION)
print("No calibrated policy ->", decision.route, ":", decision.reason)
good["answers"]["answer"]["probabilities"] = {}
try:
    validate_response(request, good)
except ContractError as exc:
    print("Malformed successful response rejected:", exc)
