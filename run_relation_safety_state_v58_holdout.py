#!/usr/bin/env python3
"""Run one fresh fallback per target and compare matched V56/V58 states."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from audit_relation_safety_state_v58_holdout import audit as audit_holdout
from grounded_commitment_classifier_v42 import ground_supported_targets
from relation_authorized_action_compiler_v57 import compile_relation_authorized_v57
from relation_bound_event_graph_v56 import resolve_target_state as resolve_v56
from relation_safety_state_v58 import resolve_target_state as resolve_v58
from relational_commitment_context_v43 import assemble_commitment_only_case
from run_precise_target_mentions_v52 import _model_snapshot, _run_judgment, build_prompts
from run_rightbrain_qwen35_migration_v33 import _unload_model
from run_target_event_map_v51 import build_candidate_rows
from selective_discourse_state_v53 import select_commitment


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_safety_state_v58_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_safety_state_v58_holdout.json"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"
V51_CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DEFAULT_OUTPUT = ROOT / "reports" / "relation_safety_state_v58_holdout_raw.json"
CONTROL = "fresh_v56_state_with_frozen_v57_compiler_control"
CANDIDATE = "fresh_v58_state_with_frozen_v57_compiler_candidate"
CONDITIONS = (CONTROL, CANDIDATE)
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
        path_key = key.removesuffix("_sha256")
        path = ROOT / config["frozen_inputs"][path_key]
        if _sha256(path) != expected:
            raise ValueError(f"V58 holdout frozen input hash mismatch: {path}")
    if tuple(config["conditions"]) != CONDITIONS:
        raise ValueError("V58 holdout condition order mismatch")
    if dataset["evidence_status"] != "frozen_before_any_v58_holdout_inference":
        raise ValueError("V58 holdout was not frozen before inference")
    frozen = config["frozen_inputs"]
    if dataset["case_count"] != frozen["case_count"]:
        raise ValueError("V58 holdout case count mismatch")
    if config["model_call_budget"] != frozen["grounded_target_count"]:
        raise ValueError("V58 holdout model-call budget mismatch")
    if any(
        config[key]
        for key in (
            "post_run_tuning_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "broad_human_likeness_claim_authorized",
        )
    ):
        raise ValueError("V58 holdout cannot begin with advancement authorized")


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
                raise ValueError(f"Existing V58 holdout report {field} mismatch")
        return report
    return {
        "schema": "uruha_relation_safety_state_fresh_holdout_raw_v58",
        "evidence_status": "project_fresh_external_and_frozen_controlled_holdout",
        "base_model_pretraining_exclusion_guaranteed": False,
        "controlled_cases_are_official_corpus": False,
        "controlled_cases_human_blind_reviewed": False,
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "conditions": list(CONDITIONS),
        "selected_carrier": config["fixed_carrier"],
        "model_snapshot": snapshot,
        "model_call_budget": config["model_call_budget"],
        "paid_api_used": False,
        "physical_vrm_actions_executed": 0,
        "construction_audit": construction,
        "candidate_rows": candidate_rows,
        "target_rows": [],
        "case_rows": [],
    }


def _parsed(user_input, candidates, commitments):
    judgments = {
        candidate["target_id"]: {
            "parse_success": True,
            "errors": [],
            "commitment": commitments[candidate["target_id"]],
        }
        for candidate in candidates
    }
    return assemble_commitment_only_case(user_input, candidates, judgments)


def _compile_cases(dataset, target_rows):
    raw_by_case = {}
    for row in target_rows:
        raw_by_case.setdefault(row["case_id"], {})[row["target_id"]] = row
    ontology = load_v47_anchor_ontology()
    rows = []
    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        frozen_rows = raw_by_case[case["id"]]
        control_commitments = {
            target_id: row["control_commitment"]
            for target_id, row in frozen_rows.items()
        }
        candidate_commitments = {
            target_id: row["candidate_commitment"]
            for target_id, row in frozen_rows.items()
        }
        control_states = {
            target_id: row["control_state"] for target_id, row in frozen_rows.items()
        }
        candidate_states = {
            target_id: row["candidate_state"] for target_id, row in frozen_rows.items()
        }
        rows.append(
            {
                "case_id": case["id"],
                "user_input": case["user_input"],
                "control_commitments": control_commitments,
                "candidate_commitments": candidate_commitments,
                "control_compilation": compile_relation_authorized_v57(
                    case["user_input"],
                    _parsed(case["user_input"], candidates, control_commitments),
                    control_states,
                    ontology,
                ),
                "candidate_compilation": compile_relation_authorized_v57(
                    case["user_input"],
                    _parsed(case["user_input"], candidates, candidate_commitments),
                    candidate_states,
                    ontology,
                ),
            }
        )
    return rows


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    dataset = load(DATASET_PATH)
    v52_config = load(V52_CONFIG_PATH)
    v51_config = load(V51_CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    _validate_inputs(config, dataset)

    construction = audit_holdout(dataset, config["target_mention_patterns"])
    if not construction["passed"]:
        raise ValueError(
            f"V58 holdout construction gate failed: {construction['failed_checks']}"
        )
    candidate_rows = build_candidate_rows(dataset)
    target_count = sum(len(row["candidates"]) for row in candidate_rows)
    if target_count != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V58 holdout grounded target count drift")

    snapshot = _model_snapshot(config)
    judgment_config = {
        **v52_config,
        "fixed_model": config["fixed_model"],
        "fixed_carrier": config["fixed_carrier"],
    }
    v51_prompt = build_prompts(v52_config, v51_config, v45_config, v44_lock)[
        "v51_event_map_control"
    ]
    report = _load_or_create(
        output, config, v51_prompt, snapshot, candidate_rows, construction
    )
    completed = {(row["case_id"], row["target_id"]) for row in report["target_rows"]}
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
                parsed.get("commitment")
                if parsed.get("parse_success")
                else "ambiguous"
            )
            state56 = resolve_v56(
                candidate_row["user_input"],
                candidates,
                candidate["target_id"],
                config["target_mention_patterns"],
            )
            state58 = resolve_v58(
                candidate_row["user_input"],
                candidates,
                candidate["target_id"],
                config["target_mention_patterns"],
            )
            selected56 = select_commitment(state56, fallback)
            selected58 = select_commitment(state58, fallback)
            report["target_rows"].append(
                {
                    "case_id": candidate_row["case_id"],
                    "target_id": candidate["target_id"],
                    "fresh_v51_result": model_result,
                    "shared_fallback_commitment": fallback,
                    "control_state": state56,
                    "control_commitment": selected56["commitment"],
                    "control_selection_source": selected56["source"],
                    "candidate_state": state58,
                    "candidate_commitment": selected58["commitment"],
                    "candidate_selection_source": selected58["source"],
                }
            )
            _atomic_write(output, report)
            print(
                f"[v58 holdout {len(report['target_rows'])}/{target_count}] "
                f"{candidate_row['case_id']} {candidate['target_id']}",
                flush=True,
            )
    _unload_model(snapshot["model_tag"])

    if len(report["target_rows"]) == target_count:
        report["case_rows"] = _compile_cases(dataset, report["target_rows"])
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
                "case_rows": len(report["case_rows"]),
                "model_calls_made": report.get("model_calls_made"),
                "paid_api_used": report["paid_api_used"],
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
