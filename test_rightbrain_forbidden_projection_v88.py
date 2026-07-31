import copy
import json
import unittest
from pathlib import Path

import analyze_rightbrain_forbidden_projection_v88 as analyzer
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v88 as v88
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/rightbrain_forbidden_projection_v88_preregistration.json"
LOCK = ROOT / "configs/rightbrain_forbidden_projection_v88_harness_lock.json"


def candidate(identifier="v88-synthetic", session="session-a", conflict=True):
    marker = "ポテトなら" if conflict else "そうなんだ"
    logic = {
        "jp_summary": "前に話した食べ物について答える。",
        "core_message_jp": "ポテトなら普通にあり。少しもらう。",
        "memory_use_expected": True,
        "memory_speakability": "explicit_ok",
        "memory_anchor": {
            "kind": "context",
            "jp_anchor": "User:我愛吃薯條",
            "terms": ["またポテトの"],
        },
        "constraints": {"max_chars": 40},
        "human_speech_plan": {
            "content_units": ["ポテトなら普通にあり", "少しもらう"],
            "speech_moves": [],
            "grounding_terms": ["ポテト"],
            "forbidden_repetition": {"recent_openings": [marker]},
        },
        "must_avoid": [marker, "危険な指示"],
    }
    return {
        "id": identifier,
        "source_session_id": session,
        "scenario_family": "memory_recall_update",
        "target_plan": logic,
        "target_plan_sha256": v76.canonical_sha256(logic),
        "input": {
            "user_utterance": "前に話したポテト、今も食べたい？",
            "psyche_state": {"mood": 0, "trust": 60},
            "working_memory": [],
        },
    }


def summary(**updates):
    base = {
        "sample_count": 36,
        "case_count": 12,
        "sample_gate_accept_rate": 0.75,
        "any_gate_accept_rate": 0.75,
        "raw_clean_semantic_recall": 0.8,
        "selected_clean_semantic_recall": 0.8,
        "selected_surface_pass_rate": 0.75,
        "selected_external_forbidden_violation_rate": 0.0,
        "selected_private_intrusion_rate": 0.0,
        "selected_over_max_rate": 0.0,
        "median_latency_seconds": 2.0,
        "p95_latency_seconds": 3.0,
        "peak_ollama_rss_bytes": 8_000_000_000,
        "gate_failure_code_counts": {},
    }
    base.update(updates)
    return base


