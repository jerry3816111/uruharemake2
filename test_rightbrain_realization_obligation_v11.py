import copy
import json
import unittest
from pathlib import Path

import public_persona_missing_role_v8 as role_schema
import rightbrain_realization_obligation_v11 as v11
import run_public_persona_contract_v3_development as v3_runner
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"


class RealizationObligationV11Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        cls.right_brain = RightBrain(load_model=False)

    def payload(self, case):
        return v3_runner.build_payload(
            self.right_brain, case, v3_runner.CONDITIONS[0]
        )[2]

    def test_contract_is_generic_ascii_metadata(self):
        serialized = json.dumps(v11.OBLIGATION, ensure_ascii=False, sort_keys=True)
        self.assertTrue(serialized.isascii())
        self.assertNotIn("reply", serialized.lower().replace("natural_reply", ""))

    def test_projection_changes_only_one_field(self):
        for case in self.dataset["cases"]:
            control = self.payload(case)
            treatment = v11.project(control)
            self.assertEqual(v11.remove(treatment), control)
            self.assertEqual(
                treatment["leftbrain_plan"][v11.FIELD], v11.OBLIGATION
            )

    def test_existing_content_and_semantics_are_identical(self):
        for case in self.dataset["cases"]:
            control = self.payload(case)
            treatment = v11.project(control)
            self.assertEqual(
                treatment["leftbrain_plan"]["content_units"],
                control["leftbrain_plan"]["content_units"],
            )
            self.assertEqual(
                treatment["required_marker_groups"], control["required_marker_groups"]
            )

    def test_added_field_contains_no_role_scorer_markers(self):
        serialized = json.dumps(v11.OBLIGATION, ensure_ascii=False)
        markers = {
            marker
            for role_items in role_schema.ROLE_SCHEMAS.values()
            for role in role_items
            for marker in role["evidence_markers"]
        }
        self.assertFalse(any(marker in serialized for marker in markers))

    def test_projection_does_not_mutate_input(self):
        control = self.payload(self.dataset["cases"][0])
        before = copy.deepcopy(control)
        v11.project(control)
        self.assertEqual(control, before)

    def test_all_cases_have_existing_content_units(self):
        self.assertEqual(
            sum(bool(self.payload(case)["leftbrain_plan"]["content_units"])
                for case in self.dataset["cases"]),
            20,
        )


if __name__ == "__main__":
    unittest.main()
