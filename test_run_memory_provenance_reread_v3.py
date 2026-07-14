import copy
import json
import re
import unittest
from pathlib import Path

from memory_evidence_ledger import LEDGER_SCHEMA
from run_memory_provenance_reread_v3 import (
    CONDITIONS,
    _evidence_recall,
    build_analysis,
    load_protocol,
    render_markdown,
    run_case,
    span_contract_answer,
)


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_provenance_reread_v3.json"


def generation(text):
    return {
        "text": text,
        "latency_seconds": 0.01,
        "prompt_tokens": 10,
        "completion_tokens": 5,
    }


def condition_artifact(*, answerable, treatment=False, span=False):
    semantic = True if answerable else None
    abstention = None if answerable else True
    return {
        "response": "valid",
        "metrics": {
            "answerable": answerable,
            "required_slot_span_hit": semantic,
            "polarity_hit": semantic,
            "relation_hit": semantic,
            "answerable_semantic_case_pass": semantic,
            "explicit_abstention": bool(abstention),
            "unanswerable_explicit_abstention": abstention,
            "overall_cognitive_case_pass": True,
            "unsafe_answer_on_unanswerable": False if not answerable else None,
            "false_abstention_on_answerable": False if answerable else None,
            "gold_user_evidence_quote_recall": 1.0,
            "authoritative_user_evidence_rate": 1.0,
            "assistant_fact_admission_rate": 0.0,
            "gate_sufficient": answerable if treatment else None,
            "primary_gate_triggered": (not answerable) if treatment else None,
            "fallback_triggered": not answerable if treatment else False,
            "fallback_recovered": False if treatment and not answerable else None,
            "fallback_trigger_valid": True,
            "structured_parse_ok": True,
            "grounded_quote_pass": True,
            "full_context_restoration_exact": True,
            "markup_repair_attempt_count": 0,
            "markup_repair_success_count": 0,
            "all_markup_repairs_grounded": True,
            "ledger_grounded": True,
            "span_contract_valid": True if span and answerable else None,
            "span_slot_complete": True if span and answerable else None,
            "span_grounded": True if span and answerable else None,
            "span_source_records_grounded": True if span and answerable else None,
            "empty_response": False,
            "latency_seconds": 0.1,
            "prompt_tokens": 10,
            "completion_tokens": 2,
        },
    }


def result_row(scenario_id, split, position, answerable, capability):
    return {
        "case_id": f"{scenario_id}__{position}",
        "scenario_id": scenario_id,
        "split": split,
        "capability": capability,
        "evidence_position": position,
        "conditions": {
            CONDITIONS[0]: condition_artifact(answerable=answerable),
            CONDITIONS[1]: condition_artifact(answerable=answerable, treatment=True),
            CONDITIONS[2]: condition_artifact(answerable=answerable, treatment=True),
            CONDITIONS[3]: condition_artifact(
                answerable=answerable, treatment=True, span=True
            ),
        },
    }


def complete_synthetic_rows():
    rows = []
    scenarios = (
        ("dev_answer", "development", True, "location"),
        ("dev_unknown", "development", False, "unanswerable_location"),
        ("transfer_answer", "transfer", True, "count"),
        ("transfer_unknown", "transfer", False, "unanswerable_count"),
    )
    for scenario_id, split, answerable, capability in scenarios:
        for position in ("beginning", "middle", "end"):
            rows.append(result_row(scenario_id, split, position, answerable, capability))
    return rows


