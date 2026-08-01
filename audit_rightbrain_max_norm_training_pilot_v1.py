#!/usr/bin/env python3
"""Audit and formally invalidate the confounded max-norm pilot v1."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import build_rightbrain_max_norm_training_pilot_v1 as construction
import run_rightbrain_max_norm_training_pilot_v1 as runner


ROOT = Path(__file__).resolve().parent
AMENDMENT = ROOT / "configs/rightbrain_max_norm_training_pilot_v1_protocol_amendment_01.json"
RESULT_JSON = ROOT / "reports/rightbrain_max_norm_training_pilot_v1_invalid_result.json"
RESULT_MD = ROOT / "reports/rightbrain_max_norm_training_pilot_v1_invalid_result.md"
RESULT_LOCK = ROOT / "configs/rightbrain_max_norm_training_pilot_v1_result_lock.json"


def relative_error(left, right):
    return abs(float(left) - float(right)) / max(abs(float(left)), abs(float(right)), 1e-300)


def audit():
    preregistration = construction.load_json(construction.DEFAULT_PREREGISTRATION)
    amendment = construction.load_json(AMENDMENT)
    lock_validation = runner.validate_execution_lock()
    reports = {
        condition: construction.load_json(runner._training_report_path(preregistration, condition))
        for condition in construction.CONDITIONS
    }
    control = reports["control_0_3"]
    treatment = reports["treatment_3_0"]
    first_losses_match = control["micro_step_losses"][:8] == treatment["micro_step_losses"][:8]
    control_norm = control["updates"][0]["preclip_gradient_norm"]
    treatment_norm = treatment["updates"][0]["preclip_gradient_norm"]
    norm_error = relative_error(control_norm, treatment_norm)
    tolerance = amendment["omitted_integrity_invariant"]["required_relative_error_maximum"]
    integrity = {
        "execution_lock_valid": lock_validation["passed"],
        "both_runs_complete": all(
            row["micro_steps"] == 80 and row["optimizer_updates"] == 10
            for row in reports.values()
        ),
        "zero_nonfinite_events": all(row["nonfinite_events"] == 0 for row in reports.values()),
        "first_eight_losses_identical": first_losses_match,
        "first_preclip_norm_reproducible": norm_error <= tolerance,
        "no_holdout_evaluation_outputs": all(
            not runner._evaluation_report_path(preregistration, condition).exists()
            for condition in construction.CONDITIONS
        ),
    }
    valid_causal_comparison = all(integrity.values())
    return {
        "schema": "uruha_rightbrain_max_norm_training_pilot_invalid_result_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "inputs": {
            "preregistration": construction.file_binding(construction.DEFAULT_PREREGISTRATION),
            "execution_lock": construction.file_binding(construction.DEFAULT_EXECUTION_LOCK),
            "protocol_amendment": construction.file_binding(AMENDMENT),
            "training_reports": {
                condition: construction.file_binding(
                    runner._training_report_path(preregistration, condition)
                )
                for condition in construction.CONDITIONS
            },
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
            for condition, row in reports.items()
        },
        "causal_integrity": {
            "checks": integrity,
            "first_eight_micro_step_losses": control["micro_step_losses"][:8],
            "control_first_preclip_gradient_norm": control_norm,
            "treatment_first_preclip_gradient_norm": treatment_norm,
            "treatment_to_control_norm_ratio": treatment_norm / max(control_norm, 1e-300),
            "preclip_norm_relative_error": norm_error,
            "required_relative_error_maximum": tolerance,
        },
        "decision": {
            "valid_causal_comparison": valid_causal_comparison,
            "outcome": (
                "pilot_valid"
                if valid_causal_comparison
                else "invalidate_v1_due_nonreproducible_preclip_norm"
            ),
            "holdout_evaluation_executed": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
            "authorized_next_step": (
                "none"
                if valid_causal_comparison
                else "preregister_v2_with_foreach_false_norm_and_clipping"
            ),
        },
        "boundaries": preregistration["boundaries"],
    }


def render_markdown(result):
    causal = result["causal_integrity"]
    decision = result["decision"]
    return "\n".join(
        [
            "# RightBrain max_norm 公平訓練試驗 v1 無效結果",
            "",
            f"- 判定：`{decision['outcome']}`",
            "- 前 8 個 loss：兩組完全相同",
            f"- control 第一個 preclip norm：`{causal['control_first_preclip_gradient_norm']:.6f}`",
            f"- treatment 第一個 preclip norm：`{causal['treatment_first_preclip_gradient_norm']:.6f}`",
            f"- norm 比率：`{causal['treatment_to_control_norm_ratio']:.3f}x`",
            f"- 相對誤差：`{causal['preclip_norm_relative_error']:.6%}`",
            "- holdout／全新生成：`未執行`",
            "- 正式 runtime 修改：`0`",
            "",
            "兩組在第一次裁切前的計算完全相同，raw norm 卻不一致，因此單一變因不成立。v1 不能回答 0.3 或 3.0 哪個較好。",
            "",
            "下一個允許步驟是使用已由 MPS、CPU float64 與逐參數合成共同驗證的 `foreach=False` 路徑重跑。",
        ]
    ) + "\n"


def write_result():
    result = audit()
    if result["decision"]["valid_causal_comparison"]:
        raise RuntimeError("Audit did not reproduce the invalidating condition")
    construction.atomic_json(RESULT_JSON, result)
    construction.atomic_text(RESULT_MD, render_markdown(result))
    lock = {
        "schema": "uruha_rightbrain_max_norm_training_pilot_result_lock_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "result_bindings": [
            construction.file_binding(RESULT_JSON),
            construction.file_binding(RESULT_MD),
            construction.file_binding(AMENDMENT),
            construction.file_binding(Path(__file__)),
            *[
                construction.file_binding(
                    runner._training_report_path(
                        construction.load_json(construction.DEFAULT_PREREGISTRATION), condition
                    )
                )
                for condition in construction.CONDITIONS
            ],
        ],
        "decision": result["decision"],
        "authorization": {
            "preregister_v2_with_foreach_false_norm_and_clipping": True,
            "additional_v1_training": False,
            "v1_holdout_evaluation": False,
            "production_runtime_change": False,
            "production_adapter_replacement": False,
            "persona_similarity_claim": False,
        },
    }
    construction.atomic_json(RESULT_LOCK, lock)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = write_result() if args.write else audit()
    print(json.dumps(result["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
