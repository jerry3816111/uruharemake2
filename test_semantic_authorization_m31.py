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


SOURCE = "明天要考試。"


def candidate_for(text=SOURCE):
    return uapm.build_literal_topic_projection_candidate_m29(
        text,
        unlinked_feedback(),
        upl.build_human_pragmatic_understanding(text, turn_index=4),
    )


def faithful_verdict(response="明日試験なんだ。", anchors=None):
    return {
        "proposal_semantics_faithful": True,
        "safe_response_semantics_faithful": True,
        "subject_preserved": True,
        "predicate_preserved": True,
        "time_quantity_relation_preserved": True,
        "polarity_preserved": True,
        "unsupported_addition_absent": True,
        "source_polarity": "affirmed",
        "source_subject_jp": "明日の試験",
        "source_predicate_jp": "ある",
        "source_time_jp": "明日",
        "source_literal_summary_jp": "明日試験がある。",
        "safe_response_jp": response,
        "safe_surface_anchors_jp": anchors or ["明日", "試験"],
        "confidence": 0.93,
        "error_tags": [],
    }


class SemanticAuthorizationM31Tests(unittest.TestCase):
    def setUp(self):
        self.left = brain_runtime.LeftBrain(_Client(valid_payload()))
        _plan, self.projection = self.left.project_literal_topic_m29(
            SOURCE,
            candidate_for(),
        )

    def test_two_model_faithful_verdict_grants_final_surface_authority(self):
        self.left._native_semantic_authorizer_m31 = lambda _prompt: faithful_verdict()

        plan, contract = self.left.authorize_literal_topic_m31(
            SOURCE,
            self.projection,
        )

        self.assertEqual(contract["status"], "semantically_authorized")
        self.assertTrue(contract["surface_authority"])
        self.assertTrue(all(contract["authorization_checks"].values()))
        self.assertEqual(contract["source_polarity"], "affirmed")
        self.assertEqual(contract["polarity"], "affirmed")
        self.assertEqual(plan["core_message_jp"], "明日試験なんだ。")
        self.assertFalse(contract["raw_dialogue_persisted"])
        self.assertNotIn(SOURCE, str(contract))

    def test_source_first_candidate_bypasses_untrusted_m29_generation(self):
        self.left._native_semantic_authorizer_m31 = lambda _prompt: faithful_verdict()

        plan, contract = self.left.authorize_literal_topic_m31(
            SOURCE,
            candidate_for(),
        )

        self.assertEqual(contract["status"], "semantically_authorized")
        self.assertTrue(contract["source_first_fast_path"])
        self.assertEqual(plan["core_message_jp"], "明日試験なんだ。")

    def test_visible_negation_overrides_incorrect_model_polarity(self):
        text = "会議は金曜日ではなく木曜日だ。"
        verdict = faithful_verdict(
            response="会議は金曜日ではなく木曜日だね。",
            anchors=["会議", "木曜日"],
        )
        verdict.update(
            {
                "source_subject_jp": "会議",
                "source_predicate_jp": "木曜日にある",
                "source_time_jp": "金曜日ではなく木曜日",
                "source_literal_summary_jp": "会議は金曜日ではなく木曜日だ。",
                "source_polarity": "affirmed",
            }
        )
        self.left._native_semantic_authorizer_m31 = lambda _prompt: verdict

        _plan, contract = self.left.authorize_literal_topic_m31(
            text,
            candidate_for(text),
        )

        self.assertEqual(contract["status"], "semantically_authorized")
        self.assertEqual(contract["polarity"], "negated")

    def test_ticket_counter_is_normalized_before_surface_commit(self):
        text = "I have only one ticket."
        verdict = faithful_verdict(
            response="チケット一つだけね。",
            anchors=["チケット", "一つ"],
        )
        verdict.update(
            {
                "source_subject_jp": "チケット",
                "source_predicate_jp": "一つしかない",
                "source_time_jp": "一つ",
                "source_literal_summary_jp": "チケットは一つしかない。",
            }
        )
        self.left._native_semantic_authorizer_m31 = lambda _prompt: verdict

        plan, contract = self.left.authorize_literal_topic_m31(
            text,
            candidate_for(text),
        )

        self.assertEqual(contract["status"], "semantically_authorized")
        self.assertIn("一枚", contract["literal_summary_jp"])
        self.assertEqual(plan["core_message_jp"], "チケット一枚だけね。")

    def test_relationship_reversal_revokes_fluent_projection(self):
        verdict = {
            "proposal_diagnosis": {
                "semantics_faithful": False,
                "error_tags": ["relationship_direction_reversed"],
            },
            "source_normalization": {
                "polarity": "affirmed",
                "subject_jp": "姉",
                "predicate_jp": "大阪に住んでいる",
                "time_quantity_relation_jp": "",
                "literal_summary_jp": "姉は大阪に住んでいる。",
            },
            "surface_authorization": {
                "semantics_faithful": False,
                "subject_preserved": False,
                "predicate_preserved": True,
                "time_quantity_relation_preserved": True,
                "polarity_preserved": True,
                "unsupported_addition_absent": True,
                "safe_response_jp": "妹が大阪に住んでるね。",
                "safe_surface_anchors_jp": ["妹", "大阪"],
            },
            "confidence": 0.95,
        }
        self.left._native_semantic_authorizer_m31 = lambda _prompt: verdict

        plan, contract = self.left.authorize_literal_topic_m31(
            SOURCE,
            self.projection,
        )

        self.assertIsNone(plan)
        self.assertEqual(contract["status"], "semantic_authority_rejected")
        self.assertFalse(contract["surface_authority"])
        self.assertIn("relationship_direction_reversed", contract["error_tags"])
        self.assertFalse(
            contract["authorization_checks"][
                "safe_surface_anchors_grounded_in_canonical"
            ]
        )

    def test_unsupported_promised_action_revokes_authority(self):
        verdict = faithful_verdict("明日試験なんだ。手伝ってあげる。")
        verdict["unsupported_addition_absent"] = False
        verdict["error_tags"] = ["unsupported_promised_action"]
        self.left._native_semantic_authorizer_m31 = lambda _prompt: verdict

        _plan, contract = self.left.authorize_literal_topic_m31(
            SOURCE,
            self.projection,
        )

        self.assertEqual(contract["status"], "semantic_authority_rejected")
        self.assertFalse(
            contract["authorization_checks"]["unsupported_addition_absent"]
        )

    def test_realization_only_m29_rejection_can_be_semantically_repaired(self):
        payload = valid_payload()
        payload["response_jp"] = "明日テストなんだ。"
        left = brain_runtime.LeftBrain(_Client(payload))
        _plan, rejected = left.project_literal_topic_m29(SOURCE, candidate_for())
        self.assertEqual(rejected["status"], "projection_rejected")
        self.assertFalse(
            rejected["validation_checks"]["surface_anchors_reach_response"]
        )
        self.assertEqual(rejected["proposed_subject_jp"], "明日の試験")
        left._native_semantic_authorizer_m31 = lambda _prompt: faithful_verdict()

        plan, contract = left.authorize_literal_topic_m31(SOURCE, rejected)

        self.assertEqual(contract["status"], "semantically_authorized")
        self.assertEqual(plan["core_message_jp"], "明日試験なんだ。")

    def test_semantically_wrong_proposal_can_be_independently_repaired(self):
        verdict = faithful_verdict()
        verdict["proposal_semantics_faithful"] = False
        verdict["error_tags"] = ["proposal_time_removed"]
        self.left._native_semantic_authorizer_m31 = lambda _prompt: verdict

        plan, contract = self.left.authorize_literal_topic_m31(
            SOURCE,
            self.projection,
        )

        self.assertEqual(contract["status"], "semantically_authorized")
        self.assertEqual(contract["repair_mode"], "independent_semantic_repair")
        self.assertEqual(contract["literal_summary_jp"], "明日試験がある。")
        self.assertEqual(plan["core_message_jp"], "明日試験なんだ。")

    def test_nested_repair_keeps_proposal_diagnosis_out_of_surface_gate(self):
        verdict = {
            "proposal_diagnosis": {
                "semantics_faithful": False,
                "error_tags": ["proposal_entity_mismatch"],
            },
            "source_normalization": {
                "polarity": "affirmed",
                "subject_jp": "明日の試験",
                "predicate_jp": "ある",
                "time_quantity_relation_jp": "明日",
                "literal_summary_jp": "明日試験がある。",
            },
            "surface_authorization": {
                # Some local models echo the proposal diagnosis here even
                # after producing a corrected canonical surface.  The repair
                # path is instead gated by canonical fields, local surface
                # checks, and the no-unsupported-addition decision.
                "semantics_faithful": False,
                "subject_preserved": False,
                "predicate_preserved": True,
                "time_quantity_relation_preserved": True,
                "polarity_preserved": True,
                "unsupported_addition_absent": True,
                "safe_response_jp": "明日試験なんだ。",
                "safe_surface_anchors_jp": ["明日", "試験"],
            },
            "confidence": 0.94,
        }
        self.left._native_semantic_authorizer_m31 = lambda _prompt: verdict

        plan, contract = self.left.authorize_literal_topic_m31(
            SOURCE,
            self.projection,
        )

        self.assertEqual(contract["status"], "semantically_authorized")
        self.assertEqual(contract["repair_mode"], "independent_semantic_repair")
        self.assertFalse(
            contract["surface_self_checks"][
                "safe_response_semantics_faithful"
            ]
        )
        self.assertTrue(contract["authorization_checks"]["proposal_or_repair_path_valid"])
        self.assertEqual(plan["core_message_jp"], "明日試験なんだ。")

    def test_nested_repair_still_rejects_locally_detectable_promised_action(self):
        verdict = {
            "proposal_diagnosis": {
                "semantics_faithful": False,
                "error_tags": ["proposal_time_removed"],
            },
            "source_normalization": {
                "polarity": "affirmed",
                "subject_jp": "明日の試験",
                "predicate_jp": "ある",
                "time_quantity_relation_jp": "明日",
                "literal_summary_jp": "明日試験がある。",
            },
            "surface_authorization": {
                "semantics_faithful": True,
                "subject_preserved": True,
                "predicate_preserved": True,
                "time_quantity_relation_preserved": True,
                "polarity_preserved": True,
                "unsupported_addition_absent": True,
                "safe_response_jp": "明日試験なんだ。手伝ってあげる。",
                "safe_surface_anchors_jp": ["明日", "試験"],
            },
            "confidence": 0.94,
        }
        self.left._native_semantic_authorizer_m31 = lambda _prompt: verdict

        plan, contract = self.left.authorize_literal_topic_m31(
            SOURCE,
            self.projection,
        )

        self.assertIsNone(plan)
        self.assertEqual(contract["status"], "semantic_authority_rejected")
        self.assertFalse(
            contract["authorization_checks"][
                "local_unsupported_addition_absent"
            ]
        )

    def test_apply_and_final_surface_supersede_m29_but_keep_trace(self):
        authorization = {
            "schema": uapm.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
            "status": "semantically_authorized",
            "surface_authority": True,
            "literal_summary_jp": "明日試験がある。",
            "response_jp": "明日試験なんだ。",
            "surface_anchors_jp": ["明日", "試験"],
            "suppresses_new_pending_prediction": True,
            "raw_dialogue_persisted": False,
        }
        plan, applied = uapm.apply_semantic_authorization_m31(
            {
                "intent": "grounded_literal_topic_m29",
                "scene": "casual",
                "core_message_jp": "古い表面",
                "literal_topic_projection_m29": copy.deepcopy(self.projection),
            },
            authorization,
        )
        visible, audited = uapm.ensure_semantic_authorization_m31_reaches_surface(
            "別の下書き",
            plan,
        )

        self.assertEqual(visible, "明日試験なんだ。")
        self.assertEqual(audited["surface_status"], "matched")
        self.assertEqual(audited["surface_anchor_status"], "matched")
        self.assertEqual(
            plan["literal_topic_projection_m29"]["status"],
            "superseded_by_semantic_authorization_m31",
        )
        self.assertTrue(applied["plan_applied"])

    def test_literal_chinese_negation_is_no_longer_misclassified_as_correction(self):
        text = "今天不是星期五。"
        candidate = uapm.build_literal_topic_projection_candidate_m29(
            text,
            unlinked_feedback(),
            upl.build_human_pragmatic_understanding(text, turn_index=4),
        )

        self.assertEqual(candidate["status"], "projection_candidate")
        self.assertTrue(candidate["projection_required"])


if __name__ == "__main__":
    unittest.main()
