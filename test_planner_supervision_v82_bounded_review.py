import copy
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import planner_supervision_bounded_review_v82 as v82
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v82_bounded_review_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v82_bounded_review.json"


class PlannerBoundedReviewV82Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def target_plan(self):
        return {
            "intent": "support",
            "hidden_intent": "emotional_bid",
            "scene": "support",
            "response_mode": "direct_answer",
            "premise_check": "accept",
            "dialogue_act": "emotional_containment",
            "reply_goal": "疲れを認めて休ませる",
            "core_message_jp": "今日は無理せず休んでいい",
            "listener_state": "疲れている",
            "uncertainty": 0.1,
            "user_belief": "休むのは悪いと思っている",
            "user_expectation": "責めずに受け止めてほしい",
            "stance": {"warmth": 0.8},
            "memory_use_expected": False,
            "memory_speakability": "no_memory",
            "memory_anchor": {},
            "human_speech_plan": {
                "content_units": ["疲れを認める", "休んでよいと伝える"],
                "speech_moves": [{"move": "validate"}],
                "style_operators": ["casual"],
                "target_length": "2_short_sentences",
                "grounding_terms": ["疲れ"],
            },
            "constraints": {"sentence_count": 2, "max_chars": 40, "casual_japanese_only": True, "forbid_polite": True},
            "must_avoid": [],
            "planner_tick_trace": [{"tick": 1}],
            "self_monitor": {"needs_repair": True},
        }

    def packet(self, index=1, mutation=True):
        full = {"input_context": {"user_utterance": "今日は疲れた"}, "plan": self.target_plan()}
        compact = {"input_context": copy.deepcopy(full["input_context"]), "plan": v82.v81.executable_view(full["plan"])}
        return {
            "fresh_index": index,
            "candidate_id": f"candidate-{index}",
            "scenario_family": "ordinary_direct",
            "mutation_calibration": mutation,
            "views": {v82.C0: full, v82.T1: compact},
            "view_sha256": {v82.C0: v76.canonical_sha256(full), v82.T1: v76.canonical_sha256(compact)},
        }

    def raw(self, packet, model, condition, variant, line, request_bytes=None, elapsed=None):
        judge = next(row for row in self.contract["judges"] if row["model"] == model)
        request = v82.build_request(packet, self.contract, model, condition, variant)
        return {
            "candidate_id": packet["candidate_id"],
            "condition": condition,
            "variant": variant,
            "packet_view_sha256": packet["view_sha256"][condition],
            "model": model,
            "model_digest": judge["digest"],
            "request_sha256": v76.canonical_sha256(request),
            "request_bytes": request_bytes if request_bytes is not None else (1000 if condition == v82.C0 else 500),
            "response_model": model,
            "done": True,
            "parsed": v82.parse_line(line, self.contract),
            "parse_error": "",
            "transport_error": "",
            "elapsed_seconds": elapsed if elapsed is not None else (2.0 if condition == v82.C0 else 1.0),
            "prompt_eval_count": 500 if condition == v82.C0 else 200,
            "eval_count": 4,
        }

    def test_line_protocol_is_strict_and_parser_compatible(self):
        self.assertEqual(v82.parse_line("ACCEPT|none", self.contract), {"decision": "accept", "failure_code": "none"})
        self.assertEqual(
            v82.parse_line("REJECT|missing_executable_intent", self.contract),
            {"decision": "reject", "failure_code": "missing_executable_intent"},
        )
        for invalid in (" ACCEPT|none", "ACCEPT|none\n", "ACCEPT|other", "REJECT|none", "accept|none", "ACCEPT"):
            with self.assertRaises(ValueError):
                v82.parse_line(invalid, self.contract)
        with self.assertRaisesRegex(ValueError, "invalid keys"):
            v82.parse_stored_judgment(
                {"decision": "accept", "failure_code": "none", "extra": "not allowed"},
                self.contract,
            )

    def test_request_has_generation_bound_and_no_experiment_disclosure(self):
        request = v82.build_request(self.packet(), self.contract, self.contract["judges"][0]["model"], v82.T1, v82.VARIANT_MUTATION)
        payload = json.dumps(request, ensure_ascii=False).lower()
        self.assertEqual(request["options"]["num_predict"], 32)
        self.assertFalse(request["think"])
        self.assertNotIn(v82.T1, payload)
        self.assertNotIn("known_defect", payload)
        self.assertNotIn("expected_failure_code", payload)
        self.assertNotIn("gold_answer", payload)

    def test_hard_deadline_converts_hang_to_bounded_failure(self):
        with patch.object(v82.subprocess, "run", side_effect=subprocess.TimeoutExpired(["curl"], 1)):
            with self.assertRaisesRegex(TimeoutError, "hard_deadline"):
                v82._post_json_bounded({}, curl_max_time_seconds=1, hard_deadline_seconds=1)

    def test_fresh_selection_excludes_v79_and_v81(self):
        candidates = []
        units = []
        for index in range(1, 33):
            plan = self.target_plan()
            candidates.append(
                {
                    "id": f"candidate-{index}",
                    "input": {"user_utterance": f"input-{index}"},
                    "target_plan": plan,
                    "target_plan_sha256": v76.canonical_sha256(plan),
                    "scenario_family": "ordinary_direct",
                    "source_session_id": f"session-{(index - 1) % 6}",
                    "provenance": {"source_sha256": f"source-{index}"},
                }
            )
            units.append(
                {
                    "candidate_id": f"candidate-{index}",
                    "candidate_binding_sha256": f"binding-{index}",
                    "session_binding_sha256": f"session-binding-{index}",
                    "scenario_family": "ordinary_direct",
                }
            )
        frozen_v79 = units[:12]
        v81_packets = [{"candidate_id": f"candidate-{index}"} for index in range(13, 25)]
        with patch.object(v82.v79, "select_pilot", return_value=(candidates, frozen_v79)):
            packets = v82.build_packets(candidates, [], frozen_v79, v81_packets, self.contract)
        self.assertEqual(len(packets), 8)
        excluded = {f"candidate-{index}" for index in range(1, 25)}
        self.assertFalse(excluded.intersection(row["candidate_id"] for row in packets))

    def test_frozen_sequence_has_48_attempts(self):
        packets = [self.packet(index, mutation=index <= 4) for index in range(1, 9)]
        self.assertEqual(len(v82.expected_run_sequence(packets, self.contract)), 48)

    def test_synthetic_success_requires_all_preregistered_gates(self):
        packets = [self.packet(index, mutation=index <= 4) for index in range(1, 9)]
        models = [row["model"] for row in self.contract["judges"]]
        rows = []
        for packet in packets:
            for condition in self.contract["conditions"]:
                for model_index, model in enumerate(models):
                    line = "ACCEPT|none"
                    if condition == v82.C0 and packet["fresh_index"] <= 4 and model_index == 1:
                        line = "UNCERTAIN|excessive_implementation_noise"
                    rows.append(self.raw(packet, model, condition, v82.VARIANT_ORIGINAL, line))
                if packet["mutation_calibration"]:
                    for model in models:
                        rows.append(
                            self.raw(
                                packet,
                                model,
                                condition,
                                v82.VARIANT_MUTATION,
                                "REJECT|missing_executable_intent",
                            )
                        )
        rows_by_key = {(row["candidate_id"], row["condition"], row["variant"], row["model"]): row for row in rows}
        ordered = [
            rows_by_key[(packet["candidate_id"], condition, variant, judge["model"])]
            for judge, packet, condition, variant in v82.expected_run_sequence(packets, self.contract)
        ]
        report = v82.analyze(packets, ordered, self.contract, production_runtime_files_changed=0)
        self.assertTrue(report["integrity"]["passed"], report["integrity"])
        self.assertTrue(report["success"]["passed"], report["success"])
        self.assertEqual(report["conditions"][v82.C0]["original_interjudge_agreement"], 0.5)
        self.assertEqual(report["conditions"][v82.T1]["original_interjudge_agreement"], 1.0)
        self.assertTrue(report["comparative_metrics_authorized"])
        self.assertFalse(report["planner_training_authorized"])

    def test_runtime_is_unchanged(self):
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", self.contract["parent_commit"], "--", "uruha_brain_mac.py", "uruha_web_ui.py"],
            cwd=ROOT,
            text=True,
        )
        self.assertEqual(changed.strip(), "")

    def test_tracked_report_is_aggregate_only_when_present(self):
        if not REPORT_PATH.exists():
            self.skipTest("V82 formal report does not exist yet")
        payload = REPORT_PATH.read_text(encoding="utf-8")
        for private_key in ("candidate_id", "user_utterance", "session_id", "target_plan", "reason_summary"):
            self.assertNotIn(f'"{private_key}"', payload)


if __name__ == "__main__":
    unittest.main()
