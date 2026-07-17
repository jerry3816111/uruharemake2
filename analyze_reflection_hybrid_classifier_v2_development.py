#!/usr/bin/env python3
"""Analyze the frozen local semantic fallback capacity pilot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reflection_hybrid_classifier_v2_core import (
    analyze_condition,
    select_smallest_passing,
)
from run_reflection_classifier_v1_baseline import sha256


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT / "configs" / "reflection_hybrid_classifier_v2_development_preregistration.json"
)
LOCK_PATH = ROOT / "configs" / "reflection_hybrid_classifier_v2_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "reflection_classifier_v1_external_holdout.json"
RAW_PATH = ROOT / "reports" / "reflection_hybrid_classifier_v2_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "reflection_hybrid_classifier_v2_development_analysis.json"
DEFAULT_MD = ROOT / "reports" / "reflection_hybrid_classifier_v2_development_analysis.md"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown(report):
    lines = []
    for model in report["tested_models"]:
        row = report["analyses"][model]
        lines.append(
            f"| {model} | {row['hybrid_correct_count']}/32 | {row['hybrid_accuracy']:.2%} | "
            f"{row['newly_correct_count']} | {row['regression_count']} | "
            f"{row['median_fallback_wall_seconds']:.3f}s | "
            f"{'PASS' if row['all_gates_pass'] else 'FAIL'} |"
        )
    selected = report["selected_model"] or "none"
    return f"""# Reflection Hybrid Classifier V2 Development Pilot

| Model | Correct | Accuracy | Newly correct | Regressions | Median fallback | Gates |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(lines)}

- Rules-only control: 20/32 (62.50%)
- Selected smallest passing model: **{selected}**
- Decision: `{report['decision']}`

This is a development capacity pilot on a retired failed holdout. It cannot establish generalization or authorize runtime reflection writes.
"""


def analyze(raw_path=RAW_PATH, json_path=DEFAULT_JSON, md_path=DEFAULT_MD):
    if json_path.exists() or md_path.exists():
        raise FileExistsError("refusing to overwrite hybrid development analysis")
    config = _load(CONFIG_PATH)
    lock = _load(LOCK_PATH)
    dataset = _load(DATASET_PATH)
    raw = _load(raw_path)
    expected_hashes = {
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "dataset_sha256": sha256(DATASET_PATH),
    }
    for key, expected in expected_hashes.items():
        if raw.get(key) != expected:
            raise ValueError(f"raw result provenance drift: {key}")
    if raw["runner_branch"] != lock["required_run_branch"]:
        raise ValueError("raw result did not run from required branch")
    if raw["gold_label_passed_to_model"]:
        raise ValueError("gold label was exposed to model")

    frozen_models = {
        row["model"]: row for row in config["model_search"]["ordered_conditions"]
    }
    model_calls = 0
    for condition in raw["conditions"]:
        model = condition["model"]
        if model not in frozen_models:
            raise ValueError(f"unexpected tested model: {model}")
        if condition["model_snapshot"]["digest"] != frozen_models[model]["digest"]:
            raise ValueError(f"model digest drift: {model}")
        model_calls += len(condition["fallback_rows"])
    if model_calls != raw["model_calls"]:
        raise ValueError("raw model-call accounting drift")
    if model_calls > config["model_search"]["maximum_model_calls"]:
        raise ValueError("raw model-call budget exceeded")

    analyses = {}
    for condition in raw["conditions"]:
        analyses[condition["model"]] = analyze_condition(
            dataset["cases"],
            raw["rules_predictions"],
            condition["fallback_rows"],
            config["success_gates"],
        )
        if analyses[condition["model"]] != condition["gate_snapshot"]:
            raise ValueError(f"runner gate snapshot drift: {condition['model']}")
    selected = select_smallest_passing(
        config["model_search"]["ordered_conditions"], analyses
    )
    if selected != raw["selected_model"]:
        raise ValueError("runner early-stop selection drift")
    decision = (
        config["decision_rule"]["first_model_passes_all_gates"]
        if selected
        else config["decision_rule"]["no_model_passes_all_gates"]
    )
    report = {
        "schema": "uruha_reflection_hybrid_classifier_development_analysis_v2",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "raw_result_sha256": sha256(raw_path),
        "preregistration_sha256": sha256(CONFIG_PATH),
        "harness_lock_sha256": sha256(LOCK_PATH),
        "tested_models": [row["model"] for row in raw["conditions"]],
        "selected_model": selected,
        "model_calls": raw["model_calls"],
        "analyses": analyses,
        "decision": decision,
        "fresh_holdout_required_before_generalization_claim": True,
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
