import json
import unittest
from pathlib import Path

import analyze_rightbrain_forbidden_projection_v87 as analyzer
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/rightbrain_forbidden_projection_v87_preregistration.json"
LOCK = ROOT / "configs/rightbrain_forbidden_projection_v87_harness_lock.json"


def fixture(reply="何を言っているの？"):
    logic = {
        "core_message_jp": "何を言っているのか聞き返す。",
        "must_avoid": ["何を言ってい", "私", "そうなんだ"],
        "constraints": {"max_chars": 40},
        "human_speech_plan": {
            "content_units": ["何を言っているのか聞く"],
            "grounding_terms": [],
            "forbidden_repetition": {
                "recent_openings": ["何を言ってい"],
                "avoid_generic_frames": ["そうなんだ"],
            },
        },
    }
    candidate = {
        "id": "v87-synthetic",
        "target_plan": logic,
        "target_plan_sha256": v76.canonical_sha256(logic),
    }
    packet = {
        "candidate_id": candidate["id"],
        "packet_sha256": "packet-v87",
        "outcome_contract": {
            "required_semantic_groups": [["何を言っている"]],
            "maximum_reply_chars": 40,
        },
    }
    row = {
        "candidate_id": candidate["id"],
        "condition": "t2_canonical_cue_explicit_length",
        "packet_sha256": packet["packet_sha256"],
        "raw_reply": reply,
    }
    return packet, row, candidate


class RightBrainForbiddenProjectionV87Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_pair_recovers_conflict_only_rejection_without_changing_reply(self):
        packet, row, candidate = fixture()
        result = v87.evaluate_pair(RightBrain(load_model=False), packet, row, candidate)
        self.assertFalse(result["conditions"][v87.C0]["accepted"])
        self.assertEqual(result["conditions"][v87.C0]["rejection_reasons"], ["must_avoid_violation"])
        self.assertTrue(result["conditions"][v87.T1]["accepted"])
        self.assertTrue(result["conflict_only_recovered"])
        self.assertTrue(result["reply_hash_matches"])
        self.assertTrue(result["projection_scope_matches"])
        self.assertEqual(result["added_reasons"], [])

    def test_projection_does_not_weaken_short_hard_marker(self):
        packet, row, candidate = fixture("私はそう思う。")
        result = v87.evaluate_pair(RightBrain(load_model=False), packet, row, candidate)
        self.assertIn("must_avoid_violation", result["conditions"][v87.C0]["rejection_reasons"])
        self.assertIn("must_avoid_violation", result["conditions"][v87.T1]["rejection_reasons"])
        self.assertFalse(result["conditions"][v87.T1]["accepted"])

    def test_bind_cases_rejects_packet_drift(self):
        packet, row, candidate = fixture()
        row["packet_sha256"] = "drifted"
        with self.assertRaisesRegex(ValueError, "binding mismatch"):
            v87.bind_cases([packet], [row], [candidate], {"scope": {"case_count": 1}})

    def test_success_authorizes_only_fresh_full_pipeline_holdout(self):
        summary = {
            "treatment_gate_accept_rate": 1.0,
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
        self.assertFalse(self.contract["authorizations"]["production_shadow"])

    def test_failure_and_integrity_paths_are_distinct(self):
        summary = {
            "treatment_gate_accept_rate": 0.8,
            "recovered_conflict_only_rejection_count": 0,
            "new_rejection_count": 0,
            "nonconflict_decision_identity_rate": 1.0,
            "projected_marker_count": 4,
            "projection_scope_mismatch_count": 0,
            "reply_hash_mismatch_count": 0,
            "hard_marker_regression_count": 0,
        }
        self.assertEqual(analyzer.decision(self.contract, False, summary), ("inconclusive_integrity_failure", {}))
        self.assertEqual(analyzer.decision(self.contract, True, summary)[0], "stop_forbidden_conflict_projection_hypothesis")

    def test_harness_lock_hashes_match(self):
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        for artifact in lock["frozen_artifacts"].values():
            self.assertEqual(v87.file_sha256(ROOT / artifact["path"]), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
