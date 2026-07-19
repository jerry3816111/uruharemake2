import copy
import json
import tempfile
import unittest
from pathlib import Path

import analyze_planner_memory_causality_v84 as analyzer
import planner_memory_causality_v84 as v84
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/planner_memory_causality_v84_preregistration.json"
LOCK = ROOT / "configs/planner_memory_causality_v84_harness_lock.json"


class FakeRightBrain:
    def _model_required_semantic_groups(self, logic):
        anchor = logic.get("memory_anchor") or {}
        return [(anchor["jp_anchor"],)] if anchor.get("jp_anchor") else []

    def _audited_memory_forbidden_surface_terms(self, _logic):
        return []

    def _build_model_surface_payload(self, logic, psyche, max_chars, memory_data=None):
        anchor = logic.get("memory_anchor") or {}
        groups = [list(group) for group in self._model_required_semantic_groups(logic)]
        speech = logic.get("human_speech_plan") or {}
        explicit = bool(logic.get("memory_use_expected") and anchor)
        return json.dumps({
            "task": "write_one_user_facing_japanese_reply",
            "user_input": logic.get("jp_summary"),
            "leftbrain_plan": {
                "meaning": logic.get("core_message_jp"),
                "content_units": speech.get("content_units") or [],
                "grounding_terms": speech.get("grounding_terms") or [],
            },
            "context": {
                "audited_memory_brief": {
                    "policy": "explicit_allowed" if explicit else "no_memory",
                    "allowed_memory_cues": [anchor] if explicit else [],
                },
                "psyche": psyche,
                "max_chars": max_chars,
            },
            "required_marker_groups": groups,
        }, ensure_ascii=False)


def synthetic_candidate(index=1):
    plan = {
        "jp_summary": "前に話した飲み物を聞いている。",
        "memory_use_expected": True,
        "memory_speakability": "explicit_ok",
        "memory_anchor": {"kind": "preference", "jp_anchor": "麦茶", "terms": ["麦茶"]},
        "working_memory_used": ["memory-1"],
        "reply_goal": "前の好みを答える",
        "core_message_jp": "前に好きだと言っていたのは麦茶。",
        "must_avoid": [],
        "constraints": {"max_chars": 48},
        "human_speech_plan": {
            "content_units": ["麦茶だと答える"],
            "speech_moves": [{"move": "answer"}],
            "grounding_terms": ["麦茶"],
        },
    }
    return {
        "id": f"candidate-{index}",
        "scenario_family": "memory_recall_update",
        "source_session_id": f"session-{index}",
        "target_plan": plan,
        "target_plan_sha256": v76.canonical_sha256(plan),
        "input": {"psyche_state": {"mood": 0, "trust": 60}, "working_memory": [{"id": "memory-1"}]},
    }


