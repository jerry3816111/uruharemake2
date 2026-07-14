import copy
import json
import unittest
from pathlib import Path

from run_memory_highlight_span_v2 import (
    CONDITIONS,
    build_analysis,
    extract_note,
    load_protocol,
    render_markdown,
    span_contract_answer,
)


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_highlight_span_v2.json"


def generation(text):
    return {
        "text": text,
        "latency_seconds": 0.01,
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }


def condition_artifact(*, semantic=True, selected=False, span=False):
    return {
        "metrics": {
            "attention_selection_precision": 1.0 if selected else None,
            "attention_selection_recall": 1.0 if selected else None,
            "gold_evidence_quote_recall": 1.0,
            "required_slot_span_hit": semantic,
            "polarity_hit": True,
            "relation_hit": True,
            "semantic_case_pass": semantic,
            "structured_parse_ok": True,
            "grounded_quote_pass": True,
            "ledger_grounded": True,
            "full_context_restoration_exact": True,
            "empty_response": not semantic,
            "span_contract_valid": True if span else None,
            "span_slot_complete": True if span else None,
            "span_grounded": True if span else None,
            "span_source_records_grounded": True if span else None,
            "latency_seconds": 0.1,
            "prompt_tokens": 10,
            "completion_tokens": 2,
        }
    }


def result_row(scenario_id, split, position, capability="lookup"):
    return {
        "case_id": f"{scenario_id}__{position}",
        "scenario_id": scenario_id,
        "split": split,
        "capability": capability,
        "evidence_position": position,
        "conditions": {
            "full_session_freeform": condition_artifact(),
            "highlighted_full_session_freeform": condition_artifact(selected=True),
            "highlighted_full_session_span_contract": condition_artifact(
                selected=True, span=True
            ),
        },
    }


class RunMemoryHighlightSpanV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_frozen_protocol_loads_and_verifies_hashes(self):
        protocol, dataset, dataset_path = load_protocol()
        self.assertEqual(dataset_path, DATASET)
        self.assertEqual(len(dataset["cases"]), 36)
        self.assertEqual(protocol["dataset"]["cases_sha256"], dataset["cases_sha256"])

    def test_highlighted_note_keeps_full_context_and_grounds_original_quote(self):
        case = self.dataset["cases"][0]
        quote = case["gold"]["attention_quotes"][1]
        prompts = []

        def chat(prompt, **_kwargs):
            prompts.append(prompt)
            return generation(
                json.dumps(
                    {
                        "relevant": True,
                        "facts": [
                            {
                                "source_role": "user",
                                "quote": quote,
                                "attribute": case["question_frame"]["attribute"],
                            }
                        ],
                    }
                )
            )

        note = extract_note(case, chat, "highlighted_full_session", 4)

        self.assertTrue(note["context_restoration_exact"])
        self.assertTrue(note["quote_grounded"])
        self.assertIn("<memory-highlight", note["highlighted_context"])
        self.assertIn(quote, note["highlighted_context"])
        self.assertIn("Session Content:", prompts[0])

    def test_span_answer_reuses_grounded_ledger_and_model_only_binds(self):
        case = next(
            case
            for case in self.dataset["cases"]
            if case["scenario_id"] == "dev_study_time_increase"
        )
        quote = case["gold"]["attention_quotes"][1]
        ledger = {
            "events": [
                {
                    "date": case["session"]["timestamp"],
                    "session_id": case["session"]["session_id"],
                    "source_role": "user",
                    "source_quote": quote,
                    "attribute": case["question_frame"]["attribute"],
                }
            ]
        }
        prompts = []

        def chat(prompt, **_kwargs):
            prompts.append(prompt)
            return generation(
                json.dumps(
                    {
                        "bindings": [
                            {
                                "slot": "before",
                                "source_index": 0,
                                "answer_span": "four hours per week",
                            },
                            {
                                "slot": "current",
                                "source_index": 0,
                                "answer_span": "seven hours per week",
                            },
                        ],
                        "polarity": "none",
                    }
                )
            )

        artifact = span_contract_answer(case, ledger, chat)

        self.assertTrue(artifact["source_records_grounded"])
        self.assertTrue(artifact["validation"]["valid"])
        self.assertEqual(
            artifact["text"],
            "four hours per week -> seven hours per week; increase.",
        )
        self.assertIn('"required_slots": ["before", "current"]', prompts[0])
        self.assertNotIn("correct answer", prompts[0].lower())

    def test_complete_nonregressing_results_pass_every_frozen_gate(self):
        rows = []
        for scenario_id, split in (("dev", "development"), ("transfer", "transfer")):
            for position in ("beginning", "middle", "end"):
                rows.append(result_row(scenario_id, split, position))
        protocol = {"dataset": {"case_count": 6}, "inference": {"seed": 20260715}}

        analysis = build_analysis(rows, protocol, complete=True)

        self.assertTrue(analysis["all_gates_pass"])
        self.assertEqual(analysis["decision"], "eligible_for_new_untouched_evaluation")
        self.assertTrue(all(analysis["gates"].values()))

    def test_single_component_regression_fails_split_family_and_position_gates(self):
        rows = []
        for scenario_id, split in (("dev", "development"), ("transfer", "transfer")):
            for position in ("beginning", "middle", "end"):
                rows.append(result_row(scenario_id, split, position))
        regressed = copy.deepcopy(rows)
        regressed[0]["conditions"]["highlighted_full_session_freeform"]["metrics"][
            "semantic_case_pass"
        ] = False
        protocol = {"dataset": {"case_count": 6}, "inference": {"seed": 20260715}}

        analysis = build_analysis(regressed, protocol, complete=True)

        self.assertFalse(
            analysis["gates"][
                "highlight_development_semantic_pass_not_lower_than_control"
            ]
        )
        self.assertFalse(
            analysis["gates"]["no_capability_family_regression_for_either_change"]
        )
        self.assertFalse(
            analysis["gates"]["position_invariance_not_lower_for_either_change"]
        )
        self.assertEqual(analysis["decision"], "reject_v2_runtime_integration")

    def test_markdown_names_all_three_matched_conditions(self):
        rows = []
        for scenario_id, split in (("dev", "development"), ("transfer", "transfer")):
            for position in ("beginning", "middle", "end"):
                rows.append(result_row(scenario_id, split, position))
        protocol = {"dataset": {"case_count": 6}, "inference": {"seed": 20260715}}
        analysis = build_analysis(rows, protocol, complete=True)
        report = {
            "complete": True,
            "completed_case_count": 6,
            "expected_case_count": 6,
            "model_evidence": {"name": "test", "digest": "sha256:test"},
            "results": rows,
            **analysis,
        }

        markdown = render_markdown(report)

        for condition in CONDITIONS:
            self.assertIn(condition, markdown)
        self.assertIn("Runtime integration remains unauthorized", markdown)


if __name__ == "__main__":
    unittest.main()
