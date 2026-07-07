#!/usr/bin/env python3
"""Build a deterministic RightBrain repair candidate-selection dataset."""

import argparse
import json
import random
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_repair_curriculum_v1 import _target_errors
from project_paths import (
    RIGHTBRAIN_REPAIR_CURRICULUM_V1_DATASET_PATH,
    RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH,
    RIGHTBRAIN_REPAIR_SELECTION_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_REPAIR_SELECTION_V1_REPORT_MD_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_SEED = 20260707
DEFAULT_MAX_ROWS = 360
GOLD_TRANSFORM_ID = "gold_valid_reply"


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _load_contract_payload(row):
    return json.loads(row["messages"][1]["content"])


def _target_reply(row):
    return str(row["messages"][-1]["content"] or "").strip()


def _remove_required_group(reply, payload):
    candidate = reply
    changed = False
    for group in payload.get("required_marker_groups") or []:
        if any(str(marker) and str(marker) in candidate for marker in group):
            for marker in group:
                marker = str(marker)
                if marker:
                    candidate = candidate.replace(marker, "")
            changed = True
            break
    if not changed:
        candidate = "そういうことだろ。"
    return " ".join(candidate.split()).strip("、。 ") or "そういうことだろ。"


def _inject_forbidden(reply, payload):
    forbidden = [str(item).strip() for item in payload.get("forbidden_markers") or [] if str(item).strip()]
    marker = forbidden[0] if forbidden else "私"
    return f"{reply}{marker}"


def _make_overlong(reply, payload):
    max_chars = int((payload.get("context") or {}).get("max_chars") or 80)
    suffix = "。".join([reply] * 4)
    return suffix if len(suffix) > max_chars + 2 else f"{reply}。{reply}。{reply}。{reply}"


def _candidate_transforms(reply, payload):
    return [
        ("missing_required_marker", _remove_required_group(reply, payload)),
        ("ascii_leak", f"{reply} OK"),
        ("chinese_leak", f"{reply} 好了"),
        ("nonstandard_cjk_surface", f"{reply} 调"),
        ("polite_tone_drift", f"{reply}です。"),
        ("instruction_or_plan_leak", f"required_semantic: {reply}"),
        ("forbidden_marker", _inject_forbidden(reply, payload)),
        ("over_max_chars", _make_overlong(reply, payload)),
    ]


def _build_candidates(row, rng):
    payload = _load_contract_payload(row)
    target = _target_reply(row)
    candidates = [
        {
            "candidate_id": f"{row['id']}_cand_gold",
            "source": GOLD_TRANSFORM_ID,
            "text": target,
            "is_gold": True,
            "expected_errors": [],
            "detected_errors": _target_errors(target, payload),
        }
    ]
    seen = {target}
    for transform_id, text in _candidate_transforms(target, payload):
        text = str(text or "").strip()
        if not text or text in seen:
            continue
        detected = _target_errors(text, payload)
        if not detected:
            continue
        candidates.append(
            {
                "candidate_id": f"{row['id']}_cand_{transform_id}",
                "source": transform_id,
                "text": text,
                "is_gold": False,
                "expected_errors": detected,
                "detected_errors": detected,
            }
        )
        seen.add(text)
    gold = candidates[0]
    negatives = candidates[1:]
    rng.shuffle(negatives)
    candidates = [gold] + negatives
    rng.shuffle(candidates)
    return candidates


def build_selection_dataset(source_rows, max_rows=DEFAULT_MAX_ROWS, seed=DEFAULT_SEED):
    rng = random.Random(seed)
    rows = []
    skipped = Counter()
    candidate_source_counts = Counter()
    detected_error_counts = Counter()
    source_rows = list(source_rows)
    rng.shuffle(source_rows)

    for source_row in source_rows:
        if len(rows) >= max_rows:
            break
        try:
            payload = _load_contract_payload(source_row)
            target = _target_reply(source_row)
        except (KeyError, IndexError, json.JSONDecodeError, TypeError):
            skipped["invalid_source_row"] += 1
            continue
        if _target_errors(target, payload):
            skipped["invalid_gold_target"] += 1
            continue
        candidates = _build_candidates(source_row, rng)
        negative_count = sum(not candidate["is_gold"] for candidate in candidates)
        if negative_count < 5:
            skipped["too_few_invalid_candidates"] += 1
            continue
        for candidate in candidates:
            candidate_source_counts[candidate["source"]] += 1
            detected_error_counts.update(candidate["detected_errors"])
        rows.append(
            {
                "id": f"rb_repair_selection_v1_{len(rows) + 1:04d}",
                "source_repair_row_id": source_row["id"],
                "source_contract_fingerprint": source_row.get("source_contract_fingerprint", ""),
                "category": source_row.get("category"),
                "source_repair_reason_family": source_row.get("repair_reason_family"),
                "task": "select_valid_rightbrain_repair_candidate",
                "contract_payload": payload,
                "gold_candidate_id": next(
                    candidate["candidate_id"] for candidate in candidates if candidate["is_gold"]
                ),
                "candidates": candidates,
            }
        )

    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_repair_selection_v1",
        "seed": seed,
        "source_row_count": len(source_rows),
        "selection_row_count": len(rows),
        "max_rows": max_rows,
        "candidate_count": sum(len(row["candidates"]) for row in rows),
        "gold_candidate_count": sum(
            sum(candidate["is_gold"] for candidate in row["candidates"])
            for row in rows
        ),
        "invalid_candidate_count": sum(
            sum(not candidate["is_gold"] for candidate in row["candidates"])
            for row in rows
        ),
        "candidate_source_counts": dict(sorted(candidate_source_counts.items())),
        "detected_error_counts": dict(sorted(detected_error_counts.items())),
        "category_counts": dict(sorted(Counter(str(row.get("category") or "uncategorized") for row in rows).items())),
        "skipped_counts": dict(sorted(skipped.items())),
        "research_boundary": (
            "This is a synthetic candidate-selection harness built from the leakage-audited repair curriculum. "
            "It does not add benchmark answers. It tests whether a future selector can preserve the validated "
            "clean reply while rejecting general surface and semantic contract failures."
        ),
    }
    return rows, summary


