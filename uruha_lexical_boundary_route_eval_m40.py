"""One-shot, frozen deterministic M40 comparison. Never a human-rating claim."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

from uruha_lexical_boundary_route_m40 import evaluate_boundary_route_m40


ROOT = Path(__file__).resolve().parent
PROTECTED_SCENES = {"boundary", "refusal", "ooc_defense", "crisis"}
CATEGORIES = {
    "benign_affirmation", "cross_token_collision", "embedded_token_collision",
    "protected_explicit", "affirmation_with_protected_content",
    "protected_separator_variant", "ordinary_noninterference",
}


def validate_reserve_m40(dataset):
    rows = dataset.get("cases") or []
    errors = []
    ids = [r.get("id") for r in rows]
    inputs = [r.get("input") for r in rows]
    if not rows or len(ids) != len(set(ids)) or len(inputs) != len(set(inputs)):
        errors.append("empty_or_duplicate_cases")
    for row in rows:
        if not row.get("input") or row.get("category") not in CATEGORIES:
            errors.append(f"invalid_case:{row.get('id')}")
        if row.get("language") not in {"en", "zh", "ja"}:
            errors.append(f"invalid_language:{row.get('id')}")
        if not isinstance(row.get("expected_protected"), bool):
            errors.append(f"missing_boolean_label:{row.get('id')}")
        if bool(row.get("expected_boundary_intent")) != bool(row.get("expected_protected")):
            errors.append(f"intent_label_inconsistent:{row.get('id')}")
    if errors:
        raise ValueError("; ".join(errors))
    return {"case_count": len(rows), "errors": [], "language_counts": dict(Counter(r["language"] for r in rows))}


def _protected(plan):
    return (plan or {}).get("scene") in PROTECTED_SCENES


def _rate(rows, field):
    return sum(bool(r[field]) for r in rows) / len(rows) if rows else 0.0


def evaluate_reserve_m40(dataset, protocol):
    validation = validate_reserve_m40(dataset)
    rows = []
    for case in dataset["cases"]:
        baseline, guarded, trace = evaluate_boundary_route_m40(case["input"])
        expected = case["expected_protected"]
        rows.append({
            **case,
            "baseline_intent": (baseline or {}).get("intent"),
            "system_intent": (guarded or {}).get("intent"),
            "baseline_protected": _protected(baseline),
            "system_protected": _protected(guarded),
            "baseline_correct": _protected(baseline) == expected,
            "system_correct": _protected(guarded) == expected,
            "protected_intent_correct": not expected or (guarded or {}).get("intent") == case.get("expected_boundary_intent"),
            "plan_unchanged": baseline == guarded,
            "raw_trace_contains_input": case["input"] in json.dumps(trace, ensure_ascii=False),
            "trace": trace,
        })
    category = lambda name: [r for r in rows if r["category"] == name]
    collision = [r for r in rows if "collision" in r["category"]]
    protected = [r for r in rows if r["expected_protected"]]
    latency = sorted(r["trace"]["added_audit_seconds"] for r in rows)
    metrics = {
        "case_count": len(rows),
        "baseline_protection_accuracy": _rate(rows, "baseline_correct"),
        "system_protection_accuracy": _rate(rows, "system_correct"),
        "benign_affirmation_false_protection_rate": _rate(category("benign_affirmation"), "system_protected"),
        "collision_false_protection_rate": _rate(collision, "system_protected"),
        "explicit_protection_recall": _rate(category("protected_explicit"), "system_protected"),
        "mixed_signal_protection_recall": _rate(category("affirmation_with_protected_content"), "system_protected"),
        "separator_variant_protection_recall": _rate(category("protected_separator_variant"), "system_protected"),
        "protected_intent_accuracy": _rate(protected, "protected_intent_correct"),
        "ordinary_noninterference_rate": _rate(category("ordinary_noninterference"), "plan_unchanged"),
        "raw_trace_write_count": sum(r["raw_trace_contains_input"] or r["trace"]["raw_dialogue_persisted"] for r in rows),
        "mental_fact_write_count": sum(r["trace"]["mental_fact_write_count"] for r in rows),
        "median_added_seconds": statistics.median(latency),
        "p95_added_seconds": latency[min(len(latency)-1, int(len(latency)*0.95))],
        "model_call_count": sum(r["trace"]["model_call_count"] for r in rows),
    }
    gates = {}
    for key, threshold in protocol["gates"].items():
        metric, direction = key.rsplit("_", 1)
        value = metrics[metric]
        gates[key] = {"observed": value, "threshold": threshold,
                      "passed": value >= threshold if direction == "min" else value <= threshold}
    return {
        "schema": "uruha_m40_lexical_boundary_route_result_v1",
        "validation": validation,
        "decision": "pass_all_frozen_gates" if all(g["passed"] for g in gates.values()) else "fail_one_or_more_frozen_gates",
        "metrics": metrics, "gates": gates, "rows": rows,
        "claim_boundary": protocol.get("boundary"),
        "evidence_type": "predeclared researcher-authored deterministic mechanism comparison, not same-model generation or human preference",
    }


def frozen_integrity_m40(freeze_path):
    freeze = json.loads(Path(freeze_path).read_text())
    mismatches = [p for p, digest in freeze["frozen_files"].items()
                  if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
    if mismatches:
        raise RuntimeError(f"frozen_file_mismatch:{mismatches}")
    return len(freeze["frozen_files"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--freeze", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError("Refusing to overwrite or rerun formal evidence")
    verified = frozen_integrity_m40(args.freeze)
    dataset_path = ROOT / "datasets/m40_lexical_boundary_route_reserve_v1.json"
    protocol_path = ROOT / "research/m40_lexical_boundary_route_protocol_v1.json"
    dataset = json.loads(dataset_path.read_text())
    protocol = json.loads(protocol_path.read_text())
    result = evaluate_reserve_m40(dataset, protocol)
    result["provenance"] = {
        "formal_run_index": 1,
        "frozen_file_count_verified": verified,
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "implementation_freeze_sha256": hashlib.sha256(Path(args.freeze).read_bytes()).hexdigest(),
    }
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"decision": result["decision"], "metrics": result["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
