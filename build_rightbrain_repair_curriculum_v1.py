#!/usr/bin/env python3
"""Build a leakage-audited RightBrain contract-repair SFT curriculum."""

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_model_surface_holdout import _case_inputs
from project_paths import (
    RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH,
    RIGHTBRAIN_REPAIR_CURRICULUM_V1_DATASET_PATH,
    RIGHTBRAIN_REPAIR_CURRICULUM_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_REPAIR_CURRICULUM_V1_REPORT_MD_PATH,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT, RightBrain


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_HOLDOUT_REPORT = Path("reports/rightbrain_v10_repair_off_holdout.json")
DEFAULT_SEED = 20260704
DEFAULT_ROW_LIMIT = 720

JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶー一-龠]")
ASCII_WORD_RE = re.compile(r"[A-Za-z\u00C0-\u024F][A-Za-z0-9_\-\u00C0-\u024F]*")
CHINESE_SPECIFIC_RE = re.compile(
    r"[这吗么们没还让给说话這嗎麼們沒還讓說泠]|好了|不是|我想|你的|可以|為什麼|为什么"
)
NONSTANDARD_CJK_RE = re.compile(
    r"[调选个话这吗么们没还让给说为泠虑责应绪过样经觉开关实进问间东长门见车书风鱼鸟龙]"
    r"|[體國學氣會來處變與樂臺]"
)
POLITE_RE = re.compile(
    r"(?:です|ます|でした|ません|ましょう|ください|ございました|しましょう)"
    r"(?:よね|よ|ね)?(?:[。！？!?、]|$)"
)
INSTRUCTION_MARKERS = (
    "required_semantic",
    "speech_moves",
    "leftbrain",
    "ユーザー入力",
    "出力契約",
    "回答を生成",
)

REPAIR_REASON_PATTERNS = (
    ("semantic_only", ("semantic_slots_missing:0/{slot_count}",)),
    ("ascii_only", ("unexpected_ascii_leak",)),
    ("chinese_only", ("cjk_language_leak",)),
    ("nonstandard_cjk_only", ("nonstandard_cjk_surface",)),
    ("polite_only", ("polite_tone_drift",)),
    ("plan_leak_only", ("instruction_or_plan_leak",)),
    ("length_only", ("over_max_chars",)),
    ("duplicate_only", ("duplicate_candidate",)),
    ("ascii_plus_semantic", ("unexpected_ascii_leak", "semantic_slots_missing:0/{slot_count}")),
    ("cjk_plus_semantic", ("nonstandard_cjk_surface", "semantic_slots_missing:0/{slot_count}")),
    ("tone_plus_semantic", ("polite_tone_drift", "semantic_slots_missing:0/{slot_count}")),
    ("plan_plus_length", ("instruction_or_plan_leak", "over_max_chars")),
    ("forbidden_marker", ("must_avoid_violation",)),
)


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _contract_fingerprint(payload):
    contract = {
        "user_input": payload.get("user_input"),
        "leftbrain_plan": payload.get("leftbrain_plan"),
        "audited_memory_brief": (payload.get("context") or {}).get("audited_memory_brief"),
        "required_marker_groups": payload.get("required_marker_groups"),
        "forbidden_markers": payload.get("forbidden_markers"),
    }
    return hashlib.sha256(_canonical_json(contract).encode("utf-8")).hexdigest()


def _target_errors(reply, payload):
    reply = str(reply or "").strip()
    errors = []
    if not reply or not JAPANESE_RE.search(reply):
        errors.append("not_japanese")
    if CHINESE_SPECIFIC_RE.search(reply):
        errors.append("chinese_leak")
    if NONSTANDARD_CJK_RE.search(reply):
        errors.append("nonstandard_cjk_surface")
    if ASCII_WORD_RE.search(reply):
        errors.append("ascii_leak")
    if "私" in reply:
        errors.append("first_person")
    if POLITE_RE.search(reply):
        errors.append("polite_tone_drift")
    if any(marker.lower() in reply.lower() for marker in INSTRUCTION_MARKERS):
        errors.append("instruction_or_plan_leak")
    required_groups = payload.get("required_marker_groups") or []
    if required_groups and not all(
        any(str(marker) and str(marker) in reply for marker in group)
        for group in required_groups
    ):
        errors.append("required_marker_missing")
    forbidden = [str(item) for item in payload.get("forbidden_markers") or [] if str(item).strip()]
    if any(marker in reply for marker in forbidden):
        errors.append("forbidden_marker")
    max_chars = int((payload.get("context") or {}).get("max_chars") or 80)
    if len(reply) > max_chars + 2:
        errors.append("over_max_chars")
    return errors


