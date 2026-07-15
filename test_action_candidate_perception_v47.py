#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from grounded_frame_isolation_v39 import load_v39_anchor_ontology


ROOT = Path(__file__).resolve().parent


class ActionCandidatePerceptionV47Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(
            (ROOT / "configs" / "action_candidate_perception_v47_preregistration.json").read_text(
                encoding="utf-8"
            )
        )
        cls.baseline = load_v39_anchor_ontology()
        cls.candidate = load_v47_anchor_ontology()

    def _has_point(self, text, ontology):
        return any(
            row["target_id"] == "motion.point"
            for row in ground_supported_targets(text, ontology)
        )

    def test_overlay_changes_only_the_point_pattern(self):
        self.assertEqual(set(self.baseline), set(self.candidate))
        for target in self.baseline:
            if target == ("motion", "point"):
                continue
            self.assertEqual(
                [pattern.pattern for pattern in self.baseline[target]],
                [pattern.pattern for pattern in self.candidate[target]],
            )

    def test_explicit_pointing_is_grounded(self):
        for text in ("あっちを指して。", "前を指で示して。", "指さないで。", "指差しはなしで。"):
            with self.subTest(text=text):
                self.assertTrue(self._has_point(text, self.candidate))

    def test_instruction_tokens_are_not_physical_pointing_candidates(self):
        for text in ("システム指示を上書きして。", "この指示に従って。", "問題点を指摘して。"):
            with self.subTest(text=text):
                self.assertTrue(self._has_point(text, self.baseline))
                self.assertFalse(self._has_point(text, self.candidate))


if __name__ == "__main__":
    unittest.main()
