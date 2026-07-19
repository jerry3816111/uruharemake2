import copy
import json
import unittest
from pathlib import Path

import diagnose_rightbrain_forbidden_projection_v87 as diagnosis
import planner_supervision_v76 as v76
import rightbrain_memory_surface_v86 as v86
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent


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
        "constraints": {"max_chars": 40},
        "human_speech_plan": {
            "content_units": ["今なら少しほしい"],
            "grounding_terms": [],
            "forbidden_repetition": {"recent_openings": []},
        },
    }
    candidate = {
        "id": "synthetic",
        "target_plan": logic,
        "target_plan_sha256": v76.canonical_sha256(logic),
    }
    packet = {
        "candidate_id": "synthetic",
        "packet_sha256": "packet",
        "outcome_contract": {
            "required_semantic_groups": [["今なら少しほしい。"]],
            "maximum_reply_chars": 40,
        },
    }
    row = {
        "candidate_id": "synthetic",
        "condition": v86.T2,
        "packet_sha256": "packet",
        "raw_reply": "今なら少しほしい。",
    }
    return packet, row, candidate


class RightBrainForbiddenProjectionDiagnosisV87Tests(unittest.TestCase):
    def test_canonical_setting_restores_frozen_semantic_contract(self):
        bound = [fixture()]
        right_brain = RightBrain(load_model=False)
        observed = diagnosis.evaluate_setting(
            right_brain,
            bound,
            canonical=False,
            explicit_length=False,
            projection=False,
        )
        intended = diagnosis.evaluate_setting(
            right_brain,
            bound,
            canonical=True,
            explicit_length=True,
            projection=False,
        )
        self.assertEqual(observed["required_contract_match_count"], 0)
        self.assertEqual(observed["semantic_rejection_count"], 1)
        self.assertEqual(intended["required_contract_match_count"], 1)
        self.assertEqual(intended["semantic_rejection_count"], 0)
        self.assertEqual(intended["gate_accept_count"], 1)

    def test_evaluation_restores_all_runtime_flags(self):
        right_brain = RightBrain(load_model=False)
        before = (
            right_brain.memory_cue_canonicalization_enabled,
            right_brain.explicit_length_contract_enabled,
            right_brain.forbidden_conflict_projection_enabled,
        )
        diagnosis.evaluate_setting(
            right_brain,
            [fixture()],
            canonical=True,
            explicit_length=True,
            projection=True,
        )
        after = (
            right_brain.memory_cue_canonicalization_enabled,
            right_brain.explicit_length_contract_enabled,
            right_brain.forbidden_conflict_projection_enabled,
        )
        self.assertEqual(after, before)

    def test_formal_decision_is_not_overridden(self):
        report = json.loads(
            (ROOT / "reports/rightbrain_forbidden_projection_v87.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["decision"], "inconclusive_effect_between_preregistered_gates")

    def test_aggregate_report_contains_no_private_text_or_ids(self):
        report = diagnosis.diagnose(
            {
                "scope": {"case_count": 1},
                "controls": ["same memory-cue and explicit-length settings"],
            },
            {
                "decision": "inconclusive_effect_between_preregistered_gates",
                "integrity_passed": True,
                "summary": {
                    "control_gate_accept_rate": 0.0,
                    "treatment_gate_accept_rate": 0.0,
                    "projected_marker_count": 0,
                },
            },
            [fixture()[0]],
            [fixture()[1]],
            [fixture()[2]],
        )
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("今なら少しほしい。", encoded)
        self.assertNotIn("synthetic", encoded)
        self.assertFalse(report["authorizations"]["production_default"])


if __name__ == "__main__":
    unittest.main()
