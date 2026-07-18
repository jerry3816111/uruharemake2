import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path

import analyze_leftbrain_meaning_contract_v64 as analyzer
import run_leftbrain_meaning_contract_v64 as runner


ROOT = Path(__file__).resolve().parent


class LeftBrainMeaningContractV64HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))
        cls.prereg = json.loads(runner.PREREG_PATH.read_text(encoding="utf-8"))

    def test_model_input_contains_only_user_and_memory(self):
        payload = runner.model_input(self.dataset["cases"][0])
        self.assertEqual(set(payload), {"user_input", "memory_records"})
        runner.assert_gold_isolated(payload)
        encoded = json.dumps(payload, ensure_ascii=False)
        for field in runner.GOLD_FIELDS:
            self.assertNotIn(f'"{field}"', encoded)

    def test_paired_messages_hold_user_payload_constant(self):
        case = self.dataset["cases"][2]
        control = runner.build_messages(case, runner.C0)
        treatment = runner.build_messages(case, runner.T1)
        self.assertEqual(control[1], treatment[1])
        self.assertIn("common planning fields", control[0]["content"])
        self.assertNotIn("semantic_frame", control[0]["content"])
        self.assertIn("semantic_frame", treatment[0]["content"])
        self.assertIn("same common planning fields", treatment[0]["content"])

    def test_gold_isolation_fails_closed(self):
        contaminated = runner.model_input(self.dataset["cases"][0])
        contaminated["required_commitments"] = []
        with self.assertRaisesRegex(ValueError, "scoring gold leaked"):
            runner.assert_gold_isolated(contaminated)

    def test_json_parser_accepts_plain_json_and_code_fence(self):
        payload = {"intent": "answer"}
        encoded = json.dumps(payload)
        self.assertEqual(analyzer.parse_json_output(encoded), payload)
        self.assertEqual(analyzer.parse_json_output(f"```json\n{encoded}\n```"), payload)
        self.assertIsNone(analyzer.parse_json_output("not-json"))

    def test_required_commitments_are_scored_only_from_common_fields(self):
        case = self.dataset["cases"][0]
        output = self._payload(case, treatment=True, include_required=False)
        output["semantic_frame"]["propositions"][0]["object"] += " 鍵を預かって母に伝える"
        score = analyzer.score_row({"output_text": json.dumps(output, ensure_ascii=False)}, case)
        self.assertEqual(score["required_hits"], 0)
        self.assertGreaterEqual(score["relation_hits"], 1)

    def test_memory_state_scoring_distinguishes_current_and_superseded(self):
        case = self.dataset["cases"][2]
        output = self._payload(case, treatment=True, include_required=True)
        score = analyzer.score_row({"output_text": json.dumps(output, ensure_ascii=False)}, case)
        self.assertEqual(score["memory_hits"], 2)
        self.assertEqual(score["memory_count"], 2)

    @staticmethod
    def _payload(case, treatment, include_required):
        required_text = " / ".join(item["accepted_surfaces"][0] for item in case["required_commitments"]) if include_required else "一般的に返す"
        payload = {
            "intent": case["expected_response_act"],
            "user_summary": "入力を要約する",
            "response_goal": required_text,
            "core_message_jp": required_text,
            "uncertainty": 0.1,
            "forbidden_moves": ["禁止行為を避ける"],
        }
        if treatment:
            relation = case["required_frame_relations"][0]
            payload["semantic_frame"] = {
                "actors": [{"id": relation["subject_any"][0], "role": "other"}],
                "propositions": [{
                    "subject": relation["subject_any"][0],
                    "predicate": relation["predicate_any"][0],
                    "object": relation["object_any"][0],
                    "polarity": "positive",
                    "temporality": "current",
                    "source": "user_utterance",
                    "certainty": 0.9,
                }],
                "memory_state": [
                    {
                        "memory_id": item["id"],
                        "status": item["status"],
                        "relevance": "active" if item["status"] == "current" else "background",
                        "reason": "fixture state",
                    }
                    for item in case["memory_fixture"]
                ],
            }
            payload["response_contract"] = {
                "dialogue_act": "answer",
                "required_moves": [required_text],
                "forbidden_moves": ["禁止行為を避ける"],
            }
        return payload

    def _synthetic_raw(self, treatment_complete):
        rows = []
        for case in self.dataset["cases"]:
            for condition in runner.CONDITIONS:
                include_required = condition == runner.T1 and treatment_complete
                payload = self._payload(case, condition == runner.T1, include_required)
                rows.append({
                    "case_id": case["id"],
                    "condition": condition,
                    "output_text": json.dumps(payload, ensure_ascii=False),
                    "transport_error": None,
                    "generation_metrics": {"wall_seconds": 2.0},
                    "ollama_rss_bytes": 8_000_000_000,
                })
        return {
            "model_call_count": 28,
            "transport_error_count": 0,
            "rows": rows,
        }

    def test_synthetic_passing_report_authorizes_only_new_data_pilot(self):
        lock = {"statistics": {"bootstrap_samples": 100}}
        report = analyzer.analyze(self._synthetic_raw(True), self.prereg, self.dataset, lock)
        self.assertTrue(report["automatic_gates"]["passed"])
        self.assertEqual(report["decision"], "advance_only_to_fresh_rightbrain_realization_pilot")
        self.assertFalse(report["production_runtime_changed"])

    def test_synthetic_no_gain_report_stops_hypothesis(self):
        raw = self._synthetic_raw(False)
        lock = {"statistics": {"bootstrap_samples": 100}}
        report = analyzer.analyze(raw, self.prereg, self.dataset, lock)
        self.assertFalse(report["automatic_gates"]["passed"])
        self.assertFalse(report["automatic_gates"]["checks"]["t1_recall_delta_vs_c0"])
        self.assertIn("freeze_negative_result", report["decision"])

    def test_harness_lock_binds_inputs_and_forbids_production_change(self):
        lock_path = ROOT / "configs/leftbrain_meaning_contract_v64_harness_lock.json"
        self.assertTrue(lock_path.exists())
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for name, artifact in lock["frozen_artifacts"].items():
            if name == "harness_test":
                continue
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(digest, artifact["sha256"], name)
        self.assertTrue(lock["formal_run"]["candidate_inference_authorized"])
        self.assertFalse(lock["runtime_change_authorized"])
        self.assertFalse(lock["human_review_authorized"])


if __name__ == "__main__":
    unittest.main()
