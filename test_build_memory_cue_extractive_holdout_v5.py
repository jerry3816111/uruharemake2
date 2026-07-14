import json
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path

from build_memory_cue_extractive_holdout_v5 import (
    POSITIONS,
    build_payload,
    main,
)
from memory_utterance_attention import parse_dialogue_turns
from memory_utterance_attention import rank_user_utterances
from memory_cue_extractive import build_candidate_artifact
from run_longmemeval_retrieval_benchmark import canonical_sha256, file_sha256


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_cue_extractive_holdout_v5.json"
PREREGISTRATION = (
    ROOT / "configs" / "memory_cue_extractive_holdout_v5_preregistration.json"
)
PRIOR_DATASETS = (
    ROOT / "datasets" / "memory_utterance_attention_v1.json",
    ROOT / "datasets" / "memory_highlight_span_v2.json",
    ROOT / "datasets" / "memory_provenance_reread_v3.json",
    ROOT / "datasets" / "memory_cue_extractive_v4.json",
)


class BuildMemoryCueExtractiveHoldoutV5Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = build_payload()

    def test_balanced_unseen_holdout_design(self):
        cases = self.payload["cases"]
        self.assertEqual(len(cases), 72)
        self.assertEqual(len({row["scenario_id"] for row in cases}), 24)
        self.assertEqual(Counter(row["split"] for row in cases), {"holdout_a": 36, "holdout_b": 36})
        self.assertEqual(sum(row["gold"]["answerable"] for row in cases), 54)
        self.assertEqual(sum(not row["gold"]["answerable"] for row in cases), 18)

        positions = defaultdict(set)
        for row in cases:
            positions[row["scenario_id"]].add(row["evidence_position"])
        self.assertTrue(all(value == set(POSITIONS) for value in positions.values()))

        answerable_capabilities = Counter(
            row["capability"] for row in cases if row["gold"]["answerable"]
        )
        self.assertEqual(
            answerable_capabilities,
            {
                "current_count": 9,
                "current_location": 9,
                "previous_frequency": 9,
                "change_direction": 9,
                "historical_yes_no": 9,
                "current_time": 9,
            },
        )

    def test_no_exact_scenario_or_question_reuse_from_v1_through_v4(self):
        prior_scenarios = set()
        prior_questions = set()
        for path in PRIOR_DATASETS:
            payload = json.loads(path.read_text(encoding="utf-8"))
            prior_scenarios.update(row["scenario_id"] for row in payload["cases"])
            prior_questions.update(row["question"] for row in payload["cases"])
        current_scenarios = {row["scenario_id"] for row in self.payload["cases"]}
        current_questions = {row["question"] for row in self.payload["cases"]}
        self.assertFalse(current_scenarios & prior_scenarios)
        self.assertFalse(current_questions & prior_questions)

    def test_gold_quotes_are_role_grounded(self):
        for row in self.payload["cases"]:
            turns = parse_dialogue_turns(row["session"]["text"])
            users = {turn["text"] for turn in turns if turn["role"] == "user"}
            assistants = {
                turn["text"] for turn in turns if turn["role"] == "assistant"
            }
            self.assertTrue(set(row["gold"]["required_evidence_quotes"]) <= users)
            self.assertTrue(set(row["gold"]["attention_quotes"]) <= users)
            self.assertTrue(set(row["gold"]["assistant_decoy_quotes"]) <= assistants)
            self.assertFalse(set(row["gold"]["assistant_decoy_quotes"]) & users)

    def test_checked_in_dataset_is_byte_reproducible(self):
        checked_in = json.loads(DATASET.read_text(encoding="utf-8"))
        self.assertEqual(checked_in, self.payload)
        self.assertEqual(checked_in["cases_sha256"], self.payload["cases_sha256"])

    def test_preregistration_binds_dataset_and_frozen_v4_treatment(self):
        protocol = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
        self.assertEqual(file_sha256(DATASET), protocol["dataset"]["file_sha256"])
        self.assertEqual(
            canonical_sha256(self.payload["cases"]),
            protocol["dataset"]["cases_sha256"],
        )
        for component in protocol["frozen_v4_treatment"].values():
            if not isinstance(component, dict) or "path" not in component:
                continue
            self.assertEqual(file_sha256(ROOT / component["path"]), component["sha256"])

    def test_preimplementation_audit_is_reproducible_without_model_calls(self):
        protocol = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))
        audit = protocol["preimplementation_audit"]
        quote_hits = 0
        quote_total = 0
        selected_count = 0
        false_positive_count = 0
        answerable_sufficient = 0
        unanswerable_insufficient = 0
        answerable_total = 0
        unanswerable_total = 0
        for case in self.payload["cases"]:
            selected = rank_user_utterances(
                case["question"],
                case["question_frame"],
                case["session"]["text"],
                limit=4,
            )
            selected_text = {row["text"] for row in selected}
            gold = set(case["gold"]["required_evidence_quotes"])
            quote_hits += len(selected_text & gold)
            quote_total += len(gold)
            selected_count += len(selected)
            false_positive_count += len(selected_text - gold)
            sufficient = build_candidate_artifact(case, selected)["gate"]["sufficient"]
            if case["gold"]["answerable"]:
                answerable_total += 1
                answerable_sufficient += int(sufficient)
            else:
                unanswerable_total += 1
                unanswerable_insufficient += int(not sufficient)
        self.assertEqual(quote_hits, audit["selected_required_quote_hits"])
        self.assertEqual(quote_total, audit["selected_required_quote_total"])
        self.assertEqual(selected_count, audit["selected_utterance_count"])
        self.assertEqual(false_positive_count, audit["selected_false_positive_count"])
        self.assertEqual(
            answerable_sufficient,
            audit["candidate_gate_answerable_sufficient_count"],
        )
        self.assertEqual(answerable_total, audit["candidate_gate_answerable_total"])
        self.assertEqual(
            unanswerable_insufficient,
            audit["candidate_gate_unanswerable_insufficient_count"],
        )
        self.assertEqual(
            unanswerable_total, audit["candidate_gate_unanswerable_total"]
        )


if __name__ == "__main__":
    unittest.main()
