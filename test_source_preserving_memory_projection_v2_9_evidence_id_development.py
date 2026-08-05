import copy
import json
import unittest

import build_source_preserving_memory_projection_v2_9_evidence_id_development as v29
from test_build_source_preserving_memory_projection_v2_5_locomo_cases import sample


def evidence_neighbor_sample(sample_id, prefix):
    row = sample(sample_id, prefix)
    row["conversation"]["session_1"] = [
        {
            "speaker": "B",
            "dia_id": f"{prefix}-anchor",
            "text": "A favorite fruit question and answer.",
        },
        {
            "speaker": "A",
            "dia_id": f"{prefix}-1",
            "text": "Mango, every Friday.",
        },
        {
            "speaker": "B",
            "dia_id": f"{prefix}-d1",
            "text": "favorite fruit question detail one",
        },
        {
            "speaker": "B",
            "dia_id": f"{prefix}-d2",
            "text": "favorite fruit question detail two",
        },
    ] + [
        {
            "speaker": "B",
            "dia_id": f"{prefix}-padding-{index}",
            "text": "unrelated background conversation with enough padding " * 3,
        }
        for index in range(8)
    ]
    return row


class EvidenceIdDevelopmentV29Tests(unittest.TestCase):
    def setUp(self):
        self.prereg = v29.load_preregistration()
        self.data = [
            evidence_neighbor_sample(f"sample-{index}", f"d{index}")
            for index in range(6)
        ]
        self.prereg["development_scope"]["exposed_sample_ids"] = [
            f"sample-{index}" for index in range(4)
        ]
        self.prereg["development_scope"][
            "exposed_sample_ids_sha256"
        ] = v29.v25.canonical_sha256(
            self.prereg["development_scope"]["exposed_sample_ids"]
        )
        self.prereg["success_gates"]["eligible_case_count_at_least"] = 12

    def test_official_evidence_ids_define_eligibility_without_answer_text(self):
        modified = copy.deepcopy(self.data[0])
        for qa in modified["qa"]:
            qa["answer"] = "not present in any dialogue turn"
        eligible = v29.eligible_cases(modified, self.prereg)
        self.assertEqual(len(eligible), 3)

    def test_missing_or_cross_session_evidence_is_ineligible(self):
        missing = copy.deepcopy(self.data[0])
        missing["qa"][0]["evidence"] = ["missing"]
        self.assertEqual(len(v29.eligible_cases(missing, self.prereg)), 2)
        cross_session = copy.deepcopy(self.data[0])
        cross_session["qa"][0]["evidence"] = ["d0-1", "d0-4"]
        self.assertEqual(len(v29.eligible_cases(cross_session, self.prereg)), 2)

    def test_adjacency_recovers_neighbor_evidence_and_passes_synthetic_gates(self):
        report = v29.build_report(self.data, self.prereg)
        self.assertEqual(report["metrics"]["eligible_case_count"], 12)
        self.assertEqual(report["metrics"]["isolated_micro_evidence_recall"], 0.0)
        self.assertEqual(report["metrics"]["adjacency_micro_evidence_recall"], 1.0)
        self.assertTrue(all(report["gates"].values()))
        self.assertEqual(
            report["decision"],
            "development_pass_authorize_final_reserve_preregistration_only",
        )

    def test_report_contains_no_official_text_answers_or_evidence_ids(self):
        report = v29.build_report(self.data, self.prereg)
        payload = json.dumps(report)
        self.assertNotIn("Mango, every Friday", payload)
        self.assertNotIn("not present in any dialogue turn", payload)
        for case in report["cases"]:
            self.assertNotIn("question", case)
            self.assertNotIn("answer", case)
            self.assertNotIn("evidence_ids", case)
            self.assertNotIn("text", case)

    def test_unscoped_payload_cannot_change_development_result(self):
        original = v29.build_report(self.data, self.prereg)
        modified = copy.deepcopy(self.data)
        for row in modified[4:]:
            row["conversation"] = {}
            row["qa"] = []
        rebuilt = v29.build_report(modified, self.prereg)
        self.assertEqual(original, rebuilt)

    def test_frozen_dependencies_match_and_drift_is_rejected(self):
        v29.verify_frozen_dependencies(self.prereg)
        drifted = copy.deepcopy(self.prereg)
        drifted["frozen_sources"]["v2_8_report_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen source hash drift"):
            v29.verify_frozen_dependencies(drifted)

    def test_model_runtime_and_final_reserve_are_not_authorized(self):
        authorization = self.prereg["authorization"]
        self.assertTrue(authorization["run_exposed_development_analysis_once_after_merge"])
        self.assertFalse(authorization["preregister_final_reserve_validation"])
        self.assertFalse(authorization["access_final_reserve_case_selection_payload"])
        self.assertFalse(authorization["run_model_generation"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])


if __name__ == "__main__":
    unittest.main()
