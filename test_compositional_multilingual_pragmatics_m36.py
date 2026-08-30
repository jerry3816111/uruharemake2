import json
import unittest

from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_adaptive_person_model import classify_explicit_desired_response_m25
from uruha_functional_understanding import semantic_features
from uruha_memory_observatory import collect_cognitive_graph, render_memory_observatory


class CompositionalMultilingualPragmaticsM36Tests(unittest.TestCase):
    def test_response_form_classifier_composes_unseen_modifiers(self):
        examples = {
            "先聽我把整段講完，不要給建議。": "listen_presence",
            "先給我一個現在就能做的小步驟。": "solve_regulation",
            "別追問，陪我待一會。": "share_arousal",
            "輕鬆吐槽我一句。": "playful_tease",
            "Let me finish before you offer advice.": "listen_presence",
            "Give me one small practical thing to try.": "solve_regulation",
            "Stay nearby without asking questions.": "share_arousal",
            "Give me a gentle roast.": "playful_tease",
            "話が終わるまで聞いて、解決しようとしなくていい。": "listen_presence",
            "一つの手順を教えて。": "solve_regulation",
            "何も聞かず、少しここにいて。": "share_arousal",
            "短いツッコミを入れて。": "playful_tease",
        }
        for text, expected in examples.items():
            with self.subTest(text=text):
                result = classify_explicit_desired_response_m25(text)
                self.assertEqual(result["selected_policy"], expected)
                self.assertEqual(result["authority"], "current_explicit_desired_response")

    def test_arousal_detection_allows_bounded_words_between_head_and_predicate(self):
        examples = (
            "想法一個接一個完全停不住。",
            "My ideas are still circling even after midnight.",
            "頭が今も全然止まってくれない。",
            "頭がまだずっと回りっぱなし。",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertIn("ambiguous_mood", semantic_features(text))

    def test_exposed_m35_english_solve_and_japanese_adverb_regressions(self):
        en_brain = _IsolatedContractBrain()
        en_brain.run_turn_debug(
            "When my thoughts keep racing, tell me what I should do first."
        )
        en_brain.run_turn_debug("That's right; keep that approach.")
        en_current = en_brain.run_turn_debug(
            "My thoughts keep racing even though it's late."
        )
        en_ledger = en_current["runtime_trace"]["counterfactual_pragmatic_branch_m34"]
        self.assertEqual(en_ledger["selected_branch"]["policy_id"], "solve_regulation")
        self.assertEqual(
            en_ledger["selected_branch"]["authority_basis"],
            "verified_reversible_context",
        )

        ja_brain = _IsolatedContractBrain()
        ja_brain.run_turn_debug("頭が止まらないって言ったら、軽くいじって。")
        ja_brain.run_turn_debug("そうそう、その通り。")
        ja_current = ja_brain.run_turn_debug("今夜は頭がずっと止まらない。")
        ja_ledger = ja_current["runtime_trace"]["counterfactual_pragmatic_branch_m34"]
        ja_m36 = ja_current["runtime_trace"]["compositional_pragmatic_cue_m36"]
        self.assertEqual(ja_ledger["selected_branch"]["policy_id"], "playful_tease")
        self.assertEqual(
            ja_ledger["selected_branch"]["authority_basis"],
            "verified_reversible_context",
        )
        self.assertEqual(ja_m36["status"], "compositional_arousal_detected")
        graph = collect_cognitive_graph(ja_current)
        self.assertIn(
            "compositional_pragmatic_cue_m36",
            {node["label"] for node in graph["nodes"]},
        )
        self.assertIn(
            "COMPOSITIONAL MULTILINGUAL PRAGMATIC CUES · M36",
            render_memory_observatory(ja_current),
        )

    def test_leading_no_or_chigau_requires_an_explicit_replacement(self):
        en_brain = _IsolatedContractBrain()
        en_brain.run_turn_debug("When my mind races, tease me.")
        en_brain.run_turn_debug("Exactly.")
        en_brain.run_turn_debug("My mind is racing again tonight.")
        corrected = en_brain.run_turn_debug(
            "No—give me one concrete step this time."
        )
        corrected_ledger = corrected["runtime_trace"]["counterfactual_pragmatic_branch_m34"]
        self.assertEqual(
            corrected_ledger["previous_branch_verification"]["status"],
            "contradicted",
        )
        self.assertEqual(
            corrected_ledger["revision"]["replacement_policy_id"],
            "solve_regulation",
        )

        no_target_brain = _IsolatedContractBrain()
        no_target_brain.run_turn_debug("When my mind races, tease me.")
        no_target_brain.run_turn_debug("Exactly.")
        no_target_brain.run_turn_debug("My mind is racing again tonight.")
        no_target = no_target_brain.run_turn_debug(
            "No idea why, but the hallway light just flickered."
        )
        no_target_ledger = no_target["runtime_trace"]["counterfactual_pragmatic_branch_m34"]
        self.assertEqual(
            no_target_ledger["previous_branch_verification"]["status"],
            "uncertain",
        )
        self.assertEqual(no_target_ledger["revision"]["status"], "no_revision")

        ja_brain = _IsolatedContractBrain()
        ja_brain.run_turn_debug("頭が止まらない時は、そばにいて。")
        ja_brain.run_turn_debug("そうそう、その通り。")
        ja_brain.run_turn_debug("頭がまだ止まらない。")
        ja_no_target = ja_brain.run_turn_debug("違う、外は雨みたい。")
        ja_ledger = ja_no_target["runtime_trace"]["counterfactual_pragmatic_branch_m34"]
        self.assertEqual(ja_ledger["previous_branch_verification"]["status"], "uncertain")
        self.assertFalse(
            json.dumps(ja_brain.runtime.adaptive_person_model, ensure_ascii=False).find(
                "違う、外は雨みたい。"
            )
            >= 0
        )


if __name__ == "__main__":
    unittest.main()
