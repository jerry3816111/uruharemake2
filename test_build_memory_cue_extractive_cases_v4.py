import json
import unittest
from pathlib import Path

from build_memory_cue_extractive_cases_v4 import build_payload
from memory_provenance_reread import evaluate_evidence_sufficiency
from memory_utterance_attention import rank_user_utterances
from run_longmemeval_retrieval_benchmark import file_sha256


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_cue_extractive_v4.json"
PREREGISTRATION = ROOT / "configs" / "memory_cue_extractive_v4_preregistration.json"
OLD_DATASETS = (
    ROOT / "datasets" / "memory_utterance_attention_v1.json",
    ROOT / "datasets" / "memory_highlight_span_v2.json",
    ROOT / "datasets" / "memory_provenance_reread_v3.json",
)


def raw_candidate_ledger(case, selected):
    events = [
        {
            "date": case["session"]["timestamp"],
            "session_id": case["session"]["session_id"],
            "source_role": "user",
            "source_quote": row["text"],
            "attribute": case["question_frame"]["attribute"],
            "claim": row["text"],
            "value": row["text"],
            "value_role": "state",
            "relation": "none",
        }
        for row in selected
    ]
    return {
        "schema": "uruha_memory_evidence_ledger_v3",
        "events": events,
        "current_event_indices": list(range(len(events))),
        "superseded_event_indices": [],
        "historical_event_indices": list(range(len(events))),
        "uncertainties": [],
    }


class BuildMemoryCueExtractiveCasesV4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        cls.protocol = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))

    def test_frozen_dataset_is_exactly_reproducible_and_hash_bound(self):
        rebuilt = build_payload()
        self.assertEqual(rebuilt, self.dataset)
        self.assertEqual(file_sha256(DATASET), self.protocol["dataset"]["file_sha256"])
        self.assertEqual(rebuilt["cases_sha256"], self.protocol["dataset"]["cases_sha256"])

    def test_balanced_source_separated_design(self):
        cases = self.dataset["cases"]
        self.assertEqual(len(cases), 48)
        self.assertEqual(sum(row["gold"]["answerable"] for row in cases), 36)
        self.assertEqual(sum(not row["gold"]["answerable"] for row in cases), 12)
        self.assertEqual(sum(row["split"] == "development" for row in cases), 24)
        self.assertEqual(sum(row["split"] == "transfer" for row in cases), 24)
        scenarios = {}
        for row in cases:
            scenarios.setdefault(row["scenario_id"], set()).add(row["evidence_position"])
        self.assertEqual(len(scenarios), 16)
        self.assertTrue(all(value == {"beginning", "middle", "end"} for value in scenarios.values()))

    def test_no_scenario_or_question_reuse_from_v1_v2_v3(self):
        old_cases = []
        for path in OLD_DATASETS:
            old_cases.extend(json.loads(path.read_text(encoding="utf-8"))["cases"])
        self.assertFalse(
            {row["scenario_id"] for row in self.dataset["cases"]}
            & {row["scenario_id"] for row in old_cases}
        )
        self.assertFalse(
            {row["question"] for row in self.dataset["cases"]}
            & {row["question"] for row in old_cases}
        )

    def test_gold_quotes_are_exactly_role_grounded(self):
        for case in self.dataset["cases"]:
            user_lines = {
                line.removeprefix("User: ")
                for line in case["session"]["text"].splitlines()
                if line.startswith("User: ")
            }
            assistant_lines = {
                line.removeprefix("Assistant: ")
                for line in case["session"]["text"].splitlines()
                if line.startswith("Assistant: ")
            }
            self.assertTrue(set(case["gold"]["required_evidence_quotes"]) <= user_lines)
            self.assertTrue(set(case["gold"]["assistant_decoy_quotes"]) <= assistant_lines)

    def test_selector_audit_is_frozen_without_tuning(self):
        hits = total = selected_count = false_positive_count = 0
        for case in self.dataset["cases"]:
            selected = rank_user_utterances(
                case["question"], case["question_frame"], case["session"]["text"], limit=4
            )
            selected_text = {row["text"] for row in selected}
            gold = case["gold"]["attention_quotes"]
            hits += sum(quote in selected_text for quote in gold)
            total += len(gold)
            selected_count += len(selected)
            false_positive_count += sum(text not in gold for text in selected_text)
        frozen = self.protocol["frozen_preimplementation_components"]["selector"]
        self.assertEqual((hits, total, selected_count, false_positive_count), (91, 96, 96, 5))
        self.assertEqual(hits, frozen["gold_utterance_hits"])
        self.assertFalse(frozen["tuning_on_v4_allowed"])

    def test_candidate_sufficiency_audit_preserves_known_misses(self):
        answerable_sufficient = unanswerable_insufficient = 0
        mismatches = []
        for case in self.dataset["cases"]:
            selected = rank_user_utterances(
                case["question"], case["question_frame"], case["session"]["text"], limit=4
            )
            gate = evaluate_evidence_sufficiency(
                raw_candidate_ledger(case, selected), case["question_frame"]
            )
            answerable = case["gold"]["answerable"]
            answerable_sufficient += bool(answerable and gate["sufficient"])
            unanswerable_insufficient += bool(not answerable and not gate["sufficient"])
            if answerable != gate["sufficient"]:
                mismatches.append(case["case_id"])
        frozen = self.protocol["frozen_preimplementation_components"][
            "candidate_sufficiency_gate"
        ]
        self.assertEqual(answerable_sufficient, 33)
        self.assertEqual(unanswerable_insufficient, 12)
        self.assertEqual(mismatches, frozen["known_miss_case_ids"])
        self.assertFalse(frozen["tuning_on_v4_allowed"])


if __name__ == "__main__":
    unittest.main()
