#!/usr/bin/env python3
"""Replay frozen V56 states through V48 and V57 without model inference."""

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from relational_commitment_context_v43 import assemble_commitment_only_case
from relation_authorized_action_compiler_v57 import compile_relation_authorized_v57
from run_relation_bound_event_graph_v56_holdout import V56_HYBRID
from target_relative_scope_v48 import compile_target_relative_v48


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "relation_authorized_action_compiler_v57_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "relation_bound_event_graph_v56_holdout.json"
V56_RAW_PATH = ROOT / "reports" / "relation_bound_event_graph_v56_holdout_raw.json"
DEFAULT_OUTPUT = ROOT / "reports" / "relation_authorized_action_compiler_v57_development_raw.json"
CONTROL = "v56_with_frozen_v48_compiler_control"
CANDIDATE = "v56_with_relation_authorized_v57_compiler_candidate"
CONDITIONS = (CONTROL, CANDIDATE)
TZ = ZoneInfo("Asia/Tokyo")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _validate(config, dataset, frozen_raw):
    for key, expected in config["frozen_inputs"].items():
        if not key.endswith("_sha256"):
            continue
        path = ROOT / config["frozen_inputs"][key.removesuffix("_sha256")]
        if _sha256(path) != expected:
            raise ValueError(f"V57 frozen input hash mismatch: {path}")
    if tuple(config["conditions"]) != CONDITIONS:
        raise ValueError("V57 condition order mismatch")
    if config["model_calls_authorized"]:
        raise ValueError("V57 development must not call a model")
    if len(dataset["cases"]) != config["frozen_inputs"]["case_count"]:
        raise ValueError("V57 dataset case count mismatch")
    if len(frozen_raw["target_rows"]) != config["frozen_inputs"][
        "grounded_target_count"
    ]:
        raise ValueError("V57 frozen target count mismatch")


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    dataset = load(DATASET_PATH)
    frozen_raw = load(V56_RAW_PATH)
    _validate(config, dataset, frozen_raw)
    raw_by_case = {}
    for row in frozen_raw["target_rows"]:
        raw_by_case.setdefault(row["case_id"], {})[row["target_id"]] = row

    ontology = load_v47_anchor_ontology()
    case_rows = []
    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        frozen_rows = raw_by_case[case["id"]]
        judgments = {
            candidate["target_id"]: {
                "parse_success": True,
                "errors": [],
                "commitment": frozen_rows[candidate["target_id"]][
                    "condition_commitments"
                ][V56_HYBRID],
            }
            for candidate in candidates
        }
        parsed = assemble_commitment_only_case(
            case["user_input"], candidates, judgments
        )
        states = {
            target_id: row["v56_state_machine"]
            for target_id, row in frozen_rows.items()
        }
        control = compile_target_relative_v48(case["user_input"], parsed, ontology)
        candidate = compile_relation_authorized_v57(
            case["user_input"], parsed, states, ontology
        )
        case_rows.append(
            {
                "case_id": case["id"],
                "user_input": case["user_input"],
                "frozen_commitments": {
                    target_id: judgment["commitment"]
                    for target_id, judgment in judgments.items()
                },
                "control_compilation": control,
                "candidate_compilation": candidate,
            }
        )

    report = {
        "schema": "uruha_relation_authorized_action_compiler_development_raw_v57",
        "evidence_status": "development_replay_on_consumed_v56_holdout",
        "completed_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "source_v56_raw_sha256": _sha256(V56_RAW_PATH),
        "conditions": list(CONDITIONS),
        "model_calls": 0,
        "paid_api_used": False,
        "case_rows": case_rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main():
    report = run()
    print(
        json.dumps(
            {
                "case_count": len(report["case_rows"]),
                "model_calls": report["model_calls"],
                "paid_api_used": report["paid_api_used"],
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
