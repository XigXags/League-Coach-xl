# Coach Jev implementation plan

## Current baseline

The current live Coach ranker makes one direct HTTP Choice call in `coach.py:jev_rank`, uses only the probability map, and turns malformed/missing probabilities into zeros. The bot has deterministic intent/plan handling and deferred board commits, but `bot.py:accept` commits before the subsequent Discord send is awaited. These are the two highest-value integration seams. The current runtime remains unchanged in this staging pass.

## Design boundaries

Jev is for bounded judgments. Claude is for reasoning and plain spoken wording. Code owns arithmetic, timers, dates, counts, eligibility, patch rules, retries, cancellation, persistence, and delivery identity. Retrieved text, player speech, and player-reported facts are untrusted data; instructions in those fields are never treated as system policy.

Every evaluation carries a named state snapshot with `player_question`, observed facts, computed facts, timestamped player reports, current plan, references/citations, and the candidate or line being judged. Facts retain source and freshness. The same snapshot is used for independent fan-out questions; a second call is used only when candidate text or other evidence was fetched after the first call.

## Stage A — transport and contract (foundation is staged)

Target files: `jev_implementation/foundation/contracts.py`, new `jev_service.py`, `coach.py` adapter seam, and offline tests.

Implement a typed transport with a monotonic deadline and cancellation. Use a pinned versioned model during calibration. Preserve the response envelope and request fingerprint. Validate the API bounds: Choice 2–255 options, Score 2–10 ordered levels, Noul yes probability, exact answer IDs, finite values, valid probability mass, and Score expectation. Put all guidance inside documented `instructions` or criteria objects. Keep the question revision and policy ID alongside results.

Gate: malformed 200, timeout, cancellation, 401, 422, 429, 529, retry-after, missing probabilities, wrong answer IDs, and model mismatch all produce safe fallback behavior in tests. No live bot path changes yet.

## Stage B — labeled evaluation and policies

Target files: new `evals/` fixture format, calibration script, policy artifact loader, and tests.

Create real Coach examples with labels for intent, response type, candidate fit, unsupported location/number/rule, unanswered question, option parroting, severity, mutation confirmation, and should-speak. Include “none fits” and near misses. Repeat exact inputs, perturb irrelevant fields, and permute Choice options. Track correctness, coverage, false action, fallback burden, calibration, latency, tokens, and retry rate. Thresholds are per action and error cost; never copy cookbook cutoffs.

Gate: a frozen held-out set demonstrates the selected policy; the calibration artifact names model version and question revision; a stale/missing policy refuses to act. Owner feedback UI remains an adapter-neutral label contract until chosen.

## Stage C — split ranker

Target files: `coach.py` ranker seam, new question definitions, candidate eligibility tests.

Keep deterministic `two_options` eligibility and hard safety. Ask focused Score/Noul judgments for safety, role fit, tempo/immediacy, payoff, and unseen assumptions in one shared state. Normalize ordered scores in code, apply `/approach` weights in code, inspect components, and preserve top-two probabilities. Compare broad and split rankers with option-order and state-ablation tests.

Gate: no impossible or unsupported option survives a high Jev payoff; split ranker improves or matches held-out decisions and latency within the measured budget; rollback remains one configuration switch.

## Stage D — input routing and Claude

Target files: new `routing.py`, `claude_adapter.py`, `coach.py`/`bot.py` integration tests.

Route deterministic stop/more/track commands first. Fan out intent, desired options, plan-change request, and difficulty/fit checks where they share the same snapshot. Clarify low-confidence cases, send `other` and difficult cases to Claude, and require confirmation for middle-band mutations. Claude receives a small topic brief and returns only plain speech. Jev guards input and every output line. A review hazard gets one rewrite; high severity or a second failure falls back.

Gate: generated lines never bypass output checks; “options” lines do not blindly repeat prepared hints; no Claude structured-response parsing is introduced.

## Stage E — evidence, retrieval, and library (paused)

Target files: evidence contracts, retrieval adapter, library fixtures only after owner decision.

Keep observed, player-reported, and reference facts separate. Expire reports by match/time. If library work resumes, first measure cheap shortlist recall, then Jev candidate fit and selected-answer suitability, not `max(any fit)`. Keep `none fits`, source IDs, provenance, patch freshness, and injection/premise checks. Preserve original entries during dedupe and send ambiguous pairs to review.

Gate: no library answer is spoken automatically without selected-answer fit, current-state support, output guard, and delivery identity. Until the owner decides sourcing/quality, the library remains an empty or fixture-only dependency.

## Stage F — delivery and pilot

Target files: `bot.py`, `coach.py`, observability sink, pilot configuration.

After Discord send succeeds, recheck guild/session/request version, match key/serial, and single-commit status under the session lock, then commit board/topic/note. A stop, newer request, match restart, or failed send leaves state unchanged. Keep automatic proactive speech disabled until separately evaluated.

Gate: all existing tests plus new cancellation/delivery tests pass; shadow mode has measured quality, latency, tokens, and fallback; a kill switch restores the current ranker and deterministic speech.

## Explicit conflict resolutions

- Notes 20–24 describe retrieval/reranking; notes 26–31 describe a later meaning-based two-pass Choice. Stage A/B benchmark both. Do not enable both or assume cross-chunk probabilities are comparable.
- Notes 25 and 36 are owner decisions. Stage neutral interfaces and fixtures only; do not pick the feedback UI or generate the library.
- Notes 40 and 141 coexist by separating roles: Claude speech remains plain text; a future compound-request splitter may be a separate generative extractor whose output is validated before any action.
- Notes 58, 71, 72, 94, and 151 distinguish Choice winner/probabilities from whole-answer confidence. Use `choice`/probabilities to select, confidence and calibrated top-two checks to decide whether to trust.
- Notes 73, 74, and 154 keep Score/Noul semantics separate. Never treat a Noul near 0.5 as a medium amount; never use a Score as exact arithmetic.
- Notes 98–100 and 140 support fan-out only where the initial state contains enough evidence. Candidate-dependent checks remain a second request.
- Notes 142–149 supersede older model/pricing assumptions. Pin/log the resolved model and measure current usage; do not copy old cookbook prices or thresholds.
