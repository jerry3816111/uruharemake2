#!/usr/bin/env python3
"""Replay the one-change V54 correction with frozen V51 fallback."""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets
from metalinguistic_nonrequest_v54 import resolve_target_state
from run_selective_discourse_state_v53 import (
    CONTROL_CONDITION,
    DETERMINISTIC_CONDITION,
    HYBRID_CONDITION,
    _atomic_write,
    _frozen_v51_lookup,
    _git_head,
    _now,
    _sha256,
    _validate_inputs,
)
from selective_discourse_state_v53 import select_commitment


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "metalinguistic_nonrequest_v54_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "precise_target_mentions_v52_holdout.json"
V52_RAW_PATH = ROOT / "reports" / "precise_target_mentions_v52_holdout_raw.json"
DEFAULT_OUTPUT = ROOT / "reports" / "metalinguistic_nonrequest_v54_development_raw.json"


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
    correction_count = 0
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
            correction_count += int("v54_correction" in state)
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
        raise ValueError("V54 grounded target count drift")

    report = {
        "schema": "uruha_metalinguistic_nonrequest_development_raw_v54",
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
        "v54_correction_count": correction_count,
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
                "v54_correction_count": report["v54_correction_count"],
                "model_calls_made": report["model_calls_made"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
