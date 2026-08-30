import copy
import unittest

import uruha_adaptive_person_model as uapm
import uruha_brain_mac as brain_runtime
import uruha_personhood_loop as upl
from test_generalized_literal_topic_projection_m29 import (
    _Client,
    unlinked_feedback,
    valid_payload,
)
from test_semantic_authorization_m31 import faithful_verdict


def candidate_for(text, feedback=None):
    pragmatic = upl.build_human_pragmatic_understanding(text, turn_index=1)
    return uapm.build_literal_topic_projection_candidate_m29(
        text,
        {} if feedback is None else feedback,
        pragmatic,
    )


def repairable_rejection():
    return {
        "schema": uapm.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
        "status": "semantic_authority_rejected",
        "surface_authority": False,
        "m32_repair_candidate": {
            "schema": "uruha_semantic_commit_repair_candidate_m32",
            "canonical_ready": True,
            "subject_jp": "林医師",
            "predicate_jp": "電話する",
            "time_jp": "明日午後四時",
            "polarity": "affirmed",
            "literal_summary_jp": "林医師は明日午後四時に電話する。",
            "failed_authorization_checks": ["safe_casual_register_only"],
            "raw_dialogue_persisted": False,
        },
        "raw_dialogue_persisted": False,
    }


def undercommitted_authorization():
    return {
        "schema": uapm.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
        "status": "semantically_authorized",
        "surface_authority": True,
        "subject_jp": "ダニエル",
        "predicate_jp": "メイに赤いペン四本を渡した",
        "time_jp": "火曜日",
        "polarity": "affirmed",
        "literal_summary_jp": "ダニエルは火曜日にメイに赤いペン四本を渡した",
        "response_jp": "赤いペン四本、火曜日",
        "surface_self_checks": {
            "safe_response_semantics_faithful": False,
            "subject_preserved": False,
            "predicate_preserved": False,
            "time_quantity_relation_preserved": False,
            "polarity_preserved": False,
            "unsupported_addition_absent": True,
        },
        "raw_dialogue_persisted": False,
    }


class SemanticCommitRepairM32Tests(unittest.TestCase):
    def test_fresh_session_literal_topic_reaches_candidate_gate(self):
        candidate = candidate_for("Daniel gave Mei four red pens on Tuesday.")

        self.assertTrue(candidate["projection_required"])
        self.assertEqual(candidate["candidate_context_m32"], "fresh_session")

    def test_hesitation_marker_does_not_match_um_inside_community(self):
        text = "The community center does not close on Sundays."
        pragmatic = upl.build_human_pragmatic_understanding(text, turn_index=1)
        candidate = candidate_for(text)

        self.assertFalse(pragmatic["text_visible_hesitation"])
        self.assertEqual(pragmatic["pragmatic_label"], "literal_intent_unresolved")
        self.assertTrue(candidate["projection_required"])

    def test_explicit_correction_is_still_excluded_from_literal_commit(self):
        text = "That is not what I meant; I meant Thursday."
        pragmatic = upl.build_human_pragmatic_understanding(text, turn_index=2)
        candidate = candidate_for(text)

        self.assertEqual(pragmatic["pragmatic_label"], "explicit_correction")
        self.assertFalse(candidate["projection_required"])

    def test_m31_rejection_exposes_canonical_only_repair_candidate(self):
        source = "明天要考試。"
        left = brain_runtime.LeftBrain(_Client(valid_payload()))
        verdict = faithful_verdict(
            response="明日の試験です。",
            anchors=["明日", "試験"],
        )
        left._native_semantic_authorizer_m31 = lambda _prompt: verdict

        _plan, rejected = left.authorize_literal_topic_m31(
            source,
            candidate_for(source),
        )

        self.assertEqual(rejected["status"], "semantic_authority_rejected")
        repair_candidate = rejected["m32_repair_candidate"]
        self.assertTrue(repair_candidate["canonical_ready"])
        self.assertEqual(repair_candidate["literal_summary_jp"], "明日試験がある。")
        self.assertNotIn(source, str(repair_candidate))

    def test_deterministic_commit_repairs_realization_without_new_model(self):
        plan, contract = uapm.build_deterministic_semantic_commit_m32(
            repairable_rejection()
        )

        self.assertEqual(contract["status"], "deterministic_commit_repaired")
        self.assertTrue(contract["surface_authority"])
        self.assertEqual(
            contract["response_jp"],
            "林医師は明日午後四時に電話するんだね。",
        )
        self.assertEqual(
            contract["surface_anchors_jp"],
            ["林医師", "明日午後四時", "電話する"],
        )
        self.assertEqual(plan["core_message_jp"], contract["response_jp"])

    def test_authorized_but_incomplete_m31_surface_is_replaced_from_canonical(self):
        plan, contract = uapm.build_deterministic_semantic_commit_m32(
            undercommitted_authorization()
        )

        self.assertTrue(contract["surface_authority"])
        self.assertEqual(
            contract["repair_kind"],
            "authoritative_surface_completeness_override",
        )
        self.assertEqual(
            contract["response_jp"],
            "ダニエルは火曜日にメイに赤いペン四本を渡したんだね。",
        )
        self.assertEqual(plan["core_message_jp"], contract["response_jp"])

    def test_complete_m31_authority_is_not_replaced(self):
        source = undercommitted_authorization()
        source["response_jp"] = source["literal_summary_jp"] + "んだね。"
        source["surface_self_checks"] = {
            key: True for key in source["surface_self_checks"]
        }

        plan, contract = uapm.build_deterministic_semantic_commit_m32(source)

        self.assertIsNone(plan)
        self.assertEqual(contract["reason"], "m31_authoritative_surface_complete")
        self.assertFalse(contract["surface_authority"])

    def test_missing_canonical_semantics_remains_fail_closed(self):
        rejected = repairable_rejection()
        rejected["m32_repair_candidate"]["canonical_ready"] = False

        plan, contract = uapm.build_deterministic_semantic_commit_m32(rejected)

        self.assertIsNone(plan)
        self.assertEqual(contract["status"], "repair_rejected")
        self.assertFalse(contract["surface_authority"])

    def test_apply_and_final_surface_commit_preserve_m32_authority(self):
        _seed, repair = uapm.build_deterministic_semantic_commit_m32(
            repairable_rejection()
        )
        plan, applied = uapm.apply_semantic_commit_repair_m32(
            {
                "intent": "chat",
                "scene": "casual",
                "core_message_jp": "古い下書き",
                "semantic_authorization_m31": copy.deepcopy(
                    repairable_rejection()
                ),
            },
            repair,
        )
        visible, audited = uapm.ensure_semantic_commit_repair_m32_reaches_surface(
            "別の下書き",
            plan,
        )

        self.assertTrue(applied["plan_applied"])
        self.assertEqual(visible, repair["response_jp"])
        self.assertEqual(audited["surface_status"], "matched")
        self.assertEqual(audited["surface_anchor_status"], "matched")


if __name__ == "__main__":
    unittest.main()
