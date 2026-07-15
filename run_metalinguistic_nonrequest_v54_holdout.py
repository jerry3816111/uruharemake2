#!/usr/bin/env python3
"""Run fresh V51 fallback judgments and the frozen V54 state machine."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from audit_metalinguistic_nonrequest_v54_holdout import audit as audit_holdout
from grounded_commitment_classifier_v42 import ground_supported_targets
from metalinguistic_nonrequest_v54 import resolve_target_state
from run_precise_target_mentions_v52 import (
    _model_snapshot,
    _run_judgment,
    build_prompts,
)
from run_rightbrain_qwen35_migration_v33 import _unload_model
from run_target_event_map_v51 import build_candidate_rows
from selective_discourse_state_v53 import select_commitment


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "metalinguistic_nonrequest_v54_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "metalinguistic_nonrequest_v54_holdout.json"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"
V51_CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DEFAULT_OUTPUT = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_raw.json"
CONTROL = "fresh_v51_model_control"
DETERMINISTIC = "v54_deterministic_state_machine_only"
HYBRID = "v54_selective_state_machine_with_fresh_v51_fallback"
CONDITIONS = (CONTROL, DETERMINISTIC, HYBRID)
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
            raise ValueError(f"V54 holdout frozen input hash mismatch: {path}")
    if tuple(config["conditions"]) != CONDITIONS:
        raise ValueError("V54 holdout condition order mismatch")
    if dataset["evidence_status"] != "frozen_before_any_model_inference":
        raise ValueError("V54 holdout was not frozen before inference")
    if dataset["case_count"] != config["frozen_inputs"]["case_count"]:
        raise ValueError("V54 holdout case count mismatch")
    if config["model_call_budget"] != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V54 holdout model-call budget mismatch")
    if any(
        config[key]
        for key in (
            "post_run_tuning_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "human_likeness_claim_authorized",
        )
    ):
        raise ValueError("V54 holdout cannot begin with advancement authorized")


def _checks(config, prompt):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "source_snapshot_sha256": _sha256(
            ROOT / config["frozen_inputs"]["external_source_snapshot"]
        ),
        "v51_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
    }


def _load_or_create(output, config, prompt, snapshot, candidate_rows, construction):
    checks = _checks(config, prompt)
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        for field, expected in checks.items():
            if report.get(field) != expected:
                raise ValueError(f"Existing V54 holdout report {field} mismatch")
        return report
    return {
        "schema": "uruha_metalinguistic_nonrequest_independent_holdout_raw_v54",
        "evidence_status": "project_fresh_external_and_controlled_holdout",
        "base_model_pretraining_exclusion_guaranteed": False,
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "conditions": list(CONDITIONS),
        "selected_carrier": config["fixed_carrier"],
        "model_snapshot": snapshot,
        "model_call_budget": config["model_call_budget"],
        "paid_api_used": False,
        "construction_audit": construction,
        "candidate_rows": candidate_rows,
        "target_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    dataset = load(DATASET_PATH)
    v52_config = load(V52_CONFIG_PATH)
    v51_config = load(V51_CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    _validate_inputs(config, dataset)

    construction = audit_holdout(
        dataset, config["target_mention_patterns"]
    )
    if not construction["passed"]:
        raise ValueError(
            f"V54 holdout construction gate failed: {construction['failed_checks']}"
        )
    candidate_rows = build_candidate_rows(dataset)
    target_count = sum(len(row["candidates"]) for row in candidate_rows)
    if target_count != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V54 holdout grounded target count drift")

    snapshot = _model_snapshot(config)
    judgment_config = {
        **v52_config,
        "fixed_model": config["fixed_model"],
        "fixed_carrier": config["fixed_carrier"],
    }
    v51_prompt = build_prompts(
        v52_config, v51_config, v45_config, v44_lock
    )["v51_event_map_control"]
    report = _load_or_create(
        output, config, v51_prompt, snapshot, candidate_rows, construction
    )
    completed = {
        (row["case_id"], row["target_id"]) for row in report["target_rows"]
    }
    ontology = load_v47_anchor_ontology()

    for candidate_row in candidate_rows:
        candidates = ground_supported_targets(candidate_row["user_input"], ontology)
        for candidate in candidates:
            key = (candidate_row["case_id"], candidate["target_id"])
            if key in completed:
                continue
            model_result = _run_judgment(
                "v51_event_map_control",
                candidate_row,
                candidate,
                judgment_config,
                v45_config,
                {"v51_event_map_control": v51_prompt},
                snapshot,
            )
            parsed = model_result["parsed"]
            fallback = (
                parsed.get("commitment") if parsed.get("parse_success") else "ambiguous"
            )
            state = resolve_target_state(
                candidate_row["user_input"],
                candidates,
                candidate["target_id"],
                config["target_mention_patterns"],
            )
            selected = select_commitment(state, fallback)
            report["target_rows"].append(
                {
                    "case_id": candidate_row["case_id"],
                    "target_id": candidate["target_id"],
                    "fresh_v51_result": model_result,
                    "state_machine": state,
                    "condition_commitments": {
                        CONTROL: fallback,
                        DETERMINISTIC: (
                            state["commitment"] if state["resolved"] else "ambiguous"
                        ),
                        HYBRID: selected["commitment"],
                    },
                    "hybrid_selection_source": selected["source"],
                }
            )
            _atomic_write(output, report)
            print(
                f"[v54 independent {len(report['target_rows'])}/{target_count}] "
                f"{candidate_row['case_id']} {candidate['target_id']}",
                flush=True,
            )
    _unload_model(snapshot["model_tag"])

    if len(report["target_rows"]) == target_count:
        report["completed_at"] = _now()
        report["model_calls_made"] = len(report["target_rows"])
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
                "target_rows": len(report["target_rows"]),
                "model_calls_made": report.get("model_calls_made"),
                "paid_api_used": report["paid_api_used"],
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
