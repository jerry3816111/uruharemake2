import json
import unittest
from pathlib import Path

from build_memory_highlight_span_cases_v2 import build_payload, canonical_sha256
from memory_utterance_attention import rank_user_utterances
from run_longmemeval_retrieval_benchmark import file_sha256


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_highlight_span_v2.json"
V1_DATASET = ROOT / "datasets" / "memory_utterance_attention_v1.json"
PROTOCOL = ROOT / "configs" / "memory_highlight_span_v2_preregistration.json"


class BuildMemoryHighlightSpanCasesV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))
        cls.v1 = json.loads(V1_DATASET.read_text(encoding="utf-8"))
        cls.protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    def test_frozen_dataset_is_exactly_reproducible(self):
        self.assertEqual(build_payload(), self.dataset)
        self.assertEqual(file_sha256(DATASET), self.protocol["dataset"]["file_sha256"])
        self.assertEqual(
            canonical_sha256(self.dataset["cases"]),
            self.protocol["dataset"]["cases_sha256"],
        )

    def test_balanced_source_separated_design(self):
        cases = self.dataset["cases"]
        self.assertEqual((self.dataset["scenario_count"], len(cases)), (12, 36))
        self.assertEqual(
            {case["evidence_position"] for case in cases},
            {"beginning", "middle", "end"},
        )
        self.assertEqual(sum(case["split"] == "development" for case in cases), 18)
        self.assertEqual(sum(case["split"] == "transfer" for case in cases), 18)
        for scenario_id in {case["scenario_id"] for case in cases}:
            variants = [case for case in cases if case["scenario_id"] == scenario_id]
            self.assertEqual(len(variants), 3)
            self.assertEqual(
                {case["evidence_position"] for case in variants},
                {"beginning", "middle", "end"},
            )

    def test_v2_does_not_reuse_v1_scenarios_or_questions(self):
        self.assertTrue(
            {case["scenario_id"] for case in self.dataset["cases"]}.isdisjoint(
                {case["scenario_id"] for case in self.v1["cases"]}
            )
        )
        self.assertTrue(
            {case["question"] for case in self.dataset["cases"]}.isdisjoint(
                {case["question"] for case in self.v1["cases"]}
            )
        )

    def test_every_gold_span_is_verbatim_source_evidence(self):
        for case in self.dataset["cases"]:
            source = case["session"]["text"]
            attention = case["gold"]["attention_quotes"]
            self.assertEqual(
                case["gold"]["answer_spans"],
                list(case["gold"]["slot_spans"].values()),
            )
            for quote in attention:
                self.assertIn(quote, source, case["case_id"])
            for span in case["gold"]["slot_spans"].values():
                self.assertTrue(
                    any(span in quote for quote in attention),
                    (case["case_id"], span),
                )

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
        self.assertEqual((gold_hits, gold_total), (72, 72))
        self.assertEqual(selected_count, 74)
        self.assertEqual(audit["selected_utterance_count"], selected_count)
        self.assertEqual(audit["false_positive_count"], selected_count - gold_hits)
        self.assertFalse(self.protocol["frozen_selector"]["tuning_on_v2_allowed"])


if __name__ == "__main__":
    unittest.main()
