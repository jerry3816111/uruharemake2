#!/usr/bin/env python3

import unittest

from analyze_commitment_carrier_v44_probe import analyze, evaluate_gate
from commitment_carrier_v44 import CARRIERS


class AnalyzeCommitmentCarrierV44ProbeTests(unittest.TestCase):
    def test_gate_requires_every_format_property(self):
        summary = {
            "parse_success_rate": 1.0,
            "source_label_fidelity": 1.0,
            "single_result_rate": 1.0,
            "unexpected_content_rate": 0.0,
            "p95_latency_seconds": 1.0,
        }
        targets = {
            "parse_success_rate": 1.0,
            "source_label_fidelity": 1.0,
            "single_result_rate": 1.0,
            "unexpected_content_rate": 0.0,
            "p95_latency_seconds_at_most": 4.0,
        }
        self.assertTrue(evaluate_gate(summary, targets)["passed"])
        summary["source_label_fidelity"] = 0.99
        self.assertEqual(evaluate_gate(summary, targets)["failed_checks"], ["source_label_fidelity"])

    def test_selection_uses_lowest_median_among_eligible_carriers(self):
        rows = []
        for index, carrier in enumerate(CARRIERS):
            for case_index in range(2):
                rows.append(
                    {
                        "carrier": carrier,
                        "case_id": f"{carrier}-{case_index}",
                        "source_label": "requested",
                        "result": {
                            "parsed": {
                                "parse_success": True,
                                "commitment": "requested",
                                "single_result": True,
                                "unexpected_content": False,
                            },
                            "response_metrics": {"wall_seconds": 0.5 + index},
                            "response_message": {},
                        },
                    }
                )
        config = {
            "stage_1_format_probe": {
                "gates": {
                    "parse_success_rate": 1.0,
                    "source_label_fidelity": 1.0,
                    "single_result_rate": 1.0,
                    "unexpected_content_rate": 0.0,
                    "p95_latency_seconds_at_most": 4.0,
                },
                "selection_rule": "fixed",
            }
        }
        result = analyze({"evidence_status": "test", "probe_rows": rows}, config)
        self.assertEqual(result["selected_carrier"], CARRIERS[0])


if __name__ == "__main__":
    unittest.main()
