#!/usr/bin/env python3
"""Run the post-fix diagnostic replay through the frozen V1 paired harness."""

from __future__ import annotations

import argparse
from pathlib import Path

import run_reflection_causal_pilot_v1 as v1


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "reflection_causal_replay_v2_preregistration.json"
LOCK_PATH = ROOT / "configs" / "reflection_causal_replay_v2_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "reflection_causal_pilot_v1.json"
DEFAULT_OUTPUT = ROOT / "reports" / "reflection_causal_replay_v2_raw.json"


def run(output=DEFAULT_OUTPUT):
    originals = (v1.CONFIG_PATH, v1.LOCK_PATH, v1.DATASET_PATH, v1.DEFAULT_OUTPUT)
    try:
        v1.CONFIG_PATH = CONFIG_PATH
        v1.LOCK_PATH = LOCK_PATH
        v1.DATASET_PATH = DATASET_PATH
        v1.DEFAULT_OUTPUT = DEFAULT_OUTPUT
        report = v1.run(output)
        report["schema"] = "uruha_reflection_causal_replay_raw_v2"
        report["evidence_status"] = "diagnostic_seen_case_replay_after_persistent_candidate_fix"
        report["dataset_reuse_status"] = "exact_seen_v1_replay_not_an_independent_holdout"
        report["v1_baseline_analysis"] = "reports/reflection_causal_pilot_v1_analysis.json"
        v1.atomic_write(output, report)
        return report
    finally:
        v1.CONFIG_PATH, v1.LOCK_PATH, v1.DATASET_PATH, v1.DEFAULT_OUTPUT = originals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
