#!/usr/bin/env python3
"""Evaluate V27 with the unchanged V26 promotion gates."""

from eval_rightbrain_group_mpo_v26_decision import main
from project_paths import (
    RIGHTBRAIN_GROUP_MPO_V27_DECISION_JSON_PATH,
    RIGHTBRAIN_GROUP_MPO_V27_DECISION_MD_PATH,
    RIGHTBRAIN_GROUP_MPO_V27_TRAINING_RUN_REPORT_PATH,
)


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_training_report=RIGHTBRAIN_GROUP_MPO_V27_TRAINING_RUN_REPORT_PATH,
            default_output_json=RIGHTBRAIN_GROUP_MPO_V27_DECISION_JSON_PATH,
            default_output_md=RIGHTBRAIN_GROUP_MPO_V27_DECISION_MD_PATH,
        )
    )
