# Coach Jev implementation staging

This folder is the reviewed handoff for the Coach Jev work. Read this file first.

The current live Coach behavior is unchanged. The only implementation currently staged is an offline foundation under `foundation/`: request/response contract validation, request fingerprints, provenance and delivery identity contracts, and pure routing policy prototypes. It has no network client, no Claude client, no Discord writes, and is not imported by `bot.py` or `coach.py`.

That boundary is deliberate. The design notes include calibrated thresholds, new question wording, an answer library, and a generative Claude path. None of those should be enabled from guesses or documentation examples. The next implementation stages must be measured against labeled Coach cases and must keep the existing two-choice safety behavior until their gates pass.

## What is ready

- `foundation/contracts.py` validates the documented `POST /v1/systemone` request and response shape. Missing probabilities are rejected rather than converted to zero. It retains the versioned model and usage envelope.
- `foundation/questions.py` contains a reviewable output-hazard battery and severity Score. Wording is marked draft and is not calibrated.
- `foundation/policy.py` models three-way routing, one rewrite maximum, selected-answer fit, mutation confirmation, and policy/model/question-revision identity matching. It intentionally has no production thresholds.
- `foundation/evidence.py` keeps observed facts, player reports, and references distinct and models match/request identity checks before delivery.
- `tests/test_foundation.py` has 31 synthetic offline tests. They check contracts and invariants; they do not claim Jev accuracy.
- `demo.py` demonstrates the validation path without opening a network connection.

## What is not ready

- No TypeSafe or Anthropic request is made by this folder.
- No threshold is calibrated. The numbers in the unit fixtures are explicitly synthetic.
- No answer-library entries are generated or merged. The owner notes keep that work paused pending sourcing and quality decisions.
- No Claude prompt or spoken-generation adapter is wired into the bot.
- No runtime `coach.py`/`bot.py` integration has been made. Existing tests are the baseline.
- No model alias, account policy, or legal retention assumption is treated as a deployment decision.

## Staged order

1. Lock the baseline and keep the current runtime passing. Confirm the 246 existing tests and the 29 foundation tests offline.
2. Add a real, bounded Jev transport behind an adapter. Pin and log the returned model, include usage, validate every envelope, retry only 429/529 within a voice deadline, and fall back safely on 401/422, malformed 200 responses, timeout, or cancellation.
3. Build a fixed labeled evaluation set from real Coach utterances. Label intent, desired response, answer-library fit, unseen-fact hazards, and whether a line should be spoken. Include none-fits and near-miss cases, repeated states, harmless perturbations, and Choice option permutations. Fit per-action thresholds and version the resulting policy artifact.
4. Split the current broad `next_play` ranker into deterministic eligibility plus independent Jev dimensions (safety, role fit, immediacy/tempo, payoff) over one named state snapshot. Keep hard constraints and arithmetic in code. Compare this against the existing ranker before replacing it.
5. Add the input route: deterministic commands first, then one shared Jev fan-out for intent, request shape, and plan-change risk. Send uncertain/other cases to clarification or Claude. Mutations require a high gate and a confirmation path.
6. Add the Claude spoken-line adapter. Claude returns plain speech only. Jev checks the input and every generated line, including follow-ups. A failed or uncertain check uses the prepared/safe fallback, never silent guessed execution.
7. Fix delivery semantics in the Discord adapter. Send the message, confirm the delivery identity is still current, then commit board/topic/note changes exactly once. A stop, newer question, match restart, or failed send must leave state unchanged.
8. Resume answer-library work only after the owner selects sourcing, review, deduplication, provenance, patch freshness, and retention rules. Implement shortlist recall and selected-answer fit gates before any library answer can be spoken.
9. Pilot with logging and a kill switch. Measure quality, false action, fallback burden, latency, input tokens, retries, and player marks before changing live defaults.

## Verification commands

From the repository root on Windows PowerShell:

```powershell
$env:PYTHONPATH = 'jev_implementation'
.\.venv\Scripts\python.exe -B -m unittest discover -s jev_implementation\tests -v
.\.venv\Scripts\python.exe -B jev_implementation\demo.py
.\.venv\Scripts\python.exe -B -m unittest discover -v
```

The last command is the existing Coach suite. It must remain offline and must pass before a staged change is considered ready.

## Files for the next agent

- `CLAUDE_CODE_HANDOFF.md` is the copy/paste prompt for Claude Code or Codex.
- `IMPLEMENTATION_PLAN.md` contains the file-by-file plan, interfaces, gates, and rollback rules.
- `NOTE_COVERAGE.csv` assigns every numbered note in `JEV_DESIGN_NOTES.md` to a primary stage and records conflicts or deferrals.
- `BASELINE.md` records the source boundary and verification result for this staging pass.
