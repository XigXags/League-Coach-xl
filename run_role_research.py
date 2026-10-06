"""Run five read-only League role studies through System Administrator."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
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

FOCUS = {
    "top": "wave control, matchup and level breakpoints, weak/strong side, jungle tracking, Teleport and side-lane assignment, split push, grouping, siege defense, and 2026 role quest effects",
    "jungle": "clear route and camp cycles, lanes' wave states, gank and countergank windows, tracking the opposing jungler, invades, cross-map trades, vision and fog uncertainty, Smite and objective conversion, and 2026 jungle rules",
    "mid": "wave control and priority, matchup and roam windows, jungle-support coordination, side-lane transition, siege and anti-siege, teamfight positioning, rotations, and 2026 role quest effects",
    "bot": "ADC or bot carry lane matchups, wave control and recall timings, support and jungle coordination, tower plates, lane swaps, mid-game farm assignment, teamfight positioning, objective damage, and 2026 role quest effects",
    "support": "lane pressure with bot, wave and reset timing, roam windows, warding and denial, jungle and mid partnership, engage versus peel, vision around sieges and objectives, resource tradeoffs, and 2026 support rules",
}

COMMON = (
    "You are one of five separate read-only researchers in the user's System Administrator app. "
    "Research League of Legends for a five-stack Discord coach. Do not edit files or run code. "
    "Use public web research, prefer current official Riot rules and direct interviews or game reviews by "
    "professional players/coaches; distinguish verified patch mechanics from enduring strategic principles. "
    "Never claim you watched a match unless you actually inspected it. Give direct URLs for key claims. "
    "Research this role in depth across lane phase, transitions, mid/late game, playing ahead and behind, "
    "fight setup, resets, vision, map information, team communication, and interactions with all four other roles. "
    "For each decision pattern specify trigger, information required, action sequence, counterexample, "
    "and what the existing Riot local Live Client Data API can/cannot verify. Include 6 concrete ten-second "
    "voice calls a coach might make and 6 failure cases or misleading heuristics. Separate observed, scheduled, "
    "inferred, and unknown facts. End with a source list and research gaps. Avoid generic 'play around objectives' advice. "
    "No credentials, private data, downloads, purchases, messages, or further agents."
)


def main() -> None:
    command = team.cli_check() + ["-c", 'web_search="live"']
    policy = json.loads((SYSTEMADMIN / "model-policy.json").read_text(encoding="utf-8"))
    config = policy["roles"]["project"]
    model = config["model"]
    worker_command = command + ["-c", "model_reasoning_effort=" + json.dumps(
        config.get("reasoning_effort", "medium"))]
    run = SYSTEMADMIN / "runs" / (time.strftime("%Y%m%d-%H%M%S") + "-league-roles-" + uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    output = PROJECT / "artifacts" / "role-research" / run.name
    output.mkdir(parents=True)
    task = "Five role-specific League coaching studies; research only, no product changes"
    team.atomic_json(run / "job.json", {
        "project": str(PROJECT), "task": task, "worker_sandbox": "read-only", "web_search": "live",
        "output": str(output), "automatic_followup": False,
        "assignments": {role: FOCUS[role] for role in FOCUS},
    })
    team.atomic_json(run / "grant.json", {
        "mode": "read-only public League role research", "project": str(PROJECT),
        "edits": False, "downloads": False, "purchases": False,
    })
    state = team.State(run, PROJECT, task, policy["roles"]["lead"]["model"])
    with state.lock:
        template = state.data["agents"]["project"]
        for role in FOCUS:
            seat = deepcopy(template)
            seat.update(name=role.capitalize() + " lane researcher", role="assessor", model=model)
            state.data["agents"][role] = seat
            state.data["positions"].append({
                "id": str(len(state.data["positions"])), "parent": "0",
                "title": seat["name"], "holder": model, "match": role,
                "role": "assessor", "status": "filled",
            })
        state.flush()
    state.phase("Five League role researchers browsing public sources")
    print("RUN=" + str(run), flush=True)
    print("OUTPUT=" + str(output), flush=True)

    def research(role: str) -> dict:
        prompt = COMMON + "\nROLE: " + role.upper() + "\nFOCUS: " + FOCUS[role]
        report = team.call_agent(state, role, prompt, worker_command, model,
                                 PROJECT, "league-" + role, timeout=900)
        (output / (role + ".md")).write_text(report, encoding="utf-8")
        return {"status": "reported", "report": role + ".md"}

    results = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(research, role): role for role in FOCUS}
        for future in as_completed(futures):
            role = futures[future]
            try:
                results[role] = future.result()
            except Exception as exc:
                results[role] = {"status": "failed", "error": str(exc)}
            team.atomic_json(output / "results.json", results)
            print(role + ": " + results[role]["status"], flush=True)
    failed = any(result["status"] == "failed" for result in results.values())
    state.phase("League role research incomplete" if failed else "League role research ready for review", complete=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
