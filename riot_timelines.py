r"""Pull ranked match timelines from Riot's Match-V5 API, with player positions per minute.

The key is read from the RIOT_API_KEY environment variable and is never printed.
Set it in the same PowerShell window you run this from:
  $env:RIOT_API_KEY = (Get-Content "$env:USERPROFILE\OneDrive\Desktop\LOLAPI.txt" -Raw).Trim()

Usage:
  .venv\\Scripts\\python -B riot_timelines.py --riot-id "Name#TAG" --region americas --count 5
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REGIONS = ("americas", "asia", "europe", "sea")
OUTPUT = Path(__file__).with_name("artifacts") / "riot-timelines"


def _key() -> str:
    key = os.getenv("RIOT_API_KEY", "").strip()
    if not key:
        raise SystemExit("RIOT_API_KEY is not set in this window. Set it first; see the module docstring.")
    return key


def _get(url: str, key: str, retries: int = 3) -> dict | list:
    """GET with Riot's rate-limit handling: wait for Retry-After on 429 and retry a few times."""
    for attempt in range(retries + 1):
        # Python's default User-Agent is rejected by some Riot gateways, so send an explicit one.
        request = urllib.request.Request(url, headers={"X-Riot-Token": key, "User-Agent": "league-coach/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < retries:
                time.sleep(int(error.headers.get("Retry-After", "2")))
                continue
            raise SystemExit(f"Riot API returned HTTP {error.code} for {url.split('?')[0]}") from None
    raise SystemExit("Riot API kept rate-limiting; try again later.")


def account_puuid(game_name: str, tag_line: str, region: str, key: str) -> str:
    quoted = urllib.parse.quote(game_name)
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quoted}/{urllib.parse.quote(tag_line)}"
    return _get(url, key)["puuid"]


def match_ids(puuid: str, region: str, key: str, count: int) -> list[str]:
    url = (f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
           f"?queue=420&start=0&count={count}")
    return _get(url, key)


def timeline(match_id: str, region: str, key: str) -> dict:
    return _get(f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline", key)


def positions_per_minute(data: dict) -> list[dict]:
    """One row per minute per participant with x/y map coordinates, plus that minute's events."""
    rows = []
    for minute, frame in enumerate(data["info"]["frames"]):
        for participant_id, state in frame["participantFrames"].items():
            position = state.get("position") or {}
            rows.append({"minute": minute, "participant": int(participant_id),
                         "x": position.get("x"), "y": position.get("y")})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull Match-V5 timelines with player positions")
    parser.add_argument("--riot-id", required=True, help='e.g. "Name#TAG"')
    parser.add_argument("--region", default="americas", choices=REGIONS)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    key = _key()
    game_name, _, tag_line = args.riot_id.partition("#")
    puuid = account_puuid(game_name, tag_line, args.region, key)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for match_id in match_ids(puuid, args.region, key, args.count):
        data = timeline(match_id, args.region, key)
        target = OUTPUT / f"{match_id}.json"
        target.write_text(json.dumps(data), encoding="utf-8")
        print(f"Saved {target.name}: {len(positions_per_minute(data))} position rows.")


if __name__ == "__main__":
    main()
