# Coach model integration and scoreboard capture

Implemented 2026-10-06. This is the active runtime setup; the staged implementation plan remains the longer roadmap.

## Discord controls

- `/models`: list provider profiles and missing configuration.
- `/model`: inspect the server's selection and Jev calibration status.
- `/model use:PROFILE`: persist a server selection. Manage Server is required.
- `/model reset:true`: restore the default `legacy` profile.
- `/model reload:true`: reload local config; cancel outstanding answers and speech.
- `/compare profiles:legacy,local-test question:YOUR QUESTION`: compare up to three profiles on one frozen match snapshot. Private text only, no voice, no plan/note commits. Generative outputs are explicitly unvalidated drafts with Jev check results. These calls use the configured APIs and can consume credits.
- `/scoreboard`: inspect captures, age and OCR status.

## Configure an LLM

`coach_models.json` is local and ignored by version control. All generator templates start disabled. No Claude key or credit is required to keep using Jev. Exact model IDs come from your own provider account or local server; no automatic model substitution occurs.

Create the local config using `.venv\Scripts\python.exe -B configure_model.py`.

For a local OpenAI-compatible server, for example:

```powershell
.\.venv\Scripts\python.exe -B configure_model.py local-test --provider chat_completions --model YOUR_INSTALLED_MODEL --base-url http://127.0.0.1:11434/v1 --enable
```

For OpenAI, set `OPENAI_API_KEY` in `.env`, then:

```powershell
.\.venv\Scripts\python.exe -B configure_model.py openai-test --provider openai_responses --model YOUR_MODEL_ID --key-env OPENAI_API_KEY --enable
```

Anthropic uses `anthropic_messages` and `ANTHROPIC_API_KEY`. Do not put a secret token in `--key-env`; it takes only the environment variable's name. Restart the bot after changing its environment. Changing just the model config requires `/model reload:true`.

Adapters use native Responses, native Messages, or explicit Chat Completions endpoints. Requests have deadlines, bounded transient retries, no redirects, refusal/truncation rejection and resolved model/usage metadata. OpenAI requests set `store=false`. No default logs include raw prompts, screenshot text or secret keys.

### Live wording gate

The bot retains Jev ranking, role coordinators and code-owned plans. Generative models receive the same observed API facts, role/reference context, dated OCR and approved alternatives. Jev checks each proposed spoken line and at most one rewrite. No generated tokens stream to voice before approval.

There is **no calibrated Jev guard policy yet**. Generative profiles can be configured, selected and compared, but live calls visibly fall back to the prepared Jev response without consuming generator tokens. This is not a trained or evaluated quality improvement. A measured policy JSON in `evals/policies/<policy_id>.json`, bound to Jev `jev-1.13.0` and question revision `coach-staged-v1`, is needed to activate generated voice. It must include `eligible_generators`, an array of evaluated `{provider, model, prompt_sha256}` scopes; a different model or prompt cannot inherit eligibility. See `jev_implementation/EVALUATION.md`; do not invent threshold numbers to bypass this gate.

Switches stop pending speech/generation and preserve delivered topics and match plans. A failed Discord send or interruption during send cannot commit the new plan. Model callbacks never directly change notes/plans.

## Scoreboard input

While League of Legends is the foreground process and its local live API reports a match, holding **Tab** for at least 0.18 seconds saves a scoreboard crop on each opening. It does not open the scoreboard or control the game. The watcher uses the standard scoreboard key; it does not visually detect custom bindings or toggle-mode scoreboards. Rebind `COACH_SCOREBOARD_VK` to your scoreboard key if necessary.

Screenshots stay under `artifacts/scoreboards/`, with a maximum of 20 files. Windows OCR extracts text locally; the raw PNG is never uploaded. Fresh OCR text (up to 45 seconds old, same roster, no match-time rollback) goes to Jev and configured LLMs as **unverified, timestamped evidence**. API facts take priority. Missing/unreadable text never becomes a zero, an item, a spell cooldown, an enemy location or an observed fact. The game's API already supplies scores, CS, levels and items; OCR may add visible text, but player-row associations and icon-only items are not parsed into confirmed facts.

Defaults crop the central 76% of the game window. `COACH_SCOREBOARD_RECT=x,y,width,height` overrides it with pixel coordinates relative to that window and must stay inside it. Set `COACH_SCOREBOARD=0` to disable. With unusually positioned/resized UI, check the saved image and adjust the crop.

OCR uses [Windows.Media.Ocr](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine.recognizeasync?view=winrt-26100). Run `verify_model_setup.py` for a local OCR and provider readiness check. A successful synthetic OCR check does not prove every in-game scoreboard will read accurately.

## Verification

Runtime regression suite, provider protocol fixtures, model persistence/cancellation, failed delivery and OCR freshness tests: `python -B -m unittest discover`.
Jev foundation invariants: `python -B -m unittest discover -s jev_implementation\tests`.
Live Jev ranking/check smoke tests: `verify_jev.py`, `verify_jev_guard.py`.
Local OCR smoke test: `verify_model_setup.py`.
