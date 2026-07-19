import json
import unittest
from pathlib import Path

import analyze_rightbrain_forbidden_projection_v87_2 as v872_analyzer
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87
import rightbrain_forbidden_projection_v87_3 as v873
import rightbrain_memory_surface_v86 as v86
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/rightbrain_forbidden_projection_v87_3_preregistration.json"
LOCK = ROOT / "configs/rightbrain_forbidden_projection_v87_3_harness_lock.json"


def fixture():
    logic = {
        "core_message_jp": "今なら少しほしい。",
        "memory_anchor": {"kind": "recent_dialogue", "jp_anchor": "User:old -> Uruha:old", "terms": []},
        "memory_use_expected": True,
        "memory_speakability": "explicit_allowed",
        "must_avoid": ["今なら少し", "ちょっと手 "],
        "constraints": {"max_chars": 40},
        "human_speech_plan": {
            "content_units": ["今なら少しほしい"],
            "grounding_terms": [],
            "forbidden_repetition": {"recent_openings": ["今なら少し"]},
        },
    }
    candidate = {"id": "synthetic", "target_plan": logic, "target_plan_sha256": v76.canonical_sha256(logic)}
    packet = {
        "candidate_id": "synthetic",
        "packet_sha256": "packet",
        "outcome_contract": {"required_semantic_groups": [["今なら少しほしい。"]], "maximum_reply_chars": 40},
    }
    row = {"candidate_id": "synthetic", "condition": v86.T2, "packet_sha256": "packet", "raw_reply": "今なら少しほしい。"}
    return packet, row, candidate


class RightBrainForbiddenProjectionV873Tests(unittest.TestCase):
    def test_normalized_scope_oracle_accepts_only_expected_projection(self):
        packet, row, candidate = fixture()
        result = v873.evaluate_all(
            RightBrain(load_model=False),
            [packet],
            [row],
            [candidate],
            {"scope": {"case_count": 1}},
        )[0]
        self.assertTrue(result["projection_scope_matches"])
        self.assertTrue(result["normalized_scope_oracle_applied"])
        self.assertEqual(result["conditions"][v87.T1]["dropped_marker_count"], 1)
        self.assertTrue(result["conflict_only_recovered"])

    def test_pass_gates_remain_identical_to_v87_2(self):
        contract = json.loads(PREREG.read_text(encoding="utf-8"))
        summary = {
            "required_contract_match_count": 12,
            "control_gate_accept_count": 10,
            "treatment_gate_accept_count": 12,
            "recovered_conflict_only_rejection_count": 2,
            "new_rejection_count": 0,
            "nonconflict_decision_identity_rate": 1.0,
            "projected_marker_count": 4,
            "projection_scope_mismatch_count": 0,
            "reply_hash_mismatch_count": 0,
            "hard_marker_regression_count": 0,
        }
        decision, checks = v872_analyzer.decision(contract, True, summary)
        self.assertEqual(decision, "authorize_fresh_v88_full_pipeline_holdout_only")
        self.assertTrue(all(checks.values()))

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(v87.file_sha256(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
