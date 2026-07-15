#!/usr/bin/env python3
"""Run one fresh shared fallback per target for matched V59/V60 evaluation."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from audit_predicate_morphology_v60_independent_holdout import audit as audit_holdout
from event_role_governor_v59 import resolve_target_state as resolve_v59
from grounded_commitment_classifier_v42 import ground_supported_targets
from predicate_morphology_v60 import resolve_target_state as resolve_v60
from relation_authorized_action_compiler_v57 import compile_relation_authorized_v57
from relational_commitment_context_v43 import assemble_commitment_only_case
from run_precise_target_mentions_v52 import _model_snapshot, _run_judgment, build_prompts
from run_rightbrain_qwen35_migration_v33 import _unload_model
from run_target_event_map_v51 import build_candidate_rows
from selective_discourse_state_v53 import select_commitment


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "predicate_morphology_v60_independent_holdout_preregistration.json"
HARNESS_LOCK_PATH = ROOT / "configs" / "predicate_morphology_v60_independent_holdout_harness_lock.json"
CONSTRUCTION_CONFIG_PATH = ROOT / "configs" / "predicate_morphology_v60_independent_holdout_construction_preregistration.json"
PATTERN_CONFIG_PATH = ROOT / "configs" / "relation_safety_state_v58_holdout_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "predicate_morphology_v60_independent_holdout.json"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"
V51_CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DEFAULT_OUTPUT = ROOT / "reports" / "predicate_morphology_v60_independent_holdout_raw.json"
CONTROL = "fresh_v59_state_with_frozen_v57_compiler_control"
CANDIDATE = "fresh_v60_state_with_frozen_v57_compiler_candidate"
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


def _git_branch():
    return subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()


def _git_tracked_tree_clean():
    worktree = subprocess.run(
        ["git", "diff", "--quiet"], cwd=ROOT, check=False
    )
    index = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False
    )
    return worktree.returncode == 0 and index.returncode == 0


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _verify_bindings(section, label):
    for key, expected in section.items():
        if not key.endswith("_sha256"):
            continue
        path_key = key.removesuffix("_sha256")
        if path_key not in section:
            raise ValueError(f"V60 {label} missing path for {key}")
        path = ROOT / section[path_key]
        if _sha256(path) != expected:
            raise ValueError(f"V60 {label} hash mismatch: {path}")


def _validate_inputs(config, harness, dataset):
    _verify_bindings(config["frozen_inputs"], "preregistration input")
    _verify_bindings(harness["frozen_artifacts"], "harness artifact")
    if tuple(config["conditions"]) != CONDITIONS:
        raise ValueError("V60 holdout preregistered condition order mismatch")
    if tuple(harness["conditions"]) != CONDITIONS:
        raise ValueError("V60 holdout harness condition order mismatch")
    if dataset["evidence_status"] != "frozen_before_any_v59_or_v60_independent_evaluation":
        raise ValueError("V60 holdout was not frozen before evaluation")
    frozen = config["frozen_inputs"]
    if dataset["case_count"] != frozen["case_count"]:
        raise ValueError("V60 holdout case count mismatch")
    if dataset["grounded_target_count"] != frozen["grounded_target_count"]:
        raise ValueError("V60 holdout target count mismatch")
    if config["model_call_budget"] != frozen["grounded_target_count"]:
        raise ValueError("V60 holdout model-call budget mismatch")
    if harness["model_calls_authorized"] != config["model_call_budget"]:
        raise ValueError("V60 harness model-call authorization mismatch")
    if _git_branch() != harness["required_run_branch"]:
        raise ValueError("V60 holdout can run only from the merged main branch")
    if not _git_tracked_tree_clean():
        raise ValueError("V60 holdout requires a clean tracked worktree and index")
    committed_lock = subprocess.run(
        [
            "git",
            "cat-file",
            "-e",
            f"HEAD:{HARNESS_LOCK_PATH.relative_to(ROOT)}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if committed_lock.returncode != 0:
        raise ValueError("V60 harness lock is not committed at the run revision")
    if any(
        config[key]
        for key in (
            "holdout_inference_before_harness_freeze_authorized",
            "post_run_tuning_authorized",
            "post_run_threshold_change_authorized",
            "post_run_case_exclusion_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "broad_human_likeness_claim_authorized",
        )
    ):
        raise ValueError("V60 holdout cannot begin with tuning or deployment authorized")


def _checks(config, prompt):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "harness_lock_sha256": _sha256(HARNESS_LOCK_PATH),
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
                raise ValueError(f"Existing V60 holdout report {field} mismatch")
        for field, expected in (
            ("model_snapshot", snapshot),
            ("candidate_rows", candidate_rows),
            ("construction_audit", construction),
            ("model_call_budget", config["model_call_budget"]),
            ("conditions", list(CONDITIONS)),
        ):
            if report.get(field) != expected:
                raise ValueError(f"Existing V60 holdout report {field} drift")
        return report
    return {
        "schema": "uruha_predicate_morphology_fresh_holdout_raw_v60",
        "evidence_status": "second_project_fresh_external_and_controlled_predicate_holdout",
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
    by_case = {}
    for row in target_rows:
        by_case.setdefault(row["case_id"], {})[row["target_id"]] = row
    ontology = load_v47_anchor_ontology()
    rows = []
    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        frozen_rows = by_case[case["id"]]
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
    harness = load(HARNESS_LOCK_PATH)
    construction_config = load(CONSTRUCTION_CONFIG_PATH)
    pattern_config = load(PATTERN_CONFIG_PATH)
    dataset = load(DATASET_PATH)
    v52_config = load(V52_CONFIG_PATH)
    v51_config = load(V51_CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    _validate_inputs(config, harness, dataset)

    construction = audit_holdout(dataset, construction_config)
    if not construction["passed"]:
        failures = [name for name, passed in construction["checks"].items() if not passed]
        raise ValueError(f"V60 holdout construction gate failed: {failures}")
    candidate_rows = build_candidate_rows(dataset)
    target_count = sum(len(row["candidates"]) for row in candidate_rows)
    if target_count != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V60 holdout grounded target count drift")

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
    mention_patterns = pattern_config["target_mention_patterns"]

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
            state59 = resolve_v59(
                candidate_row["user_input"],
                candidates,
                candidate["target_id"],
                mention_patterns,
            )
            state60 = resolve_v60(
                candidate_row["user_input"],
                candidates,
                candidate["target_id"],
                mention_patterns,
            )
            selected59 = select_commitment(state59, fallback)
            selected60 = select_commitment(state60, fallback)
            report["target_rows"].append(
                {
                    "case_id": candidate_row["case_id"],
                    "target_id": candidate["target_id"],
                    "fresh_v51_result": model_result,
                    "shared_fallback_commitment": fallback,
                    "control_state": state59,
                    "control_commitment": selected59["commitment"],
                    "control_selection_source": selected59["source"],
                    "candidate_state": state60,
                    "candidate_commitment": selected60["commitment"],
                    "candidate_selection_source": selected60["source"],
                }
            )
            _atomic_write(output, report)
            print(
                f"[v60 holdout {len(report['target_rows'])}/{target_count}] "
                f"{candidate_row['case_id']} {candidate['target_id']}",
                flush=True,
            )
    _unload_model(snapshot["model_tag"])

    if len(report["target_rows"]) == target_count:
        report["case_rows"] = _compile_cases(dataset, report["target_rows"])
        report["completed_at"] = _now()
        report["model_calls_made"] = len(report["target_rows"])
        report["transport_attempts_made"] = sum(
            row["fresh_v51_result"]["transport_attempts"]
            for row in report["target_rows"]
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
                "target_rows": len(report["target_rows"]),
                "case_rows": len(report["case_rows"]),
                "model_calls_made": report.get("model_calls_made"),
                "transport_attempts_made": report.get("transport_attempts_made"),
                "paid_api_used": report["paid_api_used"],
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
