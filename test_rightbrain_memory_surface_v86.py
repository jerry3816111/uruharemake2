import copy
import json
import unittest
from pathlib import Path

import analyze_rightbrain_memory_surface_v86 as analyzer
import planner_supervision_v76 as v76
import rightbrain_length_contract_v85_1 as v851
import rightbrain_memory_surface_v86 as v86
from uruha_brain_mac import RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE, RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/rightbrain_memory_surface_v86_preregistration.json"
LOCK = ROOT / "configs/rightbrain_memory_surface_v86_harness_lock.json"


def candidate(identifier="v86-synthetic", session="session-a"):
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
        "id": identifier,
        "candidate_binding_sha256": f"binding-{identifier}",
        "session_binding_sha256": f"binding-{session}",
        "source_session_id": session,
        "scenario_family": "memory_recall_update",
        "target_plan": logic,
        "target_plan_sha256": v76.canonical_sha256(logic),
        "input": {"psyche_state": {"mood": 0, "trust": 60}, "working_memory": []},
    }


class RightBrainMemorySurfaceV86Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_packet_has_two_single_variable_comparisons(self):
        rightbrain = RightBrain(load_model=False)
        packet = v86.build_packet(rightbrain, candidate())
        legacy = packet["payloads"][v86.C0]
        canonical = packet["payloads"][v86.C1]
        treatment = packet["payloads"][v86.T2]
        self.assertIn("User:", json.dumps(legacy, ensure_ascii=False))
        self.assertNotIn("User:", json.dumps(canonical, ensure_ascii=False))
        self.assertEqual(canonical, v851._without_length_contract(treatment))
        self.assertEqual(
            packet["system_prompts"][v86.T2],
            packet["system_prompts"][v86.C1] + RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE,
        )
        self.assertFalse(rightbrain.memory_cue_canonicalization_enabled)
        self.assertFalse(rightbrain.explicit_length_contract_enabled)

    def test_request_excludes_holdout_and_scorer_metadata(self):
        packet = v86.build_packet(RightBrain(load_model=False), candidate())
        request = v86.build_request(packet, self.contract, v86.T2)
        serialized = json.dumps(request, ensure_ascii=False)
        self.assertNotIn("outcome_contract", serialized)
        self.assertNotIn("candidate_id", serialized)
        self.assertNotIn("source_session_id", serialized)

    def test_rotating_sequence_is_balanced_and_exact(self):
        rightbrain = RightBrain(load_model=False)
        packets = [v86.build_packet(rightbrain, candidate(f"v86-{index}", f"session-{index % 4}")) for index in range(12)]
        sequence = v86.expected_sequence(packets, self.contract)
        self.assertEqual(len(sequence), 36)
        first = [sequence[index][1] for index in range(0, 36, 3)]
        self.assertEqual({condition: first.count(condition) for condition in v86.CONDITIONS}, {condition: 4 for condition in v86.CONDITIONS})

    def test_score_uses_clean_contract_for_every_condition(self):
        packet = v86.build_packet(RightBrain(load_model=False), candidate())
        clean = v86.score_reply(packet, "ポテトなら普通にあり。少しもらう。")
        polluted = v86.score_reply(packet, "User:我愛吃薯條 -> Uruha:ポテトならあり。")
        self.assertEqual(clean["clean_semantic_recall"], 1.0)
        self.assertFalse(clean["transcript_label_leak"])
        self.assertTrue(polluted["transcript_label_leak"])

    def test_success_authorizes_shadow_only(self):
        legacy = {
            "clean_semantic_recall": 0.8,
            "surface_pass_rate": 0.25,
            "transcript_label_leak_rate": 0.75,
            "over_max_rate": 0.5,
            "forbidden_violation_rate": 0.1,
            "private_intrusion_rate": 0.0,
            "median_latency_seconds": 3.0,
            "p95_latency_seconds": 5.0,
            "peak_ollama_rss_bytes": 9_000_000_000,
        }
        canonical = {
            **legacy,
            "clean_semantic_recall": 0.9,
            "surface_pass_rate": 0.75,
            "transcript_label_leak_rate": 0.0,
            "over_max_rate": 0.25,
            "forbidden_violation_rate": 0.0,
            "median_latency_seconds": 3.2,
        }
        treatment = {
            **canonical,
            "clean_semantic_recall": 0.9,
            "surface_pass_rate": 0.9,
            "over_max_rate": 0.1,
            "median_latency_seconds": 3.3,
        }
        result, checks = analyzer.decision(
            self.contract,
            True,
            {v86.C0: legacy, v86.C1: canonical, v86.T2: treatment},
        )
        self.assertEqual(result, "authorize_production_shadow_only")
        self.assertTrue(all(checks.values()))
        self.assertFalse(self.contract["authorizations"]["production_default_enable"])

    def test_integrity_and_failure_decisions_are_distinct(self):
        base = {
            "clean_semantic_recall": 0.8,
            "surface_pass_rate": 0.5,
            "transcript_label_leak_rate": 0.0,
            "over_max_rate": 0.2,
            "forbidden_violation_rate": 0.0,
            "private_intrusion_rate": 0.0,
            "median_latency_seconds": 2.0,
            "p95_latency_seconds": 3.0,
            "peak_ollama_rss_bytes": 8_000_000_000,
        }
        summaries = {condition: copy.deepcopy(base) for condition in v86.CONDITIONS}
        self.assertEqual(analyzer.decision(self.contract, False, summaries), ("inconclusive_integrity_failure", {}))
        self.assertEqual(analyzer.decision(self.contract, True, summaries)[0], "stop_memory_surface_bundle_generalization")

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(v86.file_sha256(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
