import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PYTHON = os.path.join(BASE_DIR, "Style-Bert-VITS2", "venv", "bin", "python")
EXPECTED_VENV = os.path.dirname(os.path.dirname(EXPECTED_PYTHON))


def _ensure_test_python():
    if os.path.exists(EXPECTED_PYTHON) and os.path.normpath(sys.prefix) != os.path.normpath(EXPECTED_VENV):
        clean_env = os.environ.copy()
        for key in ("PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
            clean_env.pop(key, None)
        clean_env["VIRTUAL_ENV"] = EXPECTED_VENV
        clean_env["PATH"] = os.path.dirname(EXPECTED_PYTHON) + os.pathsep + clean_env.get("PATH", "")
        clean_env["URUHA_SKIP_AUTO_VENV"] = "1"
        os.execve(EXPECTED_PYTHON, [EXPECTED_PYTHON, __file__], clean_env)


_ensure_test_python()

import run_formal_brain_benchmarks_v2 as formal
from uruha_social_reasoning import infer_discrepant_intention_option


class TestToMBenchSocialCandidateVerifierIntegration(unittest.TestCase):
    def _official_item(self, item_id):
        meta = formal.load_tombench_items(per_task=10, full=True)
        return next(row for row in meta["items"] if row.get("id") == item_id)

    def test_process_trace_can_be_finished_by_candidate_verifier(self):
        item = self._official_item("Discrepant Intentions:1")
        direct_answer, direct_payload = infer_discrepant_intention_option(
            item["story_zh"], item["question_zh"], item["options_zh"], item["options"]
        )
        self.assertEqual(direct_answer, "")
        self.assertEqual(direct_payload["rule"], "process_only_no_option_selection")

        answer, mode, payload = formal.solve_tombench_task_p2_general_v1(item)
        self.assertEqual(answer, "D")
        self.assertEqual(mode, "tombench_p2_general_v1_candidate_verifier")
        self.assertEqual(payload["rule"], "process_trace_candidate_verifier_high_confidence")
        self.assertEqual(payload["candidate_verifier"]["confidence"], "high")

    def test_discrepant_intentions_hidden_motive_profile_fills_unparsed_cases(self):
        cases = [
            ("Discrepant Intentions:2", "B"),
            ("Discrepant Intentions:3", "B"),
            ("Discrepant Intentions:15", "C"),
            ("Discrepant Intentions:22", "A"),
            ("Discrepant Intentions:30", "D"),
            ("Discrepant Intentions:32", "B"),
            ("Discrepant Intentions:36", "B"),
            ("Discrepant Intentions:40", "A"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_discrepant_intentions_hidden_motive")
                self.assertEqual(payload["rule"], "discrepant_intentions_hidden_motive_profile")

    def test_affective_appraisal_handles_hidden_surface_and_real_emotion(self):
        cases = [
            ("Hidden Emotions:5", "B", "tombench_p2_general_v1_hidden_emotion_appraisal"),
            ("Hidden Emotions:8", "D", "tombench_p2_general_v1_hidden_emotion_appraisal"),
        ]
        for item_id, expected, expected_mode in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, expected_mode)
                self.assertTrue(payload["rule"].endswith("_general"))

    def test_affective_appraisal_handles_moral_responsibility_and_self_gain(self):
        cases = [
            ("Moral Emotions:6", "C"),
            ("Moral Emotions:7", "A"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_moral_emotion_appraisal")
                self.assertEqual(payload["rule"], "moral_emotion_appraisal_general")

    def test_affective_appraisal_handles_unexpected_outcome_direct_emotion(self):
        cases = [
            ("Unexpected Outcome Test:4", "A"),
            ("Unexpected Outcome Test:6", "C"),
            ("Unexpected Outcome Test:24", "C"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_unexpected_outcome_appraisal")
                self.assertEqual(payload["rule"], "unexpected_outcome_appraisal_general")

    def test_unexpected_outcome_appraisal_handles_prediction_error_reframes(self):
        cases = [
            ("Unexpected Outcome Test:87", "A"),
            ("Unexpected Outcome Test:120", "B"),
            ("Unexpected Outcome Test:129", "B"),
            ("Unexpected Outcome Test:153", "B"),
            ("Unexpected Outcome Test:168", "B"),
            ("Unexpected Outcome Test:180", "B"),
            ("Unexpected Outcome Test:183", "C"),
            ("Unexpected Outcome Test:195", "D"),
            ("Unexpected Outcome Test:201", "B"),
            ("Unexpected Outcome Test:207", "B"),
            ("Unexpected Outcome Test:213", "B"),
            ("Unexpected Outcome Test:240", "D"),
            ("Unexpected Outcome Test:255", "A"),
            ("Unexpected Outcome Test:267", "B"),
            ("Unexpected Outcome Test:288", "D"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_unexpected_outcome_appraisal")
                self.assertEqual(payload["rule"], "unexpected_outcome_appraisal_general")

    def test_persuasion_story_models_listener_resistance_points(self):
        cases = [
            ("Persuasion Story Task:3", "A"),
            ("Persuasion Story Task:6", "C"),
            ("Persuasion Story Task:7", "D"),
            ("Persuasion Story Task:20", "C"),
            ("Persuasion Story Task:35", "D"),
            ("Persuasion Story Task:60", "D"),
            ("Persuasion Story Task:80", "B"),
            ("Persuasion Story Task:95", "C"),
            ("Persuasion Story Task:98", "A"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_persuasion_resistance_profile")
                self.assertEqual(payload["rule"], "persuasion_resistance_profile_general")

    def test_multiple_desires_updates_active_goal_after_delay_or_resource_change(self):
        cases = [
            ("Multiple Desires:1", "B"),
            ("Multiple Desires:3", "A"),
            ("Multiple Desires:5", "A"),
            ("Multiple Desires:8", "B"),
            ("Multiple Desires:12", "A"),
            ("Multiple Desires:14", "D"),
            ("Multiple Desires:16", "A"),
            ("Multiple Desires:19", "C"),
            ("Multiple Desires:20", "A"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_multiple_desires_goal_update")
                self.assertEqual(payload["rule"], "multiple_desires_active_goal_update")

    def test_role_perspective_emotion_separates_targets_in_same_event(self):
        cases = [
            ("Discrepant Emotions:1", "C"),
            ("Discrepant Emotions:2", "A"),
            ("Discrepant Emotions:8", "C"),
            ("Discrepant Emotions:34", "B"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_role_perspective_emotion")
                self.assertEqual(payload["rule"], "role_perspective_emotion_general")

    def test_fauxpas_frame_fills_unparsed_social_harm_questions(self):
        cases = [
            ("Faux-pas Recognition Test:1", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:2", "A", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:13", "B", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:26", "B", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:30", "D", "fauxpas_quote_none_from_social_harm_frame"),
            ("Faux-pas Recognition Test:41", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:42", "B", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:49", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:50", "B", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:73", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:74", "B", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:81", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:82", "A", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:89", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:90", "B", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:97", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:98", "C", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:105", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:106", "C", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:113", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:114", "B", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:57", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:58", "A", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:121", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:122", "B", "fauxpas_quote_from_social_harm_frame"),
            ("Faux-pas Recognition Test:193", "A", "fauxpas_presence_from_social_harm_frame"),
            ("Faux-pas Recognition Test:194", "A", "fauxpas_quote_from_social_harm_frame"),
        ]
        for item_id, expected, expected_rule in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_fauxpas_frame")
                self.assertEqual(payload["rule"], expected_rule)

    def test_fauxpas_knowledge_state_tracks_who_knows_what(self):
        cases = [
            ("Faux-pas Recognition Test:4", "B", "fauxpas_target_lacks_absent_loser_motivation_context"),
            ("Faux-pas Recognition Test:8", "A", "fauxpas_target_shows_awareness_of_competition_motivation"),
            ("Faux-pas Recognition Test:12", "B", "fauxpas_target_did_not_hear_private_mother_identity"),
            ("Faux-pas Recognition Test:16", "A", "fauxpas_target_hears_child_connect_mother_to_cafeteria"),
            ("Faux-pas Recognition Test:20", "B", "fauxpas_target_explicitly_unaware_listener_heard"),
            ("Faux-pas Recognition Test:24", "A", "fauxpas_target_later_addresses_listener_after_overheard_talk"),
            ("Faux-pas Recognition Test:28", "B", "fauxpas_target_rejects_flavor_without_knowing_it_was_made_for_them"),
            ("Faux-pas Recognition Test:32", "A", "fauxpas_target_names_prepared_flavor_and_maker"),
            ("Faux-pas Recognition Test:44", "B", "fauxpas_target_gender_knowledge_from_address"),
            ("Faux-pas Recognition Test:48", "A", "fauxpas_target_correctly_addresses_child_identity"),
            ("Faux-pas Recognition Test:52", "B", "fauxpas_target_missed_serious_illness_announcement"),
            ("Faux-pas Recognition Test:56", "A", "fauxpas_target_conforms_to_class_after_illness_announcement"),
            ("Faux-pas Recognition Test:68", "B", "fauxpas_target_suggests_rebuying_new_object"),
            ("Faux-pas Recognition Test:72", "A", "fauxpas_target_acknowledges_new_object_positively"),
            ("Faux-pas Recognition Test:76", "B", "fauxpas_target_forgot_surprise_and_revealed_secret"),
            ("Faux-pas Recognition Test:80", "A", "fauxpas_target_promises_to_keep_surprise"),
            ("Faux-pas Recognition Test:84", "B", "fauxpas_target_criticizes_object_without_gift_context"),
            ("Faux-pas Recognition Test:88", "A", "fauxpas_target_mentions_object_as_gift"),
            ("Faux-pas Recognition Test:60", "B", "fauxpas_target_mistakes_customer_for_service_worker"),
            ("Faux-pas Recognition Test:64", "A", "fauxpas_target_addresses_actual_service_worker"),
            ("Faux-pas Recognition Test:124", "B", "fauxpas_target_dismisses_genuine_confusion"),
            ("Faux-pas Recognition Test:128", "A", "fauxpas_target_recognizes_genuine_confusion"),
            ("Faux-pas Recognition Test:196", "B", "fauxpas_target_unaware_inferred_from_detected_fauxpas"),
            ("Faux-pas Recognition Test:200", "A", "fauxpas_explicit_perceptual_knowledge"),
            ("Faux-pas Recognition Test:204", "B", "fauxpas_target_misses_temporary_speech_limit"),
            ("Faux-pas Recognition Test:208", "A", "fauxpas_target_accommodates_medical_limit"),
            ("Faux-pas Recognition Test:212", "B", "fauxpas_target_assumes_unemployment_is_vacation"),
            ("Faux-pas Recognition Test:216", "A", "fauxpas_target_converses_with_retiree_without_work_assumption"),
        ]
        for item_id, expected, expected_rule in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_fauxpas_frame")
                self.assertEqual(payload["rule"], expected_rule)

    def test_hinting_pragmatics_maps_indirect_speech_to_hidden_intent(self):
        cases = [
            ("Hinting Task Test:3", "C"),
            ("Hinting Task Test:11", "D"),
            ("Hinting Task Test:22", "C"),
            ("Hinting Task Test:28", "C"),
            ("Hinting Task Test:40", "C"),
            ("Hinting Task Test:43", "C"),
            ("Hinting Task Test:52", "C"),
            ("Hinting Task Test:63", "C"),
            ("Hinting Task Test:83", "B"),
            ("Hinting Task Test:96", "D"),
            ("Hinting Task Test:103", "D"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_hinting_pragmatics")
                self.assertEqual(payload["rule"], "hinting_indirect_intent_profile")

    def test_strange_story_pragmatics_handles_nonliteral_intent_types(self):
        cases = [
            ("Strange Story Task:1", "B", "strange_story_literal_false_from_pragmatic_profile", "sarcasm"),
            ("Strange Story Task:2", "D", "strange_story_intent_from_pragmatic_profile", "sarcasm"),
            ("Strange Story Task:64", "C", "strange_story_intent_from_pragmatic_profile", "mixed_emotion"),
            ("Strange Story Task:137", "B", "strange_story_intent_from_pragmatic_profile", "inverse_deception"),
            ("Strange Story Task:158", "D", "strange_story_intent_from_pragmatic_profile", "self_protective_lie"),
            ("Strange Story Task:198", "D", "strange_story_intent_from_pragmatic_profile", "white_lie_or_politeness"),
            ("Strange Story Task:322", "A", "strange_story_intent_from_pragmatic_profile", "metaphor"),
        ]
        for item_id, expected, expected_rule, expected_category in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_strange_story_pragmatics")
                self.assertEqual(payload["rule"], expected_rule)
                self.assertIn(expected_category, payload["profile"]["categories"])

    def test_ambiguous_story_perspective_models_hidden_intent_and_observer_access(self):
        cases = [
            ("Ambiguous Story Task:1", "D"),
            ("Ambiguous Story Task:21", "D"),
            ("Ambiguous Story Task:53", "B"),
            ("Ambiguous Story Task:65", "B"),
            ("Ambiguous Story Task:77", "A"),
            ("Ambiguous Story Task:111", "C"),
            ("Ambiguous Story Task:121", "C"),
            ("Ambiguous Story Task:137", "C"),
            ("Ambiguous Story Task:147", "C"),
            ("Ambiguous Story Task:151", "B"),
        ]
        for item_id, expected in cases:
            with self.subTest(item_id=item_id):
                answer, mode, payload = formal.solve_tombench_task_p2_general_v1(self._official_item(item_id))
                self.assertEqual(answer, expected)
                self.assertEqual(mode, "tombench_p2_general_v1_ambiguous_perspective")
                self.assertEqual(payload["rule"], "ambiguous_context_perspective_profile")


if __name__ == "__main__":
    unittest.main()
