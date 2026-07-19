import copy
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import planner_supervision_executable_view_v81 as v81
import planner_supervision_v76 as v76
import close_planner_supervision_executable_view_v81 as close_v81


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v81_executable_view_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v81_executable_view.json"


class PlannerExecutableViewV81Tests(unittest.TestCase):
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
            "stance": {"warmth": 0.8, "tease": 0.1},
            "memory_use_expected": True,
            "memory_speakability": "explicit_allowed",
            "memory_anchor": {
                "kind": "recent_preference",
                "jp_anchor": "最近ずっと忙しい",
                "terms": ["忙しい"],
                "source": "private_database",
                "source_text": "raw private text",
            },
            "human_speech_plan": {
                "content_units": ["疲れを認める", "休んでよいと伝える"],
                "speech_moves": [{"move": "validate"}],
                "style_operators": ["casual"],
                "target_length": "2_short_sentences",
                "grounding_terms": ["疲れ"],
            },
            "constraints": {
                "sentence_count": 2,
                "max_chars": 40,
                "casual_japanese_only": True,
                "forbid_polite": True,
            },
            "must_avoid": ["無理しても雑になるだけ"],
            "appraisal": {"threat": 0.0},
            "bayes_candidates": [{"label": "A"}, {"label": "B"}, {"label": "C"}],
            "planner_tick_trace": [{"tick": 1}],
            "self_monitor": {"needs_repair": True},
            "self_monitor_repair": {"before": "x", "after": "y"},
            "post_check": {"did_reply_cover_focus": False},
        }

    def packet(self, index=1, mutation=True):
        full = {"input_context": {"user_utterance": "今日は疲れた"}, "plan": self.target_plan()}
        compact = {"input_context": copy.deepcopy(full["input_context"]), "plan": v81.executable_view(full["plan"])}
        return {
            "fresh_index": index,
            "candidate_id": f"candidate-{index}",
            "scenario_family": "emotional_support",
            "mutation_calibration": mutation,
            "views": {v81.C0: full, v81.T1: compact},
            "view_sha256": {
                v81.C0: v76.canonical_sha256(full),
                v81.T1: v76.canonical_sha256(compact),
            },
        }

    def judgment(self, decision, codes=None):
        return {
            "decision": decision,
            "failure_codes": codes or [],
            "reason_summary": "The current plan was checked against the supplied context.",
            "confidence": 0.9,
        }

    def raw(self, packet, model, condition, variant, decision, codes=None, request_bytes=None, elapsed=None):
        judge = next(row for row in self.contract["judges"] if row["model"] == model)
        request = v81.build_request(packet, self.contract, model, condition, variant)
        return {
            "candidate_id": packet["candidate_id"],
            "condition": condition,
            "variant": variant,
            "packet_view_sha256": packet["view_sha256"][condition],
            "model": model,
            "model_digest": judge["digest"],
            "request_sha256": v76.canonical_sha256(request),
            "request_bytes": request_bytes if request_bytes is not None else (1000 if condition == v81.C0 else 500),
            "response_model": model,
            "done": True,
            "parsed": self.judgment(decision, codes),
            "elapsed_seconds": elapsed if elapsed is not None else (2.0 if condition == v81.C0 else 1.0),
            "prompt_eval_count": 500 if condition == v81.C0 else 200,
        }

    def test_executable_view_keeps_decisions_but_excludes_runtime_history(self):
        view = v81.executable_view(self.target_plan())
        payload = json.dumps(view, ensure_ascii=False)
        self.assertEqual(view["response_intent"]["core_message_jp"], "今日は無理せず休んでいい")
        self.assertEqual(view["surface_brief"]["content_units"], ["疲れを認める", "休んでよいと伝える"])
        for forbidden in ("appraisal", "bayes_candidates", "planner_tick_trace", "self_monitor", "post_check"):
            self.assertNotIn(forbidden, payload)
        self.assertNotIn("source_text", payload)
        self.assertNotIn("private_database", payload)

    def test_known_defect_removes_same_executable_intent_from_both_views(self):
        packet = self.packet()
        for condition in self.contract["conditions"]:
            mutated = v81.apply_known_defect(packet["views"][condition], condition)
            payload = json.dumps(mutated, ensure_ascii=False)
            self.assertNotIn("今日は無理せず休んでいい", payload)
            self.assertNotIn("疲れを認めて休ませる", payload)
            self.assertNotEqual(v76.canonical_sha256(mutated), packet["view_sha256"][condition])

    def test_request_does_not_disclose_condition_mutation_or_gold(self):
        packet = self.packet()
        request = v81.build_request(packet, self.contract, self.contract["judges"][0]["model"], v81.T1, v81.VARIANT_MUTATION)
        payload = json.dumps(request, ensure_ascii=False).lower()
        self.assertNotIn(v81.T1, payload)
        self.assertNotIn("known_defect", payload)
        self.assertNotIn("gold_answer", payload)
        self.assertNotIn("expected_failure_code", payload)
        self.assertFalse(request["think"])

    def test_parser_rejects_boolean_confidence_and_accept_with_failure(self):
        invalid = self.judgment("accept", ["missing_executable_intent"])
        with self.assertRaisesRegex(ValueError, "cannot have"):
            v81.parse_judgment(invalid, self.contract)
        invalid = self.judgment("accept")
        invalid["confidence"] = True
        with self.assertRaisesRegex(ValueError, "confidence"):
            v81.parse_judgment(invalid, self.contract)

    def test_fresh_selection_preserves_prefix_and_excludes_it(self):
        candidates = []
        units = []
        for index in range(1, 25):
            plan = self.target_plan()
            candidate = {
                "id": f"candidate-{index}",
                "input": {"user_utterance": f"input-{index}"},
                "target_plan": plan,
                "target_plan_sha256": v76.canonical_sha256(plan),
                "scenario_family": "ordinary_direct",
                "source_session_id": f"session-{(index - 1) % 6}",
                "provenance": {"source_sha256": f"source-{index}"},
            }
            candidates.append(candidate)
            units.append(
                {
                    "candidate_id": candidate["id"],
                    "candidate_binding_sha256": f"binding-{index}",
                    "session_binding_sha256": f"session-{index}",
                    "scenario_family": "ordinary_direct",
                }
            )
        frozen = units[:12]
        with patch.object(v81.v79, "select_pilot", return_value=(candidates, frozen)):
            packets = v81.build_packets(candidates, [], frozen, self.contract)
        self.assertEqual(len(packets), 12)
        self.assertFalse({row["candidate_id"] for row in packets}.intersection(row["candidate_id"] for row in frozen))

    def test_frozen_sequence_has_expected_call_budget(self):
        packets = [self.packet(index, mutation=index <= 6) for index in range(1, 13)]
        self.assertEqual(len(v81.expected_run_sequence(packets, self.contract)), 72)

    def test_synthetic_success_requires_agreement_mutation_detection_and_efficiency(self):
        packets = [self.packet(index, mutation=index <= 6) for index in range(1, 13)]
        rows = []
        models = [row["model"] for row in self.contract["judges"]]
        for packet in packets:
            for condition in self.contract["conditions"]:
                for model_index, model in enumerate(models):
                    decision = "accept"
                    if condition == v81.C0 and packet["fresh_index"] <= 6 and model_index == 1:
                        decision = "uncertain"
                    rows.append(self.raw(packet, model, condition, v81.VARIANT_ORIGINAL, decision))
                if packet["mutation_calibration"]:
                    for model in models:
                        rows.append(
                            self.raw(
                                packet,
                                model,
                                condition,
                                v81.VARIANT_MUTATION,
                                "reject",
                                ["missing_executable_intent"],
                            )
                        )
        sequence_keys = [
            (packet["candidate_id"], condition, variant, judge["model"])
            for judge, packet, condition, variant in v81.expected_run_sequence(packets, self.contract)
        ]
        rows_by_key = {(row["candidate_id"], row["condition"], row["variant"], row["model"]): row for row in rows}
        ordered_rows = [rows_by_key[key] for key in sequence_keys]
        report = v81.analyze(packets, ordered_rows, self.contract, production_runtime_files_changed=0)
        self.assertTrue(report["integrity"]["passed"], report["integrity"])
        self.assertTrue(report["success"]["passed"], report["success"])
        self.assertEqual(report["conditions"][v81.C0]["original_interjudge_agreement"], 0.5)
        self.assertEqual(report["conditions"][v81.T1]["original_interjudge_agreement"], 1.0)
        self.assertFalse(report["planner_training_authorized"])

    def test_runtime_is_unchanged(self):
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", self.contract["parent_commit"], "--", "uruha_brain_mac.py", "uruha_web_ui.py"],
            cwd=ROOT,
            text=True,
        )
        self.assertEqual(changed.strip(), "")

    def test_abort_report_never_authorizes_partial_metrics_or_training(self):
        prefix = {
            "completed_prefix_hash_binding_passed": True,
            "completed_count": 48,
            "expected_count": 72,
            "parse_category_counts": {"parsed": 12, "invalid_output_keys": 35, "malformed_json": 1},
        }
        report = close_v81.build_abort_report(prefix, self.contract, 0)
        self.assertEqual(report["formal_run_status"], "aborted")
        self.assertFalse(report["capability_metrics_authorized"])
        self.assertFalse(report["planner_training_authorized"])
        self.assertFalse(report["production_runtime_change_authorized"])

    def test_tracked_report_is_aggregate_only_when_present(self):
        if not REPORT_PATH.exists():
            self.skipTest("V81 formal local run has not produced the aggregate report")
        payload = REPORT_PATH.read_text(encoding="utf-8")
        for private_key in ("candidate_id", "user_utterance", "reason_summary", "session_id", "target_plan"):
            self.assertNotIn(f'"{private_key}"', payload)


if __name__ == "__main__":
    unittest.main()
