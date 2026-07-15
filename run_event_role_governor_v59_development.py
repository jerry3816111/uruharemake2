#!/usr/bin/env python3
"""Replay frozen V58 holdout evidence through matched V58/V59 states."""

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from event_role_governor_v59 import resolve_target_state as resolve_v59
from grounded_commitment_classifier_v42 import ground_supported_targets
from relation_authorized_action_compiler_v57 import compile_relation_authorized_v57
from relational_commitment_context_v43 import assemble_commitment_only_case
from selective_discourse_state_v53 import select_commitment


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "event_role_governor_v59_preregistration.json"
LOCK_PATH = ROOT / "configs" / "event_role_governor_v59_replay_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "relation_safety_state_v58_holdout.json"
SOURCE_RAW_PATH = ROOT / "reports" / "relation_safety_state_v58_holdout_raw.json"
DEFAULT_OUTPUT = ROOT / "reports" / "event_role_governor_v59_development_raw.json"
CONTROL = "frozen_v58_state_with_v57_compiler_control"
CANDIDATE = "event_role_governor_v59_state_with_frozen_v57_compiler_candidate"
CONDITIONS = (CONTROL, CANDIDATE)
TZ = ZoneInfo("Asia/Tokyo")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _validate(config, lock, dataset, source_raw):
    for section in (config["frozen_inputs"], lock["frozen_artifacts"]):
        for key, expected_hash in section.items():
            if not key.endswith("_sha256"):
                continue
            path_key = key.removesuffix("_sha256")
            path = ROOT / section[path_key]
            if _sha256(path) != expected_hash:
                raise ValueError(f"V59 frozen artifact hash mismatch: {path}")
    if tuple(config["conditions"]) != CONDITIONS:
        raise ValueError("V59 preregistered condition order mismatch")
    if tuple(lock["conditions"]) != CONDITIONS:
        raise ValueError("V59 replay lock condition order mismatch")
    if config["model_calls_authorized"] != 0 or lock["model_calls_authorized"] != 0:
        raise ValueError("V59 development replay must make zero model calls")
    frozen = config["frozen_inputs"]
    if dataset["case_count"] != frozen["case_count"]:
        raise ValueError("V59 replay dataset case count mismatch")
    if len(source_raw["target_rows"]) != frozen["grounded_target_count"]:
        raise ValueError("V59 replay source target count mismatch")
    if len(source_raw["case_rows"]) != frozen["case_count"]:
        raise ValueError("V59 replay source case count mismatch")
    if source_raw.get("model_calls_made") != len(source_raw["target_rows"]):
        raise ValueError("V59 replay source model evidence is incomplete")
    if source_raw.get("dataset_sha256") != _sha256(DATASET_PATH):
        raise ValueError("V59 replay source is not bound to the frozen dataset")


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


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    lock = load(LOCK_PATH)
    dataset = load(DATASET_PATH)
    source_raw = load(SOURCE_RAW_PATH)
    _validate(config, lock, dataset, source_raw)

    source_by_case = {}
    for row in source_raw["target_rows"]:
        source_by_case.setdefault(row["case_id"], {})[row["target_id"]] = row

    patterns = load(
        ROOT / "configs" / "relation_safety_state_v58_holdout_preregistration.json"
    )["target_mention_patterns"]
    ontology = load_v47_anchor_ontology()
    target_rows = []
    case_rows = []
    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        frozen = source_by_case[case["id"]]
        control_commitments = {}
        candidate_commitments = {}
        control_states = {}
        candidate_states = {}
        for candidate in candidates:
            target_id = candidate["target_id"]
            source = frozen[target_id]
            fallback = source["shared_fallback_commitment"]
            state59 = resolve_v59(
                case["user_input"], candidates, target_id, patterns
            )
            selected59 = select_commitment(state59, fallback)
            control_commitments[target_id] = source["candidate_commitment"]
            candidate_commitments[target_id] = selected59["commitment"]
            control_states[target_id] = source["candidate_state"]
            candidate_states[target_id] = state59
            target_rows.append(
                {
                    "case_id": case["id"],
                    "target_id": target_id,
                    "shared_fallback_commitment": fallback,
                    "control_commitment": source["candidate_commitment"],
                    "control_selection_source": source[
                        "candidate_selection_source"
                    ],
                    "control_state": source["candidate_state"],
                    "candidate_commitment": selected59["commitment"],
                    "candidate_selection_source": selected59["source"],
                    "candidate_state": state59,
                }
            )

        case_rows.append(
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

    report = {
        "schema": "uruha_event_role_governor_development_raw_v59",
        "evidence_status": "zero_model_replay_on_consumed_v58_holdout",
        "completed_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "replay_harness_lock_sha256": _sha256(LOCK_PATH),
        "source_raw_sha256": _sha256(SOURCE_RAW_PATH),
        "conditions": list(CONDITIONS),
        "model_calls": 0,
        "paid_api_used": False,
        "physical_vrm_actions_executed": 0,
        "target_rows": target_rows,
        "case_rows": case_rows,
    }
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main():
    report = run()
    print(
        json.dumps(
            {
                "target_rows": len(report["target_rows"]),
                "case_rows": len(report["case_rows"]),
                "model_calls": report["model_calls"],
                "paid_api_used": report["paid_api_used"],
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
