import copy
import json
import unittest

import analyze_memory_utterance_attention_v1 as analyzer


class AnalyzeMemoryUtteranceAttentionV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(analyzer.DEFAULT_REPORT.read_text(encoding="utf-8"))

    def test_frozen_analysis_localizes_each_stage(self):
        analysis = analyzer.build_analysis(self.report)

        self.assertEqual(analysis["selection_stage"]["gold_utterance_hits"], 72)
        self.assertEqual(analysis["selection_stage"]["gold_utterance_total"], 72)
        self.assertEqual(
            len(analysis["extraction_stage"]["attention_only_missing_case_ids"]), 9
        )
        self.assertEqual(
            analysis["answer_stage"]["proposition_failure_categories"],
            {
                "model_owned_contract_field_invalid": 6,
                "semantic_pass": 14,
                "single_event_cannot_express_before_and_current": 6,
                "upstream_evidence_or_ledger_missing": 9,
                "valid_contract_but_strict_span_metric_miss": 1,
            },
        )
        self.assertEqual(
            analysis["answer_stage"]["admitted_proposition_claim_count"], 27
        )
        self.assertEqual(
            analysis["answer_stage"]["admitted_proposition_span_grounding_rate"],
            1.0,
        )
        self.assertEqual(analysis["decision"], "reject_v1_runtime_integration")

    def test_tampered_results_fail_closed(self):
        tampered = copy.deepcopy(self.report)
        tampered["results"][0]["question"] = "tampered"

        with self.assertRaisesRegex(ValueError, "results_sha256_matches"):
            analyzer.verify_report(tampered)


if __name__ == "__main__":
    unittest.main()
