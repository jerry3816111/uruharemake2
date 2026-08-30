import json
import unittest

import uruha_semantic_commit_eval_m32 as evaluator


class SemanticCommitEvaluationM32Tests(unittest.TestCase):
    def test_sealed_reserve_hash_balance_and_contexts(self):
        protocol, dataset, _protocol_path, dataset_path = evaluator.load_dataset(
            evaluator.DEFAULT_PROTOCOL,
            "reserve",
        )
        cases = dataset["cases"]

        self.assertEqual(evaluator._sha256(dataset_path), protocol["reserve"]["sha256"])
        self.assertEqual(len(cases), 15)
        self.assertEqual(sum(row["authority_expected"] for row in cases), 12)
        self.assertEqual(
            {language: sum(row["language"] == language for row in cases)
             for language in ("zh", "en", "ja")},
            {"zh": 5, "en": 5, "ja": 5},
        )
        self.assertGreater(
            sum(row["candidate_context"] == "fresh_session" for row in cases),
            9,
        )

    def test_candidate_context_builds_fresh_and_previous_paths(self):
        fresh_case = {
            "input": "Nora lent Ken three books yesterday.",
            "candidate_context": "fresh_session",
        }
        previous_case = {
            "input": "Our flight moved to next Wednesday.",
            "candidate_context": "previous_unlinked_unknown",
        }

        fresh, _pragmatic, _transition = evaluator._candidate_for_case(fresh_case)
        previous, _pragmatic, _transition = evaluator._candidate_for_case(previous_case)

        self.assertTrue(fresh["projection_required"])
        self.assertEqual(fresh["candidate_context_m32"], "fresh_session")
        self.assertTrue(previous["projection_required"])
        self.assertEqual(
            previous["candidate_context_m32"],
            "previous_unlinked_unknown",
        )


if __name__ == "__main__":
    unittest.main()
