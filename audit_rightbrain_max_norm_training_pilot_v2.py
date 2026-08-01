#!/usr/bin/env python3
"""Finalize the preregistered pre-evaluation invalidation of max-norm pilot v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_rightbrain_max_norm_training_pilot_v2 as construction
import run_rightbrain_max_norm_training_pilot_v2 as runner


ROOT = Path(__file__).resolve().parent
RESULT_JSON = ROOT / "reports/rightbrain_max_norm_training_pilot_v2_invalid_result.json"
RESULT_MD = ROOT / "reports/rightbrain_max_norm_training_pilot_v2_invalid_result.md"


def audit():
    preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)
    pair_path = ROOT / preregistration["result_paths"]["training_pair_integrity_json"]
    evaluation_lock_path = ROOT / preregistration["result_paths"]["evaluation_lock"]
    pair = construction.load_json(pair_path)
    evaluation_lock = construction.load_json(evaluation_lock_path)
    training = {
        condition: construction.load_json(runner._training_report_path(preregistration, condition))
        for condition in construction.CONDITIONS
    }
    checks = {
        "pair_integrity_failed": not pair["decision"]["passed"],
        "first_losses_match": pair["checks"]["first_eight_losses_exact_match"],
        "first_preclip_norm_not_reproducible": not pair["checks"][
            "first_preclip_norm_reproducible"
        ],
        "both_training_runs_complete": pair["checks"]["both_80_micro_steps"]
        and pair["checks"]["both_10_updates"],
        "zero_nonfinite_events": pair["checks"]["zero_nonfinite_events"],
        "foreach_false_every_update": pair["checks"]["foreach_false_recorded_every_update"],
        "evaluation_not_authorized": not evaluation_lock["authorization"][
            "condition_isolated_holdout_evaluation"
        ],
        "no_evaluation_outputs": all(
            not runner._evaluation_report_path(preregistration, condition).exists()
            for condition in construction.CONDITIONS
        ),
    }
    return {
        "schema": "uruha_rightbrain_max_norm_training_pilot_invalid_result_v2",
        "experiment_id": construction.EXPERIMENT_ID,
        "inputs": {
            "preregistration": construction.file_binding(construction.DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(construction.DEFAULT_EXECUTION_LOCK),
            "training_pair_integrity": construction.file_binding(pair_path),
            "evaluation_lock": construction.file_binding(evaluation_lock_path),
            "training_reports": {
                condition: construction.file_binding(
                    runner._training_report_path(preregistration, condition)
                )
                for condition in construction.CONDITIONS
            },
        },
        "checks": checks,
        "causal_integrity": {
            "control_first_preclip_gradient_norm": pair[
                "control_first_preclip_gradient_norm"
            ],
            "treatment_first_preclip_gradient_norm": pair[
                "treatment_first_preclip_gradient_norm"
            ],
            "preclip_norm_relative_error": pair["preclip_norm_relative_error"],
            "required_relative_error_maximum": pair["required_relative_error_maximum"],
            "first_eight_micro_step_losses": pair["first_eight_micro_step_losses"],
        },
        "training_summary": {
            condition: {
                "mean_training_loss": row["mean_training_loss"],
                "final_training_loss": row["final_training_loss"],
                "clipped_update_count": row["clipped_update_count"],
                "maximum_observed_gradient_norm_before_clipping": row[
                    "maximum_observed_gradient_norm_before_clipping"
                ],
                "adapter_relative_l2_change": row["adapter_change"][
                    "adapter_relative_l2_change"
                ],
            }
            for condition, row in training.items()
        },
        "decision": {
            "valid_causal_comparison": False,
            "outcome": "invalidate_v2_before_holdout_due_backward_nondeterminism",
            "holdout_evaluation_executed": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
            "authorized_next_step": "zero_update_factorial_reproducibility_probe_before_any_v3_training",
        },
        "boundaries": preregistration["boundaries"],
    }


def render_markdown(result):
    causal = result["causal_integrity"]
    return "\n".join(
        [
            "# RightBrain max_norm 公平訓練試驗 v2 無效結果",
            "",
            f"- 判定：`{result['decision']['outcome']}`",
            "- `foreach=False`：兩組全部更新皆成立",
            "- 前 8 個 loss：完全一致",
            f"- control 第一個 raw norm：`{causal['control_first_preclip_gradient_norm']:.10f}`",
            f"- treatment 第一個 raw norm：`{causal['treatment_first_preclip_gradient_norm']:.10f}`",
            f"- 相對誤差：`{causal['preclip_norm_relative_error']:.6%}`",
            "- holdout／全新生成：`未執行`",
            "- 正式 runtime 修改：`0`",
            "",
            "v2 排除了 foreach reduction，但 backward 本身仍無法跨程序重現。下一步只能做零更新因素診斷，不能直接重訓。",
        ]
    ) + "\n"


def write_result():
    result = audit()
    if not all(result["checks"].values()):
        raise RuntimeError("v2 invalidation audit did not satisfy all evidence checks")
    construction.atomic_json(RESULT_JSON, result)
    construction.atomic_text(RESULT_MD, render_markdown(result))
    preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)
    result_lock_path = ROOT / preregistration["result_paths"]["result_lock"]
    lock = {
        "schema": "uruha_rightbrain_max_norm_training_pilot_result_lock_v2",
        "experiment_id": construction.EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(RESULT_JSON),
            construction.file_binding(RESULT_MD),
            construction.file_binding(
                ROOT / preregistration["result_paths"]["training_pair_integrity_json"]
            ),
            construction.file_binding(
                ROOT / preregistration["result_paths"]["evaluation_lock"]
            ),
            construction.file_binding(Path(__file__)),
            *[
                construction.file_binding(runner._training_report_path(preregistration, condition))
                for condition in construction.CONDITIONS
            ],
        ],
        "decision": result["decision"],
        "authorization": {
            "zero_update_factorial_reproducibility_probe": True,
            "additional_v2_training": False,
            "v2_holdout_evaluation": False,
            "production_runtime_change": False,
            "production_adapter_replacement": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(result_lock_path, lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = write_result() if args.write else audit()
    print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
