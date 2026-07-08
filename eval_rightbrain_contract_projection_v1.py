#!/usr/bin/env python3
"""Paired actual-model evaluation for the RightBrain public-plan projection."""

import argparse
import json
import os
import types
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_model_surface_holdout import _adapter_ref, _case_inputs, _set_model_env
from eval_rightbrain_sampling_schedule_v1 import DEFAULT_SEED, SCHEDULES, run_schedule
from project_paths import (
    RIGHTBRAIN_CONTRACT_PROJECTION_V1_AUDIT_JSON_PATH,
    RIGHTBRAIN_CONTRACT_PROJECTION_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_CONTRACT_PROJECTION_V1_REPORT_MD_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
TARGET_CASE_IDS = (
    "background_family_pressure",
    "private_do_not_mention",
    "no_memory_plain_question",
)


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _legacy_plan_projection(self, logic_data, memory_brief):
    speech_plan = logic_data.get("human_speech_plan") or {}
    plan = {
        "scene": str(logic_data.get("scene") or ""),
        "intent": str(logic_data.get("intent") or ""),
        "surface_act": str(logic_data.get("surface_act") or ""),
        "dialogue_act": str(speech_plan.get("dialogue_act") or logic_data.get("dialogue_act") or ""),
        "meaning": str(logic_data.get("core_message_jp") or ""),
        "content_units": list(speech_plan.get("content_units") or []),
        "style_operators": list(speech_plan.get("style_operators") or []),
        "grounding_terms": list(speech_plan.get("grounding_terms") or []),
    }
    return plan, {
        "policy": str(memory_brief.get("policy") or "no_memory"),
        "mode": "legacy_unprojected",
        "dropped_content_units": [],
        "dropped_grounding_terms": [],
    }


def _target_cases():
    by_id = {case["id"]: case for case in _case_inputs()}
    return [by_id[case_id] for case_id in TARGET_CASE_IDS]


def _fixed_dynamic_context_anchor(self, logic_data, memory_data, current_psyche, user_input):
    return {
        "text": "",
        "boost_tokens": [],
        "variants": [],
        "time_anchor": "",
        "body_anchor": "",
    }


def _excluded_memory_terms(case, projection):
    logic = case["logic"]
    anchor = logic.get("memory_anchor") or {}
    terms = [
        *(anchor.get("terms") or []),
        anchor.get("jp_anchor"),
        *(projection.get("dropped_grounding_terms") or []),
    ]
    output = []
    for term in terms:
        term = str(term or "").strip()
        if len(term) < 2 or not any("ぁ" <= char <= "龠" for char in term):
            continue
        if term not in output:
            output.append(term)
    return output


def _condition_contract_metrics(condition, cases):
    case_inputs = {case["id"]: case for case in cases}
    rows = []
    for row in condition["cases"]:
        case = case_inputs[row["id"]]
        projection = row.get("model_surface_plan_projection") or {}
        excluded_terms = _excluded_memory_terms(case, projection)
        intrusion_hits = [term for term in excluded_terms if term in row["final_reply"]]
        pass_contract = bool(row["final_quality_pass"] and not intrusion_hits)
        rows.append({
            "id": row["id"],
            "final_reply": row["final_reply"],
            "selected_source": row["selected_source"],
            "projection": projection,
            "excluded_memory_terms": excluded_terms,
            "intrusion_hits": intrusion_hits,
            "contract_pass": pass_contract,
        })
    return {
        "case_count": len(rows),
        "contract_pass_count": sum(row["contract_pass"] for row in rows),
        "contract_pass_rate": _safe_rate(sum(row["contract_pass"] for row in rows), len(rows)),
        "memory_intrusion_case_count": sum(bool(row["intrusion_hits"]) for row in rows),
        "cases": rows,
    }


def _contract_snapshots(rightbrain, cases):
    snapshots = []
    for case in cases:
        logic = deepcopy(case["logic"])
        max_chars = int((logic.get("constraints") or {}).get("max_chars") or 80)
        payload = json.loads(
            rightbrain._build_model_surface_payload(
                logic,
                deepcopy(case["psyche"]),
                max_chars,
                deepcopy(case["memory_data"]),
            )
        )
        snapshots.append({
            "id": case["id"],
            "policy": payload["context"]["audited_memory_brief"]["policy"],
            "projected_leftbrain_plan": payload["leftbrain_plan"],
            "projection": logic["model_surface_plan_projection"],
        })
    return snapshots


def _snapshot_respects_memory_policy(snapshot, case):
    plan = snapshot.get("projected_leftbrain_plan") or {}
    projection = snapshot.get("projection") or {}
    if projection.get("mode") == "semantic_contract_only":
        return True
    plan_text = " ".join(
        str(value or "")
        for value in [
            plan.get("scene"),
            plan.get("intent"),
            plan.get("surface_act"),
            plan.get("dialogue_act"),
            plan.get("meaning"),
            *(plan.get("content_units") or []),
            *(plan.get("grounding_terms") or []),
        ]
    )
    return not any(term and term in plan_text for term in _excluded_memory_terms(case, projection))


def apply_naturalness_audit(report, audit):
    expected_candidates = {
        (condition_name, row["id"], candidate["candidate"])
        for condition_name, condition in report["conditions"].items()
        for row in condition["cases"]
        for candidate in row["accepted_candidates"]
    }
    annotated_candidates = {
        (row["condition"], row["id"], row["reply"])
        for row in audit["candidate_annotations"]
    }
    if annotated_candidates != expected_candidates:
        raise ValueError("Naturalness candidate audit is stale or incomplete")

    expected_pairs = {
        row["id"]: row for row in report["contract_metrics"]["legacy_unprojected"]["cases"]
    }
    projected_pairs = {
        row["id"]: row for row in report["contract_metrics"]["projected_contract"]["cases"]
    }
    pair_ids = {row["id"] for row in audit["final_pair_annotations"]}
    if pair_ids != set(TARGET_CASE_IDS):
        raise ValueError("Naturalness final-pair audit does not cover every target case")
    for row in audit["final_pair_annotations"]:
        case_id = row["id"]
        if row["legacy_reply"] != expected_pairs[case_id]["final_reply"]:
            raise ValueError(f"Stale legacy final reply audit for {case_id}")
        if row["projected_reply"] != projected_pairs[case_id]["final_reply"]:
            raise ValueError(f"Stale projected final reply audit for {case_id}")

    candidate_metrics = {}
    for condition_name in ("legacy_unprojected", "projected_contract"):
        rows = [
            row for row in audit["candidate_annotations"]
            if row["condition"] == condition_name
        ]
        passed = sum(row["verdict"] == "pass" for row in rows)
        candidate_metrics[condition_name] = {
            "audited_candidate_count": len(rows),
            "pass_count": passed,
            "fail_count": len(rows) - passed,
            "pass_rate": _safe_rate(passed, len(rows)),
        }
    pairwise = {
        "projected_wins": sum(
            row["preference"] == "projected_contract"
            for row in audit["final_pair_annotations"]
        ),
        "legacy_wins": sum(
            row["preference"] == "legacy_unprojected"
            for row in audit["final_pair_annotations"]
        ),
        "ties": sum(row["preference"] == "tie" for row in audit["final_pair_annotations"]),
    }
    report["naturalness_audit"] = {
        "audit_type": audit["audit_type"],
        "candidate_metrics": candidate_metrics,
        "final_pairwise": pairwise,
        "candidate_annotations": audit["candidate_annotations"],
        "final_pair_annotations": audit["final_pair_annotations"],
        "boundary": audit["boundary"],
    }
    report["gate"].update({
        "naturalness_audit_matches_every_accepted_candidate": True,
        "projected_candidate_audit_pass_count_improves": (
            candidate_metrics["projected_contract"]["pass_count"]
            > candidate_metrics["legacy_unprojected"]["pass_count"]
        ),
        "projected_final_pairwise_has_no_losses": pairwise["legacy_wins"] == 0,
    })
    report["gate_passed"] = all(report["gate"].values())
    return report


def build_report(adapter_path, load_model=True, seed=DEFAULT_SEED):
    _set_model_env(adapter_path=adapter_path, candidate_count=3, repair_enabled=False)
    import torch
    import uruha_brain_mac as runtime_module

    cases = _target_cases()
    static_rightbrain = runtime_module.RightBrain(load_model=False)
    snapshots = _contract_snapshots(static_rightbrain, cases)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_contract_projection_v1",
        "base_model": os.getenv("URUHA_RIGHT_BRAIN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        "adapter_ref": _adapter_ref(adapter_path),
        "seed": seed,
        "schedule": deepcopy(SCHEDULES["conservative"]),
        "candidate_count_per_case": 3,
        "dynamic_context_anchor": "fixed_empty_for_paired_ablation",
        "session_state_reset_per_case": True,
        "target_case_ids": list(TARGET_CASE_IDS),
        "contract_snapshots": snapshots,
        "load_model": bool(load_model),
        "conditions": {},
    }
    if not load_model:
        report["research_boundary"] = "Static contract projection only; no model outputs were generated."
        return report

    deterministic_right = runtime_module.RightBrain(load_model=False)
    deterministic_right.model_blend_enabled = False
    model_right = runtime_module.RightBrain(load_model=True)
    model_right.model_blend_enabled = True
    model_right.model_candidate_count = 3
    model_right.model_repair_enabled = False
    deterministic_right._build_dynamic_context_anchor = types.MethodType(
        _fixed_dynamic_context_anchor,
        deterministic_right,
    )
    model_right._build_dynamic_context_anchor = types.MethodType(
        _fixed_dynamic_context_anchor,
        model_right,
    )
    projected_method = model_right._project_model_surface_plan
    model_right._project_model_surface_plan = types.MethodType(_legacy_plan_projection, model_right)
    try:
        legacy = run_schedule(
            runtime_module,
            torch,
            model_right,
            deterministic_right,
            cases,
            "legacy_unprojected",
            SCHEDULES["conservative"],
            seed,
        )
    finally:
        model_right._project_model_surface_plan = projected_method
    projected = run_schedule(
        runtime_module,
        torch,
        model_right,
        deterministic_right,
        cases,
        "projected_contract",
        SCHEDULES["conservative"],
        seed,
    )
    conditions = {"legacy_unprojected": legacy, "projected_contract": projected}
    report["conditions"] = conditions
    legacy_metrics = _condition_contract_metrics(legacy, cases)
    projected_metrics = _condition_contract_metrics(projected, cases)
    report["contract_metrics"] = {
        "legacy_unprojected": legacy_metrics,
        "projected_contract": projected_metrics,
    }
    report["comparison"] = {
        "contract_pass_count_delta": (
            projected_metrics["contract_pass_count"] - legacy_metrics["contract_pass_count"]
        ),
        "memory_intrusion_case_count_delta": (
            projected_metrics["memory_intrusion_case_count"]
            - legacy_metrics["memory_intrusion_case_count"]
        ),
        "accepted_candidate_count_delta": (
            projected["summary"]["accepted_candidate_count"]
            - legacy["summary"]["accepted_candidate_count"]
        ),
    }
    cases_by_id = {case["id"]: case for case in cases}
    report["gate"] = {
        "target_contracts_respect_memory_policy": all(
            _snapshot_respects_memory_policy(row, cases_by_id[row["id"]])
            for row in snapshots
        ),
        "projected_contract_does_not_reduce_contract_pass_count": (
            projected_metrics["contract_pass_count"] >= legacy_metrics["contract_pass_count"]
        ),
        "projected_contract_has_no_memory_intrusion": (
            projected_metrics["memory_intrusion_case_count"] == 0
        ),
    }
    report["gate_passed"] = all(report["gate"].values())
    audit_path = Path(RIGHTBRAIN_CONTRACT_PROJECTION_V1_AUDIT_JSON_PATH)
    if audit_path.exists():
        try:
            report = apply_naturalness_audit(
                report,
                json.loads(audit_path.read_text(encoding="utf-8")),
            )
        except ValueError as exc:
            report["naturalness_audit_status"] = "stale"
            report["naturalness_audit_error"] = str(exc)
            report["gate"]["naturalness_audit_current"] = False
            report["gate_passed"] = False
    report["research_boundary"] = (
        "This is a paired development-set ablation on three known conflicting contracts. The same model, adapter, "
        "cases, seed, candidate count, and conservative sampling schedule are held constant. It supports the "
        "contract-projection mechanism, not a broad claim of Japanese naturalness or benchmark improvement."
    )
    return report


def write_markdown(report, path):
    lines = [
        "# RightBrain Contract Projection v1",
        "",
        "## 目的",
        "",
        "左腦內部計畫含有未授權或與公開核心意思衝突的欄位時，先投影成可對使用者說出的契約，再交給右腦。",
        "",
        "## 控制變因",
        "",
        "- 同一個 Qwen2.5-7B、同一個 v10 adapter、同一 seed、同一組三題、每題三候選。",
        "- 唯一操作變因：舊版完整計畫直接輸入，或新版公開契約投影。",
        "",
        "## 契約投影",
        "",
        "| case | memory policy | mode | dropped units | dropped grounding |",
        "|---|---|---|---:|---:|",
    ]
    for row in report["contract_snapshots"]:
        projection = row["projection"]
        lines.append(
            f"| {row['id']} | {row['policy']} | {projection['mode']} | "
            f"{len(projection['dropped_content_units'])} | {len(projection['dropped_grounding_terms'])} |"
        )
    if report.get("contract_metrics"):
        lines.extend([
            "",
            "## 實際模型結果",
            "",
            "| condition | final contract pass | final memory intrusion | gate-accepted candidates |",
            "|---|---:|---:|---:|",
        ])
        for name in ("legacy_unprojected", "projected_contract"):
            metrics = report["contract_metrics"][name]
            summary = report["conditions"][name]["summary"]
            lines.append(
                f"| {name} | {metrics['contract_pass_count']}/{metrics['case_count']} "
                f"({_fmt_pct(metrics['contract_pass_rate'])}) | {metrics['memory_intrusion_case_count']} | "
                f"{summary['accepted_candidate_count']}/{summary['generated_candidate_count']} |"
            )
        if report.get("naturalness_audit"):
            audit = report["naturalness_audit"]
            lines.extend([
                "",
                "## 非盲自然度審核",
                "",
                "| condition | audit pass | audit fail |",
                "|---|---:|---:|",
            ])
            for name in ("legacy_unprojected", "projected_contract"):
                metrics = audit["candidate_metrics"][name]
                lines.append(
                    f"| {name} | {metrics['pass_count']} | {metrics['fail_count']} |"
                )
            pairwise = audit["final_pairwise"]
            lines.extend([
                "",
                f"最終回答配對：projected win {pairwise['projected_wins']}、"
                f"legacy win {pairwise['legacy_wins']}、tie {pairwise['ties']}。",
                "",
                "自動 final contract 指標只檢查最後送出的回答；候選本身是否自然，以本節逐句 audit 為準。",
            ])
        lines.extend(["", "### 回答對照", ""])
        legacy_rows = {row["id"]: row for row in report["contract_metrics"]["legacy_unprojected"]["cases"]}
        projected_rows = {row["id"]: row for row in report["contract_metrics"]["projected_contract"]["cases"]}
        for case_id in TARGET_CASE_IDS:
            lines.extend([
                f"- `{case_id}`",
                f"  - before: {legacy_rows[case_id]['final_reply']}",
                f"  - after: {projected_rows[case_id]['final_reply']}",
            ])
        lines.extend(["", "## Gate", ""])
        for name, passed in report["gate"].items():
            lines.append(f"- {name}: {'PASS' if passed else 'FAIL'}")
    lines.extend([
        "",
        "## 證據邊界",
        "",
        "這是三個已知矛盾契約的配對開發測試，不代表整體日文自然度或 ToMBench 分數已提升。",
        "",
    ])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--adapter-path",
        default="/Users/jerrychang/Desktop/uruharemake2/uruha_v10_all_linear_lora",
    )
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output-json", default=RIGHTBRAIN_CONTRACT_PROJECTION_V1_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_CONTRACT_PROJECTION_V1_REPORT_MD_PATH)
    args = parser.parse_args()
    report = build_report(args.adapter_path, load_model=not args.no_model, seed=args.seed)
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps({
        "gate_passed": report.get("gate_passed"),
        "comparison": report.get("comparison"),
    }, ensure_ascii=False, indent=2))
    return 0 if not report.get("gate") or report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
