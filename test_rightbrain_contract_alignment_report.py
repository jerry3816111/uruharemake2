import unittest

from build_rightbrain_contract_alignment_report import build_report


def source(adapter, raw, selected, contract=None):
    return {
        "path": type("PathRef", (), {"name": f"{adapter}.json"})(),
        "sha256": f"sha-{adapter}-{raw}-{selected}",
        "payload": {
            "adapter_ref": adapter,
            "runtime_contract_version": contract,
            "dataset_sha256": "dataset-sha",
            "seed": 42,
            "case_state_reset": True,
            "candidate_count_per_enabled_case": 3,
            "summary": {
                "generated_candidate_count": 18,
                "raw_candidate_acceptance_rate": raw,
                "model_selected_case_rate": selected,
                "final_contract_pass_rate": 1.0,
                "final_language_clean_rate": 1.0,
                "fallback_protection_rate": 1.0,
                "rejection_reason_counts": {},
            },
        },
    }


class RightBrainContractAlignmentReportTest(unittest.TestCase):
    def test_report_keeps_best_observed_separate_from_default_qualification(self):
        before = {
            "V10": source("v10", 0.0, 0.0),
            "V5": source("v5", 0.05, 0.1),
        }
        after = {
            "V10": source("v10", 0.05, 0.0, "plan_surface_contract_v1"),
            "V5": source("v5", 0.11, 0.0, "plan_surface_contract_v1"),
        }

        report = build_report(before, after)

        self.assertEqual(report["best_observed_after"]["label"], "V5")
        self.assertEqual(report["qualified_default_adapters"], [])
        self.assertFalse(report["default_adapter_change_recommended"])

    def test_report_rejects_unmatched_trials(self):
        before = {"V10": source("v10", 0.0, 0.0)}
        after = {"V10": source("v10", 0.1, 0.0, "plan_surface_contract_v1")}
        after["V10"]["payload"]["seed"] = 99

        with self.assertRaisesRegex(ValueError, "not matched trials"):
            build_report(before, after)


if __name__ == "__main__":
    unittest.main()
