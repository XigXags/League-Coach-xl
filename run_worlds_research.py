"""Run one read-only League research batch through the local SystemAdmin runner."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys
import time
import uuid

PACKAGE = Path(r"C:\New folder\New folder\SystemAdmin-Windows")
SYSTEMADMIN = Path.home() / "AppData" / "Local" / "SystemAdmin"
PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE))
import team  # noqa: E402

ASSIGNMENTS = {
    "project": (
        "worlds-data",
        "Audit World Championship match data coverage from 2011 through the latest completed Worlds. "
        "Find original data providers and direct downloads or APIs for team/player/game records. "
        "Report exact covered years, missing years, fields (objectives, towers, gold, champions, items), "
        "licensing, and patch comparability. Do not calculate a statistic without downloading and "
        "checking the underlying data. Give a reproducible, bounded plan to calculate pick rates, "
        "win rates and objective trades without treating old-patch rates as current guidance.",
    ),
    "windows": (
        "worlds-macro",
        "Research primary Worlds VODs, official recaps, or analyst material across early, middle, "
        "and recent eras for recurring non-objective macro plays: wave crash into roam, side-lane "
        "pressure, mid priority, cross-map tower trades, jungle tempo and vision traps. Inspect a "
        "small, named sample deeply. Give URLs, match/date/patch and timestamps only when verified. "
        "Clearly distinguish VOD frames personally inspected from summaries or metadata read. "
        "Do not claim to have watched every Worlds game. Extract concrete, testable play patterns "
        "that a five-stack voice coach could express in ten seconds.",
    ),
    "workflow": (
        "current-rules",
        "Research official current-season League rules for jungle camps and respawns, lane waves, "
        "Teleport and champion global movement, vision and fog information, and objective timing. "
        "Use Riot primary sources and cite exact patch numbers. Audit Riot local Live Client Data API "
        "and Overwolf League game events for which live facts the coach can actually access. "
        "Separate observable facts from inference and unavailable information. Propose a staged, "
        "policy-compliant implementation plan with explicit tests for wrong early-game claims.",
    ),
}

COMMON = (
    "You are a read-only research worker in the user's System Administrator app, helping build "
    "C:/Users/lukee/league-coach. Use live web search and direct source URLs. This is research, "
    "not a code-change task. Never read credentials, send messages, purchase content, or edit files. "
    "Be exact about evidence and uncertainty. This is not a claim to have watched every Worlds VOD. "
    "Do not launch further agents. Return a concise report with sources, actionable findings, "
    "source limits, and the next implementable steps.\nASSIGNMENT:\n"
)


def main() -> None:
    command = team.cli_check() + ["-c", 'web_search="live"']
    policy = json.loads((SYSTEMADMIN / "model-policy.json").read_text(encoding="utf-8"))
    roles = policy["roles"]
    run = SYSTEMADMIN / "runs" / (time.strftime("%Y%m%d-%H%M%S") + "-league-" + uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    output = PROJECT / "artifacts" / "worlds-research" / run.name
    output.mkdir(parents=True)
    task = "League Worlds evidence audit for a faster, broader two-option five-stack coach"
    team.atomic_json(run / "job.json", {
        "project": str(PROJECT), "task": task, "worker_sandbox": "read-only",
        "web_search": "live", "output": str(output), "automatic_followup": False,
        "assignments": {key: assignment for key, (_, assignment) in ASSIGNMENTS.items()},
    })
    team.atomic_json(run / "grant.json", {
        "mode": "read-only public League research", "project": str(PROJECT),
        "edits": False, "downloads": False, "purchases": False,
    })
    state = team.State(run, PROJECT, task, roles["lead"]["model"])
    state.phase("Three League research workers browsing public sources")
    state.note("lead", "Scoped League Worlds research started; unrelated SystemAdmin jobs untouched.", "Research")
    print("RUN=" + str(run), flush=True)
    print("OUTPUT=" + str(output), flush=True)

    def research(key: str) -> dict:
        slug, assignment = ASSIGNMENTS[key]
        role = roles[key]
        worker_command = command + ["-c", "model_reasoning_effort=" + json.dumps(
            role.get("reasoning_effort", "medium"))]
        report = team.call_agent(state, key, COMMON + assignment, worker_command,
                                 role["model"], PROJECT, slug, timeout=720)
        (output / (slug + ".txt")).write_text(report, encoding="utf-8")
        return {"status": "reported", "report": slug + ".txt"}

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(research, key): key for key in ASSIGNMENTS}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                results[key] = {"status": "failed", "error": str(exc)}
            team.atomic_json(output / "results.json", results)
            print(key + ": " + results[key]["status"], flush=True)
    failed = any(result["status"] == "failed" for result in results.values())
    state.phase("League research incomplete" if failed else "League research ready for review", complete=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
