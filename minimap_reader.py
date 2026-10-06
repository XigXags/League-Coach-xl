"""Read champion icons from the League minimap on the PC running the game.

Allies always show on the minimap. Enemies show only while they are in vision.
The reader finds the coloured team rings, then names each icon by matching it
against the five champions the Live Client Data API lists for that team. Output
is a fraction of the minimap (0 to 1 on each axis), not game coordinates.

Commands:
  .venv\\Scripts\\python -B minimap_reader.py --fetch-icons
  .venv\\Scripts\\python -B minimap_reader.py --calibrate
  .venv\\Scripts\\python -B minimap_reader.py --file shot.png --rect x,y,w,h --teams "ORDER:Lucian,Nami|CHAOS:Jinx"
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np


DDRAGON_VERSION = "16.19.1"
ICON_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{id}.png"
CHAMPION_LIST = Path(__file__).with_name(f"champions-{DDRAGON_VERSION}.json")
ICON_DIR = Path(__file__).with_name("champion_icons")
TEMPLATE_SIZE = 32
# Guess for 1920x1080, bottom-right. Run --calibrate and set COACH_MINIMAP_RECT to the real box.
DEFAULT_RECT = (1668, 812, 236, 236)

# OpenCV hue runs 0-180. Blue rings sit near 100-130; red rings wrap around 0 and 180.
TEAM_RANGES = {
    "ORDER": [((95, 120, 110), (130, 255, 255))],
    "CHAOS": [((0, 120, 110), (8, 255, 255)), ((170, 120, 110), (180, 255, 255))],
}


@dataclass(frozen=True)
class Ring:
    team: str
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class Sighting:
    team: str
    champion: str | None
    x: float
    y: float
    score: float
    seen_at: float


def _key(name: str) -> str:
    return "".join(c for c in name.casefold() if c.isalnum())


def fetch_icons() -> int:
    """Download one portrait per champion into champion_icons/. Run once per patch."""
    ICON_DIR.mkdir(exist_ok=True)
    champions = json.loads(CHAMPION_LIST.read_text(encoding="utf-8"))["data"].values()
    fetched = 0
    for champion in champions:
        target = ICON_DIR / f"{champion['id']}.png"
        if target.exists():
            continue
        url = ICON_URL.format(version=DDRAGON_VERSION, id=champion["id"])
        with urllib.request.urlopen(url, timeout=20) as response:
            target.write_bytes(response.read())
        fetched += 1
    return fetched


@lru_cache(maxsize=1)
def _templates() -> dict[str, np.ndarray]:
    """Circular colour portraits keyed by normalized champion name."""
    mask = _circle_mask()
    templates = {}
    champions = json.loads(CHAMPION_LIST.read_text(encoding="utf-8"))["data"].values()
    for champion in champions:
        path = ICON_DIR / f"{champion['id']}.png"
        image = cv2.imread(str(path)) if path.exists() else None
        if image is None:
            continue
        image = cv2.resize(image, (TEMPLATE_SIZE, TEMPLATE_SIZE), interpolation=cv2.INTER_AREA)
        templates[_key(champion["name"])] = cv2.bitwise_and(image, image, mask=mask)
    return templates


def find_rings(minimap_bgr: np.ndarray) -> list[Ring]:
    """Find team-coloured rings. Size limits are relative to the minimap, so they scale with it."""
    side = min(minimap_bgr.shape[:2])
    hsv = cv2.cvtColor(minimap_bgr, cv2.COLOR_BGR2HSV)
    rings: list[Ring] = []
    for team, ranges in TEAM_RANGES.items():
        mask = np.zeros(hsv.shape[:2], np.uint8)
        for low, high in ranges:
            mask |= cv2.inRange(hsv, np.array(low, np.uint8), np.array(high, np.uint8))
        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=2)
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        for index in range(1, count):
            x, y, w, h, area = stats[index]
            if not (0.05 * side <= w <= 0.2 * side and 0.05 * side <= h <= 0.2 * side):
                continue
            if not (0.6 <= w / h <= 1.6) or area < 0.01 * side * side:
                continue
            rings.append(Ring(team, int(x), int(y), int(w), int(h)))
    return rings


def _circle_mask() -> np.ndarray:
    mask = np.zeros((TEMPLATE_SIZE, TEMPLATE_SIZE), np.uint8)
    cv2.circle(mask, (TEMPLATE_SIZE // 2, TEMPLATE_SIZE // 2), TEMPLATE_SIZE // 2, 255, -1)
    return mask


PORTRAIT_SCALES = (0.4, 0.5, 0.6, 0.7, 0.8)


def _best_match(minimap_bgr: np.ndarray, ring: Ring, template: np.ndarray) -> float:
    """Slide the portrait over the ring's box at several sizes; the true size is not known in advance."""
    region = minimap_bgr[ring.y:ring.y + ring.h, ring.x:ring.x + ring.w]
    best = -1.0
    for fraction in PORTRAIT_SCALES:
        size = max(8, int(round(min(region.shape[:2]) * fraction)))
        if size > min(region.shape[:2]):
            continue
        scaled = cv2.resize(template, (size, size), interpolation=cv2.INTER_AREA)
        best = max(best, float(cv2.matchTemplate(region, scaled, cv2.TM_CCOEFF_NORMED).max()))
    return best


