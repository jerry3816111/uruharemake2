#!/usr/bin/env python3
"""Run V4 through the frozen matched typed-reflection harness."""

from __future__ import annotations

import argparse
from pathlib import Path

import run_typed_reflection_v3_development as v3


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "typed_reflection_v4_development_preregistration.json"
LOCK_PATH = ROOT / "configs" / "typed_reflection_v4_harness_lock.json"
DATASET_PATH = ROOT / "datasets" / "typed_reflection_v4_development_pilot.json"
DEFAULT_OUTPUT = ROOT / "reports" / "typed_reflection_v4_development_raw.json"
CONTROL = "same_episode_without_v4_reflection_control"
TREATMENT = "same_episode_with_v4_structured_reflection_treatment"
CONDITIONS = (CONTROL, TREATMENT)


def run(output=DEFAULT_OUTPUT):
    originals = (
        v3.CONFIG_PATH,
        v3.LOCK_PATH,
        v3.DATASET_PATH,
        v3.DEFAULT_OUTPUT,
        v3.CONTROL,
        v3.TREATMENT,
        v3.CONDITIONS,
    )
    try:
        v3.CONFIG_PATH = CONFIG_PATH
        v3.LOCK_PATH = LOCK_PATH
        v3.DATASET_PATH = DATASET_PATH
        v3.DEFAULT_OUTPUT = DEFAULT_OUTPUT
        v3.CONTROL = CONTROL
        v3.TREATMENT = TREATMENT
        v3.CONDITIONS = CONDITIONS
        report = v3.run(output)
        report["schema"] = "uruha_typed_reflection_development_raw_v4"
        report["evidence_status"] = (
            "frozen_matched_v4_development_pilot_completed_without_runtime_tuning"
        )
        report["extractor"] = "program_grounded_fields_plus_ollama_json_schema_surface"
        v3.atomic_write(output, report)
        return report
    finally:
        (
            v3.CONFIG_PATH,
            v3.LOCK_PATH,
            v3.DATASET_PATH,
            v3.DEFAULT_OUTPUT,
            v3.CONTROL,
            v3.TREATMENT,
            v3.CONDITIONS,
        ) = originals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
