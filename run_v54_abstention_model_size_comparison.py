#!/usr/bin/env python3
"""Compare installed local model sizes on the frozen V54 abstention subset."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from run_precise_target_mentions_v52 import _model_snapshot, _run_judgment, build_prompts
from run_rightbrain_qwen35_migration_v33 import _unload_model


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "v54_abstention_model_size_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "v54_abstention_model_size_holdout.json"
V54_RAW_PATH = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_raw.json"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"
V51_CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DEFAULT_OUTPUT = ROOT / "reports" / "v54_abstention_model_size_raw.json"
TZ = ZoneInfo("Asia/Tokyo")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def _git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _validate_inputs(config, dataset):
    for key, expected in config["frozen_inputs"].items():
        if not key.endswith("_sha256"):
            continue
        path = ROOT / config["frozen_inputs"][key.removesuffix("_sha256")]
        if _sha256(path) != expected:
            raise ValueError(f"V54 model-size frozen input hash mismatch: {path}")
    if dataset["evidence_status"] != "frozen_before_any_new_model_size_inference":
        raise ValueError("V54 abstention subset was not frozen before new inference")
    if dataset["item_count"] != config["frozen_inputs"]["item_count"]:
        raise ValueError("V54 abstention item count mismatch")
    if config["new_model_call_budget"] != 30:
        raise ValueError("V54 model-size call budget must remain 30")
    if any(
        config[key]
        for key in (
            "fallback_replacement_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
        )
    ):
        raise ValueError("V54 model-size comparison cannot pre-authorize integration")


def _frozen_4b_lookup(v54_raw):
    return {
        (row["case_id"], row["target_id"]): row["fresh_v51_result"]
        for row in v54_raw["target_rows"]
        if not row["state_machine"]["resolved"]
    }


def _candidate_row(item):
    return {
        "case_id": item["case_id"],
        "family": item["family"],
        "user_input": item["input_text"],
        "candidates": item["all_candidates"],
    }


def _checks(prompt):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "v54_raw_sha256": _sha256(V54_RAW_PATH),
        "v51_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
    }


def _load_or_create(output, config, prompt, snapshots):
    checks = _checks(prompt)
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        for field, expected in checks.items():
            if report.get(field) != expected:
                raise ValueError(f"Existing V54 model-size report {field} mismatch")
        return report
    return {
        "schema": "uruha_v54_abstention_model_size_raw",
        "evidence_status": "diagnostic_on_consumed_frozen_abstentions",
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "conditions": config["condition_order"],
        "model_snapshots": snapshots,
        "selected_carrier": config["fixed_carrier"],
        "new_model_call_budget": config["new_model_call_budget"],
        "paid_api_used": False,
        "judgment_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    dataset = load(DATASET_PATH)
    v54_raw = load(V54_RAW_PATH)
    v52_config = load(V52_CONFIG_PATH)
    v51_config = load(V51_CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    _validate_inputs(config, dataset)

    snapshots = {
        condition: _model_snapshot({"fixed_model": spec})
        for condition, spec in config["model_conditions"].items()
    }
    prompt = build_prompts(v52_config, v51_config, v45_config, v44_lock)[
        "v51_event_map_control"
    ]
    report = _load_or_create(output, config, prompt, snapshots)
    frozen_4b = _frozen_4b_lookup(v54_raw)
    completed = {
        (row["condition"], row["case_id"], row["target_id"])
        for row in report["judgment_rows"]
    }

    for condition in config["condition_order"]:
        spec = config["model_conditions"][condition]
        judgment_config = {
            **v52_config,
            "fixed_model": spec,
            "fixed_carrier": config["fixed_carrier"],
        }
        snapshot = snapshots[condition]
        for item in dataset["items"]:
            key = (condition, item["case_id"], item["target_id"])
            if key in completed:
                continue
            if spec["inference_mode"] == "reuse_frozen_v54_output":
                result = frozen_4b[(item["case_id"], item["target_id"])]
            else:
                result = _run_judgment(
                    "v51_event_map_control",
                    _candidate_row(item),
                    item["candidate"],
                    judgment_config,
                    v45_config,
                    {"v51_event_map_control": prompt},
                    snapshot,
                )
            report["judgment_rows"].append(
                {
                    "condition": condition,
                    "case_id": item["case_id"],
                    "target_id": item["target_id"],
                    "inference_mode": spec["inference_mode"],
                    "result": result,
                }
            )
            _atomic_write(output, report)
            print(
                f"[v54 model size {len(report['judgment_rows'])}/40] "
                f"{condition} {item['case_id']} {item['target_id']}",
                flush=True,
            )
        if spec["inference_mode"] == "new_local_inference":
            _unload_model(snapshot["model_tag"])

    if len(report["judgment_rows"]) == 40:
        report["completed_at"] = _now()
        report["new_model_calls_made"] = sum(
            row["inference_mode"] == "new_local_inference"
            for row in report["judgment_rows"]
        )
    _atomic_write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(
        json.dumps(
            {
                "rows": len(report["judgment_rows"]),
                "new_model_calls_made": report.get("new_model_calls_made"),
                "paid_api_used": report["paid_api_used"],
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
