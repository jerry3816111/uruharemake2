import json
import unittest
from pathlib import Path

import analyze_rightbrain_forbidden_projection_v87_2 as analyzer
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87
import rightbrain_forbidden_projection_v87_2 as v872
import rightbrain_memory_surface_v86 as v86
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/rightbrain_forbidden_projection_v87_2_preregistration.json"
LOCK = ROOT / "configs/rightbrain_forbidden_projection_v87_2_harness_lock.json"


def fixture():
    logic = {
        "core_message_jp": "今なら少しほしい。",
        "memory_anchor": {
            "kind": "recent_dialogue",
            "jp_anchor": "User:old text -> Uruha:今は古い返事",
            "terms": [],
        },
        "memory_use_expected": True,
        "memory_speakability": "explicit_allowed",
        "must_avoid": ["今なら少し", "私"],
        "constraints": {"max_chars": 40},
        "human_speech_plan": {
            "content_units": ["今なら少しほしい"],
            "grounding_terms": [],
            "forbidden_repetition": {"recent_openings": ["今なら少し"]},
        },
    }
    candidate = {
        "id": "synthetic-v87-2",
        "target_plan": logic,
        "target_plan_sha256": v76.canonical_sha256(logic),
    }
    packet = {
        "candidate_id": candidate["id"],
        "packet_sha256": "packet-v87-2",
        "outcome_contract": {
            "required_semantic_groups": [["今なら少しほしい。"]],
            "maximum_reply_chars": 40,
        },
    }
    row = {
        "candidate_id": candidate["id"],
        "condition": v86.T2,
        "packet_sha256": packet["packet_sha256"],
        "raw_reply": "今なら少しほしい。",
    }
    return packet, row, candidate


class RightBrainForbiddenProjectionV872Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_corrected_replay_changes_only_projection_and_restores_flags(self):
        packet, row, candidate = fixture()
        right_brain = RightBrain(load_model=False)
        before = (
            right_brain.memory_cue_canonicalization_enabled,
            right_brain.explicit_length_contract_enabled,
            right_brain.forbidden_conflict_projection_enabled,
        )
        rows = v872.evaluate_all(
            right_brain,
            [packet],
            [row],
            [candidate],
            {"scope": {"case_count": 1}},
        )
        result = rows[0]
        self.assertTrue(result["required_contract_matches"])
        self.assertTrue(result["fixed_runtime_settings_match"])
        self.assertFalse(result["conditions"][v87.C0]["accepted"])
        self.assertTrue(result["conditions"][v87.T1]["accepted"])
        self.assertTrue(result["conflict_only_recovered"])
        after = (
            right_brain.memory_cue_canonicalization_enabled,
            right_brain.explicit_length_contract_enabled,
            right_brain.forbidden_conflict_projection_enabled,
        )
        self.assertEqual(after, before)

    def test_pass_decision_authorizes_only_fresh_holdout(self):
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
        result, checks = analyzer.decision(self.contract, True, summary)
        self.assertEqual(result, "authorize_fresh_v88_full_pipeline_holdout_only")
        self.assertTrue(all(checks.values()))
        self.assertFalse(self.contract["authorizations"]["production_default_enable"])

    def test_integrity_failure_cannot_authorize(self):
        result, checks = analyzer.decision(self.contract, False, {})
        self.assertEqual(result, "inconclusive_integrity_failure")
        self.assertEqual(checks, {})

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(v87.file_sha256(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
