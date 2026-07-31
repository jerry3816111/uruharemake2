#!/usr/bin/env python3
"""Independently audit the V4 public-persona scorer calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import public_persona_contract_v3 as v3
import public_persona_scorer_contract_v4 as scorer


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/public_persona_scorer_v4_calibration.json"
PREREGISTRATION_PATH = ROOT / "configs/public_persona_scorer_contract_v4_preregistration.json"
V3_RESULT_LOCK_PATH = ROOT / "configs/public_persona_contract_v3_model_result_lock.json"
DEFAULT_JSON = ROOT / "reports/public_persona_scorer_contract_v4_audit.json"
DEFAULT_MD = ROOT / "reports/public_persona_scorer_contract_v4_audit.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_report(dataset, preregistration, v3_result_lock):
    contracts = {context: scorer.compile_scorer_contract(context) for context in scorer.SCORER_POLICIES}
    rows = []
    per_context = defaultdict(list)
    per_mutation = defaultdict(list)
    for probe in dataset["probes"]:
        result = scorer.score_reply(probe["calibration_text"], contracts[probe["context"]])
        correct = result["passed"] is probe["expected_pass"]
        primary_reason_present = (
            probe["expected_primary_reason"] is None
            or probe["expected_primary_reason"] in result["reasons"]
        )
        row = {
            "probe_id": probe["probe_id"],
            "context": probe["context"],
            "mutation_type": probe["mutation_type"],
            "expected_pass": probe["expected_pass"],
            "observed_pass": result["passed"],
            "correct": correct,
            "expected_primary_reason": probe["expected_primary_reason"],
            "primary_reason_present": primary_reason_present,
            "reasons": result["reasons"],
            "optional_hits": result["optional_hits"],
        }
        rows.append(row)
        per_context[probe["context"]].append(correct and primary_reason_present)
        per_mutation[probe["mutation_type"]].append(correct and primary_reason_present)

    accuracy = sum(row["correct"] and row["primary_reason_present"] for row in rows) / len(rows)
    context_accuracy = {
        name: sum(values) / len(values) for name, values in sorted(per_context.items())
    }
    mutation_accuracy = {
        name: sum(values) / len(values) for name, values in sorted(per_mutation.items())
    }
    expected_mutations = {
        "optional_omission",
        "synonym_substitution",
        "missing_required",
        "forbidden_injection",
        "order_reversal",
        "length_violation",
    }
    relevant_mutations_pass = all(mutation_accuracy.get(name) == 1.0 for name in expected_mutations)
    required_ids = {
        context: {group["id"] for group in contract["required_groups"]}
        for context, contract in contracts.items()
    }
    optional_ids = {
        context: {group["id"] for group in contract["optional_groups"]}
        for context, contract in contracts.items()
    }
    all_order_ids_valid = all(
        first in required_ids[context] and second in required_ids[context]
        for context, contract in contracts.items()
        for first, second in contract["ordered_pairs"]
    )
    authorizations_clear = all(
        contract["runtime_authorized"] is False and contract["training_authorized"] is False
        for contract in contracts.values()
    )
    checks = {
        "v3_negative_dependency": v3_result_lock["passed"] is False
        and v3_result_lock["decision"]
        == preregistration["depends_on"]["required_decision"],
        "context_set": set(contracts) == set(v3.POLICIES),
        "probe_count": len(rows) == preregistration["scope"]["probe_count_exact"],
        "label_balance": Counter(probe["expected_pass"] for probe in dataset["probes"])
        == Counter({True: 15, False: 15}),
        "overall_accuracy": accuracy >= preregistration["success_gates"]["overall_accuracy_min"],
        "per_context_accuracy": min(context_accuracy.values())
        >= preregistration["success_gates"]["per_context_accuracy_min"],
        "required_mutations": relevant_mutations_pass,
        "optional_is_not_required": "mild_self_tease"
        in optional_ids["informal_public_self_introduction"]
        and "mild_self_tease" not in required_ids["informal_public_self_introduction"],
        "order_references_required_groups": all_order_ids_valid,
        "no_runtime_or_training_authorization": authorizations_clear,
        "no_model_calls": preregistration["scope"]["model_call_count_exact"] == 0,
        "holdout_still_sealed": preregistration["scope"]["v2_holdout_content_review_count_exact"]
        == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_public_persona_scorer_contract_audit_v4",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": (
            preregistration["decision_policy"]["pass"]
            if passed
            else preregistration["decision_policy"]["fail"]
        ),
        "summary": {
            "probe_count": len(rows),
            "correct_count": sum(row["correct"] and row["primary_reason_present"] for row in rows),
            "overall_accuracy": accuracy,
            "context_count": len(context_accuracy),
            "model_call_count": 0,
            "runtime_change_count": 0,
            "holdout_content_review_count": 0,
            "training_authorized_count": 0,
        },
        "per_context_accuracy": context_accuracy,
        "per_mutation_accuracy": mutation_accuracy,
        "checks": checks,
        "rows": rows,
        "authorizations": {
            "new_matched_carrier_preregistration": passed,
            "model_execution": False,
            "runtime_default_enable": False,
            "model_change": False,
            "training": False,
            "holdout_unsealing": False,
            "persona_fidelity_claim": False,
        },
        "inputs": {
            "dataset": {"path": DATASET_PATH.name, "sha256": sha(DATASET_PATH)},
            "preregistration": {
                "path": PREREGISTRATION_PATH.name,
                "sha256": sha(PREREGISTRATION_PATH),
            },
            "v3_result_lock": {"path": V3_RESULT_LOCK_PATH.name, "sha256": sha(V3_RESULT_LOCK_PATH)},
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    lines = [
        "# 公開人格 Scorer Contract V4 校準結果",
        "",
        f"- 決策：`{report['decision']}`",
        f"- 校準正確：{report['summary']['correct_count']}/{report['summary']['probe_count']}",
        "- 模型呼叫、runtime 修改、holdout 檢視、訓練授權：全部 0。",
        "",
        "| 情境 | 正確率 |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {context} | {accuracy:.1%} |"
        for context, accuracy in report["per_context_accuracy"].items()
    )
    lines.extend(["", "| 變形類型 | 正確率 |", "|---|---:|"])
    lines.extend(
        f"| {mutation} | {accuracy:.1%} |"
        for mutation, accuracy in report["per_mutation_accuracy"].items()
    )
    lines.extend(["", "## 證據邊界", "", report["evidence_boundary"]])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    for path in (args.output_json, args.output_md):
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"refusing to overwrite {path}")
    report = build_report(load(DATASET_PATH), load(PREREGISTRATION_PATH), load(V3_RESULT_LOCK_PATH))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if args.require_pass and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
