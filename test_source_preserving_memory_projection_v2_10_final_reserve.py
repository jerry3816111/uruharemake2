import copy
import json
import unittest

import build_source_preserving_memory_projection_v2_10_final_reserve as v210
from test_source_preserving_memory_projection_v2_9_evidence_id_development import (
    evidence_neighbor_sample,
)


class FinalReserveV210Tests(unittest.TestCase):
    def setUp(self):
        self.prereg = v210.load_preregistration()
        self.data = [
            evidence_neighbor_sample(f"sample-{index}", f"d{index}")
            for index in range(6)
        ]
        self.prereg["frozen_partition"]["excluded_exposed_sample_ids"] = [
            f"sample-{index}" for index in range(4)
        ]
        self.prereg["frozen_partition"]["fresh_holdout_conversation_count"] = 0
        self.prereg["frozen_partition"]["final_reserve_conversation_count"] = 2
        ordered = sorted(
            self.data[4:],
            key=lambda row: v210.partition_digest(row["sample_id"], self.prereg),
        )
        final_ids = [row["sample_id"] for row in ordered]
        self.prereg["frozen_partition"][
            "final_reserve_sample_ids_sha256"
        ] = v210.v25.canonical_sha256(final_ids)
        self.prereg["success_gates"]["eligible_case_count_at_least"] = 6

    def test_final_partition_is_deterministic_and_hash_locked(self):
        final, ids = v210.final_reserve_samples(self.data, self.prereg)
        reversed_final, reversed_ids = v210.final_reserve_samples(
            list(reversed(self.data)), self.prereg
        )
        self.assertEqual(ids, reversed_ids)
        self.assertEqual([row["sample_id"] for row in final], ids)
        self.assertEqual([row["sample_id"] for row in reversed_final], ids)

    def test_final_report_passes_synthetic_contract_and_uses_aliases(self):
        report = v210.build_report(self.data, self.prereg)
        self.assertTrue(all(report["gates"].values()))
        self.assertEqual(report["metrics"]["eligible_case_count"], 6)
        self.assertEqual(report["metrics"]["isolated_micro_evidence_recall"], 0.0)
        self.assertEqual(report["metrics"]["adjacency_micro_evidence_recall"], 1.0)
        self.assertEqual(
            report["metrics"]["final_reserve_evaluation_payload_access_count"], 2
        )
        self.assertEqual(
            report["decision"],
            "final_reserve_pass_authorize_independent_model_preregistration_only",
        )
        self.assertEqual(
            {case["sample_id"] for case in report["cases"]},
            {"final-reserve-1", "final-reserve-2"},
        )

    def test_exposed_payload_cannot_change_final_result(self):
        original = v210.build_report(self.data, self.prereg)
        modified = copy.deepcopy(self.data)
        for row in modified[:4]:
            row["conversation"] = {}
            row["qa"] = []
        rebuilt = v210.build_report(modified, self.prereg)
        self.assertEqual(original, rebuilt)

    def test_report_excludes_raw_final_ids_and_official_content(self):
        _final, final_ids = v210.final_reserve_samples(self.data, self.prereg)
        report = v210.build_report(self.data, self.prereg)
        payload = json.dumps(report)
        for sample_id in final_ids:
            self.assertNotIn(sample_id, payload)
        self.assertNotIn("Mango, every Friday", payload)
        for case in report["cases"]:
            self.assertNotIn("question", case)
            self.assertNotIn("answer", case)
            self.assertNotIn("evidence_ids", case)
            self.assertNotIn("text", case)

    def test_frozen_dependencies_match_and_drift_is_rejected(self):
        v210.verify_frozen_dependencies(self.prereg)
        drifted = copy.deepcopy(self.prereg)
        drifted["development_authorization"]["v2_9_report_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen source hash drift"):
            v210.verify_frozen_dependencies(drifted)

    def test_only_one_final_evaluation_is_authorized(self):
        authorization = self.prereg["authorization"]
        self.assertTrue(authorization["evaluate_final_reserve_payload_once_after_merge"])
        self.assertFalse(authorization["preregister_independent_model_evaluation"])
        self.assertFalse(authorization["run_model_generation"])
        self.assertFalse(authorization["runtime_change"])
        self.assertFalse(authorization["runtime_shadow"])
        self.assertFalse(authorization["production_enablement"])


if __name__ == "__main__":
    unittest.main()
