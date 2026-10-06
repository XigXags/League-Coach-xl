# Coach public upload manifest

The public export is `public_export/`. It is a deliberate subset of the local runtime folder.

Included:

- Coach Python source, tests, verification scripts, requirements, and setup documentation.
- `JEV_DESIGN_NOTES.md` and the complete `jev_implementation/` staging package.
- Lane playbooks and the generated answer snapshots under `lane_playbook/answers/`.
- Generated champion metadata and mobility/kit files.
- Derived role research and Worlds research under `artifacts/`.
- Worlds playlist metadata, without the raw transcript archive or game CSVs.

Excluded:

- `.venv/`, caches, logs, restart traces, voice samples, and any microphone/audio material.
- `TYPESAFE_API_KEY.txt`, Discord/Riot credential files, `.env`, certificates, and private desktop files.
- Raw Riot timeline JSON and raw transcript/game data.

The export was scanned for credential-like filenames and common key/token markers before commit. The `credentials.py` file contains only code that reads environment variables or local files; it contains no credential value.
