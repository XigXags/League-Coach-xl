# Coach Jev and interchangeable LLM integration

Status: profile/provider, Jev contract/guard, Discord delivery and scoreboard integration implemented. Generative live speech is gated on calibration. See [../MODEL_INTEGRATION.md](../MODEL_INTEGRATION.md) for current setup and limits; the remaining stages below are a roadmap.
Owner: Codex. Updated: 2026-10-06.

This supersedes the earlier Claude-only plan and handoff. Old documents are retained in `archive/2026-10-06-claude-only-plan/` for history; they no longer control this project. Reuse the useful `foundation/` validators, policies and tests.

The owner approved implementation after preparation. Model controls and provider adapters now run in the bot; no additional provider key is configured and Claude remains disabled. The historical preparation-only checks remain in BASELINE.md.

## Read in order

1. `IMPLEMENTATION_PLAN.md`: implementation stages and acceptance checks.
2. `MODEL_SWITCHING.md`: profiles, Discord controls, providers and comparisons.
3. `INTERFACES.md`: state, generation, cancellation and delivery contracts.
4. `profiles.example.json` and `profiles.schema.json`: non-secret configuration templates.
5. `prompts/coach_system.txt`: shared generation instructions.
6. `EVALUATION.md`: model comparison and calibration.
7. `NOTE_COVERAGE.csv`: all 156 Jev design notes assigned to stages. Where the source says Claude, the new design means the selected generative LLM.
8. `BASELINE.md`: actual checks and remaining implementation.

Code owns rules, timers, eligibility, persistence and identity. Five role coordinators provide dated notes and targeted guidance. Jev handles bounded intent, fit, independent play scores and input/output checks. A selected generative LLM reasons over that brief and writes a short spoken line. Every provider uses the same evidence and delivery rules.

Initial targets are OpenAI Responses, native Anthropic Messages, and explicitly configured OpenAI-compatible Chat Completions for local or other hosted models. Exact model IDs are configuration. Account access and capability must be checked when configuring them; templates do not assert availability.

The live bot retains validated Jev ranking and prepared speech until a calibrated generation policy is supplied. Its role playbooks, notes, champion kits, minimap reader, plans, follow-ups and hotkey remain available. Fresh local scoreboard OCR now contributes dated, unverified evidence. Bulk answer-library generation and the feedback UI remain unresolved owner decisions from source notes 25/36. Proactive voice requires separate evaluation.
