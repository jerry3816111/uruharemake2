import json
import unittest

import uruha_counterfactual_pragmatic_branch_m34 as m34
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


CURRENT_DEV = "今晚腦子又停不下來了。"


def _trained_turn(seed):
    brain = _IsolatedContractBrain()
    brain.run_turn_debug(seed)
    brain.run_turn_debug("對，就是這樣。")
    return brain, brain.run_turn_debug(CURRENT_DEV)


class CounterfactualPragmaticBranchM34Tests(unittest.TestCase):
    def test_pure_ledger_separates_literal_observation_from_action_hypothesis(self):
        state = {
            "input_digest": "same-current-digest",
            "context_scope": {"scope_id": "arousal:state:unspecified"},
            "scope_match": {"status": "domain", "used": []},
            "learned_atoms_used": ["solution_request"],
            "verified_response_prior_atoms_m34": ["solution_request"],
        }
        decision = {
            "prediction_id": "m18-dev-1",
            "selected": {"policy_id": "solve_regulation", "expected_utility": 0.7},
            "candidates": [
                {"policy_id": "solve_regulation", "expected_utility": 0.7},
                {"policy_id": "listen_presence", "expected_utility": 0.5},
            ],
        }
        implicit = {
            "execute_implicit": True,
            "learned_relevant_atoms": ["solution_request"],
            "top_probability": 0.61,
            "uncertainty": 0.34,
            "distribution": [
                {
                    "policy_id": "solve_regulation",
                    "outcome_weighted_probability": 0.61,
                    "relevant_evidence": [
                        {
                            "atom": "solution_request",
                            "status": "learned_interaction_prior",
                            "evidence_quality": 0.42,
                            "learned_and_reversible": True,
                        }
                    ],
                },
                {
                    "policy_id": "listen_presence",
                    "outcome_weighted_probability": 0.22,
                    "relevant_evidence": [],
                },
            ],
        }
        ledger = m34.build_counterfactual_pragmatic_branch_m34(
            pragmatic_understanding={
                "pragmatic_label": "ambiguous_arousal",
                "acoustic_evidence": {
                    "availability": "not_applicable_text_input",
                    "reliable": False,
                },
            },
            desired_response_state=state,
            desired_response_decision=decision,
            implicit_response_contract=implicit,
            adaptive_feedback={},
            turn_index=3,
        )

        self.assertEqual(ledger["literal_observation"]["current_input_digest"], "same-current-digest")
        self.assertEqual(ledger["selected_branch"]["policy_id"], "solve_regulation")
        self.assertEqual(ledger["selected_branch"]["authority_basis"], "verified_reversible_context")
        self.assertEqual(ledger["bounded_alternative"]["policy_id"], "listen_presence")
        self.assertFalse(ledger["selected_branch"]["selection_is_private_state_fact"])
        self.assertFalse(ledger["evidence_boundary"]["unverified_mental_state_fact_write_allowed"])

    def test_same_current_utterance_changes_branch_only_after_verified_context(self):
        tease_brain, tease = _trained_turn("下次我說思緒轉個不停，吐槽我就好。")
        solve_brain, solve = _trained_turn("下次我說思緒轉個不停，給我方法。")
        tease_ledger = tease["runtime_trace"]["counterfactual_pragmatic_branch_m34"]
        solve_ledger = solve["runtime_trace"]["counterfactual_pragmatic_branch_m34"]

        self.assertEqual(
            tease_ledger["literal_observation"]["current_input_digest"],
            solve_ledger["literal_observation"]["current_input_digest"],
        )
        self.assertEqual(tease_ledger["selected_branch"]["policy_id"], "playful_tease")
        self.assertEqual(solve_ledger["selected_branch"]["policy_id"], "solve_regulation")
        self.assertEqual(tease_ledger["selected_branch"]["authority_basis"], "verified_reversible_context")
        self.assertEqual(solve_ledger["selected_branch"]["authority_basis"], "verified_reversible_context")
        self.assertEqual(tease_ledger["surface_status"], "matched")
        self.assertEqual(solve_ledger["surface_status"], "matched")
        self.assertNotEqual(tease["reply"], solve["reply"])
        self.assertNotIn(CURRENT_DEV, json.dumps(tease_brain.runtime.adaptive_person_model, ensure_ascii=False))
        self.assertNotIn(CURRENT_DEV, json.dumps(solve_brain.runtime.adaptive_person_model, ensure_ascii=False))

    def test_next_turn_contradiction_revokes_branch_without_rewriting_evidence(self):
        brain, selected = _trained_turn("下次我說思緒轉個不停，給我方法。")
        selected_branch = selected["runtime_trace"]["counterfactual_pragmatic_branch_m34"]
        corrected = brain.run_turn_debug("不是，我現在不要方法，只要聽我說。")
        ledger = corrected["runtime_trace"]["counterfactual_pragmatic_branch_m34"]

        self.assertEqual(selected_branch["selected_branch"]["policy_id"], "solve_regulation")
        self.assertEqual(ledger["previous_branch_verification"]["status"], "contradicted")
        self.assertEqual(ledger["revision"]["revoked_policy_id"], "solve_regulation")
        self.assertEqual(ledger["revision"]["replacement_policy_id"], "listen_presence")
        self.assertFalse(ledger["revision"]["original_evidence_rewritten"])
        self.assertEqual(ledger["selected_branch"]["policy_id"], "listen_presence")
        self.assertIn("読み違えた", corrected["reply"])

    def test_runtime_graph_shows_branch_prediction_verification_revision_and_surface(self):
        brain, _selected = _trained_turn("下次我說思緒轉個不停，給我方法。")
        corrected = brain.run_turn_debug("不是，我現在不要方法，只要聽我說。")
        graph = collect_cognitive_graph(corrected)
        labels = {node["label"] for node in graph["nodes"]}
        html = render_memory_observatory(corrected)

        self.assertTrue(
            {
                "pragmatic_branch_ledger_m34",
                "pragmatic_branch_prediction_m34",
                "pragmatic_branch_verification_m34",
                "pragmatic_branch_revision_m34",
                "pragmatic_branch_surface_m34",
            }.issubset(labels)
        )
        self.assertIn("COUNTERFACTUAL PRAGMATIC BRANCH LEDGER · M34", html)
        self.assertIn("solve_regulation→listen_presence", html)


if __name__ == "__main__":
    unittest.main()
