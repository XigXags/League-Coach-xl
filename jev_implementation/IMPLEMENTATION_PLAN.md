# Coach integration implementation plan

This replaces the Claude-only plan. Preparation is complete; the owner requested a readiness report before runtime implementation.

## Integration seams

- `coach.py:jev_rank`: replace broad direct HTTP Choice with a validated transport; move undocumented `role_rule` into documented instructions; preserve model/usage/confidence and reject missing probabilities instead of filling with zero.
- `coach.py:coach`: create one named snapshot from current game, plan, champion kits, coordinator notes, role/reference lessons and minimap observations; retrieve focused context instead of dumping every playbook.
- `bot.py:make_answer`: preserve responsive handling while adding cancellable async model transports.
- `bot.py:accept`: currently commits before the awaited Discord send. Move commits after successful delivery and identity recheck, with tests for failed sends and interruptions.
- Preserve code-owned notes, plans, topic, role playbooks, stop/more/track behavior, two alternatives, concise speech, full chat and voice/hotkey settings.

## Stage 0 — profiles and switching

Implement `model_profiles.py` and ignored runtime `coach_models.json` from the staged template/schema. Keep Jev's judgment model separate from the selected generator. Add `/models`, `/model` status, `/model use:<profile>` and `/model reset`. Restrict shared guild changes to Manage Server users; inspection is available to everyone. Use autocomplete, not a fixed slash enum. Persist guild selections atomically in an ignored local file.

Resolve and freeze the profile once per turn. Switching stops speech, invalidates in-flight request/model revision, and clears pending generated follow-ups. Preserve board/plan/reports and the already delivered topic. A later elaboration uses the new provider with the dated delivered snapshot; a fresh read is marked as fresh.

Gate: unknown, disabled or misconfigured profiles leave the old selection intact. Restart restores selection, guilds are isolated, status exposes no secrets or paid calls. Explicit `legacy` profile restores current behavior. No silent provider/model substitution.

## Stage A — transports and traces

Implement runtime package modules `jev_service.py`, `llm_provider.py`, `providers/openai_responses.py`, `providers/anthropic_messages.py`, `providers/chat_completions.py`. Audit/reuse `foundation/contracts.py`; remove reliance on PYTHONPATH hacks. Native APIs have native parsing. Only send parameters the chosen adapter/model supports.

Normalize plain text, requested and returned model, provider request ID, finish/refusal status, optional usage, latency and retries. Empty, truncated, refused or malformed output is not a completed answer. Use one monotonic turn deadline across routing, generation, guarding and at most one rewrite. Cancellation is checked before/after awaits. Honor Retry-After within the deadline and only retry documented transient errors; Jev 401/422 are not retries, 429/529 may be.

Log profile/revision, models, question/prompt revisions, fingerprint, route, probabilities, timings, tokens and fallback reason. No secrets or raw player content in default telemetry. Missing usage/pricing means unknown, not zero. Credential environment references resolve only for their own explicitly configured provider endpoint.

Gate: offline fixtures for malformed 200, missing/extra/NaN probabilities, wrong IDs, timeouts, cancellation, refusal, truncation, retries and provider shapes. Live smoke tests verify configured account access separately. Declared fallbacks are visible and receive the same checks.

## Stage B — cases and policies

Implement labelled replay cases, comparison runner and versioned policy artifacts using `EVALUATION.md`. Include none-fits/near misses, stale reports, early objective, plan mutations, corrections, stop and follow-ups. Synthetic cases check invariants; they are not measured player accuracy.

Calibrate per-action intent/fit/hazard/severity gates on development labels; check held-out data. Bind policy to Jev resolved version and question revision, and record generator/prompt evaluation scope. A new generator needs evaluation eligibility; changing it does not mathematically invalidate unchanged Jev calibration by itself. Untested profiles may run offline/shadow, never bypass absent live gates.

Gate: correctness, false action, unsupported claims, none-fits errors, coverage, fallback burden, latency and usage. Test identical repeats, harmless perturbations and option permutations separately. No cookbook thresholds are production defaults.

## Stage C — state and independent judgments

Implement `coach_state.py`, `jev_questions.py`, `play_scoring.py` per `INTERFACES.md`. Preserve observed/computed/player-reported/reference sources and expiry. A role field is not coordinates; champion ability text is not readiness; minimap detections retain timestamp/confidence.

Apply deterministic eligibility before Jev. Batch independent safety, role-fit, immediacy, payoff and unsupported-premise questions over one snapshot. Normalize scores and apply `/approach` weights in code. Keep distributions and none-fits. Second requests need a genuine evidence dependency. Benchmark context trimming and remove the eight-option cutoff's ability to hide a triggered play.

Gate: no high score revives an impossible play; score edges do not prove lane priority. Expired/corrected player reports are removed. Compare against the broad ranker before replacement.

## Stage D — provider-neutral routing and speech

Implement `routing.py`, `brief_builder.py`, `coach_pipeline.py`. Deterministic stop/more/track first; batch independent intent, response-shape, fit and action-risk checks. Uncertain/other cases clarify or use the selected generative provider with a small topical brief.

Generate plain speech only; code owns metadata and proposed effects. Generate initial line, then elaboration on request. Tactical calls require two supported alternatives. Jev checks input and every generated output/follow-up. Allow one bounded rewrite, then an explicit safe/prepared fallback. Never stream unverified generated tokens to Discord or TTS; approved lines may stream audio as today.

Gate: models cannot save notes or change plans directly; prepared hints can be ignored. Check the selected answer's fit, not the maximum fit of another candidate. Stop cancels any stage and prevents late commits.

## Stage E — references and reports

Implement timestamped player reports, role/reference retrieval and support checks. Read all five role reports at startup, then retrieve the relevant brief each turn. Preserve source IDs and originals for current lessons, pro tendencies, kits and champion notes.

Source notes 25/36 keep library generation/feedback decisions paused. Once selected, compare shortlist recall for BM25/keyword and meaning-based retrieval; do not compare probabilities from independent chunks as if jointly normalized. Compound splitting/extraction is separate validated work, never implicit mutations. Autoresearch waits for enough genuine labelled outcomes.

Gate: no invented location/camp/number or stale report promoted to observation. Historical tendencies stay background. No bulk job runs as part of a normal voice request.

## Stage F — delivery and pilot

After Discord text succeeds, recheck guild/session/request/model revision/match serial under the session lock, then commit staged effects exactly once. Failed send, stop, switch or restart leaves them untouched. Reject superseded speech. Keep a rollback switch to current behavior.

Start new paths in shadow mode and enable evaluated profiles individually. Explicit `/compare` uses a frozen snapshot, bounded requested profiles and request budget; labelled results go to text, with no speech or plan/note commits. Normal voice calls use one selected generator. Validate quality and first-approved-audio timing with the owner in a real match. Proactive voice is a later deduplicated, calibrated experiment.

Prepared files are docs, templates, shared prompt, interface/evaluation contracts and complete note coverage. Runtime modules above are future targets; no empty runtime stubs are imported by the live bot.
