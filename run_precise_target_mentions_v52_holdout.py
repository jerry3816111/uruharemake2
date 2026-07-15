#!/usr/bin/env python3
"""Run the frozen V51-vs-V52 fresh holdout comparison."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from audit_precise_target_mentions_v52_holdout import audit as audit_holdout
from precise_target_mentions_v52 import audit_precise_event_maps
from run_precise_target_mentions_v52 import (
    _model_snapshot,
    _run_judgment,
    build_prompts,
    evaluate_representation_audit,
)
from run_rightbrain_qwen35_migration_v33 import _unload_model
from run_target_event_map_v51 import build_candidate_rows


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_holdout_preregistration.json"
V51_CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DATASET_PATH = ROOT / "datasets" / "precise_target_mentions_v52_holdout.json"
DEFAULT_OUTPUT = ROOT / "reports" / "precise_target_mentions_v52_holdout_raw.json"
CONDITIONS = ("v51_event_map_control", "precise_target_mentions_candidate")
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


def _validate_inputs(config, dataset, v52_config):
    for key, expected in config["frozen_inputs"].items():
        if not key.endswith("_sha256"):
            continue
        path_key = key.removesuffix("_sha256")
        path = ROOT / config["frozen_inputs"][path_key]
        if _sha256(path) != expected:
            raise ValueError(f"V52 holdout frozen input hash mismatch: {path}")
    if tuple(config["conditions"]) != CONDITIONS:
        raise ValueError("V52 holdout condition order mismatch")
    if dataset["evidence_status"] != "frozen_before_any_model_inference":
        raise ValueError("V52 holdout was not frozen before inference")
    if dataset["case_count"] != config["frozen_inputs"]["case_count"]:
        raise ValueError("V52 holdout case count mismatch")
    if config["expected_judgment_count"] != (
        len(CONDITIONS) * config["frozen_inputs"]["grounded_target_count"]
    ):
        raise ValueError("V52 holdout expected judgment count mismatch")
    if config["causal_change"]["target_mention_patterns"] != v52_config[
        "causal_change"
    ]["target_mention_patterns"]:
        raise ValueError("V52 holdout target mention patterns drifted")
    if any(
        config[key]
        for key in (
            "prompt_or_map_tuning_after_run_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "human_likeness_claim_authorized",
        )
    ):
        raise ValueError("V52 holdout cannot start with advancement authorized")


def _checks(config, prompts):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "source_snapshot_sha256": _sha256(
            ROOT / config["frozen_inputs"]["external_source_snapshot"]
        ),
        "prompt_sha256": {
            condition: hashlib.sha256(prompt.encode()).hexdigest()
            for condition, prompt in prompts.items()
        },
    }


def _load_or_create(output, config, prompts, snapshot, candidate_rows, audits):
    checks = _checks(config, prompts)
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        for field, expected in checks.items():
            if report.get(field) != expected:
                raise ValueError(f"Existing V52 holdout report {field} mismatch")
        return report
    return {
        "schema": "uruha_precise_target_mentions_fresh_holdout_raw_v52",
        "evidence_status": "project_fresh_external_and_controlled_holdout",
        "base_model_pretraining_exclusion_guaranteed": False,
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "conditions": list(CONDITIONS),
        "selected_carrier": config["fixed_carrier"],
        "model_snapshot": snapshot,
        "construction_audit": audits["construction"],
        "representation_audit": audits["representation"],
        "candidate_rows": candidate_rows,
        "judgment_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    v51_config = load(V51_CONFIG_PATH)
    v52_config = load(V52_CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    dataset = load(DATASET_PATH)
    _validate_inputs(config, dataset, v52_config)

    construction = audit_holdout(
        dataset, config["causal_change"]["target_mention_patterns"]
    )
    if not construction["passed"]:
        raise ValueError(
            f"V52 holdout construction gate failed: {construction['failed_checks']}"
        )
    candidate_rows = build_candidate_rows(dataset)
    target_count = sum(len(row["candidates"]) for row in candidate_rows)
    if target_count != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V52 holdout grounded target count drift")
    representation = audit_precise_event_maps(
        candidate_rows, config["causal_change"]["target_mention_patterns"]
    )
    representation_gate = config["representation_gates"]
    representation_checks = {
        "grounded_occurrence_mention_coverage": representation[
            "grounded_occurrence_mention_coverage"
        ]
        == representation_gate["grounded_occurrence_mention_coverage"],
        "fallback_occurrence_count": representation["fallback_occurrence_count"]
        == representation_gate["fallback_occurrence_count"],
        "mention_inside_predicate_evidence_rate": representation[
            "mention_inside_predicate_evidence_rate"
        ]
        == representation_gate["mention_inside_predicate_evidence_rate"],
        "cross_target_mention_overlap_count": representation[
            "cross_target_mention_overlap_count"
        ]
        == representation_gate["cross_target_mention_overlap_count"],
    }
    if not all(representation_checks.values()):
        raise ValueError("V52 holdout representation gate failed before inference")

    snapshot = _model_snapshot(config)
    prompts = build_prompts(config, v51_config, v45_config, v44_lock)
    report = _load_or_create(
        output,
        config,
        prompts,
        snapshot,
        candidate_rows,
        {
            "construction": construction,
            "representation": {
                **representation,
                "checks": representation_checks,
                "passed": all(representation_checks.values()),
            },
        },
    )
    completed = {
        (row["condition"], row["case_id"], row["target_id"])
        for row in report["judgment_rows"]
    }
    total = config["expected_judgment_count"]
    for condition in CONDITIONS:
        for candidate_row in candidate_rows:
            for candidate in candidate_row["candidates"]:
                key = (condition, candidate_row["case_id"], candidate["target_id"])
                if key in completed:
                    continue
                report["judgment_rows"].append(
                    {
                        "condition": condition,
                        "case_id": candidate_row["case_id"],
                        "target_id": candidate["target_id"],
                        "result": _run_judgment(
                            condition,
                            candidate_row,
                            candidate,
                            config,
                            v45_config,
                            prompts,
                            snapshot,
                        ),
                    }
                )
                _atomic_write(output, report)
                print(
                    f"[v52 holdout {len(report['judgment_rows'])}/{total}] "
                    f"{condition} {candidate_row['case_id']} {candidate['target_id']}",
                    flush=True,
                )
        _unload_model(snapshot["model_tag"])
    if len(report["judgment_rows"]) == total:
        report["completed_at"] = _now()
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
                "construction_gate_passed": report["construction_audit"]["passed"],
                "representation_gate_passed": report["representation_audit"]["passed"],
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
