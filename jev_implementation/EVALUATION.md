# Comparing models and validating the pipeline

Use frozen named snapshots to compare one generator profile at a time behind the same Jev checks. No best model is selected during staging. No labelled real-player dataset or calibrated live thresholds currently exist.

## Case format

Each JSONL case will contain `case_id`, `label_origin` (synthetic or human-reviewed), `split` (development/held-out), snapshot, expected intent, required response shape, acceptable/unsupported facts, permitted effects, none-fits label and source references. Keep match IDs grouped into one split to avoid leakage. Preserve exact transcript where a case came from speech; redact identifying data not needed for the decision.

Required cases: early Dragon before spawn, explicitly unavailable objective, dead jungler, missing wave/location/cooldown, attributed versus stale enemy sighting, inflated Practice Tool scores, stop during each stage, newer question, model switch, plan pick versus question, failed Discord send, same-state repetition, none-fits and near-miss retrieval, follow-up to dated read, irrelevant kit text, compound requests, provider refusal/truncation/rate-limit/timeout/malformed response, unavailable model and fallback cycle.

## Metrics

For every profile report specific-question fit, supported alternatives, actionable role steps, unsupported claims, factual mistakes, false mutations, none-fits false selections, fallback/clarification coverage, approved output length and usefulness labels. Measure full turn and first approved audio latency (p50/p95), retries, requests, input/output tokens, and known-price estimate or unknown. Report raw-generation and post-guard results separately so excessive fallback cannot appear as superior coaching.

Hold evidence, question, prompt revision and visible output budget constant. Record provider differences in supported controls and hidden/reasoning token usage rather than pretending those are equivalent. Compare exact repeats, irrelevant perturbations and Choice-order permutations separately. A synthetic invariant pass is not a quality win or model calibration.

## Policies and feedback

Fit per-action thresholds on human-reviewed development cases and test frozen held-out examples. Policy records Jev resolved version, question revision, dataset identity, metrics and the generator/prompt scope evaluated. No example 0.5/0.75/0.85 threshold is an assumed default. A new generator can run offline/shadow until its generated lines meet live acceptance criteria.

Source note 25 leaves feedback UI undecided. Stage the label contract only: read ID, candidate/profile/model, good/bad/unclear, optional reason and timestamp. The owner can select immediate voice marks or post-match review later. Note 36 keeps bulk library growth paused. Existing sourced role/pro/champion material is available for targeted briefs.

## Pilot

First use fake/offline transports for contract and race tests, then account-authorized smoke requests, then bounded frozen-snapshot comparisons, then shadow/real-match pilot with the owner. Preserve `legacy` rollback. Enable calibrated profiles individually. Explicit comparison is text only and changes no board state. Proactive speech is a separate later evaluation.
