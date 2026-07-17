import hashlib
import json
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from run_typed_reflection_v4_development import CONTROL, TREATMENT
from typed_reflection_v4_core import decision_for, score_rows, summarize


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "typed_reflection_v4_development_preregistration.json"
DATASET = ROOT / "datasets" / "typed_reflection_v4_development_pilot.json"
LOCK = ROOT / "configs" / "typed_reflection_v4_harness_lock.json"
CLOSURE = ROOT / "configs" / "typed_reflection_v4_result_closure.json"


def successful_reply(case):
    first = case.get("behavior_first_clause_required_any") or []
    required = case.get("behavior_required_any") or []
    terms = ([first[0]] if first else []) + ([required[0]] if required else [])
    return " ".join(dict.fromkeys(terms)) or "普通の返事"


def perfect_rows():
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    rows = []
    for case in cases:
        expected_type = case["expected_reflection_type"]
        positive = expected_type != "none"
        reflection = {}
        records = []
        if positive:
            reflection = {
                "extraction_version": "v4_structured_grounded",
                "attempt_count": 1,
                "validation_reasons": [],
            }
            records = [
                {
                    "collection": case["expected_collection"],
                    "document": f"Reflection[{expected_type}]: {case['rule_required_any'][0]}",
                    "metadata": {
                        "source": "typed_reflection",
                        "extraction_version": "v4_structured_grounded",
                    },
                }
            ]
        rows.append(
            {
                "case": case,
                "conditions": {
                    CONTROL: {"future_reply": "不符合必要標記"},
                    TREATMENT: {
                        "reflection_type_observed": expected_type,
                        "reflection_return": reflection,
                        "reflection_records": records,
                        "source_provenance_valid": positive,
                        "retrieved_typed_reflection": positive,
                        "future_reply": successful_reply(case),
                    },
                },
            }
        )
    return rows


class TypedReflectionV4HarnessTest(unittest.TestCase):
    def test_harness_lock_hashes_all_v4_causal_inputs(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
        self.assertEqual(lock["required_run_branch"], "main")
        self.assertEqual(tuple(lock["conditions"]), (CONTROL, TREATMENT))
        for relative, expected in lock["frozen_artifacts"].items():
            frozen_bytes = subprocess.check_output(
                ["git", "show", f"{closure['runner_commit']}:{relative}"],
                cwd=ROOT,
            )
            self.assertEqual(hashlib.sha256(frozen_bytes).hexdigest(), expected, relative)

    def test_perfect_synthetic_result_passes_every_gate(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        summary = summarize(
            score_rows(perfect_rows(), CONTROL, TREATMENT), config["success_gates"]
        )
        self.assertTrue(summary["all_gates_pass"])
        self.assertEqual(
            decision_for(summary, config["decision_rule"]),
            config["decision_rule"]["all_gates_pass"],
        )

    def test_language_quality_failure_forces_rejection(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = deepcopy(perfect_rows())
        positive = next(
            row for row in rows if row["case"]["expected_reflection_type"] != "none"
        )
        positive["conditions"][TREATMENT]["reflection_return"][
            "validation_reasons"
        ] = ["source_external_language"]
        summary = summarize(
            score_rows(rows, CONTROL, TREATMENT), config["success_gates"]
        )
        self.assertFalse(summary["japanese_surface_quality_rate"] == 1.0)
        self.assertEqual(
            decision_for(summary, config["decision_rule"]),
            config["decision_rule"]["any_safety_or_precision_gate_fails"],
        )


if __name__ == "__main__":
    unittest.main()
