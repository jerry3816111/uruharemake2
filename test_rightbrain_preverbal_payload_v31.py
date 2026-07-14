import json
import unittest
from copy import deepcopy
from pathlib import Path

from rightbrain_on_policy_dev_cases_v29 import case_inputs, validate_cases
from rightbrain_preverbal_payload_v31 import (
    CONDITION_FACTORS,
    build_payload_variant,
)
from run_rightbrain_preverbal_payload_v31 import (
    _build_v31_rightbrain_class,
    compare_control_to_v30,
    load_control_binding,
    load_preregistration,
    verify_frozen_sources,
)


ROOT = Path(__file__).resolve().parent


class RightBrainPreverbalPayloadV31Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from uruha_brain_mac import RightBrain

        cls.rightbrain = RightBrain(load_model=False)
        cls.cases = case_inputs()
        cls.preregistration = load_preregistration()
        cls.control_binding = load_control_binding()

    def _control_payload(self, case):
        return self.rightbrain._build_model_surface_payload(
            deepcopy(case["logic"]),
            deepcopy(case["psyche"]),
            48,
            memory_data=deepcopy(case["memory_data"]),
        )

    def test_preregistered_sources_and_case_shape_are_frozen(self):
        checks = verify_frozen_sources(
            self.preregistration,
            self.control_binding,
        )
        self.assertTrue(all(checks.values()), checks)
        validation = validate_cases(self.cases)
        self.assertTrue(validation["valid"], validation)
        self.assertEqual(validation["case_count"], 12)
        self.assertEqual(validation["source_family_count"], 12)
        self.assertEqual(validation["category_count"], 9)

    def test_factorial_conditions_match_preregistration(self):
        registered = self.preregistration["design"]["conditions"]
        self.assertEqual(set(registered), set(CONDITION_FACTORS))
        for condition, factors in CONDITION_FACTORS.items():
            self.assertEqual(
                registered[condition]["instruction_label_language"],
                factors["instruction_label_language"],
            )
            self.assertEqual(
                registered[condition]["serialization"],
                factors["serialization"],
            )

    def test_control_is_byte_exact_for_every_case(self):
        for case in self.cases:
            control = self._control_payload(case)
            variant = build_payload_variant(control, "mixed_json_control")
            self.assertEqual(variant.text, control, case["id"])
            self.assertTrue(variant.metadata["representation_integrity_pass"])

    def test_all_variants_preserve_the_canonical_leaf_contract(self):
        for case in self.cases:
            control = self._control_payload(case)
            variants = {
                condition: build_payload_variant(control, condition)
                for condition in CONDITION_FACTORS
            }
            canonical_hashes = {
                row.metadata["canonical_payload_sha256"]
                for row in variants.values()
            }
            self.assertEqual(len(canonical_hashes), 1, case["id"])
            for condition, row in variants.items():
                self.assertTrue(
                    row.metadata["representation_integrity_pass"],
                    (case["id"], condition, row.metadata),
                )
                self.assertEqual(
                    row.metadata["canonical_leaf_count"],
                    row.metadata["represented_leaf_count"],
                )

    def test_japanese_variants_remove_known_ascii_instruction_vocabulary(self):
        for case in self.cases:
            control = self._control_payload(case)
            for condition in ("japanese_json", "japanese_lines"):
                row = build_payload_variant(control, condition)
                self.assertEqual(
                    row.metadata["unmapped_ascii_values"],
                    [],
                    (case["id"], condition),
                )
                self.assertTrue(row.metadata["translation_roundtrip_matches"])

    def test_context_sensitive_casual_translation_keeps_scene_and_style_distinct(self):
        case = next(row for row in self.cases if row["id"] == "v29_food_mood")
        translated = json.loads(
            build_payload_variant(
                self._control_payload(case),
                "japanese_json",
            ).text
        )
        plan = translated["左脳の発話計画"]
        self.assertEqual(plan["場面"], "日常場面")
        self.assertIn("くだけた口調", plan["話し方"])

    def test_line_conditions_are_not_json_and_keep_required_meaning(self):
        for case in self.cases:
            control = json.loads(self._control_payload(case))
            meaning = control["leftbrain_plan"]["meaning"]
            for condition in ("mixed_lines", "japanese_lines"):
                row = build_payload_variant(
                    json.dumps(control, ensure_ascii=False, separators=(",", ":")),
                    condition,
                )
                with self.assertRaises(json.JSONDecodeError):
                    json.loads(row.text)
                self.assertIn("\n", row.text)
                self.assertIn(meaning, row.text)

    def test_frozen_v30_report_reproduces_its_own_control_sequence(self):
        for entry in self.control_binding["frozen_v30_control_reports"]:
            report = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
            comparison = compare_control_to_v30(
                report,
                self.control_binding,
            )
            self.assertTrue(comparison["raw_candidate_sequences_match"])
            self.assertEqual(comparison["mismatches"], [])

    def test_control_sequence_tampering_is_detected(self):
        entry = self.control_binding["frozen_v30_control_reports"][0]
        report = json.loads((ROOT / entry["path"]).read_text(encoding="utf-8"))
        first_case = report["cases"][0]
        if first_case["model_initial_rejected_candidates"]:
            first_case["model_initial_rejected_candidates"][0]["raw_candidate"] += "改変"
        else:
            first_case["model_accepted_candidates"][0]["raw_candidate"] += "改変"
        comparison = compare_control_to_v30(report, self.control_binding)
        self.assertFalse(comparison["raw_candidate_sequences_match"])
        self.assertIn(first_case["id"], comparison["mismatches"])

    def test_payload_metadata_is_published_inside_existing_model_trace(self):
        control = self._control_payload(self.cases[0])

        class FakeBase:
            tokenizer = staticmethod(
                lambda text, add_special_tokens=False: {"input_ids": list(text)}
            )

            def _build_model_surface_payload(self, *args, **kwargs):
                return control

        variant_class = _build_v31_rightbrain_class(
            FakeBase,
            "mixed_json_control",
        )
        logic = {"model_surface_candidate_trace": {}}
        result = variant_class()._build_model_surface_payload(
            logic,
            {},
            48,
            memory_data={},
        )
        self.assertEqual(result, control)
        published = logic["model_surface_candidate_trace"][
            "preverbal_payload_v31"
        ]
        self.assertTrue(published["representation_integrity_pass"])
        self.assertTrue(published["control_exact_text_matches"])
        self.assertGreater(published["rendered_token_count"], 0)


if __name__ == "__main__":
    unittest.main()
