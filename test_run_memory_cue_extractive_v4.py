import copy
import json
import unittest
from pathlib import Path

from memory_evidence_ledger import LEDGER_SCHEMA
from run_memory_cue_extractive_v4 import (
    CONDITIONS,
    build_analysis,
    load_protocol,
    render_markdown,
    run_case,
)


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


def synthetic_artifact(
    *, answerable, passed, treatment=False, fallback=False, candidate=False, latency=1.0
):
    abstained = bool(not answerable and passed) or bool(answerable and not passed)
    semantic = passed if answerable else None
    return {
        "response": "valid" if passed and answerable else ABSTENTION,
        "metrics": {
            "answerable": answerable,
            "required_slot_span_hit": semantic,
            "polarity_hit": semantic,
            "relation_hit": semantic,
            "answerable_semantic_case_pass": semantic,
            "explicit_abstention": abstained,
            "unanswerable_explicit_abstention": passed if not answerable else None,
            "overall_cognitive_case_pass": passed,
            "unsafe_answer_on_unanswerable": False if not answerable else None,
            "false_abstention_on_answerable": (not passed) if answerable else None,
            "gold_user_evidence_quote_recall": 1.0,
            "authoritative_user_evidence_rate": 1.0,
            "assistant_fact_admission_rate": 0.0,
            "gate_sufficient": answerable and passed if treatment else None,
            "primary_gate_triggered": fallback if treatment else None,
            "fallback_triggered": fallback,
            "fallback_recovered": answerable and passed if fallback else None,
            "fallback_trigger_valid": True,
            "fallback_semantic_recovered": (
                answerable and passed if fallback and answerable else None
            ),
            "structured_parse_ok": True,
            "grounded_quote_pass": True,
            "full_context_restoration_exact": True,
            "markup_repair_attempt_count": 0,
            "markup_repair_success_count": 0,
            "all_markup_repairs_grounded": True,
            "ledger_grounded": True,
            "span_contract_valid": None,
            "span_slot_complete": None,
            "span_grounded": None,
            "span_source_records_grounded": None,
            "empty_response": False,
            "candidate_gate_sufficient": (
                answerable and passed if candidate and fallback else None
            ),
            "candidate_context_user_source_rate": (
                1.0 if candidate and fallback else None
            ),
            "candidate_context_exact_source_rate": (
                1.0 if candidate and fallback else None
            ),
            "candidate_assistant_turn_admission_rate": (
                0.0 if candidate and fallback else None
            ),
            "candidate_count": 2 if candidate and fallback else None,
            "latency_seconds": latency,
            "prompt_tokens": int(latency * 100),
            "completion_tokens": 10,
        },
    }


def synthetic_rows():
    rows = []
    scenarios = (
        ("dev_answer", "development", True, "count", False),
        ("dev_unknown", "development", False, "unanswerable_count", False),
        ("transfer_answer", "transfer", True, "location", True),
        ("transfer_unknown", "transfer", False, "unanswerable_location", False),
    )
    for scenario, split, answerable, capability, primary_answerable in scenarios:
        for position in ("beginning", "middle", "end"):
            primary_pass = primary_answerable if answerable else True
            fallback = not primary_answerable if answerable else True
            rows.append(
                {
                    "case_id": f"{scenario}__{position}",
                    "scenario_id": scenario,
                    "split": split,
                    "capability": capability,
                    "evidence_position": position,
                    "conditions": {
                        CONDITIONS[0]: synthetic_artifact(
                            answerable=answerable, passed=primary_pass
                        ),
                        CONDITIONS[1]: synthetic_artifact(
                            answerable=answerable,
                            passed=primary_pass,
                            treatment=True,
                        ),
                        CONDITIONS[2]: synthetic_artifact(
                            answerable=answerable,
                            passed=primary_pass,
                            treatment=True,
                            fallback=fallback,
                            latency=2.0,
                        ),
                        CONDITIONS[3]: synthetic_artifact(
                            answerable=answerable,
                            passed=True,
                            treatment=True,
                            fallback=fallback,
                            candidate=True,
                            latency=1.0,
                        ),
                    },
                }
            )
    return rows


