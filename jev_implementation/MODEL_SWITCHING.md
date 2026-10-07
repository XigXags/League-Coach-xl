# Switching Coach models

## Implemented controls

- `/models`: list profiles, provider, model and configured/evaluated readiness.
- `/model`: current profile, Jev judgment model and permitted fallback.
- `/model use:openai-test`, `claude-test` or `local-test`: choose a configured profile.
- `/model reset`: restore the default.

These commands are implemented. Reset is `/model reset:true`; config reload is `/model reload:true`. Shared guild switches require Manage Server; anyone may inspect. Selections persist across restart. Exact model IDs are filled from the owner's account/local server; templates claim no account access or capability. See `../MODEL_INTEGRATION.md` for the explicit calibration gate and current scoreboard input limits.

Changing the generator leaves Jev as the bounded judgment/check layer. Jev model/policy changes are separate evaluated settings. `legacy` restores current Jev ranking with deterministic wording. Speech recognizer and voice remain separate settings.

## Profiles

`profiles.example.json` is a template, not active config. `profiles.schema.json` defines its shape. Use an inline model or model environment reference, not both. Enabled generative profiles must resolve an actual model; disabled templates may be incomplete. Credentials are environment variable names, never token text. Reuse current private Jev key loading.

Adapters own endpoint paths, supported parameters and response parsing. Profiles may supply an explicit base URL; local templates use loopback. Never send credentials to an endpoint inferred from another provider. No silent substitution. An optional fallback must be named, acyclic, enabled and eligible for the same output gates; report its use. Deterministic safe fallback remains available if remote providers fail.

Switching cancels the current answer/speech and pending generated follow-ups; existing match memory stays. Freeze selection/revision per turn. Reload and validate configuration before exposing new profiles.

## Fair trials

Explicit `/compare` runs up to three requested profiles against the same frozen snapshot and prompt. It labels unvalidated drafts, generation latency, Jev hazard probabilities and usage, with no speech or live-board/note mutation. This is not measured accuracy; held-out labels are still needed. Missing price metadata is unknown cost. Generators remain disabled by default. Normal live generation is gated on calibration.

## Reviewed primary sources (2026-10-06)

- [TypeSafe API](https://docs.typesafe.ai/api): typed judgments and envelopes.
- [TypeSafe models](https://docs.typesafe.ai/models): stable `jev-1.13.0`; pin calibrated version and record resolved model.
- [OpenAI Responses](https://developers.openai.com/api/reference/python/resources/responses/methods/create): native text generation/status/usage. Planned requests set `store=false` explicitly.
- [Ollama compatibility](https://docs.ollama.com/api/openai-compatibility): compatible interfaces with capability differences; verify the selected server.
- [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create) was checked during implementation. The native adapter parses text blocks and rejects truncated/refused output; Claude remains disabled unless configured.
