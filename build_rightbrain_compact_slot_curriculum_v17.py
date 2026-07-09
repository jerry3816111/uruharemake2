#!/usr/bin/env python3
"""Build v17 compact RightBrain rows for semantic slot preservation.

v16 proved that adding a long surface_failure_watchlist to the model payload is
not a safe promotion path: final quality stayed protected by fallback logic, but
model candidates still regressed on semantic slot coverage. v17 keeps the same
holdout-separated positive targets, but trains with the compact runtime payload
schema used when the watchlist flag is off.
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_candidate_gate_contrast_curriculum_v16 import FAMILY_SPECS
from build_rightbrain_candidate_gate_curriculum_v15 import (
    _default_memory_brief,
    _holdout_boundary,
    _load_reports,
    _target_validation_errors,
)
from project_paths import (
    RIGHTBRAIN_COMPACT_SLOT_CURRICULUM_V17_DATASET_PATH,
    RIGHTBRAIN_COMPACT_SLOT_CURRICULUM_V17_REPORT_JSON_PATH,
    RIGHTBRAIN_COMPACT_SLOT_CURRICULUM_V17_REPORT_MD_PATH,
)
from rightbrain_language_quality import POLITE_RE
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RIGHT_BRAIN_MODEL_SYSTEM_PROMPT


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_SOURCE_REPORTS = [
    "reports/rightbrain_v16_contrast_watchlist_holdout_c3.json",
    "reports/rightbrain_v16_contrast_watchlist_holdout_c3_seed20260709.json",
]
DEFAULT_COMPARE_REPORT = "reports/rightbrain_v16_contrast_watchlist_compare_report.json"


def _persona_expression_brief(mood=0, trust=58):
    return {
        "role": "surface_style_only",
        "state": "neutral_energy" if mood >= -20 else "low_energy",
        "relationship_distance": "moderate" if trust < 72 else "familiar",
        "stable_traits": ["lazy_short", "slightly_bratty", "not_customer_service"],
        "must_not_override": ["leftbrain_plan", "required_marker_groups", "audited_memory_policy"],
    }


def _payload(spec):
    """Mirror RightBrain._build_model_surface_payload with the watchlist disabled."""
    return {
        "contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "task": "write_one_user_facing_japanese_reply",
        "contract_rule": (
            "required_marker_groups is the semantic contract. Include at least one phrase from "
            "every inner list naturally and avoid every forbidden marker."
        ),
        "user_input": spec["meaning"],
        "leftbrain_plan": {
            "scene": spec["scene"],
            "intent": spec["intent"],
            "surface_act": spec["surface_act"],
            "dialogue_act": spec.get("dialogue_act", spec["intent"]),
            "meaning": spec["meaning"],
            "content_units": list(spec["content_units"]),
            "style_operators": ["casual", "short", "no_polite_register"],
            "grounding_terms": list(spec["grounding_terms"]),
        },
        "context": {
            "memory_summary": "左脳が選択した作業記憶は発話計画に統合済み。",
            "audited_memory_brief": spec.get("audited_memory_brief") or _default_memory_brief(),
            "persona_expression_brief": _persona_expression_brief(
                mood=-5 if spec["category"].startswith("support") else 0,
                trust=58,
            ),
            "mood": -5 if spec["category"].startswith("support") else 0,
            "trust": 58,
            "max_chars": int(spec["max_chars"]),
        },
        "required_marker_groups": list(spec["required_marker_groups"]),
        "forbidden_markers": list(spec.get("forbidden_markers") or []),
        "reply_requirements": [
            "one sentence or short chat reply",
            "natural casual Japanese",
            "no labels or JSON",
            "no Chinese or English",
            "no first person 私",
        ],
    }


def _target_errors(reply, payload):
    errors = list(_target_validation_errors(reply, payload))
    if POLITE_RE.search(str(reply or "")):
        errors.append("polite_tone_drift")
    return list(dict.fromkeys(errors))


def _source_failure_family_counts(compare_report_path=DEFAULT_COMPARE_REPORT):
    path = Path(compare_report_path)
    if not path.exists():
        return {}
    report = json.loads(path.read_text(encoding="utf-8"))
    return {
        row["reason"]: int(row.get("candidate_count") or 0)
        for row in report.get("rejection_reason_deltas", {}).get("family", [])
    }


def _diagnostic_family_counts(reports):
    counts = Counter()
    for report in reports:
        for case in report.get("cases") or []:
            for reason in case.get("model_rejection_reasons") or []:
                counts[str(reason).split(":", 1)[0]] += 1
    return counts


def build_curriculum(specs=None, source_reports=None, compare_report_path=DEFAULT_COMPARE_REPORT):
    specs = list(specs or FAMILY_SPECS)
    source_reports = list(source_reports or _load_reports(DEFAULT_SOURCE_REPORTS))
    diagnostic_counts = _diagnostic_family_counts(source_reports)
    compare_family_counts = _source_failure_family_counts(compare_report_path)
    rows = []
    skipped = Counter()
    family_counts = Counter()
    category_counts = Counter()
    seen = set()

    for spec in specs:
        payload = _payload(spec)
        for target_index, target in enumerate(spec["targets"], start=1):
            errors = _target_errors(target, payload)
            if errors:
                skipped[f"target_validation_failed:{spec['id']}:{','.join(errors)}"] += 1
                continue
            row_key = json.dumps([spec["id"], payload, target], ensure_ascii=False, sort_keys=True)
            if row_key in seen:
                skipped["duplicate_target"] += 1
                continue
            seen.add(row_key)
            source_case_id = spec["id"].replace("v16_", "v17_", 1)
            rows.append(
                {
                    "id": f"rb_compact_slot_v17_{len(rows) + 1:04d}",
                    "source_case_id": source_case_id,
                    "category": spec["category"],
                    "training_role": "rightbrain_compact_slot_preservation_v17_sft",
                    "failure_families": ["semantic_slots_missing", *list(spec["failure_families"])],
                    "target_variant_index": target_index,
                    "contrast_focus": {
                        "positive_rule": "cover every required_marker_group with compact runtime payload only",
                        "removed_v16_feature": "surface_failure_watchlist",
                    },
                    "messages": [
                        {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
                        {"role": "assistant", "content": target},
                    ],
                }
            )
            category_counts[spec["category"]] += 1
            family_counts.update(rows[-1]["failure_families"])

    boundary = _holdout_boundary(rows, source_reports)
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_compact_slot_curriculum_v17",
        "source_diagnostic_reports": [Path(report["_source_path"]).name for report in source_reports],
        "source_compare_report": Path(compare_report_path).name,
        "design": (
            "v17 reuses the v16 holdout-separated positive targets but removes the long "
            "surface_failure_watchlist. It tests whether compact runtime-compatible SFT "
            "improves required_marker_groups preservation without adding prompt-only rules."
        ),
        "curriculum_row_count": len(rows),
        "family_spec_count": len(specs),
        "category_counts": dict(category_counts),
        "failure_family_counts": dict(family_counts),
        "source_diagnostic_family_counts": dict(diagnostic_counts),
        "source_compare_family_counts": compare_family_counts,
        "skipped_counts": dict(skipped),
        "runtime_payload_boundary": {
            "surface_failure_watchlist_present": False,
            "matches_default_watchlist_flag_off": True,
        },
        "data_boundary": boundary,
        "promotion_boundary": (
            "這是 compact runtime payload 的補充訓練資料，不是升版證據。任何用它訓練出的 adapter "
            "仍必須通過 matched-seed model-loaded holdout，才能成為預設 RightBrain adapter。"
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain Compact Slot Curriculum v17",
        "",
        "## 一句話結論",
        "",
        "v17 移除 v16 的長 watchlist，改用目前 runtime 預設會看到的短契約，專注訓練右腦不要漏掉 required_marker_groups。",
        "",
        "## 總表",
        "",
        "| 指標 | 值 |",
        "|---|---:|",
        f"| curriculum rows | {summary['curriculum_row_count']} |",
        f"| family specs | {summary['family_spec_count']} |",
        f"| surface_failure_watchlist present | {summary['runtime_payload_boundary']['surface_failure_watchlist_present']} |",
        f"| holdout case overlap | {summary['data_boundary']['holdout_case_overlap_count']} |",
        f"| holdout target overlap | {summary['data_boundary']['holdout_target_overlap_count']} |",
        f"| diagnostic only | {summary['data_boundary']['diagnostic_only']} |",
        "",
        "## v16 失敗族群與 v17 覆蓋",
        "",
        "| failure family | v16 candidate count | v17 rows covering family |",
        "|---|---:|---:|",
    ]
    families = sorted(
        set(summary["source_compare_family_counts"]) | set(summary["failure_family_counts"]),
        key=lambda family: (-summary["source_compare_family_counts"].get(family, 0), family),
    )
    for family in families:
        lines.append(
            f"| {family} | {summary['source_compare_family_counts'].get(family, 0)} | "
            f"{summary['failure_family_counts'].get(family, 0)} |"
        )
    lines.extend(
        [
            "",
            "## 訓練樣本",
            "",
            "| source case | category | target reply |",
            "|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(f"| {row['source_case_id']} | {row['category']} | {row['messages'][-1]['content']} |")
    lines.extend(["", "## 邊界", "", f"- {summary['promotion_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=RIGHTBRAIN_COMPACT_SLOT_CURRICULUM_V17_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_COMPACT_SLOT_CURRICULUM_V17_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_COMPACT_SLOT_CURRICULUM_V17_REPORT_MD_PATH)
    args = parser.parse_args()

    rows, summary = build_curriculum()
    if not rows:
        raise RuntimeError("No v17 compact slot rows were generated.")
    if summary["data_boundary"]["diagnostic_only"]:
        raise RuntimeError("Generated v17 curriculum overlaps source holdout; refusing to write dataset.")
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, rows, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