class PlannerMemoryCausalityV84Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_ablation_changes_only_preregistered_bundle(self):
        original = synthetic_candidate()["target_plan"]
        ablated = v84.ablate_memory_integration(original)
        self.assertTrue(original["memory_use_expected"])
        self.assertFalse(ablated["memory_use_expected"])
        self.assertEqual(ablated["memory_anchor"], {})
        self.assertEqual(ablated["core_message_jp"], "")
        self.assertEqual(ablated["human_speech_plan"]["content_units"], [])
        untouched = copy.deepcopy(original)
        untouched["memory_use_expected"] = False
        untouched["memory_speakability"] = "no_memory"
        untouched["memory_anchor"] = {}
        untouched["working_memory_used"] = []
        untouched["reply_goal"] = ""
        untouched["core_message_jp"] = ""
        untouched["human_speech_plan"]["content_units"] = []
        untouched["human_speech_plan"]["speech_moves"] = []
        untouched["human_speech_plan"]["grounding_terms"] = []
        self.assertEqual(ablated, untouched)

    def test_packet_has_matched_payloads_and_scorer_only_contract(self):
        packet = v84.build_packet(FakeRightBrain(), synthetic_candidate())
        self.assertEqual(packet["scenario_family"], "memory_recall_update")
        self.assertTrue(packet["payloads"][v84.C0]["required_marker_groups"])
        self.assertFalse(packet["payloads"][v84.T1]["required_marker_groups"])
        request = v84.build_request(packet, self.contract, v84.C0, 1)
        serialized = json.dumps(request, ensure_ascii=False)
        self.assertNotIn("outcome_contract", serialized)
        self.assertNotIn("target_failure_code", serialized)

    def test_sequence_is_32_calls_and_balances_first_condition(self):
        packets = [v84.build_packet(FakeRightBrain(), synthetic_candidate(index)) for index in range(1, 9)]
        sequence = v84.expected_sequence(packets, self.contract)
        self.assertEqual(len(sequence), 32)
        pair_first = [sequence[index][2] for index in range(0, len(sequence), 2)]
        self.assertEqual(pair_first.count(v84.C0), 8)
        self.assertEqual(pair_first.count(v84.T1), 8)

    def test_score_detects_memory_semantic_loss(self):
        packet = v84.build_packet(FakeRightBrain(), synthetic_candidate())
        intact = v84.score_reply(packet, "前に好きだと言ってたのは麦茶だろ。")
        removed = v84.score_reply(packet, "前に何か話してたな。")
        self.assertEqual(intact["required_group_recall"], 1.0)
        self.assertEqual(removed["required_group_recall"], 0.0)

    def test_decision_requires_effect_integrity_and_resource_gates(self):
        base = {
            "required_group_recall": 0.9,
            "surface_pass_rate": 1.0,
            "forbidden_violation_rate": 0.0,
            "private_memory_intrusion_rate": 0.0,
            "median_latency_seconds": 2.0,
            "p95_latency_seconds": 4.0,
            "peak_ollama_rss_bytes": 8_000_000_000,
        }
        conditions = {v84.C0: base, v84.T1: base | {"required_group_recall": 0.4}}
        paired = {"mean_recall_delta_intact_minus_removed": 0.5, "bootstrap_ci95": [0.2, 0.8], "intact_win_rate": 0.75}
        decision, checks = analyzer.classify_decision(self.contract, True, conditions, paired)
        self.assertEqual(decision, "memory_integration_signal_causally_supported_bounded")
        self.assertTrue(all(checks.values()))
        self.assertEqual(
            analyzer.classify_decision(self.contract, False, conditions, paired),
            ("inconclusive_integrity_failure", {}),
        )

    def test_failure_rule_stops_no_effect_hypothesis(self):
        base = {
            "required_group_recall": 0.7,
            "surface_pass_rate": 1.0,
            "forbidden_violation_rate": 0.0,
            "private_memory_intrusion_rate": 0.0,
            "median_latency_seconds": 2.0,
            "p95_latency_seconds": 4.0,
            "peak_ollama_rss_bytes": 8_000_000_000,
        }
        paired = {"mean_recall_delta_intact_minus_removed": 0.0, "bootstrap_ci95": [-0.2, 0.2], "intact_win_rate": 0.0}
        decision, _ = analyzer.classify_decision(self.contract, True, {v84.C0: base, v84.T1: base}, paired)
        self.assertEqual(decision, "stop_memory_integration_causality_hypothesis")

    def test_preregistration_forbids_benchmark_and_runtime_authorization(self):
        self.assertFalse(self.contract["authorization"]["training_data"])
        self.assertFalse(self.contract["authorization"]["production_runtime_change"])
        self.assertIn("no benchmark items or answers", self.contract["controls"])

    def test_runtime_has_no_v84_experiment_code(self):
        for name in ("uruha_brain_mac.py", "uruha_web_ui.py", "uruha_memory_runtime.py"):
            self.assertNotIn("planner_memory_causality_v84", (ROOT / name).read_text(encoding="utf-8"))

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(v84.file_sha256(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
