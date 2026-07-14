import json
import unittest
from pathlib import Path

from build_memory_provenance_reread_cases_v3 import build_payload, canonical_sha256
from memory_utterance_attention import rank_user_utterances
from run_longmemeval_retrieval_benchmark import file_sha256


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_provenance_reread_v3.json"
V1_DATASET = ROOT / "datasets" / "memory_utterance_attention_v1.json"
V2_DATASET = ROOT / "datasets" / "memory_highlight_span_v2.json"
PROTOCOL = ROOT / "configs" / "memory_provenance_reread_v3_preregistration.json"


class BuildMemoryProvenanceRereadCasesV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        cls.v1 = json.loads(V1_DATASET.read_text(encoding="utf-8"))
        cls.v2 = json.loads(V2_DATASET.read_text(encoding="utf-8"))
        cls.protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    def test_frozen_dataset_is_exactly_reproducible(self):
        self.assertEqual(build_payload(), self.dataset)
        self.assertEqual(file_sha256(DATASET), self.protocol["dataset"]["file_sha256"])
        self.assertEqual(
            canonical_sha256(self.dataset["cases"]),
            self.protocol["dataset"]["cases_sha256"],
        )

    def test_balanced_answerable_and_abstention_design(self):
        cases = self.dataset["cases"]
        self.assertEqual((self.dataset["scenario_count"], len(cases)), (16, 48))
        self.assertEqual(sum(case["gold"]["answerable"] for case in cases), 36)
        self.assertEqual(sum(case["gold"]["expected_abstention"] for case in cases), 12)
        self.assertEqual(sum(case["split"] == "development" for case in cases), 24)
        self.assertEqual(sum(case["split"] == "transfer" for case in cases), 24)
        for scenario_id in {case["scenario_id"] for case in cases}:
            variants = [case for case in cases if case["scenario_id"] == scenario_id]
            self.assertEqual(len(variants), 3)
            self.assertEqual(
                {case["evidence_position"] for case in variants},
                {"beginning", "middle", "end"},
            )

    def test_v3_does_not_reuse_v1_or_v2_scenarios_or_questions(self):
        v3_ids = {case["scenario_id"] for case in self.dataset["cases"]}
        v3_questions = {case["question"] for case in self.dataset["cases"]}
        for previous in (self.v1, self.v2):
            self.assertTrue(
                v3_ids.isdisjoint({case["scenario_id"] for case in previous["cases"]})
            )
            self.assertTrue(
                v3_questions.isdisjoint({case["question"] for case in previous["cases"]})
            )

    def test_gold_evidence_is_user_grounded_and_decoys_are_assistant_grounded(self):
        for case in self.dataset["cases"]:
            source = case["session"]["text"]
            for quote in case["gold"]["attention_quotes"]:
                self.assertIn(f"User: {quote}", source, case["case_id"])
            for quote in case["gold"]["required_evidence_quotes"]:
                self.assertIn(f"User: {quote}", source, case["case_id"])
            for quote in case["gold"]["assistant_decoy_quotes"]:
                self.assertIn(f"Assistant: {quote}", source, case["case_id"])
            if case["gold"]["answerable"]:
                self.assertTrue(case["gold"]["slot_spans"])
                for span in case["gold"]["slot_spans"].values():
                    self.assertTrue(
                        any(
                            span in quote
                            for quote in case["gold"]["required_evidence_quotes"]
                        ),
                        (case["case_id"], span),
                    )
            else:
                self.assertEqual(case["gold"]["slot_spans"], {})
                self.assertEqual(case["gold"]["polarity"], "unknown")

    def test_frozen_selector_audit_is_reproduced_without_tuning(self):
        selected_count = 0
        gold_hits = 0
        gold_total = 0
        for case in self.dataset["cases"]:
            selected = rank_user_utterances(
                case["question"],
                case["question_frame"],
                case["session"]["text"],
                limit=self.protocol["inference"]["highlight_limit"],
            )
            selected_text = [row["text"] for row in selected]
            gold = case["gold"]["attention_quotes"]
            selected_count += len(selected)
            gold_hits += sum(quote in selected_text for quote in gold)
            gold_total += len(gold)

        audit = self.protocol["frozen_selector"]["known_preimplementation_audit"]
        self.assertEqual((gold_hits, gold_total, selected_count), (96, 96, 96))
        self.assertEqual(audit["gold_utterance_hits"], gold_hits)
        self.assertEqual(audit["selected_utterance_count"], selected_count)
        self.assertFalse(self.protocol["frozen_selector"]["tuning_on_v3_allowed"])


if __name__ == "__main__":
    unittest.main()
