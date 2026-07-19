import copy
import json
import unittest
from pathlib import Path

import analyze_rightbrain_length_contract_v85_1 as analyzer
import planner_supervision_v76 as v76
import rightbrain_length_contract_v85_1 as v851
from uruha_brain_mac import RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE, RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/rightbrain_length_contract_v85_1_preregistration.json"
LOCK = ROOT / "configs/rightbrain_length_contract_v85_1_harness_lock.json"


def candidate():
    logic = {
        "jp_summary": "前の食べ物について答える。",
        "core_message_jp": "ポテトなら普通にあり。少しもらう。",
        "memory_use_expected": True,
        "memory_speakability": "explicit_ok",
        "memory_anchor": {"kind": "context", "jp_anchor": "User:我愛吃薯條", "terms": ["またポテトの"]},
        "constraints": {"max_chars": 40},
        "human_speech_plan": {
            "content_units": ["ポテトについて答える"],
            "speech_moves": [],
            "grounding_terms": ["ポテト"],
        },
        "must_avoid": [],
    }
    return {
        "id": "v85-1-synthetic",
        "scenario_family": "memory_recall_update",
        "target_plan": logic,
        "target_plan_sha256": v76.canonical_sha256(logic),
        "input": {"psyche_state": {"mood": 0, "trust": 60}, "working_memory": []},
    }


class RightBrainLengthContractV851Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_packet_changes_only_explicit_length_contract(self):
        rightbrain = RightBrain(load_model=False)
        packet = v851.build_packet(rightbrain, candidate())
        control = packet["payloads"][v851.C0]
        treatment = packet["payloads"][v851.T1]
        self.assertEqual(control, v851._without_length_contract(treatment))
        self.assertNotIn("output_budget", control)
        self.assertEqual(treatment["output_budget"]["maximum_characters"], 40)
        self.assertFalse(rightbrain.memory_cue_canonicalization_enabled)
        self.assertFalse(rightbrain.explicit_length_contract_enabled)

    def test_system_prompt_changes_only_by_frozen_rule(self):
        packet = v851.build_packet(RightBrain(load_model=False), candidate())
        self.assertEqual(
            packet["system_prompts"][v851.T1],
            packet["system_prompts"][v851.C0] + RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE,
        )

    def test_request_excludes_scorer_contract(self):
        packet = v851.build_packet(RightBrain(load_model=False), candidate())
        request = v851.build_request(packet, self.contract, v851.T1)
        serialized = json.dumps(request, ensure_ascii=False)
        self.assertNotIn("outcome_contract", serialized)
        self.assertNotIn("candidate_id", serialized)
        self.assertIn("maximum_characters", serialized)

    def test_sequence_is_balanced_and_exact(self):
        rightbrain = RightBrain(load_model=False)
        packets = []
        for index in range(8):
            row = candidate()
            row["id"] = f"v85-1-{index}"
            row["target_plan"] = copy.deepcopy(row["target_plan"])
            row["target_plan_sha256"] = v76.canonical_sha256(row["target_plan"])
            packets.append(v851.build_packet(rightbrain, row))
        sequence = v851.expected_sequence(packets, self.contract)
        self.assertEqual(len(sequence), 16)
        first = [sequence[index][1] for index in range(0, 16, 2)]
        self.assertEqual(first.count(v851.C0), 4)
        self.assertEqual(first.count(v851.T1), 4)

    def test_score_records_exact_overage_without_truncating_reply(self):
        packet = v851.build_packet(RightBrain(load_model=False), candidate())
        reply = "ポテトなら普通にあり。少しもらう。追加で長く話してしまうし、まだ説明も続けてしまう。"
        score = v851.score_reply(packet, reply)
        self.assertEqual(score["reply_chars"], len(reply))
        self.assertEqual(score["over_by_chars"], len(reply) - 40)
        self.assertTrue(score["over_max"])

    def test_success_authorizes_only_fresh_holdout(self):
        control = {
            "clean_semantic_recall": 1.0,
            "surface_pass_rate": 0.625,
            "transcript_label_leak_rate": 0.0,
            "over_max_rate": 0.375,
            "forbidden_violation_rate": 0.0,
            "private_intrusion_rate": 0.0,
            "median_latency_seconds": 3.2,
            "p95_latency_seconds": 5.0,
            "peak_ollama_rss_bytes": 9_000_000_000,
        }
        treatment = {
            **control,
            "surface_pass_rate": 0.875,
            "over_max_rate": 0.125,
            "median_latency_seconds": 3.3,
        }
        result, checks = analyzer.decision(self.contract, True, {v851.C0: control, v851.T1: treatment})
        self.assertEqual(result, "authorize_fresh_v86_holdout_only")
        self.assertTrue(all(checks.values()))
        self.assertFalse(self.contract["authorizations"]["production_default_enable"])

    def test_failure_and_integrity_paths_are_distinct(self):
        base = {
            "clean_semantic_recall": 0.8,
            "surface_pass_rate": 0.5,
            "transcript_label_leak_rate": 0.0,
            "over_max_rate": 0.5,
            "forbidden_violation_rate": 0.0,
            "private_intrusion_rate": 0.0,
            "median_latency_seconds": 2.0,
            "p95_latency_seconds": 3.0,
            "peak_ollama_rss_bytes": 8_000_000_000,
        }
        self.assertEqual(analyzer.decision(self.contract, False, {v851.C0: base, v851.T1: base}), ("inconclusive_integrity_failure", {}))
        self.assertEqual(
            analyzer.decision(self.contract, True, {v851.C0: base, v851.T1: base})[0],
            "stop_explicit_length_contract_hypothesis",
        )

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(v851.file_sha256(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
