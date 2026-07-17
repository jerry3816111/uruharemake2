#!/usr/bin/env python3
"""Analyze the frozen matched external reflection classifier result."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_classifier_v1_external_holdout_core import analyze_matched
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT
    / "configs"
    / "reflection_classifier_v1_external_holdout_construction_preregistration.json"
)
DATASET_PATH = ROOT / "datasets" / "reflection_classifier_v1_external_holdout.json"
LOCK_PATH = ROOT / "configs" / "reflection_classifier_v1_external_holdout_harness_lock.json"
RAW_PATH = ROOT / "reports" / "reflection_classifier_v1_external_holdout_raw.json"
DEFAULT_JSON = ROOT / "reports" / "reflection_classifier_v1_external_holdout_analysis.json"
DEFAULT_MD = ROOT / "reports" / "reflection_classifier_v1_external_holdout_analysis.md"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(raw, lock):
    expected_hashes = {
        "dataset_sha256": sha256(DATASET_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "legacy_classifier_sha256": lock["frozen_artifacts"][
            "legacy_classifier_sha256"
        ],
        "candidate_classifier_sha256": lock["frozen_artifacts"][
            "candidate_classifier_sha256"
        ],
    }
    for hash_key, expected in expected_hashes.items():
        if raw[hash_key] != expected:
            raise ValueError(f"raw result provenance drift: {hash_key}")
    if raw["runner_branch"] != lock["required_run_branch"]:
        raise ValueError("raw result did not run from the required branch")
    if raw["model_calls"] != 0 or raw["gold_label_passed_to_classifier"]:
        raise ValueError("matched classifier contract violated")


def _markdown(report):
    result = report["matched_result"]
    status = "PASS" if result["all_gates_pass"] else "FAIL"
    class_rows = "\n".join(
        "| {label} | {lc}/8 | {cc}/8 |".format(
            label=label,
            lc=result["legacy"]["class_metrics"][label]["correct"],
            cc=result["candidate"]["class_metrics"][label]["correct"],
        )
        for label in ("semantic", "procedural", "interpretive", "none")
    )
    gate_rows = "\n".join(
        f"- {name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in result["gate_checks"].items()
    )
    return f"""# Reflection Classifier V1 External Holdout

Status: **{status}**

| Condition | Correct | Accuracy |
|---|---:|---:|
| Frozen legacy | {result['legacy']['correct_count']}/32 | {result['legacy']['accuracy']:.2%} |
| Structural candidate | {result['candidate']['correct_count']}/32 | {result['candidate']['accuracy']:.2%} |

- Accuracy delta: {result['accuracy_delta']:+.2%}
- Newly correct: {result['newly_correct_count']}
- Regressions: {result['regression_count']}
- Critical false positives: {result['critical_false_positive_count']}

## Class results

| Class | Legacy | Candidate |
|---|---:|---:|
{class_rows}

## Frozen gates

{gate_rows}

## Decision

{report['decision']}

This result measures only source-separated reflection-entry classification. It does not measure extraction quality, memory usefulness, downstream behavioral change, or broad human likeness.
"""


def analyze(raw_path=RAW_PATH, json_path=DEFAULT_JSON, md_path=DEFAULT_MD):
    if json_path.exists() or md_path.exists():
        raise FileExistsError("refusing to overwrite external holdout analysis")
    preregistration = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    lock = _load(LOCK_PATH)
    raw = _load(raw_path)
    verify(raw, lock)
    matched = analyze_matched(
        dataset["cases"], raw["rows"], preregistration["success_gates"]
    )
    decision = (
        preregistration["decision_rule"]["all_gates_pass"]
        if matched["all_gates_pass"]
        else preregistration["decision_rule"]["any_gate_fails"]
    )
    report = {
        "schema": "uruha_reflection_classifier_external_holdout_analysis_v1",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "raw_result_sha256": sha256(raw_path),
        "dataset_sha256": sha256(DATASET_PATH),
        "preregistration_sha256": sha256(PREREG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "matched_result": matched,
        "decision": decision,
        "runtime_memory_write_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_PATH)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    analyze(args.raw, args.json, args.markdown)


if __name__ == "__main__":
    main()