def _payload_for_holdout_case(rightbrain, case):
    logic = case["logic"]
    max_chars = (logic.get("constraints") or {}).get("max_chars", 80)
    return json.loads(
        rightbrain._build_model_surface_payload(
            logic,
            case.get("psyche") or {},
            max_chars,
            memory_data=case.get("memory_data") or {},
        )
    )


def _holdout_boundaries(rightbrain, holdout_report):
    cases = list(_case_inputs())
    payloads = [_payload_for_holdout_case(rightbrain, case) for case in cases]
    target_texts = set()
    for row in holdout_report.get("cases") or []:
        for key in ("deterministic_reply", "final_reply"):
            text = str(row.get(key) or "").strip()
            if text:
                target_texts.add(text)
    return {
        "case_ids": {case["id"] for case in cases},
        "user_inputs": {str(payload.get("user_input") or "") for payload in payloads},
        "contract_fingerprints": {_contract_fingerprint(payload) for payload in payloads},
        "target_texts": target_texts,
    }


def _repair_reason_pattern(index, payload):
    name, template = REPAIR_REASON_PATTERNS[index % len(REPAIR_REASON_PATTERNS)]
    forbidden = payload.get("forbidden_markers") or []
    if name == "forbidden_marker" and not forbidden:
        name, template = "forbidden_fallback_semantic", ("semantic_slots_missing:0/{slot_count}",)
    slot_count = max(1, len(payload.get("required_marker_groups") or []))
    return name, [reason.format(slot_count=slot_count) for reason in template]


def _select_stratified(rows, limit, seed):
    by_category = defaultdict(list)
    for row in rows:
        category = str((row.get("source_row") or {}).get("category") or "uncategorized")
        by_category[category].append(row)
    rng = random.Random(seed)
    selected = []
    remaining = []
    for category in sorted(by_category):
        category_rows = list(by_category[category])
        rng.shuffle(category_rows)
        required = min(8, len(category_rows))
        selected.extend(category_rows[:required])
        remaining.extend(category_rows[required:])
    rng.shuffle(remaining)
    selected.extend(remaining[: max(0, limit - len(selected))])
    selected = selected[:limit]
    rng.shuffle(selected)
    return selected


