#!/usr/bin/env python3
"""Train V21 only after the matching frozen-policy probe authorizes it."""

import argparse
import json
from pathlib import Path

from project_paths import (
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_PROBE_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_TRAINING_RUN_REPORT_PATH,
)
from train_uruha_rightbrain_contract_v1 import _sha256
from train_uruha_rightbrain_simpo_v19 import main


DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v21_on_policy_simpo_v1"


def requested_dataset(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dataset", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH)
    args, _ = parser.parse_known_args(argv)
    return args.dataset


def validate_probe(
    dataset_path=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
    probe_path=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_PROBE_JSON_PATH,
):
    report = json.loads(Path(probe_path).read_text(encoding="utf-8"))
    if not report.get("decision", {}).get("authorize_training"):
        raise ValueError("V21 pre-training preference probe did not authorize training")
    current_sha256 = _sha256(dataset_path)
    if report.get("dataset_sha256") != current_sha256:
        raise ValueError("V21 dataset changed after the pre-training probe")
    return report


if __name__ == "__main__":
    validate_probe(requested_dataset())
    raise SystemExit(
        main(
            default_dataset=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
            default_output_dir=DEFAULT_OUTPUT_DIR,
            default_run_report=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_TRAINING_RUN_REPORT_PATH,
        )
    )
