import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import build_memory_utterance_attention_cases_v1 as builder


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_utterance_attention_v1.json"
PREREGISTRATION = (
    ROOT / "configs" / "memory_utterance_attention_v1_preregistration.json"
)


class MemoryUtteranceAttentionCasesV1Test(unittest.TestCase):
    def test_checked_in_dataset_is_reproducible_and_hash_bound(self):
        checked_in = json.loads(DATASET.read_text(encoding="utf-8"))
        preregistration = json.loads(PREREGISTRATION.read_text(encoding="utf-8"))

        self.assertEqual(checked_in, builder.build_payload())
        self.assertEqual(
            hashlib.sha256(DATASET.read_bytes()).hexdigest(),
            preregistration["dataset"]["file_sha256"],
        )
        self.assertEqual(
            checked_in["cases_sha256"],
            preregistration["dataset"]["cases_sha256"],
        )

    def test_splits_are_source_separated_and_positions_are_matched(self):
        payload = builder.build_payload()
        scenarios_by_split = {"development": set(), "transfer": set()}
        positions_by_scenario = {}
        for case in payload["cases"]:
            scenarios_by_split[case["split"]].add(case["scenario_id"])
            positions_by_scenario.setdefault(case["scenario_id"], set()).add(
                case["evidence_position"]
            )

        self.assertTrue(
            scenarios_by_split["development"].isdisjoint(
                scenarios_by_split["transfer"]
            )
        )
        self.assertEqual(len(scenarios_by_split["development"]), 6)
        self.assertEqual(len(scenarios_by_split["transfer"]), 6)
        for positions in positions_by_scenario.values():
            self.assertEqual(positions, set(builder.POSITIONS))

    def test_every_gold_quote_and_span_is_source_grounded(self):
        for case in builder.build_payload()["cases"]:
            session = case["session"]["text"]
            for quote in case["gold"]["attention_quotes"]:
                self.assertIn(f"User: {quote}", session, case["case_id"])
            for span in case["gold"]["answer_spans"]:
                self.assertIn(span.lower(), session.lower(), case["case_id"])

    def test_builder_output_is_byte_stable(self):
        payload = builder.build_payload()
        expected = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cases.json"
            output.write_text(expected, encoding="utf-8")
            self.assertEqual(output.read_bytes(), DATASET.read_bytes())


if __name__ == "__main__":
    unittest.main()
