import hashlib
import json
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from run_typed_reflection_v3_development import CONTROL, TREATMENT
from typed_reflection_v3_core import decision_for, score_rows, summarize


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "typed_reflection_v3_development_preregistration.json"
DATASET = ROOT / "datasets" / "typed_reflection_v3_development_pilot.json"
LOCK = ROOT / "configs" / "typed_reflection_v3_harness_lock.json"
CLOSURE = ROOT / "configs" / "typed_reflection_v3_result_closure.json"


def successful_reply(case):
    first_required = case.get("behavior_first_clause_required_any") or []
    required = case.get("behavior_required_any") or []
    pieces = []
    if first_required:
        pieces.append(first_required[0])
    if required and required[0] not in pieces:
        pieces.append(required[0])
    return " ".join(pieces) or "普通の返事"


def perfect_rows():
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    rows = []
    for case in cases:
        expected_type = case["expected_reflection_type"]
        positive = expected_type != "none"
        records = []
        if positive:
            records = [
                {
                    "collection": case["expected_collection"],
                    "document": f"Reflection[{expected_type}]: {case['rule_required_any'][0]}",
                    "metadata": {"source": "typed_reflection"},
                }
            ]
        rows.append(
            {
                "case": case,
                "conditions": {
                    CONTROL: {"future_reply": "不符合必要標記"},
                    TREATMENT: {
                        "reflection_type_observed": expected_type,
                        "reflection_records": records,
                        "source_provenance_valid": positive,
                        "retrieved_typed_reflection": positive,
                        "future_reply": successful_reply(case),
                    },
                },
            }
        )
    return rows


class TypedReflectionV3HarnessTest(unittest.TestCase):
    def test_harness_lock_hashes_all_causal_inputs(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        self.assertEqual(lock["required_run_branch"], "main")
        self.assertEqual(tuple(lock["conditions"]), (CONTROL, TREATMENT))
        for relative, expected in lock["frozen_artifacts"].items():
            frozen_bytes = subprocess.check_output(
                ["git", "show", f"{closure['runner_commit']}:{relative}"],
                cwd=ROOT,
            )
            actual = hashlib.sha256(frozen_bytes).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_perfect_synthetic_result_passes_every_preregistered_gate(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        scored = score_rows(perfect_rows(), CONTROL, TREATMENT)
        summary = summarize(scored, config["success_gates"])
        self.assertTrue(summary["all_gates_pass"])
        self.assertEqual(
            decision_for(summary, config["decision_rule"]),
            config["decision_rule"]["all_gates_pass"],
        )

    def test_false_write_on_negative_control_forces_rejection(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = perfect_rows()
        negative = next(
            row
            for row in rows
            if row["case"]["expected_reflection_type"] == "none"
        )
        negative["conditions"][TREATMENT].update(
            {
                "reflection_type_observed": "semantic",
                "reflection_records": [
                    {
                        "collection": "wisdom",
                        "document": "Reflection[semantic]: invented",
                        "metadata": {"source": "typed_reflection"},
                    }
                ],
            }
        )
        summary = summarize(
            score_rows(deepcopy(rows), CONTROL, TREATMENT),
            config["success_gates"],
        )
        self.assertFalse(summary["no_rule_specificity"] == 1.0)
        self.assertEqual(
            decision_for(summary, config["decision_rule"]),
            config["decision_rule"]["any_safety_or_precision_gate_fails"],
        )


if __name__ == "__main__":
    unittest.main()