def build_curriculum(source_rows, holdout_report, row_limit=DEFAULT_ROW_LIMIT, seed=DEFAULT_SEED):
    rightbrain = RightBrain(load_model=False)
    boundaries = _holdout_boundaries(rightbrain, holdout_report)
    eligible = []
    skipped = Counter()

    for source_row in source_rows:
        messages = source_row.get("messages") or []
        if len(messages) != 3:
            skipped["invalid_message_count"] += 1
            continue
        try:
            payload = json.loads(str(messages[1].get("content") or "{}"))
        except json.JSONDecodeError:
            skipped["invalid_payload_json"] += 1
            continue
        target = str(messages[-1].get("content") or "").strip()
        errors = _target_errors(target, payload)
        if errors:
            skipped[f"target_validation:{','.join(errors)}"] += 1
            continue
        if str(payload.get("user_input") or "") in boundaries["user_inputs"]:
            skipped["holdout_user_input_overlap"] += 1
            continue
        if _contract_fingerprint(payload) in boundaries["contract_fingerprints"]:
            skipped["holdout_contract_overlap"] += 1
            continue
        if target in boundaries["target_texts"]:
            skipped["holdout_target_overlap"] += 1
            continue
        eligible.append(
            {
                "source_row": source_row,
                "payload": payload,
                "target": target,
            }
        )

    selected = _select_stratified(eligible, min(row_limit, len(eligible)), seed)
    rows = []
    reason_counts = Counter()
    reason_family_counts = Counter()
    category_counts = Counter()

    for index, item in enumerate(selected):
        payload = item["payload"]
        reason_family, reasons = _repair_reason_pattern(index, payload)
        repair_payload = json.loads(
            rightbrain._build_model_surface_repair_payload(
                _canonical_json(payload),
                reasons,
            )
        )
        row = {
            "id": f"rb_repair_curriculum_v1_{index + 1:04d}",
            "source_id": item["source_row"].get("id"),
            "category": item["source_row"].get("category"),
            "training_role": "rightbrain_contract_repair_v1_sft",
            "repair_reason_family": reason_family,
            "repair_rejection_reasons": reasons,
            "source_contract_fingerprint": _contract_fingerprint(payload),
            "messages": [
                {"role": "system", "content": RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(repair_payload, ensure_ascii=False, separators=(",", ":")),
                },
                {"role": "assistant", "content": item["target"]},
            ],
        }
        rows.append(row)
        category_counts[str(row["category"] or "uncategorized")] += 1
        reason_family_counts[reason_family] += 1
        reason_counts.update(reasons)

    output_payloads = [json.loads(row["messages"][1]["content"]) for row in rows]
    output_targets = {row["messages"][-1]["content"] for row in rows}
    overlap = {
        "holdout_user_input_overlap_count": len(
            boundaries["user_inputs"]
            & {str(payload.get("user_input") or "") for payload in output_payloads}
        ),
        "holdout_contract_overlap_count": len(
            boundaries["contract_fingerprints"]
            & {_contract_fingerprint(payload) for payload in output_payloads}
        ),
        "holdout_target_overlap_count": len(boundaries["target_texts"] & output_targets),
    }
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_repair_curriculum_v1",
        "seed": seed,
        "source_row_count": len(source_rows),
        "eligible_source_row_count": len(eligible),
        "row_limit": row_limit,
        "curriculum_row_count": len(rows),
        "holdout_case_count": len(boundaries["case_ids"]),
        **overlap,
        "skipped_counts": dict(sorted(skipped.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "repair_reason_family_counts": dict(sorted(reason_family_counts.items())),
        "repair_reason_counts": dict(sorted(reason_counts.items())),
        "runtime_schema": {
            "system_prompt_matches_runtime": all(
                row["messages"][0]["content"] == RIGHT_BRAIN_MODEL_REPAIR_SYSTEM_PROMPT
                for row in rows
            ),
            "task": "repair_rejected_user_facing_japanese_reply",
            "previous_draft_in_training_prompt": False,
        },
        "research_boundary": (
            "The 11 final-surface holdout cases are excluded by input text, contract fingerprint, "
            "and exact reference target. Training uses general canonical contracts and rejection "
            "types only; benchmark answers and rejected drafts are not exposed."
        ),
    }
    return rows, summary


def write_markdown(summary, path):
    lines = [
        "# RightBrain Contract Repair Curriculum v1",
        "",
        "## 一句話結論",
        "",
        (
            f"建立 {summary['curriculum_row_count']} 筆通用修復資料；11 題 holdout 的輸入、"
            "契約指紋與標準回覆重疊均為 0。"
        ),
        "",
        "## 研究門檻",
        "",
        "| 檢查 | 結果 |",
        "|---|---:|",
        f"| source rows | {summary['source_row_count']} |",
        f"| eligible rows | {summary['eligible_source_row_count']} |",
        f"| repair curriculum rows | {summary['curriculum_row_count']} |",
        f"| holdout cases | {summary['holdout_case_count']} |",
        f"| holdout input overlap | {summary['holdout_user_input_overlap_count']} |",
        f"| holdout contract overlap | {summary['holdout_contract_overlap_count']} |",
        f"| holdout target overlap | {summary['holdout_target_overlap_count']} |",
        "",
        "## 修復原因分布",
        "",
        "| 原因 | 筆數 |",
        "|---|---:|",
    ]
    for reason, count in sorted(
        summary["repair_reason_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    ):
        lines.append(f"| {reason} | {count} |")
    lines.extend(
        [
            "",
            "## 情境分布",
            "",
            "| 情境 | 筆數 |",
            "|---|---:|",
        ]
    )
    for category, count in sorted(summary["category_counts"].items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(
        [
            "",
            "## 設計邊界",
            "",
            "- runtime 與訓練共用相同 repair system prompt、task 與 feedback schema。",
            "- 不提供失敗草稿，模型只能從左腦計畫與語意契約重新生成。",
            "- 不含 11 題 holdout 的輸入、完整契約或標準回覆。",
            "- 這是通用 denoising / revision 能力訓練，不是加入測驗答案。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH)
    parser.add_argument("--holdout-report", default=DEFAULT_HOLDOUT_REPORT)
    parser.add_argument("--output", default=RIGHTBRAIN_REPAIR_CURRICULUM_V1_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_REPAIR_CURRICULUM_V1_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_REPAIR_CURRICULUM_V1_REPORT_MD_PATH)
    parser.add_argument("--row-limit", type=int, default=DEFAULT_ROW_LIMIT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    source_rows = json.loads(Path(args.source).read_text(encoding="utf-8"))
    holdout_report = json.loads(Path(args.holdout_report).read_text(encoding="utf-8"))
    rows, summary = build_curriculum(
        source_rows,
        holdout_report,
        row_limit=args.row_limit,
        seed=args.seed,
    )
    if len(rows) != min(args.row_limit, summary["eligible_source_row_count"]):
        raise RuntimeError("Repair curriculum did not reach the expected row count.")
    overlap_keys = [
        "holdout_user_input_overlap_count",
        "holdout_contract_overlap_count",
        "holdout_target_overlap_count",
    ]
    if any(summary[key] for key in overlap_keys):
        raise RuntimeError(f"Holdout leakage detected: {summary}")
    if not summary["runtime_schema"]["system_prompt_matches_runtime"]:
        raise RuntimeError("Training and runtime repair system prompts do not match.")

    Path(args.output).write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.summary_json).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(summary, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
