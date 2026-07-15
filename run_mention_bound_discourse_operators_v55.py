#!/usr/bin/env python3
"""Replay V55 on consumed V54 evidence with the frozen V51 fallback."""

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from mention_bound_discourse_operators_v55 import resolve_target_state
from selective_discourse_state_v53 import select_commitment


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "mention_bound_discourse_operators_v55_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "metalinguistic_nonrequest_v54_holdout.json"
V54_RAW_PATH = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_raw.json"
DEFAULT_OUTPUT = ROOT / "reports" / "mention_bound_discourse_operators_v55_development_raw.json"
CONTROL = "frozen_v54_hybrid_control"
DETERMINISTIC = "v55_deterministic_operator_only"
HYBRID = "v55_selective_operator_with_frozen_v51_fallback"
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


def _validate_inputs(config, dataset, v54_raw):
    for key, expected in config["frozen_inputs"].items():
        if not key.endswith("_sha256"):
            continue
        path = ROOT / config["frozen_inputs"][key.removesuffix("_sha256")]
        if _sha256(path) != expected:
            raise ValueError(f"V55 frozen input hash mismatch: {path}")
    if tuple(config["conditions"]) != CONDITIONS:
        raise ValueError("V55 condition order mismatch")
    if dataset["case_count"] != 64 or len(v54_raw["target_rows"]) != 76:
        raise ValueError("V55 consumed V54 evidence is incomplete")
    if config["model_calls_authorized"]:
        raise ValueError("V55 development replay cannot call a model")
    if any(
        config[key]
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
        )
    ):
        raise ValueError("V55 cannot pre-authorize integration")


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    dataset = load(DATASET_PATH)
    v54_raw = load(V54_RAW_PATH)
    _validate_inputs(config, dataset, v54_raw)
    frozen = {
        (row["case_id"], row["target_id"]): row for row in v54_raw["target_rows"]
    }
    ontology = load_v47_anchor_ontology()
    rows = []
    rule_counts = Counter()
    correction_counts = Counter()

    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        for candidate in candidates:
            target_id = candidate["target_id"]
            old = frozen[(case["id"], target_id)]
            fallback = old["condition_commitments"]["fresh_v51_model_control"]
            control = old["condition_commitments"][
                "v54_selective_state_machine_with_fresh_v51_fallback"
            ]
            state = resolve_target_state(
                case["user_input"],
                candidates,
                target_id,
                config["target_mention_patterns"],
            )
            selected = select_commitment(state, fallback)
            rule_counts[state["resolution_rule"]] += 1
            if "v55_correction" in state:
                correction_counts[state["v55_correction"]["operator"]] += 1
            rows.append(
                {
                    "case_id": case["id"],
                    "target_id": target_id,
                    "state_machine": state,
                    "frozen_v51_commitment": fallback,
                    "frozen_v54_hybrid_commitment": control,
                    "condition_commitments": {
                        CONTROL: control,
                        DETERMINISTIC: (
                            state["commitment"] if state["resolved"] else "ambiguous"
                        ),
                        HYBRID: selected["commitment"],
                    },
                    "hybrid_selection_source": selected["source"],
                }
            )

    if len(rows) != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V55 grounded target count drift")
    report = {
        "schema": "uruha_mention_bound_discourse_operators_development_raw_v55",
        "evidence_status": "development_only_on_consumed_v54_holdout",
        "started_at": _now(),
        "completed_at": _now(),
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "frozen_v54_raw_sha256": _sha256(V54_RAW_PATH),
        "conditions": list(CONDITIONS),
        "model_calls_made": 0,
        "paid_api_used": False,
        "target_count": len(rows),
        "resolved_target_count": sum(row["state_machine"]["resolved"] for row in rows),
        "fallback_target_count": sum(
            not row["state_machine"]["resolved"] for row in rows
        ),
        "v55_correction_count": sum(correction_counts.values()),
        "correction_counts": dict(sorted(correction_counts.items())),
        "rule_counts": dict(sorted(rule_counts.items())),
        "target_rows": rows,
    }
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
                "target_count": report["target_count"],
                "resolved_target_count": report["resolved_target_count"],
                "fallback_target_count": report["fallback_target_count"],
                "v55_correction_count": report["v55_correction_count"],
                "model_calls_made": report["model_calls_made"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
