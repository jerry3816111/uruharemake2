#!/usr/bin/env python3
"""Attribute V2.13 failures with a zero-call gold-aware lexical oracle."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import run_source_preserving_memory_projection_v2_11_model_qa as v211
import run_source_preserving_memory_projection_v2_12_complete_session_ceiling as v212
from locomo_official_qa_f1 import STEMMER, f1_score, normalize_answer


ROOT = Path(__file__).resolve().parent
PREREG = (
    ROOT
    / "configs/source_preserving_memory_projection_v2_14_lexical_oracle_attribution_preregistration.json"
)
CONTROL = "qwen3.5:9b"
CANDIDATE = "qwen3.5:27b"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_preregistration(path=PREREG):
    return load_json(path)


def mean(values):
    return sum(values) / len(values) if values else 0.0


def official_tokens(value):
    return [STEMMER.stem(token) for token in normalize_answer(value).split()]


def token_f1(prediction_tokens, answer_tokens):
    common = Counter(prediction_tokens) & Counter(answer_tokens)
    same = sum(common.values())
    if same == 0 or not prediction_tokens or not answer_tokens:
        return 0.0
    precision = same / len(prediction_tokens)
    recall = same / len(answer_tokens)
    return 2 * precision * recall / (precision + recall)


def best_contiguous_source_span(source_text, answer):
    answer_tokens = official_tokens(answer)
    best = None
    for unit_index, source_unit in enumerate(str(source_text).splitlines()):
        source_tokens = official_tokens(source_unit)
        for start in range(len(source_tokens)):
            for end in range(start + 1, len(source_tokens) + 1):
                span = source_tokens[start:end]
                score = token_f1(span, answer_tokens)
                if score <= 0:
                    continue
                key = (score, -len(span), -unit_index, -start)
                if best is None or key > best[0]:
                    best = (key, unit_index, start, span)
    all_source_tokens = official_tokens(source_text)
    common = Counter(all_source_tokens) & Counter(answer_tokens)
    recall = sum(common.values()) / len(answer_tokens) if answer_tokens else 0.0
    if best is None:
        return {
            "official_f1": 0.0,
            "source_unit_index": None,
            "token_offset": None,
            "span_token_count": 0,
            "normalized_span_sha256": None,
            "whole_context_answer_token_recall": round(recall, 6),
            "answer_token_count": len(answer_tokens),
        }
    _, unit_index, start, span = best
    return {
        "official_f1": round(token_f1(span, answer_tokens), 12),
        "source_unit_index": unit_index,
        "token_offset": start,
        "span_token_count": len(span),
        "normalized_span_sha256": v25.text_sha256(" ".join(span)),
        "whole_context_answer_token_recall": round(recall, 6),
        "answer_token_count": len(answer_tokens),
    }


def availability_category(oracle, threshold):
    score = oracle["official_f1"]
    if abs(score - 1.0) <= 1e-12:
        return "exact_lexical_span"
    if score >= threshold:
        return "quality_gate_lexical_span"
    if oracle["whole_context_answer_token_recall"] > 0:
        return "partial_lexical_overlap"
    return "no_lexical_overlap"


def attribute_failure(model_f1, oracle, threshold):
    if model_f1 >= threshold:
        return "model_quality_pass"
    if oracle["official_f1"] >= threshold:
        return "lexical_answer_available_model_miss"
    if oracle["whole_context_answer_token_recall"] > 0:
        return "partial_lexical_evidence_inference_or_composition_needed"
    return "no_lexical_answer_evidence_in_target_session"


def question_operator(question):
    value = normalize_answer(question)
    rules = (
        ("temporal", r"^(when|what (time|date|year|month|day)|how long)\b"),
        ("quantity", r"^how (many|much|old)\b"),
        ("location", r"^where\b"),
        ("person", r"^(who|whose)\b"),
        ("causal", r"^why\b"),
        (
            "boolean",
            r"^(did|do|does|is|are|was|were|has|have|had|can|could|would|will)\b",
        ),
        ("entity_or_attribute", r"^(what|which|how)\b"),
    )
    for label, pattern in rules:
        if re.search(pattern, value):
            return label
    return "other"


def verify_frozen_inputs(contract):
    for section in (
        "development_authorization",
        "frozen_inputs",
        "frozen_local_implementation",
    ):
        values = contract[section]
        for key, relative in values.items():
            if not key.endswith("_path"):
                continue
            expected = values[key.replace("_path", "_sha256")]
            if v25.file_sha256(ROOT / relative) != expected:
                raise ValueError(f"frozen artifact hash drift: {relative}")
    v2_13_lock = load_json(
        ROOT / contract["development_authorization"]["v2_13_result_lock_path"]
    )
    resolution = v2_13_lock["decision_resolution"]
    if resolution != {
        "integrity": contract["development_authorization"]["v2_13_integrity"],
        "quality": contract["development_authorization"]["v2_13_quality"],
        "resource": contract["development_authorization"]["v2_13_resource"],
        "selected_reason": "resource_rejected_not_integrity_invalid",
    }:
        raise ValueError("V2.13 decision resolution drift")
    if any(v2_13_lock["authorization"].values()):
        raise ValueError("V2.13 unexpectedly authorizes downstream experimentation")
    v2_12_contract = v212.load_preregistration(
        ROOT / contract["frozen_inputs"]["v2_12_preregistration_path"]
    )
    v212.verify_frozen_inputs(v2_12_contract)
    v211.verify_official_scorer_runtime(contract)


def load_official_dataset_offline():
    prereg = v25.load_preregistration()
    source = prereg["official_source"]
    path = v25.DATASET
    if not path.exists():
        raise ValueError("frozen LoCoMo dataset missing; V2.14 prohibits network fallback")
    if path.stat().st_size != source["dataset_bytes"]:
        raise ValueError("local LoCoMo dataset size drift")
    if v25.file_sha256(path) != source["dataset_sha256"]:
        raise ValueError("local LoCoMo dataset hash drift")
    data = json.loads(path.read_text(encoding="utf-8"))
    if len(data) != source["expected_conversation_count"]:
        raise ValueError("local LoCoMo conversation count drift")
    return data


def reconstruct_cases_and_rows(contract):
    v2_12_contract = v212.load_preregistration(
        ROOT / contract["frozen_inputs"]["v2_12_preregistration_path"]
    )
    data = load_official_dataset_offline()
    cases = v212.final_case_specs(data, v2_12_contract)
    source_report = load_json(ROOT / contract["frozen_inputs"]["v2_13_report_path"])
    rows = source_report["rows"]
    by_case = {}
    for row in rows:
        by_case.setdefault(row["case_id"], {})[row["model_condition"]] = row
    if len(cases) != contract["data_boundary"]["case_count"]:
        raise ValueError("V2.14 case count drift")
    return cases, by_case, source_report, v2_12_contract


def build_case_rows(cases, by_case, v2_12_contract, contract):
    threshold = contract["lexical_oracle"]["case_quality_threshold"]
    diagnostic_rows = []
    audit = Counter()
    for case in cases:
        conditions = by_case.get(case["case_id"])
        if not conditions or set(conditions) != {CONTROL, CANDIDATE}:
            raise ValueError(f"incomplete V2.13 pair: {case['case_id']}")
        prompt = v212.build_prompt(case, "complete_session", v2_12_contract)
        expected_prompt_hash = v25.text_sha256(prompt)
        expected_answer_hash = v25.text_sha256(case["answer"])
        oracle = best_contiguous_source_span(
            case["contexts"]["complete_session"], case["answer"]
        )
        condition_output = {}
        for model in (CONTROL, CANDIDATE):
            source_row = conditions[model]
            audit[f"{model}_rows"] += 1
            audit["prompt_hash_matches"] += (
                source_row["prompt_sha256"] == expected_prompt_hash
            )
            audit["answer_hash_matches"] += (
                source_row["official_answer_sha256"] == expected_answer_hash
            )
            recalculated = f1_score(source_row["prediction"], case["answer"])
            audit["official_f1_matches"] += (
                abs(recalculated - source_row["official_f1"]) <= 1e-12
            )
            condition_output[model] = {
                "prediction_sha256": v25.text_sha256(source_row["prediction"]),
                "official_f1": source_row["official_f1"],
                "model_minus_lexical_oracle_f1": round(
                    source_row["official_f1"] - oracle["official_f1"], 6
                ),
                "attribution": attribute_failure(
                    source_row["official_f1"], oracle, threshold
                ),
            }
        diagnostic_rows.append(
            {
                "case_id": case["case_id"],
                "sample_alias": case["sample_alias"],
                "qa_index": case["qa_index"],
                "evidence_transition": case["evidence_transition"],
                "question_sha256": v25.text_sha256(case["question"]),
                "official_answer_sha256": expected_answer_hash,
                "complete_session_sha256": v25.text_sha256(
                    case["contexts"]["complete_session"]
                ),
                "question_operator": question_operator(case["question"]),
                "lexical_oracle": oracle,
                "availability_category": availability_category(oracle, threshold),
                "conditions": condition_output,
            }
        )
    return diagnostic_rows, audit


def summarize_rows(rows, audit, source_report, contract):
    threshold = contract["lexical_oracle"]["case_quality_threshold"]
    availability = Counter(row["availability_category"] for row in rows)
    attribution = {
        model: Counter(row["conditions"][model]["attribution"] for row in rows)
        for model in (CONTROL, CANDIDATE)
    }
    condition_metrics = {}
    for model in (CONTROL, CANDIDATE):
        scores = [row["conditions"][model]["official_f1"] for row in rows]
        gaps = [
            row["conditions"][model]["model_minus_lexical_oracle_f1"]
            for row in rows
        ]
        condition_metrics[model] = {
            "mean_official_f1": round(mean(scores), 6),
            "quality_pass_case_count": sum(score >= threshold for score in scores),
            "mean_model_minus_lexical_oracle_f1": round(mean(gaps), 6),
            "attribution_counts": dict(sorted(attribution[model].items())),
        }
    operators = {}
    for operator in contract["question_operator_priority"]:
        subset = [row for row in rows if row["question_operator"] == operator]
        if not subset:
            continue
        operators[operator] = {
            "case_count": len(subset),
            "mean_lexical_oracle_f1": round(
                mean([row["lexical_oracle"]["official_f1"] for row in subset]), 6
            ),
            "mean_9b_f1": round(
                mean([row["conditions"][CONTROL]["official_f1"] for row in subset]),
                6,
            ),
            "mean_27b_f1": round(
                mean(
                    [row["conditions"][CANDIDATE]["official_f1"] for row in subset]
                ),
                6,
            ),
            "candidate_lexical_available_miss_count": sum(
                row["conditions"][CANDIDATE]["attribution"]
                == "lexical_answer_available_model_miss"
                for row in subset
            ),
        }
    pair_deltas = [
        row["conditions"][CANDIDATE]["official_f1"]
        - row["conditions"][CONTROL]["official_f1"]
        for row in rows
    ]
    metrics = {
        "case_count": len(rows),
        "historical_control_row_count": audit[f"{CONTROL}_rows"],
        "candidate_row_count": audit[f"{CANDIDATE}_rows"],
        "complete_pair_count": len(rows),
        "prompt_hash_match_count": audit["prompt_hash_matches"] // 2,
        "answer_hash_match_count": audit["answer_hash_matches"] // 2,
        "official_f1_recalculation_match_count": audit["official_f1_matches"],
        "mean_lexical_oracle_f1": round(
            mean([row["lexical_oracle"]["official_f1"] for row in rows]), 6
        ),
        "mean_whole_context_answer_token_recall": round(
            mean(
                [
                    row["lexical_oracle"]["whole_context_answer_token_recall"]
                    for row in rows
                ]
            ),
            6,
        ),
        "lexical_quality_available_case_count": sum(
            row["lexical_oracle"]["official_f1"] >= threshold for row in rows
        ),
        "availability_counts": dict(sorted(availability.items())),
        "conditions": condition_metrics,
        "candidate_better_pair_count": sum(delta > 0 for delta in pair_deltas),
        "identical_f1_pair_count": sum(delta == 0 for delta in pair_deltas),
        "candidate_worse_pair_count": sum(delta < 0 for delta in pair_deltas),
        "question_operator_breakdown": operators,
        "new_model_call_count": 0,
        "production_memory_write_count": source_report["metrics"][
            "production_memory_write_count"
        ],
        "physical_vrm_action_count": source_report["metrics"][
            "physical_vrm_action_count"
        ],
        "report_raw_question_count": 0,
        "report_raw_answer_count": 0,
        "report_raw_source_text_count": 0,
        "report_raw_prediction_count": 0,
    }
    expected = contract["integrity_gates"]
    gates = {
        name: metrics[name.removesuffix("_equals")] == value
        for name, value in expected.items()
        if name.endswith("_equals")
        and name != "attribution_count_per_condition_equals"
    }
    gates["attribution_count_per_condition_equals"] = all(
        sum(attribution[model].values())
        == expected["attribution_count_per_condition_equals"]
        for model in (CONTROL, CANDIDATE)
    )
    return metrics, gates


def classify_decision(metrics, gates, contract):
    rules = contract["decision_rules"]
    if not all(gates.values()):
        return rules["any_integrity_gate_fails"]
    candidate_counts = metrics["conditions"][CANDIDATE]["attribution_counts"]
    dominant = contract["decision_thresholds"]["dominant_case_count_at_least"]
    lexical_miss = candidate_counts.get("lexical_answer_available_model_miss", 0)
    if lexical_miss >= dominant:
        return rules["candidate_lexical_available_miss_at_least_29"]
    nonverbatim = candidate_counts.get(
        "partial_lexical_evidence_inference_or_composition_needed", 0
    ) + candidate_counts.get("no_lexical_answer_evidence_in_target_session", 0)
    if nonverbatim >= dominant:
        return rules["candidate_partial_or_absent_lexical_evidence_at_least_29"]
    return rules["otherwise"]


def build_report(contract):
    verify_frozen_inputs(contract)
    cases, by_case, source_report, v2_12_contract = reconstruct_cases_and_rows(contract)
    rows, audit = build_case_rows(cases, by_case, v2_12_contract, contract)
    metrics, gates = summarize_rows(rows, audit, source_report, contract)
    decision = classify_decision(metrics, gates, contract)
    deterministic_authorized = decision == contract["decision_rules"][
        "candidate_lexical_available_miss_at_least_29"
    ]
    return {
        "schema": "uruha_source_preserving_memory_projection_lexical_oracle_attribution_report_v2_14",
        "experiment_id": contract["experiment_id"],
        "decision": decision,
        "scope": contract["evidence_scope"],
        "metrics": metrics,
        "gates": gates,
        "rows": sorted(rows, key=lambda row: row["case_id"]),
        "contains_official_questions": False,
        "contains_official_answers": False,
        "contains_source_context_text": False,
        "contains_raw_predictions": False,
        "authorization": {
            "preregister_source_disjoint_deterministic_span_selection_mechanism": deterministic_authorized,
            "preregister_fresh_model_generation": False,
            "preregister_full_pipeline_memory_intervention": False,
            "runtime_change": False,
            "runtime_shadow": False,
            "production_enablement": False,
        },
        "evidence_boundary": contract["evidence_boundary"],
    }


def render_markdown(report):
    metrics = report["metrics"]
    candidate = metrics["conditions"][CANDIDATE]
    lines = [
        "# V2.14 Lexical-Oracle Failure Attribution",
        "",
        f"**Decision: `{report['decision']}`**",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Cases | {metrics['case_count']} |",
        f"| Mean lexical-oracle F1 | {metrics['mean_lexical_oracle_f1']:.3f} |",
        f"| Lexical quality available | {metrics['lexical_quality_available_case_count']}/{metrics['case_count']} |",
        f"| 27B mean F1 | {candidate['mean_official_f1']:.3f} |",
        f"| 27B lexical-available misses | {candidate['attribution_counts'].get('lexical_answer_available_model_miss', 0)} |",
        "",
        "## 27B attribution",
        "",
    ]
    for name, count in candidate["attribution_counts"].items():
        lines.append(f"- `{name}`: {count}")
    lines.extend(["", report["evidence_boundary"], ""])
    return "\n".join(lines)


def main():
    contract = load_preregistration()
    execution = contract["execution"]
    json_path = ROOT / execution["report_json_path"]
    markdown_path = ROOT / execution["report_markdown_path"]
    if json_path.exists() or markdown_path.exists():
        raise SystemExit("V2.14 output exists; refusing to overwrite")
    report = build_report(contract)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "metrics": report["metrics"],
                "authorization": report["authorization"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
