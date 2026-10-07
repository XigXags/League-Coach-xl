# Preparation readiness

Date: 2026-10-06. Owner: Codex.

The earlier Claude-only plan is archived and superseded. The live runtime (`bot.py`, `coach.py`, `coordinators.py`, `lane_playbook.py`, `minimap_reader.py`, credentials and voice/hotkey code) was not changed in this preparation pass. No provider API calls, key reads, package installs, new runtime settings or bot restart were performed.

Process inspection found only the running Discord bot for this project (parent PID 13516, child PID 9708 at inspection). No earlier project-specific implementation worker was identified, so no process was terminated.

## Prepared and reviewed

- New controlling `START_HERE.md` and `IMPLEMENTATION_PLAN.md`.
- `MODEL_SWITCHING.md` specifies persistent guild profiles, model controls, cancellation, rollback, credential references and fair comparisons.
- `INTERFACES.md` specifies snapshots, provider results, Jev validation and delivered-only effects.
- `profiles.example.json` and `profiles.schema.json` specify builtin/OpenAI/Anthropic/compatible-server templates. Generative templates are disabled with model environment references; no keys are stored.
- Shared plain-speech prompt and `EVALUATION.md` specify guard/rewrite/follow-up behavior and held-out comparisons.
- `NOTE_COVERAGE.csv` regenerated: all 156 design notes are present once. Claude-specific source mentions are interpreted as the selected generator.
- Prior active documents retained under `archive/2026-10-06-claude-only-plan/`; old handoff now redirects to the replacement plan.
- README points to the prepared integration; local runtime profile/selections/evaluation outputs are ignored by version control.

## Verification performed

- Existing Coach suite: **246 passed**, `.venv\Scripts\python.exe -B -m unittest discover`.
- Offline foundation suite: **31 passed**, with `PYTHONPATH=jev_implementation`, `.venv\Scripts\python.exe -B -m unittest discover -s jev_implementation\tests`.
- Note coverage generator checked all integers 1–156 with no duplicate or missing entries.
- Both profile JSON files parse; default/enabled and fallback references were checked with Python's standard library. `jsonschema` is not installed, so full JSON Schema conformance validation was not run. Runtime implementation must include schema and cross-profile checks.
- Official TypeSafe API/models, OpenAI Responses and Ollama compatibility pages reviewed; URLs recorded in `MODEL_SWITCHING.md`. Anthropic's full Messages reference failed to fetch and needs verification when implementing that adapter.

## Implementation still to do

No `/model` or `/models` command exists yet. No generative provider transport, profile loader, split Jev ranker, labelled policy calibration, corrected delivery commit ordering or provider comparison runner has been wired into the bot. These are the concrete stages in the new plan. No claim of live provider access, best-model quality or calibrated thresholds is made.

The files are ready for the owner to start runtime implementation. Begin with Stage 0 profile/configuration contracts and Stage A transport validation, then proceed through measured routing, integration and delivery checks.