class RunMemoryCueExtractiveV4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_frozen_protocol_loads_and_verifies_component_hashes(self):
        protocol, dataset, dataset_path = load_protocol()
        self.assertEqual(dataset_path, DATASET)
        self.assertEqual(len(dataset["cases"]), 48)
        self.assertEqual(protocol["dataset"]["cases_sha256"], dataset["cases_sha256"])

    def test_run_case_uses_extractable_user_turn_when_both_ledgers_are_empty(self):
        case = next(
            row
            for row in self.dataset["cases"]
            if row["scenario_id"] == "dev_water_bottles_current_count"
            and row["evidence_position"] == "middle"
        )
        candidate_prompts = []
        highlighted_calls = 0

        def chat(prompt, **_kwargs):
            nonlocal highlighted_calls
            if prompt.rstrip().endswith("Grounded evidence JSON:"):
                highlighted_calls += int("<memory-highlight" in prompt)
                return generation(json.dumps({"relevant": False, "facts": []}))
            if prompt.rstrip().endswith("Evidence ledger JSON:"):
                return generation(
                    json.dumps(
                        {
                            "schema": LEDGER_SCHEMA,
                            "events": [],
                            "current_event_indices": [],
                            "superseded_event_indices": [],
                            "historical_event_indices": [],
                            "uncertainties": [],
                        }
                    )
                )
            if "Exact user-source records:" in prompt:
                candidate_prompts.append(prompt)
                return generation("seven")
            if prompt.rstrip().endswith("Answer:"):
                return generation(ABSTENTION)
            raise AssertionError(prompt[-240:])

        result = run_case(case, chat, 4, ABSTENTION)
        provenance = result["conditions"][CONDITIONS[1]]
        reread = result["conditions"][CONDITIONS[2]]
        cue = result["conditions"][CONDITIONS[3]]
        self.assertFalse(provenance["metrics"]["overall_cognitive_case_pass"])
        self.assertFalse(reread["metrics"]["overall_cognitive_case_pass"])
        self.assertTrue(cue["metrics"]["overall_cognitive_case_pass"])
        self.assertTrue(cue["metrics"]["fallback_semantic_recovered"])
        self.assertEqual(cue["response"], "seven")
        self.assertEqual(highlighted_calls, 1)
        self.assertEqual(len(candidate_prompts), 1)
        self.assertNotIn(case["gold"]["assistant_decoy_quotes"][0], candidate_prompts[0])
        self.assertEqual(cue["metrics"]["candidate_context_exact_source_rate"], 1.0)
        self.assertEqual(cue["metrics"]["candidate_assistant_turn_admission_rate"], 0.0)

    def test_complete_strict_gain_passes_every_preregistered_gate(self):
        rows = synthetic_rows()
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 20260717}}
        analysis = build_analysis(rows, protocol, complete=True)
        self.assertTrue(analysis["all_gates_pass"])
        self.assertTrue(all(analysis["gates"].values()))
        self.assertEqual(analysis["decision"], "eligible_for_new_untouched_evaluation")

    def test_cue_regression_rejects_promotion(self):
        rows = synthetic_rows()
        regressed = copy.deepcopy(rows)
        for row in regressed:
            if row["scenario_id"] == "transfer_answer":
                metrics = row["conditions"][CONDITIONS[3]]["metrics"]
                metrics["answerable_semantic_case_pass"] = False
                metrics["overall_cognitive_case_pass"] = False
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 20260717}}
        analysis = build_analysis(regressed, protocol, complete=True)
        self.assertFalse(
            analysis["gates"]["cue_transfer_answerable_not_lower_than_provenance"]
        )
        self.assertFalse(
            analysis["gates"]["no_capability_family_regression_cue_vs_provenance"]
        )
        self.assertEqual(analysis["decision"], "reject_v4_runtime_integration")

    def test_markdown_names_conditions_and_runtime_boundary(self):
        rows = synthetic_rows()
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 20260717}}
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
