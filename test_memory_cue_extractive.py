import json
import unittest
from pathlib import Path

from memory_cue_extractive import (
    answer_from_candidate_artifact,
    build_candidate_answer_prompt,
    build_candidate_artifact,
)
from memory_utterance_attention import rank_user_utterances


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_cue_extractive_v4.json"
ABSTENTION = "I do not have enough grounded user evidence to answer that."


def generation(text):
    return {
        "text": text,
        "latency_seconds": 0.01,
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }


class MemoryCueExtractiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    def case(self, scenario_id, position="middle"):
        return next(
            row
            for row in self.dataset["cases"]
            if row["scenario_id"] == scenario_id
            and row["evidence_position"] == position
        )

    def selected(self, case):
        return rank_user_utterances(
            case["question"], case["question_frame"], case["session"]["text"], limit=4
        )

    def test_candidate_artifact_keeps_only_exact_user_sources(self):
        case = self.case("dev_water_bottles_current_count")
        artifact = build_candidate_artifact(case, self.selected(case))
        audit = artifact["source_audit"]
        self.assertTrue(audit["all_candidates_exact_user_source"])
        self.assertEqual(audit["assistant_turn_admission_count"], 0)
        self.assertTrue(artifact["gate"]["sufficient"])
        self.assertFalse(artifact["gold_used"])

    def test_prompt_excludes_assistant_decoy_and_gold_metadata(self):
        case = self.case("dev_water_bottles_current_count")
        artifact = build_candidate_artifact(case, self.selected(case))
        prompt = build_candidate_answer_prompt(case, artifact["source_records"], ABSTENTION)
        self.assertNotIn(case["gold"]["assistant_decoy_quotes"][0], prompt)
        self.assertNotIn("slot_spans", prompt)
        self.assertNotIn("required_evidence_quotes", prompt)
        self.assertIn("the total is seven now", prompt)

    def test_uncertainty_only_candidate_abstains_without_model_call(self):
        case = self.case("dev_house_key_unknown_location")
        artifact = build_candidate_artifact(case, self.selected(case))
        calls = []

        def chat(*_args, **_kwargs):
            calls.append(True)
            return generation("should not run")

        answer = answer_from_candidate_artifact(case, artifact, chat, ABSTENTION)
        self.assertFalse(artifact["gate"]["sufficient"])
        self.assertEqual(calls, [])
        self.assertEqual(answer["response"], ABSTENTION)
        self.assertTrue(answer["used_explicit_abstention"])

    def test_sufficient_candidate_uses_one_source_only_answer_call(self):
        case = self.case("transfer_sketchbooks_current_count")
        artifact = build_candidate_artifact(case, self.selected(case))
        calls = []

        def chat(prompt, **kwargs):
            calls.append((prompt, kwargs))
            return generation("nine")

        answer = answer_from_candidate_artifact(case, artifact, chat, ABSTENTION)
        self.assertEqual(answer["response"], "nine")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]["max_tokens"], 220)
        self.assertNotIn(case["gold"]["assistant_decoy_quotes"][0], calls[0][0])


if __name__ == "__main__":
    unittest.main()
