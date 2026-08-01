#!/usr/bin/env python3
"""Recover the formal v2 decision without rerunning model computation."""

from __future__ import annotations

import json
from pathlib import Path

import build_rightbrain_role_curriculum_training_pilot_v1 as construction


ROOT = Path(__file__).resolve().parent
AMENDMENT = (
    ROOT / "configs/rightbrain_adamw_clipping_effect_v2_protocol_amendment_01.json"
)
RAW_RESULT = ROOT / "reports/rightbrain_adamw_clipping_effect_v2_result.json"
FORMAL_RESULT = ROOT / "reports/rightbrain_adamw_clipping_effect_v2_formal_result.json"
FORMAL_MARKDOWN = ROOT / "reports/rightbrain_adamw_clipping_effect_v2_formal_result.md"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_bindings(bindings):
    rows = []
    for binding in bindings:
        path = ROOT / binding["path"]
        actual = construction.sha256_file(path) if path.is_file() else None
        rows.append(
            {
                "path": binding["path"],
                "expected_sha256": binding["sha256"],
                "actual_sha256": actual,
                "match": actual == binding["sha256"],
            }
        )
    return rows


def recover():
    if FORMAL_RESULT.exists() or FORMAL_MARKDOWN.exists():
        raise RuntimeError("Formal v2 recovery result already exists")
    amendment = load_json(AMENDMENT)
    raw = load_json(RAW_RESULT)
    bindings = validate_bindings(amendment["preserved_raw_bindings"])
    checks = {
        "bindings": all(row["match"] for row in bindings),
        "raw_valid": raw["decision"]["valid"],
        "raw_material_effect": raw["decision"]["material_effect"],
        "raw_outcome": raw["decision"]["outcome"]
        == "first_step_clipping_has_material_effect",
        "raw_boolean_exposes_mismatch": not raw["decision"]["hypothesis_confirmed"],
        "raw_weights_unchanged": raw["parameter_integrity"]["unchanged"],
        "zero_optimizer_steps": raw["probe"]["optimizer_steps"] == 0,
    }
    if not all(checks.values()):
        raise RuntimeError("Formal v2 recovery preconditions failed")
    formal = {
        "schema": "uruha_rightbrain_adamw_clipping_effect_formal_result_v2",
        "experiment_id": raw["experiment_id"],
        "recovery_amendment": str(AMENDMENT.relative_to(ROOT)),
        "raw_result": str(RAW_RESULT.relative_to(ROOT)),
        "validation": {
            "passed": True,
            "checks": checks,
            "bindings": bindings,
        },
        "preserved_metrics": {
            "gradient": raw["gradient"],
            "clip_coefficient": raw["simulation"]["clip_coefficient"],
            "overall": raw["simulation"]["overall"],
            "parameter_integrity": raw["parameter_integrity"],
        },
        "raw_decision": raw["decision"],
        "formal_decision": {
            "valid": True,
            "outcome": raw["decision"]["outcome"],
            "hypothesis_confirmed": raw["decision"]["material_effect"],
            "material_effect": raw["decision"]["material_effect"],
            "maximum_positive_authorization": amendment["formal_interpretation"][
                "maximum_positive_outcome"
            ],
            "authorize_model_training": False,
            "authorize_training_parameter_change": False,
            "authorize_production": False,
            "authorize_persona_similarity_claim": False,
        },
        "boundaries": raw["boundaries"],
    }
    metrics = formal["preserved_metrics"]["overall"]
    markdown = "\n".join(
        [
            "# RightBrain AdamW 首步裁切效果 v2：正式判定",
            "",
            "- 原始數值與門檻：完全保留",
            "- 修正項目：v2 hypothesis_confirmed 的語意映射",
            f"- 正式判定：`{formal['formal_decision']['outcome']}`",
            "- 假設成立：`true`",
            f"- 相對更新差：`{metrics['relative_l2_difference']:.10f}`",
            f"- 更新 L2 比率：`{metrics['clipped_to_unclipped_l2_ratio']:.10f}`",
            f"- 更新方向 cosine：`{metrics['cosine_similarity']:.10f}`",
            "- 新 backward／optimizer／模型修改：`0／0／0`",
            "",
            "本修正只校正布林欄位語意，不改任何實驗數值或門檻。",
        ]
    ) + "\n"
    construction.atomic_json(FORMAL_RESULT, formal)
    construction.atomic_text(FORMAL_MARKDOWN, markdown)
    return formal


if __name__ == "__main__":
    print(json.dumps(recover()["formal_decision"], ensure_ascii=False, indent=2))
