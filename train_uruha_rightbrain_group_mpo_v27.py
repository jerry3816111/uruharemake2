#!/usr/bin/env python3
"""Run the V27 single-variable learning-rate ablation from frozen V10."""

from project_paths import RIGHTBRAIN_GROUP_MPO_V27_TRAINING_RUN_REPORT_PATH
from train_uruha_rightbrain_group_mpo_v26 import main


DEFAULT_OUTPUT_DIR = "./uruha_rightbrain_plan_sft_lora_v27_group_mpo_lr3e7_v1"
DEFAULT_LEARNING_RATE = 3e-7


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_output_dir=DEFAULT_OUTPUT_DIR,
            default_run_report=RIGHTBRAIN_GROUP_MPO_V27_TRAINING_RUN_REPORT_PATH,
            default_learning_rate=DEFAULT_LEARNING_RATE,
            default_experiment_label="V27",
        )
    )
