from __future__ import annotations

import json
from pathlib import Path
import unittest

from build_m9_second_person_fixture import build_fixture
from longitudinal_human_model.rolling import materialize_cutoff
from longitudinal_human_model.temporal import validate_temporal_dataset


ROOT=Path(__file__).resolve().parent


class M9SecondPersonFixtureTests(unittest.TestCase):
    def test_same_schema_new_person_and_new_texts(self):
        mira=build_fixture(); ren=json.loads((ROOT/"datasets/m8_rolling_semantic_synthetic_fixture_v1.json").read_text())
        self.assertEqual(ren["schema"],mira["schema"])
        self.assertEqual(ren["taxonomy"],mira["taxonomy"])
        self.assertEqual(ren["event_feature_names"],mira["event_feature_names"])
        self.assertNotEqual(ren["target"]["target_id"],mira["target"]["target_id"])
        self.assertFalse({r["observable_text"] for r in ren["events"]}&{r["observable_text"] for r in mira["events"]})

    def test_four_cutoffs_are_strict_and_second_person_only(self):
        mira=build_fixture()
        self.assertEqual(24,len(mira["events"]))
        for cutoff in ("E1","E2","E3","E4"):
            temporal=materialize_cutoff(mira,cutoff)
            report=validate_temporal_dataset(temporal)
            self.assertTrue(report["valid"])
            self.assertEqual("synthetic_mira",temporal["target"]["target_id"])

    def test_person_parameters_differ_without_schema_change(self):
        mira=build_fixture(); ren=json.loads((ROOT/"datasets/m8_rolling_semantic_synthetic_fixture_v1.json").read_text())
        self.assertEqual(set(ren["events"][0]["person_parameters"]),set(mira["events"][0]["person_parameters"]))
        self.assertNotEqual(ren["events"][0]["person_parameters"],mira["events"][0]["person_parameters"])
        self.assertFalse(mira["formal_target_claim"])


if __name__=="__main__": unittest.main()