class RightBrainForbiddenProjectionV88Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_packet_changes_only_the_conflicting_forbidden_marker(self):
        rightbrain = RightBrain(load_model=False)
        packet = v88.build_packet(rightbrain, candidate())
        control = packet["payloads"][v88.C0]
        treatment = packet["payloads"][v88.T1]
        self.assertEqual(packet["stratum"], v88.STRATUM_CONFLICT)
        self.assertEqual(packet["dropped_marker_count"], 1)
        self.assertIn("ポテトなら", control["forbidden_markers"])
        self.assertNotIn("ポテトなら", treatment["forbidden_markers"])
        normalized_control = copy.deepcopy(control)
        normalized_treatment = copy.deepcopy(treatment)
        normalized_control.pop("forbidden_markers")
        normalized_treatment.pop("forbidden_markers")
        self.assertEqual(normalized_control, normalized_treatment)

    def test_nonconflict_payloads_are_identical(self):
        packet = v88.build_packet(RightBrain(load_model=False), candidate(conflict=False))
        self.assertEqual(packet["stratum"], v88.STRATUM_NONCONFLICT)
        self.assertEqual(packet["payloads"][v88.C0], packet["payloads"][v88.T1])

    def test_request_pairs_share_seed_and_hide_scorer_metadata(self):
        packet = v88.build_packet(RightBrain(load_model=False), candidate())
        control = v88.build_request(packet, self.contract, v88.C0, 1)
        treatment = v88.build_request(packet, self.contract, v88.T1, 1)
        self.assertEqual(control["options"]["seed"], treatment["options"]["seed"])
        serialized = json.dumps(control, ensure_ascii=False)
        self.assertNotIn("outcome_contract", serialized)
        self.assertNotIn("candidate_id", serialized)
        self.assertNotIn("source_session_id", serialized)

    def test_sequence_is_balanced_and_has_frozen_call_count(self):
        rightbrain = RightBrain(load_model=False)
        packets = [
            v88.build_packet(
                rightbrain,
                candidate(f"v88-{index}", f"session-{index % 4}", conflict=index < 12),
            )
            for index in range(24)
        ]
        sequence = v88.expected_sequence(packets, self.contract)
        self.assertEqual(len(sequence), 144)
        counts = {condition: sum(item[1] == condition for item in sequence) for condition in v88.CONDITIONS}
        self.assertEqual(counts, {v88.C0: 72, v88.T1: 72})

    def test_production_gate_recovers_required_conflict_only(self):
        rightbrain = RightBrain(load_model=False)
        item = candidate()
        packet = v88.build_packet(rightbrain, item)
        raw = "ポテトなら普通にあり。少しもらう。"
        control = v88.evaluate_production_gate(rightbrain, item, packet, v88.C0, raw)
        treatment = v88.evaluate_production_gate(rightbrain, item, packet, v88.T1, raw)
        self.assertFalse(control["gate_accepted"])
        self.assertIn("must_avoid_violation", control["gate_rejection_reasons"])
        self.assertTrue(treatment["gate_accepted"])
        self.assertTrue(treatment["effective_forbidden_matches_payload"])

    def test_decision_requires_effect_and_nonconflict_identity(self):
        conflict_control = summary(any_gate_accept_rate=0.5, selected_clean_semantic_recall=0.65)
        conflict_treatment = summary(any_gate_accept_rate=0.75, selected_clean_semantic_recall=0.8)
        safe = summary(selected_clean_semantic_recall=0.8)
        summaries = {
            v88.STRATUM_CONFLICT: {v88.C0: conflict_control, v88.T1: conflict_treatment},
            v88.STRATUM_NONCONFLICT: {v88.C0: safe, v88.T1: copy.deepcopy(safe)},
        }
        identities = {
            v88.STRATUM_CONFLICT: {"pair_count": 36, "raw_reply_identity_rate": 0.0, "gate_decision_identity_rate": 0.5},
            v88.STRATUM_NONCONFLICT: {"pair_count": 36, "raw_reply_identity_rate": 1.0, "gate_decision_identity_rate": 1.0},
        }
        result, checks = analyzer.decision(self.contract, True, summaries, identities)
        self.assertEqual(result, "authorize_bounded_production_shadow_only")
        self.assertTrue(all(checks.values()))
        identities[v88.STRATUM_NONCONFLICT]["raw_reply_identity_rate"] = 0.99
        self.assertEqual(
            analyzer.decision(self.contract, True, summaries, identities)[0],
            "stop_forbidden_projection_generalization",
        )

    def test_integrity_failure_cannot_authorize(self):
        empty = {
            v88.STRATUM_CONFLICT: {v88.C0: summary(), v88.T1: summary()},
            v88.STRATUM_NONCONFLICT: {v88.C0: summary(), v88.T1: summary()},
        }
        identities = {
            stratum: {"pair_count": 36, "raw_reply_identity_rate": 1.0, "gate_decision_identity_rate": 1.0}
            for stratum in (v88.STRATUM_CONFLICT, v88.STRATUM_NONCONFLICT)
        }
        self.assertEqual(analyzer.decision(self.contract, False, empty, identities), ("inconclusive_integrity_failure", {}))
        self.assertFalse(self.contract["authorizations"]["production_default_enable"])
        self.assertFalse(self.contract["authorizations"]["persona_fidelity_claim"])

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(v88.file_sha256(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
