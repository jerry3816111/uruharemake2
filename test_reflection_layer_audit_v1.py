import json
import unittest
from pathlib import Path

from reflection_layer_audit_v1 import (
    japanese_surface_report,
    parse_judgments,
    response_schema,
    score_rows,
    summarize,
)


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads(
    (ROOT / "configs" / "reflection_layer_audit_v1_preregistration.json").read_text(
        encoding="utf-8"
    )
)
DATASET = json.loads(
    (ROOT / "datasets" / "reflection_layer_audit_v1_calibration.json").read_text(
        encoding="utf-8"
    )
)


def perfect_rows():
    return [
        {
            "case": case,
            "schema_valid": True,
            "judgments": {
                claim["id"]: claim["gold_relation"] for claim in case["claims"]
            },
            "raw_response": "{}",
        }
        for case in DATASET["cases"]
    ]


class ReflectionLayerAuditV1Test(unittest.TestCase):
    def test_dynamic_schema_and_parser_require_exact_claims(self):
        case = DATASET["cases"][0]
        schema = response_schema(case)
        expected = {claim["id"] for claim in case["claims"]}
        self.assertEqual(set(schema["required"]), expected)
        payload = {claim_id: "entailed" for claim_id in expected}
        self.assertEqual(parse_judgments(json.dumps(payload), case), payload)
        with self.assertRaisesRegex(ValueError, "schema_keys"):
            parse_judgments(json.dumps({**payload, "extra": "missing"}), case)

    def test_surface_check_allows_source_quote_and_rejects_unknown_chinese(self):
        clean = japanese_surface_report(
            "『give me a minute』は考える時間が必要という意味だ。",
            "When I say 'give me a minute', I need time to think.",
        )
        polluted = japanese_surface_report(
            "『どっちでも』表示决定疲劳，所以一案だけ出す。",
            "私が『どっちでも』と言う時は、決めるのに疲れている。",
        )
        self.assertTrue(clean["clean"])
        self.assertFalse(polluted["clean"])
        self.assertTrue(polluted["unknown_cjk_fragments"])

    def test_perfect_synthetic_rows_pass_every_gate(self):
        summary = summarize(score_rows(perfect_rows()), CONFIG, model_call_count=12)
        self.assertTrue(summary["all_gates_pass"])
        self.assertEqual(summary["atomic_relation_accuracy"], 1.0)
        self.assertEqual(summary["candidate_acceptance_accuracy"], 1.0)

    def test_false_entailment_for_critical_error_fails_closed(self):
        rows = perfect_rows()
        corrupted = next(row for row in rows if not row["case"]["expected_accept"])
        claim = next(
            claim
            for claim in corrupted["case"]["claims"]
            if claim["gold_relation"] != "entailed"
        )
        corrupted["judgments"][claim["id"]] = "entailed"
        summary = summarize(score_rows(rows), CONFIG, model_call_count=12)
        self.assertFalse(summary["all_gates_pass"])
        self.assertEqual(summary["critical_false_entailment_count"], 1)


if __name__ == "__main__":
    unittest.main()