def read_minimap(minimap_bgr: np.ndarray, teams: dict[str, list[str]], *, now: float | None = None,
                 min_score: float = 0.7, min_margin: float = 0.15) -> list[Sighting]:
    """Name each ring from its team's five champions.

    A name is reported only when it scores at least min_score and beats the runner-up by min_margin.
    Anything weaker is reported with champion=None, so an unclear icon is never guessed.
    """
    stamp = time.time() if now is None else now
    side = min(minimap_bgr.shape[:2])
    templates = _templates()
    sightings = []
    for ring in find_rings(minimap_bgr):
        scores = []
        for name in teams.get(ring.team, []):
            template = templates.get(_key(name))
            if template is not None:
                scores.append((_best_match(minimap_bgr, ring, template), name))
        scores.sort(reverse=True)
        best_score, best_name = scores[0] if scores else (-1.0, None)
        runner_up = scores[1][0] if len(scores) > 1 else -1.0
        confident = best_score >= min_score and best_score - runner_up >= min_margin
        champion = best_name if confident else None
        sightings.append(Sighting(
            team=ring.team,
            champion=champion,
            x=round((ring.x + ring.w / 2) / side, 3),
            y=round((ring.y + ring.h / 2) / side, 3),
            score=round(best_score, 3),
            seen_at=stamp,
        ))
    return sightings


def grab(rect: tuple[int, int, int, int]) -> np.ndarray:
    """Capture a screen rectangle (x, y, w, h) as BGR."""
    import mss

    x, y, w, h = rect
    with mss.mss() as screen:
        shot = np.array(screen.grab({"left": x, "top": y, "width": w, "height": h}))
    return shot[:, :, :3].copy()


class MinimapWatcher(threading.Thread):
    """Reads the minimap a few times a second in the background. Enabled with COACH_MINIMAP=1."""

    def __init__(self, rect: tuple[int, int, int, int], teams_provider, interval: float = 0.5) -> None:
        super().__init__(name="coach-minimap", daemon=True)
        self.rect = rect
        self.teams_provider = teams_provider
        self.interval = interval
        self.latest: list[Sighting] = []
        self.latest_at = 0.0
        self.error: Exception | None = None
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                teams = self.teams_provider()
                if teams:
                    frame = grab(self.rect)
                    self.latest = read_minimap(frame, teams)
                    self.latest_at = time.time()
                self.error = None
            except Exception as exc:
                self.error = exc
            self._stop.wait(self.interval)

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self, max_age: float = 2.0) -> list[Sighting]:
        """Sightings from the last moment only; older readings are dropped, not reused."""
        return list(self.latest) if time.time() - self.latest_at <= max_age else []


def _parse_teams(text: str) -> dict[str, list[str]]:
    teams = {}
    for part in text.split("|"):
        team, _, names = part.partition(":")
        teams[team.strip().upper()] = [name.strip() for name in names.split(",") if name.strip()]
    return teams


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimap champion reader for League Coach")
    parser.add_argument("--fetch-icons", action="store_true")
    parser.add_argument("--calibrate", action="store_true", help="save a full-screen capture with the minimap box")
    parser.add_argument("--file", help="read a saved screenshot instead of the live screen")
    parser.add_argument("--rect", default=",".join(map(str, DEFAULT_RECT)))
    parser.add_argument("--teams", default="", help='e.g. "ORDER:Lucian,Nami|CHAOS:Jinx"')
    args = parser.parse_args()
    rect = tuple(int(v) for v in args.rect.split(","))

    if args.fetch_icons:
        ICON_DIR.mkdir(exist_ok=True)
        print(f"Downloaded {fetch_icons()} new portraits into {ICON_DIR.name}.")
        return
    if args.calibrate:
        import mss

        with mss.mss() as screen:
            shot = np.array(screen.grab(screen.monitors[1]))[:, :, :3].copy()
        x, y, w, h = rect
        cv2.rectangle(shot, (x, y), (x + w, y + h), (0, 255, 255), 2)
        cv2.imwrite("minimap_calibration.png", shot)
        print("Saved minimap_calibration.png; the yellow box should surround the minimap.")
        return
    if args.file:
        image = cv2.imread(args.file)
        if image is None:
            raise SystemExit(f"Could not read {args.file}")
        x, y, w, h = rect
        frame = image[y:y + h, x:x + w]
        for sighting in read_minimap(frame, _parse_teams(args.teams)):
            print(sighting)
        return
    raise SystemExit("Use --fetch-icons, --calibrate, or --file.")


if __name__ == "__main__":
    main()

