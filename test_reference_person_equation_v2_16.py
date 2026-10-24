import unittest

from uruha_reference_person_equation import (
    POLICIES,
    REFERENCE_PERSON,
    apply_user_feedback,
    build_case_solution,
    case_choices,
    intervene_atom,
    load_case,
    load_case_bundle,
    solve_equation,
    state_from_case,
)


class ReferencePersonEquationV216Tests(unittest.TestCase):
    def test_same_observed_input_routes_to_six_distinct_desired_response_policies(self):
        bundle = load_case_bundle()
        inputs = set()
        selected = set()
        for _label, case_id in case_choices():
            case, solution = build_case_solution(case_id)
            inputs.add(case["current_input"])
            selected.add(solution["selected"]["policy_id"])
            self.assertEqual(solution["selected"]["policy_id"], case["gold_policy"])

        self.assertEqual(inputs, {bundle["shared_current_input"]})
        self.assertEqual(selected, set(POLICIES))

    def test_reference_person_is_a_replaceable_human_instantiation_not_surface_claim(self):
        self.assertIn("replaceable", REFERENCE_PERSON["role"])
        self.assertEqual(len(REFERENCE_PERSON["evidence_refs"]), 4)
        self.assertEqual(
            REFERENCE_PERSON["evidence_role"],
            "development_only_not_independent_persona_holdout",
        )
        self.assertIn("private_mental_state", REFERENCE_PERSON["unknown_space"])

    def test_single_atom_counterfactual_changes_the_equation_choice(self):
        state = state_from_case(load_case("v216_unknown_calibrate"))
        before = solve_equation(state)
        after_state = intervene_atom(
            state,
            "solution_request",
            1.0,
            1.0,
            "counterfactual explicit solution request",
        )
        after = solve_equation(after_state)

        self.assertEqual(before["selected"]["policy_id"], "calibrate_need")
        self.assertEqual(after["selected"]["policy_id"], "solve_regulation")
        self.assertEqual(after_state["intervention_history"][-1]["atom"], "solution_request")

    def test_explicit_tease_feedback_updates_named_atoms_and_changes_policy(self):
        state = state_from_case(load_case("v216_unknown_calibrate"))
        feedback = "不是要方法啦，我是在等你吐槽我，平常不是都會互相吐槽嗎？"
        updated, changes = apply_user_feedback(state, feedback)
        solution = solve_equation(updated)
        changed_atoms = {change["atom"] for change in changes}

        self.assertEqual(solution["selected"]["policy_id"], "playful_tease")
        self.assertIn("humor_invitation", changed_atoms)
        self.assertIn("relationship_familiarity", changed_atoms)
        self.assertIn("solution_request", changed_atoms)
        self.assertNotIn("global_confidence", changed_atoms)
        self.assertGreater(
            updated["atoms"]["humor_invitation"]["value"],
            state["atoms"]["humor_invitation"]["value"],
        )

    def test_unknown_state_stays_conservative_and_does_not_diagnose(self):
        _case, solution = build_case_solution("v216_unknown_calibrate")
        selected = solution["selected"]

        self.assertEqual(selected["policy_id"], "calibrate_need")
        self.assertNotIn("多動症", selected["core_message_jp"])
        self.assertNotIn("病気", selected["core_message_jp"])

    def test_candidate_score_keeps_desire_persona_evidence_and_risk_separate(self):
        _case, solution = build_case_solution("v216_playful_tease")
        candidate = solution["selected"]

        self.assertEqual(candidate["policy_id"], "playful_tease")
        self.assertIn("desired_response_fit", candidate)
        self.assertIn("reference_person_fit", candidate)
        self.assertIn("evidence_quality", candidate)
        self.assertIn("risk_penalty", candidate)
        self.assertGreaterEqual(len(candidate["persona_evidence_refs"]), 1)

    def test_equation_is_pure_and_never_writes_production_memory(self):
        for _label, case_id in case_choices():
            _case, solution = build_case_solution(case_id)
            self.assertEqual(solution["production_memory_write_count"], 0)
            self.assertEqual(solution["state"]["production_memory_write_count"], 0)


if __name__ == "__main__":
    unittest.main()
