# Staging baseline

Date: 2026-10-06

The live runtime files `bot.py`, `coach.py`, `coordinators.py`, `lane_playbook.py`, and `minimap_reader.py` were not modified by this staging pass. The new code is isolated under `jev_implementation/` and is not imported by the live bot.

Verification performed:

- Foundation tests: 31 passed with `PYTHONPATH=jev_implementation .venv\Scripts\python.exe -B -m unittest discover -s jev_implementation\tests -v`.
- Existing Coach suite: 246 tests passed with `.venv\Scripts\python.exe -B -m unittest discover -v`.
- `demo.py` is offline-only and validates a synthetic envelope; it must not be presented as a live API test.

Known baseline facts to revisit during integration:

- `coach.py:jev_rank` currently sends the direct HTTP request, keeps only probabilities, and maps missing keys to zero.
- `bot.py:accept` currently runs the commit before the caller awaits the Discord send. A future delivery stage must change this only with focused tests for failed sends and superseding requests.
- No calibrated Coach policy, live Claude adapter, answer-library approval, or production feedback label flow exists yet.
