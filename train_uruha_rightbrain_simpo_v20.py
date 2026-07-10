#!/usr/bin/env python3
"""Run the shared SimPO trainer on V20 length-matched hard negatives."""

from project_paths import (
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DATASET_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH,
)
from train_uruha_rightbrain_simpo_v19 import main


DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v20_hard_negative_simpo_v1"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_dataset=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DATASET_PATH,
            default_output_dir=DEFAULT_OUTPUT_DIR,
            default_run_report=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH,
        )
    )
