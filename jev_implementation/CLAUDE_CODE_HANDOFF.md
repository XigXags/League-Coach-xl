# Copy/paste handoff for Claude Code or Codex

Work in `C:\Users\lukee\league-coach`. Treat `jev_implementation/START_HERE.md` and `jev_implementation/IMPLEMENTATION_PLAN.md` as the controlling implementation documents, and read `JEV_DESIGN_NOTES.md` plus `jev_implementation/NOTE_COVERAGE.csv` before editing.

The task is to stage Coach's Jev architecture carefully. Do not activate a new live path just because an endpoint call succeeds. Do not invent thresholds, response fields, answer-library entries, or hidden state. Do not use documentation example metrics as Coach calibration. Do not generate thousands of library answers: note 36 remains paused until the owner chooses sourcing and review rules.

The existing Coach runtime is in `coach.py`, `bot.py`, `coordinators.py`, `lane_playbook.py`, and `minimap_reader.py`. The existing offline suite currently passes. Preserve its behavior until a replacement is evaluated. Do not read or print API keys, tokens, or private desktop files.

Start by running the existing tests and the 29 tests under `jev_implementation/tests`. Review the staged foundation rather than replacing it blindly. Then implement only the next unblocked stage:

1. Create an isolated Jev transport adapter with the documented request shape. Put all question wording, criteria, model ID, revision ID, and policy references in one reviewable module. Move `coach.py`'s undocumented `role_rule` guidance into documented structured `instructions`; never rely on an undocumented sibling field.
2. Validate successful responses before routing. Require the requested question IDs, answer types, finite probabilities with the expected keys and approximately unit mass, valid winners/Score means, model, and usage. Never map missing probabilities to zero. Keep `429`/`529` retries bounded by the voice deadline and `Retry-After`; do not retry `401` or `422`.
3. Preserve full envelopes for traces: request fingerprint, resolved model, question revision, input/output usage, latency, retries, and each answer's probabilities/confidence. Redact player secrets and do not log credentials.
4. Add fixture-driven calibration before runtime routing. Include clear, borderline, adversarial, none-fits, near-miss, repeated, harmlessly perturbed, and Choice-order-permuted cases. Fit separate intent, fit, hazard, mutation, and severity policies. A policy must refuse to act if its model or question revision does not match the recorded calibration.
5. Split ranker judgments over one named state snapshot. Deterministic code owns timers, counts, eligibility, patch rules, hard safety, and arithmetic. Jev supplies focused semantic judgments; code combines normalized scores with style weights. Compare against the broad `next_play` ranker offline before switching.
6. Add Claude only as a plain spoken-line generator with a small topic brief. Jev evaluates the player's input and every Claude line, including follow-ups. Keep one rewrite maximum, then use a safe/prepared fallback. If the player asks for options, do not allow a prepared hint to be repeated verbatim without an explicit fit check.
7. Integrate delivery only after the message is actually sent and the request/match identity is rechecked. A canceled, superseded, restarted, or failed delivery must not commit the board, topic, or note. Keep the existing “two alternatives and the player's choice” contract.

For each stage, write focused offline tests first, run the full suite, report the exact files and commands, and stop at the stage gate in the plan. Do not ask the owner for a new product choice unless the plan marks it as owner-owned; otherwise leave the feature disabled and document the unresolved choice. The unresolved feedback UI (post-match review versus immediate good/bad voice mark) is an owner decision; implement only a neutral label data contract until selected.

At the end of each stage, update `START_HERE.md`, `IMPLEMENTATION_PLAN.md`, `NOTE_COVERAGE.csv`, and `BASELINE.md` if the boundary or test result changed. Keep this handoff text copyable and factual.
