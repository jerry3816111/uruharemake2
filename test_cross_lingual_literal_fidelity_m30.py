import copy
import unittest

import uruha_literal_topic_fidelity_m30 as m30
from uruha_memory_observatory import render_memory_observatory


class CrossLingualLiteralFidelityM30Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol, cls.holdout, _, _ = m30.load_frozen_protocol()

    def test_frozen_protocol_hash_balance_and_case_counts(self):
        self.assertEqual(len(self.holdout["cases"]), 18)
        self.assertEqual(
            {language: sum(case["language"] == language for case in self.holdout["cases"])
             for language in ("zh", "en", "ja")},
            {"zh": 6, "en": 6, "ja": 6},
        )
        self.assertEqual(
            sum(case["authority_expected"] for case in self.holdout["cases"]),
            15,
        )

    def test_faithful_authority_requires_every_group_and_polarity(self):
        case = next(
            item for item in self.holdout["cases"]
            if item["case_id"] == "m30_en_time_10"
        )
        row = m30.score_case(
            case,
            {"status": "projection_candidate"},
            {
                "status": "projected_and_validated",
                "surface_authority": True,
                "subject_jp": "会議",
                "predicate_jp": "始まる",
                "time_jp": "8時30分",
                "literal_summary_jp": "会議は8時30分に始まる。",
                "response_jp": "会議、8時30分に始まるんだな。",
                "polarity": "affirmed",
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            },
        )
        self.assertEqual(row["outcome"], "faithful_authority")
        self.assertTrue(row["semantic_groups_passed"])
        self.assertTrue(row["polarity_passed"])

    def test_wrong_negation_with_surface_authority_is_false_authority(self):
        case = next(
            item for item in self.holdout["cases"]
            if item["case_id"] == "m30_en_negation_08"
        )
        row = m30.score_case(
            case,
            {"status": "projection_candidate"},
            {
                "status": "projected_and_validated",
                "surface_authority": True,
                "subject_jp": "店",
                "predicate_jp": "月曜日も開く",
                "literal_summary_jp": "店は月曜日も開く。",
                "response_jp": "月曜日も店は開くんだな。",
                "polarity": "affirmed",
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            },
        )
        self.assertEqual(row["outcome"], "false_authority")
        self.assertFalse(row["polarity_passed"])
        self.assertFalse(row["semantic_groups_passed"])

    def test_incomplete_noncandidate_is_true_abstention(self):
        case = next(
            item for item in self.holdout["cases"]
            if item["case_id"] == "m30_ja_incomplete_18"
        )
        row = m30.score_case(
            case,
            {"status": "not_candidate", "reason": "text_visible_hesitation"},
            {
                "status": "projection_not_attempted",
                "surface_authority": False,
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            },
        )
        self.assertEqual(row["outcome"], "true_abstention")

    def test_summary_keeps_false_authority_separate_from_false_reject(self):
        base = {
            "language": "zh",
            "authority_expected": True,
            "elapsed_seconds": 1.0,
            "raw_dialogue_persisted": False,
            "model_response_raw_persisted": False,
            "expected_polarity": "affirmed",
            "polarity_passed": True,
        }
        rows = []
        for language in ("zh", "en", "ja"):
            faithful = copy.deepcopy(base)
            faithful.update(language=language, outcome="faithful_authority")
            rejected = copy.deepcopy(base)
            rejected.update(language=language, outcome="false_reject")
            rows.extend([faithful, rejected])
        incomplete = copy.deepcopy(base)
        incomplete.update(
            language="zh",
            authority_expected=False,
            expected_polarity="unknown",
            outcome="true_abstention",
        )
        rows.append(incomplete)

        metrics, _gates = m30.summarize(
            rows,
            self.protocol["frozen_success_gates"],
        )
        self.assertEqual(metrics["outcome_counts"]["faithful_authority"], 3)
        self.assertEqual(metrics["outcome_counts"]["false_reject"], 3)
        self.assertNotIn("false_authority", metrics["outcome_counts"])

    def test_runtime_observatory_discloses_frozen_failure_not_only_m29_demo(self):
        html = render_memory_observatory({})
        self.assertIn("M30 · CROSS-LINGUAL SEMANTIC FIDELITY HOLDOUT", html)
        self.assertIn("FROZEN GATE · FAIL", html)
        self.assertIn("4/15", html)
        self.assertIn("fluent but wrong", html)


if __name__ == "__main__":
    unittest.main()