def write_markdown(summary, path):
    lines = [
        "# RightBrain Repair Selection Dataset v1",
        "",
        "## 一句話結論",
        "",
        (
            f"建立 {summary['selection_row_count']} 題右腦修復候選選擇資料；每題只有 1 個乾淨候選，"
            "其餘候選含可檢出的語意漏失、語言污染、語氣漂移、指令外漏或過長錯誤。"
        ),
        "",
        "## 這次新增的能力",
        "",
        "| 項目 | 數值 | 意義 |",
        "|---|---:|---|",
        f"| selection rows | {summary['selection_row_count']} | 可測選擇器的題數 |",
        f"| total candidates | {summary['candidate_count']} | 候選總數 |",
        f"| gold candidates | {summary['gold_candidate_count']} | 乾淨標準候選 |",
        f"| invalid candidates | {summary['invalid_candidate_count']} | 應被拒絕的錯誤候選 |",
        f"| invalid ratio | {_fmt_pct(_safe_rate(summary['invalid_candidate_count'], summary['candidate_count']))} | 選擇器主要要避開的比例 |",
        "",
        "## 錯誤類型分布",
        "",
        "| 錯誤 | 候選數 |",
        "|---|---:|",
    ]
    for error, count in sorted(summary["detected_error_counts"].items(), key=lambda item: (-item[1], item[0])):
        if error:
            lines.append(f"| {error} | {count} |")
    lines.extend(["", "## 候選來源分布", "", "| 候選來源 | 數量 |", "|---|---:|"])
    for source, count in sorted(summary["candidate_source_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {source} | {count} |")
    lines.extend(
        [
            "",
            "## 研究邊界",
            "",
            "- 這不是把 holdout 或 ToMBench 答案塞給模型。",
            "- 這是在建立右腦修復選擇器的可重現訓練/評測底座。",
            "- 目標是讓右腦不要把左腦已經想好的語意弄丟，也不要輸出中文、英文、敬語漂移或指令文字。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=RIGHTBRAIN_REPAIR_CURRICULUM_V1_DATASET_PATH)
    parser.add_argument("--output", default=RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_REPAIR_SELECTION_V1_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_REPAIR_SELECTION_V1_REPORT_MD_PATH)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    source_rows = json.loads(Path(args.source).read_text(encoding="utf-8"))
    rows, summary = build_selection_dataset(source_rows, max_rows=args.max_rows, seed=args.seed)
    if len(rows) != min(args.max_rows, len(source_rows)):
        raise RuntimeError(f"Selection dataset did not reach the expected row count: {summary}")
    if summary["gold_candidate_count"] != summary["selection_row_count"]:
        raise RuntimeError("Each selection row must have exactly one gold candidate.")
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
