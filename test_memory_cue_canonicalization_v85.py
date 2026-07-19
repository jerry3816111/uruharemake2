import copy
import json
import unittest
from pathlib import Path

import analyze_memory_cue_canonicalization_v85 as analyzer
import memory_cue_canonicalization_v85 as v85
import planner_supervision_v76 as v76
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/memory_cue_canonicalization_v85_preregistration.json"
LOCK = ROOT / "configs/memory_cue_canonicalization_v85_harness_lock.json"


def candidate():
    logic = {
        "jp_summary": "前の食べ物について答える。",
        "core_message_jp": "ポテトなら普通にあり。少しもらう。",
        "memory_use_expected": True,
        "memory_speakability": "explicit_ok",
        "memory_anchor": {"kind": "context", "jp_anchor": "User:我愛吃薯條", "terms": ["またポテトの"]},
        "constraints": {"max_chars": 40},
        "human_speech_plan": {"content_units": ["ポテトについて答える"], "speech_moves": [], "grounding_terms": ["ポテト"]},
        "must_avoid": [],
    }
    return {
        "id": "v85-synthetic",
        "scenario_family": "memory_recall_update",
        "target_plan": logic,
        "target_plan_sha256": v76.canonical_sha256(logic),
        "input": {"psyche_state": {"mood": 0, "trust": 60}, "working_memory": []},
    }


class MemoryCueCanonicalizationV85Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_packet_changes_only_canonicalization_condition(self):
        rightbrain = RightBrain(load_model=False)
        packet = v85.build_packet(rightbrain, candidate())
        control = json.dumps(packet["payloads"][v85.C0], ensure_ascii=False)
        treatment = json.dumps(packet["payloads"][v85.T1], ensure_ascii=False)
        self.assertIn("User:", control)
        self.assertNotIn("User:", treatment)
        self.assertEqual(packet["outcome_contract"]["required_semantic_groups"], packet["payloads"][v85.T1]["required_marker_groups"])
        self.assertFalse(rightbrain.memory_cue_canonicalization_enabled)

    def test_request_excludes_scorer_contract(self):
        packet = v85.build_packet(RightBrain(load_model=False), candidate())
        request = v85.build_request(packet, self.contract, v85.T1)
        serialized = json.dumps(request, ensure_ascii=False)
        self.assertNotIn("outcome_contract", serialized)
        self.assertNotIn("candidate_id", serialized)

    def test_sequence_is_balanced_and_exact(self):
        rightbrain = RightBrain(load_model=False)
        packets = []
        for index in range(8):
            row = candidate()
            row["id"] = f"v85-{index}"
            row["target_plan"] = copy.deepcopy(row["target_plan"])
            row["target_plan_sha256"] = v76.canonical_sha256(row["target_plan"])
            packets.append(v85.build_packet(rightbrain, row))
        sequence = v85.expected_sequence(packets, self.contract)
        self.assertEqual(len(sequence), 16)
        first = [sequence[index][1] for index in range(0, 16, 2)]
        self.assertEqual(first.count(v85.C0), 4)
        self.assertEqual(first.count(v85.T1), 4)

    def test_score_separates_transcript_leak_from_clean_semantics(self):
        packet = v85.build_packet(RightBrain(load_model=False), candidate())
        polluted = v85.score_reply(packet, "User:我愛吃薯條 -> Uruha:ポテトならあり。")
        clean = v85.score_reply(packet, "ポテトなら普通にあり。少しもらう。")
        self.assertTrue(polluted["transcript_label_leak"])
        self.assertFalse(clean["transcript_label_leak"])
        self.assertEqual(clean["clean_semantic_recall"], 1.0)

    def test_success_authorizes_only_fresh_holdout(self):
        control = {
            "clean_semantic_recall": 0.8, "surface_pass_rate": 0.0, "transcript_label_leak_rate": 1.0,
            "over_max_rate": 1.0, "forbidden_violation_rate": 0.2, "private_intrusion_rate": 0.0,
            "median_latency_seconds": 4.0, "p95_latency_seconds": 8.0, "peak_ollama_rss_bytes": 9_000_000_000,
        }
        treatment = {
            **control, "clean_semantic_recall": 0.9, "surface_pass_rate": 0.9,
            "transcript_label_leak_rate": 0.0, "over_max_rate": 0.1,
            "forbidden_violation_rate": 0.0, "median_latency_seconds": 4.2,
        }
        result, checks = analyzer.decision(self.contract, True, {v85.C0: control, v85.T1: treatment})
        self.assertEqual(result, "authorize_fresh_v86_holdout_only")
        self.assertTrue(all(checks.values()))
        self.assertFalse(self.contract["authorizations"]["production_default_enable"])

    def test_failure_and_integrity_paths_are_distinct(self):
        base = {
            "clean_semantic_recall": 0.5, "surface_pass_rate": 0.5, "transcript_label_leak_rate": 0.0,
            "over_max_rate": 0.0, "forbidden_violation_rate": 0.0, "private_intrusion_rate": 0.0,
            "median_latency_seconds": 2.0, "p95_latency_seconds": 3.0, "peak_ollama_rss_bytes": 8_000_000_000,
        }
        self.assertEqual(analyzer.decision(self.contract, False, {v85.C0: base, v85.T1: base}), ("inconclusive_integrity_failure", {}))
        self.assertEqual(analyzer.decision(self.contract, True, {v85.C0: base, v85.T1: base})[0], "stop_memory_cue_canonicalization_hypothesis")

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(v85.file_sha256(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
