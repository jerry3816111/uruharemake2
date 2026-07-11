#!/usr/bin/env python3
"""Train a prompt-balanced V23 candidate from the frozen V10 adapter."""

from project_paths import (
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V23_TRAINING_RUN_REPORT_PATH,
)
from train_uruha_rightbrain_simpo_v19 import main
from train_uruha_rightbrain_simpo_v21 import requested_dataset, validate_probe


DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v23_prompt_balanced_simpo_v1"


if __name__ == "__main__":
    validate_probe(requested_dataset())
    raise SystemExit(
        main(
            default_dataset=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
            default_output_dir=DEFAULT_OUTPUT_DIR,
            default_run_report=RIGHTBRAIN_ON_POLICY_PREFERENCE_V23_TRAINING_RUN_REPORT_PATH,
            force_prompt_balance=True,
        )
    )
