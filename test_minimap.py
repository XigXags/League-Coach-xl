import unittest

import cv2
import numpy as np

import minimap_reader as mr


def synthetic_minimap(placements):
    """Draw coloured rings with real champion portraits inside, on a dark background."""
    canvas = np.full((236, 236, 3), 30, np.uint8)
    for (cx, cy), team, champion in placements:
        ring_colour = (255, 130, 0) if team == "ORDER" else (0, 0, 230)
        cv2.circle(canvas, (cx, cy), 16, ring_colour, 3)
        portrait = cv2.imread(str(mr.ICON_DIR / f"{champion}.png"))
        portrait = cv2.resize(portrait, (24, 24), interpolation=cv2.INTER_AREA)
        canvas[cy - 12:cy + 12, cx - 12:cx + 12] = portrait
    return canvas


@unittest.skipUnless((mr.ICON_DIR / "Ashe.png").exists(), "run --fetch-icons first")
class MinimapTests(unittest.TestCase):
    def test_rings_are_found_with_their_team_colour(self):
        frame = synthetic_minimap([((60, 60), "ORDER", "Ashe"), ((170, 150), "CHAOS", "Nami")])
        teams = sorted(ring.team for ring in mr.find_rings(frame))
        self.assertEqual(teams, ["CHAOS", "ORDER"])

    def test_icons_are_named_from_their_team_only(self):
        frame = synthetic_minimap([((60, 60), "ORDER", "Ashe"), ((170, 150), "CHAOS", "Nami")])
        found = {s.team: s for s in mr.read_minimap(frame, {"ORDER": ["Ashe"], "CHAOS": ["Nami"]}, now=0)}
        self.assertEqual(found["ORDER"].champion, "Ashe")
        self.assertEqual(found["CHAOS"].champion, "Nami")
        self.assertAlmostEqual(found["ORDER"].x, 60 / 236, places=2)
        self.assertAlmostEqual(found["CHAOS"].y, 150 / 236, places=2)

    def test_a_wrong_candidate_list_does_not_invent_a_name(self):
        frame = synthetic_minimap([((170, 150), "CHAOS", "Nami")])
        sighting = mr.read_minimap(frame, {"CHAOS": ["Lucian", "Jinx", "Ezreal", "Kayle", "Garen"]}, now=0)[0]
        self.assertIsNone(sighting.champion)

    def test_stale_watcher_readings_are_dropped(self):
        watcher = mr.MinimapWatcher(mr.DEFAULT_RECT, lambda: None)
        watcher.latest = [mr.Sighting("ORDER", "Ashe", 0.2, 0.2, 0.9, 0.0)]
        watcher.latest_at = 0.0
        self.assertEqual(watcher.snapshot(), [])


if __name__ == "__main__":
    unittest.main()
