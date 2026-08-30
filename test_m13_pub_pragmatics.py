from __future__ import annotations

import json
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from longitudinal_human_model.pub_pragmatics import (
    CONDITIONS,
    audit_payload_contract,
    build_case_manifest,
    build_prompt,
    deterministic_case_ids,
    load_task_rows,
    paired_accuracy_comparison,
    parse_answer_index,
    summarize_rows,
)


ROOT = Path(__file__).resolve().parent


class PubPragmaticsTests(unittest.TestCase):
    def test_source_archive_loader_and_hash_rank_are_deterministic(self):
        rows = [
            {"id": str(index), "pretext": f"item {index}", "options": ["a", "b"], "correct answer": "a"}
            for index in range(10)
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task_2.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("task_2.jsonl", "\n".join(json.dumps(row) for row in rows))
            loaded = load_task_rows(path, 2)
        first = deterministic_case_ids(
            loaded, task_id=2, count=4, seed="fixed", excluded_ids={"0", "1"}
        )
        second = deterministic_case_ids(
            loaded, task_id=2, count=4, seed="fixed", excluded_ids={"0", "1"}
        )
        self.assertEqual(first, second)
        self.assertFalse({"0", "1"}.intersection(first))

    def test_manifest_contains_no_content_or_answers(self):
        protocol = {
            "sampling": {"items_per_task": 2, "seed": "s", "excluded_ids": ["0", "1"]},
            "dataset": {"tasks": [{
                "task_id": 2, "phenomenon": "implicature", "task_name": "indirect",
                "expected_row_count": 4,
            }]},
        }
        rows = {2: [
            {"id": str(index), "pretext": f"secret {index}", "options": ["yes", "no"], "correct answer": "yes"}
            for index in range(4)
        ]}
        manifest = build_case_manifest(protocol, rows)
        serialized = json.dumps(manifest)
        self.assertEqual(2, manifest["case_count"])
        self.assertNotIn("secret", serialized)
        self.assertNotIn("correct_answer", serialized)

    def test_prompts_keep_same_item_and_change_only_reasoning_contract(self):
        case = {
            "task_name": "indirect-answer interpretation",
            "pretext": "X: Want coffee?\nY: I need to sleep.",
            "options": ["Yes", "No"],
        }
        prompts = {condition: build_prompt(case, condition) for condition in CONDITIONS}
        for prompt in prompts.values():
            self.assertIn("X: Want coffee?", prompt)
            self.assertIn("[0] Yes", prompt)
        self.assertIn("pragmatic_target", prompts["OURS_PRAGMATIC_LOOP"])
        self.assertIn("counterargument", prompts["B1_GENERIC_DELIBERATION"])
        self.assertNotIn("pragmatic_target", prompts["B0_DIRECT"])

    def test_answer_parser_is_fail_closed(self):
        self.assertEqual(1, parse_answer_index('{"answer_index": 1}', 2)["answer_index"])
        self.assertFalse(parse_answer_index('{"answer_index": "1"}', 2)["valid"])
        self.assertFalse(parse_answer_index('{"answer_index": 2}', 2)["valid"])
        self.assertFalse(parse_answer_index("answer 1", 2)["valid"])

    def test_full_payload_contract_is_distinct_from_answer_parse(self):
        missing = {
            "literal_content": "literal",
            "context_evidence": "evidence",
            "alternative_interpretation": "alternative",
            "uncertainty": "low",
            "answer_index": 1,
        }
        self.assertFalse(audit_payload_contract("OURS_PRAGMATIC_LOOP", missing)["valid"])
        complete = dict(missing, pragmatic_target="intent")
        self.assertTrue(audit_payload_contract("OURS_PRAGMATIC_LOOP", complete)["valid"])

    def test_paired_comparison_and_summary(self):
        rows = []
        values = {
            "B0_DIRECT": [1, 0, 0, 1],
            "B1_GENERIC_DELIBERATION": [0, 0, 1, 1],
            "OURS_PRAGMATIC_LOOP": [1, 1, 1, 1],
        }
        for condition, correctness in values.items():
            for index, correct in enumerate(correctness):
                rows.append({
                    "sample_id": f"s{index}", "task_id": 2, "condition": condition,
                    "correct": bool(correct), "parse_valid": True,
                    "prompt_tokens": 10, "completion_tokens": 2, "latency_seconds": 0.1,
                })
        comparison = paired_accuracy_comparison(
            rows, candidate="OURS_PRAGMATIC_LOOP", baseline="B1_GENERIC_DELIBERATION",
            bootstrap_repetitions=200, seed=7,
        )
        self.assertEqual(2, comparison["candidate_wins"])
        self.assertEqual(0.5, comparison["accuracy_delta"])
        self.assertEqual(1.0, summarize_rows(rows)["OURS_PRAGMATIC_LOOP"]["accuracy"])

    def test_frozen_protocol_has_strong_primary_baseline_and_boundaries(self):
        protocol = json.loads(
            (ROOT / "configs/m13_pub_pragmatics_preregistration.json").read_text(encoding="utf-8")
        )
        self.assertEqual(64, protocol["sampling"]["total_case_count"])
        self.assertIn("B1_GENERIC_DELIBERATION", protocol["metrics"]["primary"])
        self.assertEqual("qwen3.5:9b", protocol["model"])
        self.assertIn("not guaranteed uncontaminated", protocol["evidence_boundary"])
        self.assertIn("felt understanding", protocol["evidence_boundary"])
        manifest_path = ROOT / protocol["case_manifest"]["path"]
        self.assertEqual(
            protocol["case_manifest"]["sha256"],
            hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        )
        self.assertFalse(protocol["case_manifest"]["contains_item_text_or_answer_keys"])
        amendment = json.loads(
            (ROOT / "configs/m13_1_pub_generation_contract_amendment.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            amendment["parent_protocol"]["sha256"],
            hashlib.sha256(
                (ROOT / amendment["parent_protocol"]["path"]).read_bytes()
            ).hexdigest(),
        )
        self.assertTrue(amendment["contract_probe"]["formal_score_excluded"])
        self.assertEqual(3, amendment["contract_probe"]["model_call_count"])
        self.assertIn("success and failure gates", amendment["unchanged"])

    def test_result_lock_preserves_negative_result_and_artifact_hashes(self):
        lock = json.loads(
            (ROOT / "configs/m13_pub_pragmatics_result_lock.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            "fail_narrow_pragmatic_gain_with_implementation_fidelity_gap",
            lock["decision"],
        )
        self.assertLess(lock["ours_accuracy"], lock["generic_accuracy"])
        self.assertEqual(0.234375, lock["ours_schema_contract_rate"])
        for artifact in lock["artifacts"].values():
            actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(artifact["sha256"], actual, artifact["path"])


if __name__ == "__main__":
    unittest.main()
