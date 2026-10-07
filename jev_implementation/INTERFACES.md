# Integration contracts

These are implementation contracts, not live APIs.

## Shared snapshot

`CoachSnapshot` contains `identity`, `player_question`, `observed`, `computed`, `reported`, `current_plan`, `references`, `coordinator_notes`, `candidates`, and `requires_alternatives`. The identity contains guild, session, request version, match key/serial and model-selection revision. Retain a snapshot hash and game clock. A snapshot is immutable once a turn starts.

Every fact has a source, game timestamp and optional expiry/confidence. Observed telemetry, minimap detections, player reports, code computations and static references remain distinguishable. Player claims expire by match/game clock; unknown fields remain unknown. Relevant references retain source ID, patch/date and support status. No credentials enter a snapshot.

## Generation boundary

`GenerationRequest`: fixed selected profile/revision, prompt revision, exact question, small topic brief, approved candidate material, deadline and cancellation signal. No writable board or Discord client is passed to a provider.

Async `generate(request) -> GenerationResult` returns `text`, `requested_model`, `returned_model` (optional if the provider omits it), `provider_request_id`, `finish_status`, `usage` (optional), `elapsed_seconds`, `retries`, `profile_id`. Text is plain speech. It cannot encode authority to commit a plan or execute a command. The adapter must mark incomplete, refused or failed generation before it reaches output checks.

Provider parameters are capability-specific. OpenAI Responses is not silently coerced to a Chat Completions shape. Anthropic gets native parsing. Local compatibility gets an explicit base URL and tested subset. No server-provided error body containing secrets is echoed to chat.

## Jev boundary

`evaluate(snapshot, questions, deadline, cancellation) -> ValidatedEnvelope`: preserve exact question IDs/types, probabilities, Choice/Score confidence, resolved model and optional token usage. `foundation/contracts.py` is the starting validation implementation, with current API behavior confirmed before adoption. Whole-answer confidence does not replace probabilities or top-two separation. Noul is P(yes), Score is an ordered rubric, arithmetic is code.

Questions use documented instructions/criteria. Shared-state independent checks batch together; selected-candidate text checks run after that text exists. Missing policy or mismatched Jev/question revision routes to clarification/safe fallback; generation eligibility also needs provider/prompt evaluation scope.

## Result and delivery boundary

`CoachTurnResult` contains approved speech, detailed chat, declared provider/fallback, staged effects, snapshot/selection identity, and trace summary. Effects include topic updates, offers, plans and note writes. The model never mutates memory directly.

Recheck identity before sending. Await successful Discord text delivery. Recheck identity under a lock and commit effects once. Stop/newer request/match restart/model switch/send failure invalidates the result. Check identity again before TTS. A message already sent during a race cannot be unsent by this contract; it must not cause stale commits or speech.

Model switches preserve the application-owned board/current plan/reports. Preserve delivered topic provenance; discard pending model output. New follow-ups against an old delivered read state that read's time; fresh reads get a new snapshot. Retries and rewrites use the originally frozen selection/deadline.

## Configuration and traces

Runtime loader additionally checks default-profile existence/enabled status, fallback cycles and availability, provider-specific required fields, model/env resolution, supported settings, deadline bounds and endpoint/credential association. JSON Schema cannot express all cross-profile checks. Template deadlines/token limits are provisional engineering budgets, not measured performance promises. `policy_id=null` means no new live policy has been calibrated.

Trace metadata: profile/revision, requested/returned model, question/prompt/policy revision, fingerprint, route, check distributions, timestamps, retry count, usage and reason for fallback/cancellation. Secret values and raw speech/game history are excluded from default logs. A separate evaluation dataset retains intentionally selected examples with provenance.
