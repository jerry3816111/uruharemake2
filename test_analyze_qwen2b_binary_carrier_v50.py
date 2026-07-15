#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from analyze_qwen2b_binary_carrier_v50 import analyze, evaluate_gate


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads(
    (ROOT / "configs" / "qwen2b_binary_carrier_v50_preregistration.json").read_text(
        encoding="utf-8"
    )
)


def _result(decision):
    return {
        "parsed": {
            "parse_success": True,
            "errors": [],
            "decision": decision,
            "result_count": 1,
            "single_result": True,
            "unexpected_content": False,
        },
        "response_message": {"content": ""},
        "response_metrics": {"wall_seconds": 0.1},
    }


class AnalyzeQwen2BBinaryCarrierV50Tests(unittest.TestCase):
    def test_fidelity_is_an_independent_gate(self):
        summary = {
            "parse_success_rate": 1.0,
            "source_decision_fidelity": 0.5,
            "single_result_rate": 1.0,
            "unexpected_content_rate": 0.0,
            "p95_latency_seconds": 1.0,
        }
        gate = evaluate_gate(summary, CONFIG["gates"])
        self.assertFalse(gate["passed"])
        self.assertIn("source_decision_fidelity", gate["failed_checks"])

    def test_selection_ignores_boolean_control_even_when_it_passes(self):
        rows = []
        decisions = ["execute", "do_not_execute"] * 6
        for carrier in CONFIG["carrier_order"]:
            for index, decision in enumerate(decisions):
                result = _result(decision)
                if carrier != "boolean_two_field_control":
                    result["parsed"]["parse_success"] = False
                    result["parsed"]["errors"] = ["synthetic_failure"]
                rows.append(
                    {
                        "carrier": carrier,
                        "case_id": f"case-{index}",
                        "source_decision": decision,
                        "result": result,
                    }
                )
        raw = {
            "completed_at": "synthetic",
            "evidence_status": "synthetic",
            "probe_rows": rows,
        }
        analysis = analyze(raw, CONFIG)
        self.assertTrue(analysis["carrier_gates"]["boolean_two_field_control"]["passed"])
        self.assertIsNone(analysis["selected_carrier"])
        self.assertFalse(analysis["v51_fresh_holdout_construction_authorized"])


if __name__ == "__main__":
    unittest.main()
