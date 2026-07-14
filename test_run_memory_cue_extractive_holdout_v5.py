import unittest

from run_memory_cue_extractive_holdout_v5 import (
    CONDITIONS,
    CONTROL,
    CUE,
    PROVENANCE,
    REREAD,
    build_analysis,
    load_protocol,
    render_markdown,
    run_case,
)
from run_memory_cue_extractive_v4 import run_case as frozen_v4_run_case


ABSTENTION = "I do not have enough grounded user evidence to answer that."


def artifact(*, answerable, passed, fallback=False, candidate=False, latency=1.0):
    semantic = passed if answerable else None
    return {
        "response": "valid" if answerable and passed else ABSTENTION,
        "metrics": {
            "answerable": answerable,
            "required_slot_span_hit": semantic,
            "polarity_hit": semantic,
            "relation_hit": semantic,
            "answerable_semantic_case_pass": semantic,
            "explicit_abstention": not answerable or not passed,
            "unanswerable_explicit_abstention": passed if not answerable else None,
            "overall_cognitive_case_pass": passed,
            "unsafe_answer_on_unanswerable": False if not answerable else None,
            "false_abstention_on_answerable": not passed if answerable else None,
            "gold_user_evidence_quote_recall": 1.0,
            "authoritative_user_evidence_rate": 1.0,
            "assistant_fact_admission_rate": 0.0,
            "gate_sufficient": answerable and passed,
            "primary_gate_triggered": fallback,
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
            "span_grounded": None,
            "span_source_records_grounded": None,
            "empty_response": False,
            "candidate_gate_sufficient": answerable if candidate and fallback else None,
            "candidate_context_user_source_rate": 1.0 if candidate and fallback else None,
            "candidate_context_exact_source_rate": 1.0 if candidate and fallback else None,
            "candidate_assistant_turn_admission_rate": 0.0 if candidate and fallback else None,
            "candidate_count": 2 if candidate and fallback else None,
            "latency_seconds": latency,
            "prompt_tokens": int(latency * 100),
            "completion_tokens": 10,
        },
    }


def synthetic_rows():
    rows = []
    scenarios = (
        ("recover_a", "holdout_a", True, "current_time", True),
        ("recover_b", "holdout_b", True, "current_location", True),
        ("stable_a", "holdout_a", True, "current_count", False),
        ("unknown_b", "holdout_b", False, "unanswerable_count", True),
    )
    for scenario, split, answerable, capability, fallback in scenarios:
        for position in ("beginning", "middle", "end"):
            provenance_pass = (not fallback) if answerable else True
            rows.append(
                {
                    "case_id": f"{scenario}__{position}",
                    "scenario_id": scenario,
                    "split": split,
                    "capability": capability,
                    "evidence_position": position,
                    "gold": {"answerable": answerable},
                    "conditions": {
                        CONTROL: artifact(answerable=answerable, passed=provenance_pass),
                        PROVENANCE: artifact(
                            answerable=answerable,
                            passed=provenance_pass,
                            fallback=False,
                        ),
                        REREAD: artifact(
                            answerable=answerable,
                            passed=True,
                            fallback=fallback,
                            latency=2.0,
                        ),
                        CUE: artifact(
                            answerable=answerable,
                            passed=True,
                            fallback=fallback,
                            candidate=True,
                            latency=1.0,
                        ),
                    },
                }
            )
    return rows


class RunMemoryCueExtractiveHoldoutV5Test(unittest.TestCase):
    def test_protocol_loads_and_treatment_is_exact_v4_function(self):
        protocol, dataset, _path = load_protocol()
        self.assertEqual(len(dataset["cases"]), 72)
        self.assertEqual(protocol["dataset"]["case_count"], 72)
        self.assertIs(run_case, frozen_v4_run_case)

    def test_two_split_recovery_passes_every_gate(self):
        rows = synthetic_rows()
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 17}}
        analysis = build_analysis(rows, protocol, complete=True)
        self.assertTrue(analysis["all_gates_pass"])
        self.assertTrue(all(analysis["gates"].values()))
        self.assertEqual(
            analysis["decision"],
            "eligible_for_separate_shadow_integration_review_only",
        )
        self.assertEqual(analysis["recovery_audit"]["distinct_scenario_count"], 2)

    def test_one_split_recovery_is_efficiency_only(self):
        rows = synthetic_rows()
        for row in rows:
            if row["scenario_id"] == "recover_b":
                for condition in (REREAD, CUE):
                    metrics = row["conditions"][condition]["metrics"]
                    metrics["answerable_semantic_case_pass"] = False
                    metrics["overall_cognitive_case_pass"] = False
                    metrics["fallback_semantic_recovered"] = False
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 17}}
        analysis = build_analysis(rows, protocol, complete=True)
        self.assertTrue(analysis["quality_and_safety_pass"])
        self.assertFalse(analysis["all_gates_pass"])
        self.assertEqual(analysis["decision"], "replicated_efficiency_only_no_runtime")

    def test_unsafe_unanswerable_answer_rejects_integration(self):
        rows = synthetic_rows()
        for row in rows:
            if row["scenario_id"] == "unknown_b":
                metrics = row["conditions"][CUE]["metrics"]
                metrics["unanswerable_explicit_abstention"] = False
                metrics["unsafe_answer_on_unanswerable"] = True
                metrics["overall_cognitive_case_pass"] = False
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 17}}
        analysis = build_analysis(rows, protocol, complete=True)
        self.assertFalse(analysis["quality_and_safety_pass"])
        self.assertEqual(analysis["decision"], "reject_v5_integration")

    def test_markdown_preserves_shadow_only_boundary(self):
        rows = synthetic_rows()
        protocol = {"dataset": {"case_count": len(rows)}, "inference": {"seed": 17}}
        analysis = build_analysis(rows, protocol, complete=True)
        report = {
            "complete": True,
            "completed_case_count": len(rows),
            "expected_case_count": len(rows),
            "decision": analysis["decision"],
            "results": rows,
            **analysis,
        }
        markdown = render_markdown(report)
        for condition in CONDITIONS:
            self.assertIn(condition.split("_")[0], markdown)
        self.assertIn("off-by-default shadow integration", markdown)
        self.assertIn("Active runtime change authorized: `False`", markdown)


if __name__ == "__main__":
    unittest.main()
