"""Champion kit text: built from Data Dragon once, read locally. No test here touches the network."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_champion_kits
import champion_metadata
from build_champion_kits import clean


class CleanTests(unittest.TestCase):
    def test_markup_entities_and_templates_are_removed(self):
        raw = ("<mainText><stats></stats>Zac&#39;s body <font color='#FFF'>stretches</font>.<br><br />It deals "
               "{{ totaldamage }} damage &amp; slows.  <keywordMajor>Bounce</keywordMajor>  twice.</mainText>")
        self.assertEqual(clean(raw), "Zac's body stretches. It deals damage & slows. Bounce twice.")
        self.assertEqual(clean(""), "")
        self.assertEqual(clean(None), "")
        self.assertEqual(clean("Attacks infect the target %i:OnHit% On-Hit, dealing damage."),
                         "Attacks infect the target On-Hit, dealing damage.")

    def test_a_title_is_not_a_sentence_end(self):
        text = "Dr. Mundo throws a saw. Dr. Mundo heals a lot when he hits something big."
        self.assertEqual(clean(text, limit=40), "Dr. Mundo throws a saw.")
        self.assertEqual(clean(text, limit=30), "Dr. Mundo throws a saw.")
        self.assertEqual(champion_metadata._first_sentence(text), "Dr. Mundo throws a saw.")

    def test_a_long_text_is_cut_at_the_last_sentence_that_fits(self):
        text = "First sentence here. Second sentence is here too! Third one runs on and on and on."
        self.assertEqual(clean(text, limit=60), "First sentence here. Second sentence is here too!")
        self.assertEqual(clean(text, limit=30), "First sentence here.")
        self.assertEqual(clean("one two three four five", limit=12), "one two")
        self.assertEqual(clean(text, limit=500), text)

    def test_a_kit_keeps_names_and_descriptions_and_no_numbers(self):
        detail = {"tags": ["Tank"], "partype": "Mana", "stats": {"hp": 600},
                  "passive": {"name": "P", "description": "Passive <b>text</b>."},
                  "spells": [{"name": name, "description": f"{name} does it.", "tooltip": "{{ damage }} secret",
                              "cooldown": [9, 8], "cost": [50], "range": [600]} for name in "ABCD"]}
        kit = build_champion_kits.kit(detail)
        self.assertEqual(kit, {"tags": ["Tank"], "resource": "Mana", "passive": {"name": "P", "text": "Passive text."},
                               "spells": {key: {"name": name, "text": f"{name} does it."}
                                          for key, name in zip("QWER", "ABCD")}})
        self.assertNotIn("secret", json.dumps(kit))

    def test_the_build_uses_only_the_pinned_data_dragon_version(self):
        self.assertEqual(build_champion_kits.DDRAGON_VERSION, "16.19.1")
        self.assertTrue(build_champion_kits.DETAIL_URL.startswith("https://ddragon.leagueoflegends.com/cdn/"))


class KitFileTests(unittest.TestCase):
    def test_the_built_file_covers_every_champion_in_the_list(self):
        kits = json.loads(champion_metadata.KITS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(kits), 173)
        self.assertEqual({champion_metadata._normal(name) for name in kits}, set(champion_metadata.known_champions()))
        for name, kit in kits.items():
            self.assertEqual(set(kit), {"tags", "resource", "passive", "spells"}, name)
            self.assertEqual(list(kit["spells"]), sorted(kit["spells"]), name)
            self.assertEqual(set(kit["spells"]), set("QWER"), name)
            self.assertEqual(kit["tags"], champion_metadata.champion_tags(name), name)
            for ability in (kit["passive"], *kit["spells"].values()):
                self.assertEqual(set(ability), {"name", "text"}, name)
                self.assertLessEqual(len(ability["text"]), 220, name)
                for mark in ("<", ">", "{{", "}}", "&amp;", "&nbsp;", "%i:"):
                    self.assertNotIn(mark, ability["text"], name)
                self.assertFalse(ability["text"].endswith(" Dr."), name)

    def test_every_summary_fits_and_names_the_kit(self):
        kits = json.loads(champion_metadata.KITS_FILE.read_text(encoding="utf-8"))
        for name, kit in kits.items():
            summary = champion_metadata.kit_summary(name)
            self.assertTrue(0 < len(summary) <= 420, name)
            self.assertTrue(summary.startswith(f"{name} ("), name)
            self.assertIn(f"Passive {kit['passive']['name']}", summary, name)
            for key in "QWER":
                self.assertIn(f"{key} {kit['spells'][key]['name']}", summary, name)
            self.assertLessEqual(len(champion_metadata.kit_summary(name, limit=150)), 150, name)
            self.assertNotRegex(summary, r"Dr\.(?! Mundo)", name)   # no ability cut down to a bare title
            short = champion_metadata.kit_summary(name, names_only=True)
            self.assertLessEqual(len(short), len(summary), name)
            self.assertIn(f"R {kit['spells']['R']['name']}", short, name)

    def test_a_summary_reads_as_tags_resource_then_abilities(self):
        self.assertEqual(champion_metadata.champion_kit("belveth")["passive"]["name"], "Death in Lavender")
        self.assertTrue(champion_metadata.kit_summary("Bel'Veth").startswith(
            "Bel'Veth (Fighter; no resource). Passive Death in Lavender: "))
        zac = champion_metadata.kit_summary("Zac")
        self.assertTrue(zac.startswith("Zac (Tank, Fighter; no resource). Passive Cell Division: "), zac)
        self.assertIn(" Q Stretching Strikes: Zac stretches an arm, grabbing an enemy. W Unstable Matter", zac)
        self.assertIn("(Marksman, Support; Mana)", champion_metadata.kit_summary("Ashe"))
        self.assertEqual(champion_metadata.kit_summary("Zac", names_only=True),
                         "Zac (Tank, Fighter; no resource). Passive Cell Division. Q Stretching Strikes. "
                         "W Unstable Matter. E Elastic Slingshot. R Let's Bounce!.")

    def test_a_missing_champion_or_file_gives_an_empty_summary(self):
        self.assertEqual(champion_metadata.kit_summary("Not A Champion"), "")
        self.assertEqual(champion_metadata.kit_summary(None), "")
        self.assertIsNone(champion_metadata.champion_kit(""))
        with patch.object(champion_metadata, "KITS_FILE", Path(__file__).with_name("no-such-kits.json")):
            champion_metadata._kits.cache_clear()
            try:
                self.assertEqual(champion_metadata.kit_summary("Zac"), "")
                self.assertIsNone(champion_metadata.champion_kit("Zac"))
            finally:
                champion_metadata._kits.cache_clear()
        self.assertTrue(champion_metadata.kit_summary("Zac"))

    def test_an_entry_of_the_wrong_shape_is_no_kit_and_no_crash(self):
        good = {"tags": ["Tank"], "resource": "", "passive": {"name": "P", "text": "Does it."}, "spells": {}}
        bad = {"A": {**good, "passive": "x"}, "B": {**good, "spells": {"Q": "x"}}, "C": {**good, "tags": [1]},
               "D": {**good, "tags": "Tank"}, "E": good}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "kits.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with patch.object(champion_metadata, "KITS_FILE", path):
                champion_metadata._kits.cache_clear()
                try:
                    self.assertEqual([champion_metadata.kit_summary(name) for name in "ABC"], ["", "", ""])
                    self.assertEqual(champion_metadata.kit_summary("D"), "D (no resource). Passive P: Does it.")
                    self.assertEqual(champion_metadata.kit_summary("E"), "E (Tank; no resource). Passive P: Does it.")
                finally:
                    champion_metadata._kits.cache_clear()


if __name__ == "__main__":
    unittest.main()
