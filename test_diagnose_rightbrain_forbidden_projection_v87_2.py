import json
import unittest

import diagnose_rightbrain_forbidden_projection_v87_2 as diagnosis
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87


class RightBrainForbiddenProjectionDiagnosisV872Tests(unittest.TestCase):
    def test_normalization_matches_runtime_forbidden_contract(self):
        self.assertEqual(diagnosis.normalized_forbidden([" 私 ", "", "私", "そうなんだ"]), ["私", "そうなんだ"])

    def test_unchanged_whitespace_case_is_classified_as_oracle_false_positive(self):
        normalized = ["私", "ちょっと手"]
        digest = v76.canonical_sha256(normalized)
        candidate = {
            "id": "private-case",
            "target_plan": {"must_avoid": ["私", "ちょっと手 "]},
        }
        condition = {
            "accepted": True,
            "rejection_reasons": [],
            "effective_forbidden_sha256": digest,
            "dropped_marker_count": 0,
        }
        row = {
            "candidate_id": "private-case",
            "projection_scope_matches": False,
            "conditions": {v87.C0: dict(condition), v87.T1: dict(condition)},
        }
        report = diagnosis.diagnose(
            [row],
            [candidate],
            {
                "decision": "inconclusive_effect_between_preregistered_gates",
                "summary": {"projection_scope_mismatch_count": 1},
            },
        )
        self.assertTrue(report["scope_mismatch_is_oracle_false_positive"])
        self.assertEqual(report["mismatches_with_zero_projection"], 1)
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("private-case", encoded)
        self.assertNotIn("ちょっと手", encoded)
        self.assertFalse(report["authorizations"]["production_default"])

    def test_actual_formal_decision_is_not_overridden(self):
        formal = json.loads(
            diagnosis.FORMAL_REPORT_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(formal["decision"], "inconclusive_effect_between_preregistered_gates")


if __name__ == "__main__":
    unittest.main()
