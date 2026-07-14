#!/usr/bin/env python3
"""Run one preregistered V30 RightBrain adapter-ablation condition."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from eval_rightbrain_model_surface_holdout import build_report, write_markdown
from rightbrain_on_policy_dev_cases_v29 import case_inputs, validate_cases


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_base_v10_ablation_v30_preregistration.json"
V10_ADAPTER_PATH = ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
CONDITIONS = ("v10_adapter", "base_only")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_preregistration(path=PREREG_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_preregistered_sources(preregistration, root=ROOT):
    checks = {}
    for name, entry in preregistration["frozen_inputs"].items():
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        path = Path(root) / entry["path"]
        checks[f"{name}_exists"] = path.is_file()
        checks[f"{name}_sha256_matches"] = (
            path.is_file() and sha256_file(path) == entry["sha256"]
        )
    for row in preregistration["frozen_v10_reports"]:
        path = Path(root) / row["path"]
        key = f"v10_seed_{row['seed']}"
        checks[f"{key}_exists"] = path.is_file()
        checks[f"{key}_sha256_matches"] = (
            path.is_file() and sha256_file(path) == row["sha256"]
        )
    return checks


def _cached_base_revision():
    ref = (
        Path.home()
        / ".cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/refs/main"
    )
    return ref.read_text(encoding="utf-8").strip() if ref.is_file() else ""


def finalize_condition_report(report, condition, preregistration, root=ROOT):
    expected = preregistration["frozen_inputs"]
    source_checks = verify_preregistered_sources(preregistration, root=root)
    validation = validate_cases()
    generated_counts = [
        int(row.get("generated_candidate_count") or 0)
        for row in report.get("cases") or []
    ]
    expected_case_ids = [case["id"] for case in case_inputs()]
    observed_case_ids = [row.get("id") for row in report.get("cases") or []]
    condition_spec = preregistration["conditions"][condition]
    expected_adapter = condition_spec["adapter_ref"]
    report.update(
        {
            "scope": "rightbrain_base_v10_ablation_v30",
            "condition": condition,
            "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
            "preregistration_sha256": sha256_file(PREREG_PATH),
            "base_model": condition_spec["base_model"],
            "base_model_revision": _cached_base_revision(),
            "source_verification": source_checks,
            "dev_case_validation": validation,
            "runner_sha256": sha256_file(Path(__file__)),
            "research_boundary": (
                "This is a matched diagnostic ablation on previously observed V29 development cases. "
                "It can authorize only a new human-blind comparison, never runtime promotion."
            ),
        }
    )
    report["formal_run_gates"] = {
        "all_preregistered_sources_match": all(source_checks.values()),
        "base_model_revision_matches": report["base_model_revision"]
        == condition_spec["base_model_revision"],
        "condition_adapter_matches": report.get("adapter_ref") == expected_adapter,
        "seed_is_preregistered": report.get("seed") in expected["seeds"],
        "candidate_count_matches": report.get("candidate_count_per_case")
        == expected["candidate_count_per_case"],
        "case_validation_passes": validation["valid"],
        "case_ids_and_order_match": observed_case_ids == expected_case_ids,
        "all_candidates_generated": (
            len(generated_counts) == expected["case_count"]
            and all(
                count == expected["candidate_count_per_case"]
                for count in generated_counts
            )
            and report["summary"]["generated_candidate_count"]
            == expected["case_count"] * expected["candidate_count_per_case"]
        ),
        "repair_disabled": report.get("repair_enabled") is False,
    }
    report["formal_run_complete"] = all(report["formal_run_gates"].values())
    report["conclusion_zh"] = (
        f"{condition} 已在固定 V29 情境、seed 與三組採樣設定下完成。"
        "這份單條件報告不做優劣宣稱，必須交由配對分析器與 V10 凍結報告比較。"
    )
    return report


def build_condition_report(condition, seed, preregistration=None):
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    preregistration = preregistration or load_preregistration()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    report = build_report(
        load_model=True,
        adapter_path=str(V10_ADAPTER_PATH) if condition == "v10_adapter" else "",
        base_only=condition == "base_only",
        candidate_count=preregistration["frozen_inputs"]["candidate_count_per_case"],
        seed=seed,
        repair_enabled=False,
        cases=case_inputs(),
        scope="rightbrain_base_v10_ablation_v30",
    )
    return finalize_condition_report(report, condition, preregistration)


def default_output_path(condition, seed, suffix):
    return ROOT / "reports" / (
        f"rightbrain_base_v10_ablation_v30_{condition}_seed{seed}.{suffix}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args()

    preregistration = load_preregistration()
    if args.seed not in preregistration["frozen_inputs"]["seeds"]:
        raise SystemExit(f"Seed {args.seed} is not preregistered")
    report = build_condition_report(args.condition, args.seed, preregistration)
    output_json = Path(args.output_json) if args.output_json else default_output_path(
        args.condition, args.seed, "json"
    )
    output_md = Path(args.output_md) if args.output_md else default_output_path(
        args.condition, args.seed, "md"
    )
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, output_md)
    with output_md.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## V30 formal-run gates\n\n"
            + "\n".join(
                f"- {name}: {value}"
                for name, value in report["formal_run_gates"].items()
            )
            + "\n"
        )
    print(
        json.dumps(
            {
                "condition": args.condition,
                "seed": args.seed,
                "summary": report["summary"],
                "formal_run_complete": report["formal_run_complete"],
                "output_json": str(output_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["formal_run_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
