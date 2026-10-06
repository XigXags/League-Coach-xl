# Public repository scope

This repository contains the League Coach source, tests, playbooks, Jev design notes, staged Jev implementation, generated champion data, and the derived role/Worlds research used to design the project.

The following are intentionally excluded from the public export:

- API keys, Discord tokens, Riot credentials, environment files, certificates, and local credential paths.
- Python virtual environments, logs, caches, restart traces, and machine-local recordings.
- Voice sample audio and microphone material.
- Raw Riot timeline dumps and raw game transcript CSVs.
- The raw Worlds transcript archive.

Those files are local inputs or generated runtime artifacts rather than necessary project documentation. The source scripts describe how to reproduce integrations with credentials supplied through environment variables. No credential value is included in this repository.

Before publishing a future change, run a secret scan and inspect the complete staged file list. Never commit a key to “test” whether it works; revoke and replace any credential that may have been exposed.