class RunMemoryProvenanceRereadV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_frozen_protocol_loads_and_verifies_hashes(self):
        protocol, dataset, dataset_path = load_protocol()
        self.assertEqual(dataset_path, DATASET)
        self.assertEqual(len(dataset["cases"]), 48)
        self.assertEqual(protocol["dataset"]["cases_sha256"], dataset["cases_sha256"])

    def test_insufficient_span_path_abstains_without_model_call(self):
        case = self.dataset["cases"][0]
        called = []

        def chat(*_args, **_kwargs):
            called.append(True)
            return generation("should not run")

        artifact = span_contract_answer(
            case,
            {"events": []},
            {"sufficient": False},
            chat,
            "I do not have enough grounded user evidence to answer that.",
        )
        self.assertEqual(called, [])
        self.assertTrue(artifact["used_explicit_abstention"])
        self.assertEqual(artifact["validation"]["errors"], ["evidence_gate_insufficient"])

    def test_evidence_recall_accepts_shortest_verbatim_sentence_not_paraphrase(self):
        case = {
            "gold": {
                "required_evidence_quotes": [
                    "No, that was only your guess. I keep them in the bottom pantry drawer now."
                ]
            }
        }
        shortest = {
            "events": [
                {
                    "source_role": "user",
                    "source_quote": "I keep them in the bottom pantry drawer now.",
                }
            ]
        }
        paraphrase = {
            "events": [
                {
                    "source_role": "user",
                    "source_quote": "The cards are stored in a lower pantry compartment.",
                }
            ]
        }
        self.assertEqual(_evidence_recall(case, shortest), 1.0)
        self.assertEqual(_evidence_recall(case, paraphrase), 0.0)

    def test_run_case_rereads_only_after_primary_insufficiency_and_repairs_markup(self):
        case = next(
            case
            for case in self.dataset["cases"]
            if case["scenario_id"] == "dev_recipe_cards_current_location"
            and case["evidence_position"] == "middle"
        )
        answer_quote = case["gold"]["required_evidence_quotes"][0]
        attribute = case["question_frame"]["attribute"]
        calls = []

        def chat(prompt, **_kwargs):
            calls.append(prompt)
            if prompt.rstrip().endswith("Grounded evidence JSON:"):
                if "<memory-highlight" not in prompt:
                    return generation(json.dumps({"relevant": False, "facts": []}))
                tagged = re.search(
                    r'(<memory-highlight rank="\d+">No, that was only your guess\. '
                    r'I keep them in the bottom pantry drawer now\.</memory-highlight>)',
                    prompt,
                )
                self.assertIsNotNone(tagged)
                return generation(
                    json.dumps(
                        {
                            "relevant": True,
                            "facts": [
                                {
                                    "source_role": "user",
                                    "quote": tagged.group(1),
                                    "attribute": attribute,
                                }
                            ],
                        }
                    )
                )
            if prompt.rstrip().endswith("Evidence ledger JSON:"):
                has_fact = answer_quote in prompt
                events = (
                    [
                        {
                            "date": case["session"]["timestamp"],
                            "session_id": case["session"]["session_id"],
                            "source_role": "user",
                            "source_quote": answer_quote,
                            "attribute": attribute,
                            "claim": "bottom pantry drawer",
                            "value": "bottom pantry drawer",
                            "value_role": "location",
                            "relation": "adds",
                        }
                    ]
                    if has_fact
                    else []
                )
                return generation(
                    json.dumps(
                        {
                            "schema": LEDGER_SCHEMA,
                            "events": events,
                            "current_event_indices": [0] if events else [],
                            "superseded_event_indices": [],
                            "historical_event_indices": [0] if events else [],
                            "uncertainties": [],
                        }
                    )
                )
            if prompt.rstrip().endswith("Source bindings JSON:"):
                return generation(
                    json.dumps(
                        {
                            "bindings": [
                                {
                                    "slot": "current",
                                    "source_index": 0,
                                    "answer_span": "bottom pantry drawer",
                                }
                            ],
                            "polarity": "none",
                        }
                    )
                )
            if prompt.rstrip().endswith("Answer:"):
                if answer_quote in prompt:
                    return generation("bottom pantry drawer.")
                return generation("I cannot determine that from the evidence.")
            raise AssertionError(prompt[-200:])

        result = run_case(
            case,
            chat,
            4,
            "I do not have enough grounded user evidence to answer that.",
        )

        provenance = result["conditions"][CONDITIONS[1]]
        adaptive = result["conditions"][CONDITIONS[2]]
        span = result["conditions"][CONDITIONS[3]]
        self.assertFalse(provenance["gate"]["sufficient"])
        self.assertTrue(adaptive["fallback_triggered"])
        self.assertTrue(adaptive["gate"]["sufficient"])
        self.assertEqual(adaptive["response"], "bottom pantry drawer.")
        self.assertEqual(adaptive["metrics"]["markup_repair_attempt_count"], 1)
        self.assertTrue(adaptive["metrics"]["all_markup_repairs_grounded"])
        self.assertEqual(adaptive["metrics"]["assistant_event_count"], 0)
        self.assertTrue(adaptive["metrics"]["overall_cognitive_case_pass"])
        self.assertTrue(span["span_contract"]["validation"]["valid"])
        self.assertTrue(span["metrics"]["overall_cognitive_case_pass"])
        self.assertEqual(
            sum("<memory-highlight" in prompt for prompt in calls),
            1,
        )

    def test_complete_nonregressing_results_pass_every_frozen_gate(self):
        rows = complete_synthetic_rows()
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 20260716}}
        analysis = build_analysis(rows, protocol, complete=True)
        self.assertTrue(analysis["all_gates_pass"])
        self.assertEqual(analysis["decision"], "eligible_for_new_untouched_evaluation")
        self.assertTrue(all(analysis["gates"].values()))

    def test_partial_pilot_without_transfer_rows_is_incomplete_not_an_error(self):
        rows = complete_synthetic_rows()[:2]
        protocol = {"dataset": {"case_count": 48}, "inference": {"seed": 20260716}}
        analysis = build_analysis(rows, protocol, complete=False)
        self.assertFalse(analysis["all_gates_pass"])
        self.assertFalse(
            analysis["gates"]["adaptive_transfer_answerable_pass_not_lower_than_control"]
        )
        self.assertEqual(analysis["decision"], "incomplete")

    def test_adaptive_regression_fails_split_family_and_position_gates(self):
        rows = complete_synthetic_rows()
        regressed = copy.deepcopy(rows)
        metrics = regressed[0]["conditions"][CONDITIONS[2]]["metrics"]
        metrics["answerable_semantic_case_pass"] = False
        metrics["overall_cognitive_case_pass"] = False
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 20260716}}
        analysis = build_analysis(regressed, protocol, complete=True)
        self.assertFalse(
            analysis["gates"]["adaptive_development_answerable_pass_not_lower_than_control"]
        )
        self.assertFalse(
            analysis["gates"]["no_capability_family_regression_adaptive_vs_control"]
        )
        self.assertFalse(
            analysis["gates"]["position_invariance_not_lower_adaptive_vs_control"]
        )
        self.assertEqual(analysis["decision"], "reject_v3_runtime_integration")

    def test_markdown_names_all_four_conditions_and_runtime_boundary(self):
        rows = complete_synthetic_rows()
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 20260716}}
        report = {
            "complete": True,
            "completed_case_count": len(rows),
            "expected_case_count": len(rows),
            "model_evidence": {"name": "test", "digest": "sha256:test"},
            "results": rows,
            **build_analysis(rows, protocol, complete=True),
        }
        markdown = render_markdown(report)
        for condition in CONDITIONS:
            self.assertIn(condition, markdown)
        self.assertIn("Runtime integration remains unauthorized", markdown)


if __name__ == "__main__":
    unittest.main()
