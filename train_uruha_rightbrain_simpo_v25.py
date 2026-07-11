#!/usr/bin/env python3
"""Train a pairwise V25 candidate with positive-completion NLL."""

from project_paths import (
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V25_TRAINING_RUN_REPORT_PATH,
)
from train_uruha_rightbrain_simpo_v19 import main
from train_uruha_rightbrain_simpo_v21 import requested_dataset, validate_probe


DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v25_pairwise_nll_simpo_v1"


if __name__ == "__main__":
    validate_probe(requested_dataset())
    raise SystemExit(
        main(
            default_dataset=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
            default_output_dir=DEFAULT_OUTPUT_DIR,
            default_run_report=RIGHTBRAIN_ON_POLICY_PREFERENCE_V25_TRAINING_RUN_REPORT_PATH,
            force_chosen_nll_weight=1.0,
        )
    )
