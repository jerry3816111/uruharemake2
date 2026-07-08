#!/usr/bin/env python3
"""Generate real v10 RightBrain candidates and inspect learned shadow choices."""

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_model_surface_holdout import (
    _adapter_ref,
    _case_inputs,
    _evaluate_surface_quality,
    _quality_pass,
    _set_model_env,
)
from project_paths import (
    RIGHTBRAIN_SELECTOR_ACTUAL_MODEL_SOAK_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_SELECTOR_ACTUAL_MODEL_SOAK_V1_REPORT_MD_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_SEED = 20260707
DEFAULT_CANDIDATE_COUNT = 3


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _alignment_label(alignment):
    alignment = alignment or {}
    return "/".join(
        f"{float(alignment.get(key) or 0.0):.2f}"
        for key in (
            "grounding_term_hit_rate",
            "semantic_reference_bigram_dice",
            "user_input_unigram_dice",
        )
    )


def _file_sha256(path):
    path = Path(path)
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_cases(cases, model_loaded):
    active = [case for case in cases if case["shadow_status"] == "active"]
    multi = [case for case in active if case["shadow_candidate_count"] > 1]
    disagreements = [case for case in active if case["shadow_would_change"]]
    generated = sum(case["generated_candidate_count"] for case in cases)
    accepted = sum(case["accepted_candidate_count"] for case in cases)
    rejected = sum(case["initial_rejected_candidate_count"] for case in cases)
    learned_valid = sum(case["learned_selected_strict_valid"] for case in active)
    learned_surface_pass = sum(case["learned_surface_contract_pass"] for case in active)
    current_surface_pass = sum(case["current_surface_contract_pass"] for case in cases)
    learned_rejected = sum(case["learned_selected_was_gate_rejected"] for case in active)
    visible_unchanged = sum(case["shadow_visible_output_unchanged"] for case in cases)
    learned_surface_gain = sum(
        case["learned_surface_contract_pass"] and not case["current_surface_contract_pass"] for case in active
    )
    learned_surface_loss = sum(
        case["current_surface_contract_pass"] and not case["learned_surface_contract_pass"] for case in active
    )
    accepted_raw = [
        str(candidate.get("raw_candidate") or candidate.get("candidate") or "")
        for case in cases
        for candidate in case["model_accepted_candidates"]
    ]
    rejected_raw = [
        str(candidate.get("raw_candidate") or candidate.get("candidate") or "")
        for case in cases
        for candidate in case["model_initial_rejected_candidates"]
    ]
    all_raw = accepted_raw + rejected_raw
    return {
        "case_count": len(cases),
        "model_loaded": bool(model_loaded),
        "generated_candidate_count": generated,
        "accepted_candidate_count": accepted,
        "initial_rejected_candidate_count": rejected,
        "raw_candidate_acceptance_rate": _safe_rate(accepted, generated),
        "shadow_active_case_count": len(active),
        "shadow_active_rate": _safe_rate(len(active), len(cases)),
        "shadow_multi_candidate_case_count": len(multi),
        "shadow_multi_candidate_rate": _safe_rate(len(multi), len(active)),
        "shadow_disagreement_count": len(disagreements),
        "shadow_disagreement_rate": _safe_rate(len(disagreements), len(active)),
        "current_surface_contract_pass_count": current_surface_pass,
        "current_surface_contract_pass_rate": _safe_rate(current_surface_pass, len(cases)),
        "learned_strict_valid_count": learned_valid,
        "learned_strict_valid_rate": _safe_rate(learned_valid, len(active)),
        "learned_surface_contract_pass_count": learned_surface_pass,
        "learned_surface_contract_pass_rate": _safe_rate(learned_surface_pass, len(active)),
        "learned_gate_rejected_selection_count": learned_rejected,
        "learned_gate_rejected_selection_rate": _safe_rate(learned_rejected, len(active)),
        "learned_surface_contract_gain_count": learned_surface_gain,
        "learned_surface_contract_loss_count": learned_surface_loss,
        "simplified_wu_generated_count": sum("无" in text for text in all_raw),
        "simplified_wu_accepted_count": sum("无" in text for text in accepted_raw),
        "unicode_replacement_generated_count": sum("\ufffd" in text for text in all_raw),
        "unicode_replacement_accepted_count": sum("\ufffd" in text for text in accepted_raw),
        "shadow_visible_output_unchanged_count": visible_unchanged,
        "shadow_visible_output_unchanged_rate": _safe_rate(visible_unchanged, len(cases)),
        "disabled_reason_counts": dict(
            sorted(Counter(case["model_disabled_reason"] for case in cases if case["model_disabled_reason"]).items())
        ),
        "learned_selected_source_counts": dict(
            sorted(Counter(case["learned_selected_source"] for case in active).items())
        ),
        "rejection_reason_counts": dict(
            sorted(Counter(reason for case in cases for reason in case["model_rejection_reasons"]).items())
        ),
    }


def _build_gate(summary):
    return {
        "model_loaded": summary["model_loaded"],
        "generated_at_least_20_real_candidates": summary["generated_candidate_count"] >= 20,
        "shadow_active_on_at_least_10_cases": summary["shadow_active_case_count"] >= 10,
        "contains_real_rejected_candidates": summary["initial_rejected_candidate_count"] > 0,
        "learned_strict_valid_rate_is_100pct": summary["learned_strict_valid_rate"] == 1.0,
        "learned_surface_contract_pass_rate_is_100pct": summary["learned_surface_contract_pass_rate"] == 1.0,
        "learned_never_selects_gate_rejected_candidate": summary["learned_gate_rejected_selection_count"] == 0,
        "shadow_never_changes_visible_output": summary["shadow_visible_output_unchanged_rate"] == 1.0,
        "actual_simplified_wu_candidate_was_generated": summary["simplified_wu_generated_count"] > 0,
        "actual_simplified_wu_candidate_was_never_accepted": summary["simplified_wu_accepted_count"] == 0,
        "actual_unicode_replacement_candidate_was_generated": summary["unicode_replacement_generated_count"] > 0,
        "actual_unicode_replacement_candidate_was_never_accepted": summary["unicode_replacement_accepted_count"] == 0,
    }


def recompute_existing_report(report):
    source_cases = {case["id"]: case for case in _case_inputs()}
    rows = []
    for original in report.get("cases") or []:
        row = dict(original)
        case = source_cases[row["id"]]
        current_surface = _evaluate_surface_quality(row["current_reply"], case)
        learned_surface = _evaluate_surface_quality(row["learned_reply"], case)
        row.pop("current_quality", None)
        row.pop("current_quality_pass", None)
        row.pop("learned_quality", None)
        row.pop("learned_quality_pass", None)
        row["current_surface_contract"] = current_surface
        row["current_surface_contract_pass"] = _quality_pass(current_surface)
        row["learned_surface_contract"] = learned_surface
        row["learned_surface_contract_pass"] = (
            _quality_pass(learned_surface) if row.get("shadow_status") == "active" else False
        )
        rows.append(row)
    summary = summarize_cases(rows, model_loaded=bool((report.get("summary") or {}).get("model_loaded")))
    gate = _build_gate(summary)
    output = dict(report)
    output.update(
        {
            "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "summary": summary,
            "gate": gate,
            "gate_passed": all(gate.values()),
            "cases": rows,
            "score_recomputed_from_existing_actual_candidates": True,
            "research_boundary": (
                "This report re-scores the same 30 candidates generated by the recorded 11-case actual-model run. "
                "No candidate text is regenerated or replaced. Surface-contract checks do not prove semantic relevance or naturalness."
            ),
        }
    )
    return output


def build_report(
    adapter_path,
    candidate_count=DEFAULT_CANDIDATE_COUNT,
    seed=DEFAULT_SEED,
    load_model=True,
):
    if load_model:
        _set_model_env(
            adapter_path=adapter_path,
            candidate_count=candidate_count,
            repair_enabled=False,
        )
        import torch

        torch.manual_seed(seed)
        if torch.backends.mps.is_available():
            torch.mps.manual_seed(seed)

    from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RightBrain

    started_at = time.time()
    deterministic_right = RightBrain(load_model=False)
    deterministic_right.model_blend_enabled = False
    model_right = RightBrain(load_model=load_model)
    model_right.model_blend_enabled = bool(load_model)
    model_right.model_candidate_count = max(1, int(candidate_count))
    model_right.model_repair_enabled = False
    model_ready_at = time.time()

    rows = []
    for case in _case_inputs():
        deterministic_right.history = []
        model_right.history = []
        deterministic_logic = deepcopy(case["logic"])
        model_logic = deepcopy(case["logic"])
        deterministic_reply = deterministic_right.speak(
            case["user_input"],
            deterministic_logic,
            deepcopy(case["memory_data"]),
            deepcopy(case["psyche"]),
        )
        final_reply = model_right.speak(
            case["user_input"],
            model_logic,
            deepcopy(case["memory_data"]),
            deepcopy(case["psyche"]),
        )
        trace = model_logic.get("model_surface_candidate_trace") or {}
        selection = model_logic.get("model_surface_selection") or {}
        shadow = model_logic.get("model_surface_selector_shadow") or {}
        learned_reply = str(shadow.get("learned_selected_text") or final_reply)
        current_surface_contract = _evaluate_surface_quality(final_reply, case)
        learned_surface_contract = _evaluate_surface_quality(learned_reply, case)
        rejection_reasons = [
            reason
            for candidate in trace.get("initial_rejected") or []
            for reason in candidate.get("rejection_reasons") or []
        ]
        shadow_active = shadow.get("status") == "active"
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "user_input": case["user_input"],
                "deterministic_reply": deterministic_reply,
                "current_reply": final_reply,
                "current_selected_source": selection.get("selected_source") or "deterministic",
                "current_selected_semantic_alignment": shadow.get("current_selected_semantic_alignment") or {},
                "current_surface_contract": current_surface_contract,
                "current_surface_contract_pass": _quality_pass(current_surface_contract),
                "model_disabled_reason": trace.get("disabled_reason") or "",
                "generated_candidate_count": int(trace.get("initial_generated_count") or 0),
                "accepted_candidate_count": len(trace.get("accepted") or []),
                "initial_rejected_candidate_count": len(trace.get("initial_rejected") or []),
                "model_rejection_reasons": rejection_reasons,
                "model_accepted_candidates": trace.get("accepted") or [],
                "model_initial_rejected_candidates": trace.get("initial_rejected") or [],
                "shadow_status": shadow.get("status") or "not_run",
                "shadow_candidate_count": int(shadow.get("candidate_count") or 0),
                "learned_selected_source": shadow.get("learned_selected_source") or "not_run",
                "learned_reply": learned_reply,
                "learned_selected_probability": shadow.get("learned_selected_probability"),
                "learned_selected_semantic_alignment": shadow.get("learned_selected_semantic_alignment") or {},
                "learned_selected_strict_valid": bool(shadow.get("learned_selected_strict_valid")) if shadow_active else False,
                "learned_selected_was_gate_rejected": bool(shadow.get("learned_selected_was_gate_rejected")) if shadow_active else False,
                "learned_surface_contract": learned_surface_contract,
                "learned_surface_contract_pass": _quality_pass(learned_surface_contract) if shadow_active else False,
                "shadow_agrees_with_current": bool(shadow.get("agrees_with_current")) if shadow_active else None,
                "shadow_would_change": bool(shadow.get("would_change_output")) if shadow_active else False,
                "shadow_visible_output_unchanged": (
                    shadow.get("changes_user_visible_reply") is False
                    and final_reply == selection.get("selected_candidate")
                )
                if shadow_active
                else True,
            }
        )

    summary = summarize_cases(rows, model_loaded=load_model)
    completed_at = time.time()
    gate = _build_gate(summary)
    adapter_config_path = Path(adapter_path) / "adapter_config.json"
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_selector_actual_model_soak_v1",
        "adapter_ref": _adapter_ref(adapter_path),
        "adapter_config_sha256": _file_sha256(adapter_config_path),
        "base_model": os.getenv("URUHA_RIGHT_BRAIN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        "seed": seed,
        "candidate_count_per_case": int(candidate_count),
        "repair_enabled": False,
        "runtime_contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "duration_seconds": round(completed_at - started_at, 3),
        "model_load_duration_seconds": round(model_ready_at - started_at, 3),
        "case_eval_duration_seconds": round(completed_at - model_ready_at, 3),
        "summary": summary,
        "gate": gate,
        "gate_passed": all(gate.values()),
        "cases": rows,
        "conclusion_zh": (
            "本輪直接使用 Qwen2.5-7B + v10 adapter 生成多候選，並在 observe-only shadow 中比較 current 與 learned selector。"
        ),
        "research_boundary": (
            "This is an 11-case actual-model generation soak with three samples per eligible case. "
            "It is stronger than synthetic corruption replay but remains a small fixed holdout, not live dialogue or human preference evidence."
        ),
    }


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# RightBrain Actual-Model Shadow Soak v1",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## 執行條件",
        "",
        f"- base model: `{report['base_model']}`",
        f"- adapter: `{report['adapter_ref']}`",
        f"- seed: `{report['seed']}`",
        f"- candidates per eligible case: `{report['candidate_count_per_case']}`",
        f"- model load seconds: `{report['model_load_duration_seconds']}`",
        f"- generation/eval seconds: `{report['case_eval_duration_seconds']}`",
        "",
        "## 結果",
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| cases | {summary['case_count']} |",
        f"| real generated candidates | {summary['generated_candidate_count']} |",
        f"| raw candidate acceptance | {_fmt_pct(summary['raw_candidate_acceptance_rate'])} |",
        f"| active shadow cases | {summary['shadow_active_case_count']} |",
        f"| multi-candidate shadow cases | {summary['shadow_multi_candidate_case_count']} |",
        f"| current surface-contract pass | {_fmt_pct(summary['current_surface_contract_pass_rate'])} |",
        f"| learned strict-valid | {_fmt_pct(summary['learned_strict_valid_rate'])} |",
        f"| learned surface-contract pass | {_fmt_pct(summary['learned_surface_contract_pass_rate'])} |",
        f"| learned selected gate-rejected | {_fmt_pct(summary['learned_gate_rejected_selection_rate'])} |",
        f"| shadow disagreements | {summary['shadow_disagreement_count']} ({_fmt_pct(summary['shadow_disagreement_rate'])}) |",
        f"| visible output unchanged | {_fmt_pct(summary['shadow_visible_output_unchanged_rate'])} |",
        f"| generated `无` / accepted | {summary['simplified_wu_generated_count']} / {summary['simplified_wu_accepted_count']} |",
        f"| generated `�` / accepted | {summary['unicode_replacement_generated_count']} / {summary['unicode_replacement_accepted_count']} |",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in report["gate"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    caught = []
    for case in report["cases"]:
        for candidate in case.get("model_initial_rejected_candidates") or []:
            raw = str(candidate.get("raw_candidate") or "")
            if "无" in raw or "\ufffd" in raw:
                caught.append((case, candidate, raw))
    lines.extend(
        [
            "",
            "## 真實污染修正證據",
            "",
            "| case | raw model candidate | rejection | current final reply |",
            "|---|---|---|---|",
        ]
    )
    for case, candidate, raw in caught:
        reasons = ", ".join(candidate.get("rejection_reasons") or [])
        lines.append(f"| {case['id']} | {raw} | {reasons} | {case['current_reply']} |")
    lines.extend(
        [
            "",
            "## 個案",
            "",
            "| case | generated | accepted | current source | learned source | valid | surface contract | change |",
            "|---|---:|---:|---|---|---|---|---|",
        ]
    )
    for case in report["cases"]:
        lines.append(
            f"| {case['id']} | {case['generated_candidate_count']} | {case['accepted_candidate_count']} | "
            f"{case['current_selected_source']} | {case['learned_selected_source']} | "
            f"{case['learned_selected_strict_valid']} | {case['learned_surface_contract_pass']} | "
            f"{case['shadow_would_change']} |"
        )
    lines.extend(
        [
            "",
            "## Selector 分歧",
            "",
            "語意欄依序為 `grounding / leftbrain bigram / user-input unigram`；它是診斷訊號，不是自然度或幽默感分數。",
            "",
            "| case | user input | current | current semantic | learned | learned semantic |",
            "|---|---|---|---:|---|---:|",
        ]
    )
    for case in report["cases"]:
        if not case.get("shadow_would_change"):
            continue
        lines.append(
            f"| {case['id']} | {case['user_input']} | {case['current_reply']} | "
            f"{_alignment_label(case['current_selected_semantic_alignment'])} | "
            f"{case['learned_reply']} | "
            f"{_alignment_label(case['learned_selected_semantic_alignment'])} |"
        )
    lines.extend(
        [
            "",
            "## 研究邊界",
            "",
            "- 候選由真實 7B+v10 adapter 生成，不是人工污染字串。",
            "- 只有 11 個固定案例，仍不能取代 live 對話與偏好比較。",
            "- surface-contract pass 只檢查語言、必要槽位與禁止項，不代表語意相關性或自然度勝出。",
            "- learner 仍是 observe-only；報告中的 change 只是反事實記錄。",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--adapter-path")
    source_group.add_argument("--recompute-from-report")
    parser.add_argument("--candidate-count", type=int, default=DEFAULT_CANDIDATE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output-json", default=RIGHTBRAIN_SELECTOR_ACTUAL_MODEL_SOAK_V1_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_SELECTOR_ACTUAL_MODEL_SOAK_V1_REPORT_MD_PATH)
    args = parser.parse_args()

    if args.recompute_from_report:
        source_report = json.loads(Path(args.recompute_from_report).read_text(encoding="utf-8"))
        report = recompute_existing_report(source_report)
    else:
        report = build_report(
            adapter_path=args.adapter_path,
            candidate_count=args.candidate_count,
            seed=args.seed,
            load_model=True,
        )
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(json.dumps({"summary": report["summary"], "gate": report["gate"]}, ensure_ascii=False, indent=2))
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
