#!/usr/bin/env python3
"""Replay V53 deterministic states with a frozen V51 fallback; no model calls."""

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from selective_discourse_state_v53 import resolve_target_state, select_commitment


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "selective_discourse_state_v53_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "precise_target_mentions_v52_holdout.json"
V52_RAW_PATH = ROOT / "reports" / "precise_target_mentions_v52_holdout_raw.json"
DEFAULT_OUTPUT = ROOT / "reports" / "selective_discourse_state_v53_development_raw.json"
CONTROL_CONDITION = "frozen_v51_model_control"
DETERMINISTIC_CONDITION = "deterministic_state_machine_only"
HYBRID_CONDITION = "selective_state_machine_with_v51_fallback"
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


def _validate_inputs(config, dataset, v52_raw):
    for key, expected in config["frozen_inputs"].items():
        if not key.endswith("_sha256"):
            continue
        path = ROOT / config["frozen_inputs"][key.removesuffix("_sha256")]
        if _sha256(path) != expected:
            raise ValueError(f"V53 frozen input hash mismatch: {path}")
    if dataset["case_count"] != config["frozen_inputs"]["case_count"]:
        raise ValueError("V53 consumed development case count mismatch")
    if not v52_raw.get("completed_at") or len(v52_raw["judgment_rows"]) != 170:
        raise ValueError("V53 frozen V52 raw source is incomplete")
    if config["conditions"] != [
        CONTROL_CONDITION,
        DETERMINISTIC_CONDITION,
        HYBRID_CONDITION,
    ]:
        raise ValueError("V53 condition order mismatch")
    if config["model_calls_authorized"]:
        raise ValueError("V53 replay must not authorize model calls")
    if any(
        config[key]
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "human_likeness_claim_authorized",
        )
    ):
        raise ValueError("V53 development cannot pre-authorize advancement")


def _frozen_v51_lookup(v52_raw):
    lookup = {}
    for row in v52_raw["judgment_rows"]:
        if row["condition"] != "v51_event_map_control":
            continue
        parsed = row["result"]["parsed"]
        if not parsed.get("parse_success"):
            raise ValueError("V53 frozen V51 fallback contains parse failure")
        lookup[(row["case_id"], row["target_id"])] = parsed["commitment"]
    return lookup


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    dataset = load(DATASET_PATH)
    v52_raw = load(V52_RAW_PATH)
    _validate_inputs(config, dataset, v52_raw)
    ontology = load_v47_anchor_ontology()
    fallback_lookup = _frozen_v51_lookup(v52_raw)

    rows = []
    rule_counts = Counter()
    started = time.monotonic()
    for case in dataset["cases"]:
        candidates = ground_supported_targets(case["user_input"], ontology)
        for candidate in candidates:
            target_id = candidate["target_id"]
            fallback = fallback_lookup[(case["id"], target_id)]
            state = resolve_target_state(
                case["user_input"],
                candidates,
                target_id,
                config["target_mention_patterns"],
            )
            selected = select_commitment(state, fallback)
            rule_counts[state["resolution_rule"]] += 1
            rows.append(
                {
                    "case_id": case["id"],
                    "target_id": target_id,
                    "state_machine": state,
                    "frozen_v51_commitment": fallback,
                    "condition_commitments": {
                        CONTROL_CONDITION: fallback,
                        DETERMINISTIC_CONDITION: (
                            state["commitment"] if state["resolved"] else "ambiguous"
                        ),
                        HYBRID_CONDITION: selected["commitment"],
                    },
                    "hybrid_selection_source": selected["source"],
                }
            )
    elapsed = time.monotonic() - started
    if len(rows) != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V53 grounded target count drift")

    report = {
        "schema": "uruha_selective_discourse_state_development_raw_v53",
        "evidence_status": "development_only_on_consumed_v52_holdout",
        "started_at": _now(),
        "completed_at": _now(),
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "frozen_v52_raw_sha256": _sha256(V52_RAW_PATH),
        "conditions": config["conditions"],
        "model_calls_made": 0,
        "paid_api_used": False,
        "target_count": len(rows),
        "resolved_target_count": sum(
            row["state_machine"]["resolved"] for row in rows
        ),
        "fallback_target_count": sum(
            not row["state_machine"]["resolved"] for row in rows
        ),
        "rule_counts": dict(sorted(rule_counts.items())),
        "wall_seconds": round(elapsed, 6),
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
                "model_calls_made": report["model_calls_made"],
                "wall_seconds": report["wall_seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
