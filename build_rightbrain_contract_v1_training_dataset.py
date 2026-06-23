#!/usr/bin/env python3
"""Convert a retired RightBrain curriculum into the canonical runtime-v1 SFT contract."""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_CONTRACT_V1_DATASET_SUMMARY_JSON_PATH,
    RIGHTBRAIN_CONTRACT_V1_DATASET_SUMMARY_MD_PATH,
    RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH,
    RIGHTBRAIN_MODEL_GATE_DATASET_PATH,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RIGHT_BRAIN_MODEL_SYSTEM_PROMPT


TZ = ZoneInfo("Asia/Tokyo")
JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶー一-龠]")
CHINESE_SPECIFIC_RE = re.compile(r"[这吗么们没还让给说话這嗎麼們沒還讓說泠]|好了|不是|我想|你的|可以|為什麼|为什么")
ASCII_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,}")
POLITE_RE = re.compile(
    r"(?:です|ます|でした|ません|ましょう|ください|ございました|しましょう)(?:よね|よ|ね)?(?:[。！？!?、]|$)"
)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_groups_hit(reply, groups):
    return all(any(str(marker) and str(marker) in reply for marker in group) for group in groups)


def _canonical_payload(source_payload):
    source_plan = source_payload.get("leftbrain_plan") or {}
    if not source_plan:
        source_plan = {
            "scene": source_payload.get("scene", ""),
            "intent": source_payload.get("intent", ""),
            "surface_act": source_payload.get("surface_act", ""),
            "dialogue_act": source_payload.get("dialogue_act", ""),
            "meaning": source_payload.get("leftbrain_meaning", ""),
            "content_units": source_payload.get("content_units", []),
            "style_operators": source_payload.get("style_operators", []),
            "grounding_terms": source_payload.get("grounding_terms", []),
        }
    context = source_payload.get("context") or {}
    meaning = str(source_plan.get("meaning") or source_payload.get("leftbrain_meaning") or "").strip()
    required = source_payload.get("required_marker_groups") or []
    forbidden = source_payload.get("forbidden_markers") or []
    return {
        "contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "task": "write_one_user_facing_japanese_reply",
        "contract_rule": (
            "required_marker_groups is the semantic contract. Include at least one phrase from every "
            "inner list naturally and avoid every forbidden marker."
        ),
        # The runtime information bottleneck exposes the normalized Japanese meaning, never raw multilingual input.
        "user_input": meaning or "ユーザーの発話を左脳が要約済み。",
        "leftbrain_plan": {
            "scene": str(source_plan.get("scene") or ""),
            "intent": str(source_plan.get("intent") or ""),
            "surface_act": str(source_plan.get("surface_act") or ""),
            "dialogue_act": str(source_plan.get("dialogue_act") or ""),
            "meaning": meaning,
            "content_units": list(source_plan.get("content_units") or []),
            "style_operators": list(source_plan.get("style_operators") or []),
            "grounding_terms": list(source_plan.get("grounding_terms") or []),
        },
        "context": {
            "memory_summary": "左脳が選択した作業記憶は発話計画に統合済み。",
            "mood": context.get("mood", 0),
            "trust": context.get("trust", 50),
            "max_chars": int(context.get("max_chars") or source_payload.get("max_chars") or 60),
        },
        "required_marker_groups": required,
        "forbidden_markers": forbidden,
        "reply_requirements": [
            "one sentence or short chat reply",
            "natural casual Japanese",
            "no labels or JSON",
            "no Chinese or English",
            "no first person 私",
        ],
    }


def build_dataset(source_rows, excluded_inputs):
    output = []
    stats = Counter()
    category_counts = Counter()
    seen = set()
    for item in source_rows:
        stats["source_rows"] += 1
        messages = item.get("messages") if isinstance(item, dict) else None
        if not messages or len(messages) < 3 or messages[-1].get("role") != "assistant":
            stats["skip_bad_messages"] += 1
            continue
        try:
            source_payload = json.loads(str(messages[-2].get("content") or "{}"))
        except json.JSONDecodeError:
            stats["skip_bad_payload"] += 1
            continue
        if str(source_payload.get("user_input") or "") in excluded_inputs:
            stats["skip_development_overlap"] += 1
            continue
        reply = str(messages[-1].get("content") or "").strip()
        canonical = _canonical_payload(source_payload)
        required = canonical["required_marker_groups"]
        forbidden = [str(marker) for marker in canonical["forbidden_markers"] if str(marker).strip()]
        if not reply or not JAPANESE_RE.search(reply):
            stats["skip_not_japanese"] += 1
            continue
        if CHINESE_SPECIFIC_RE.search(reply):
            stats["skip_chinese_leak"] += 1
            continue
        if ASCII_WORD_RE.search(reply):
            stats["skip_ascii_leak"] += 1
            continue
        if "私" in reply or POLITE_RE.search(reply):
            stats["skip_register_violation"] += 1
            continue
        if required and not _required_groups_hit(reply, required):
            stats["skip_semantic_contract"] += 1
            continue
        if any(marker in reply for marker in forbidden):
            stats["skip_forbidden_marker"] += 1
            continue
        max_chars = canonical["context"]["max_chars"]
        if len(reply) > max_chars + 2:
            stats["skip_over_max_chars"] += 1
            continue
        row_key = json.dumps([canonical, reply], ensure_ascii=False, sort_keys=True)
        if row_key in seen:
            stats["skip_duplicate"] += 1
            continue
        seen.add(row_key)
        category = str(item.get("category") or "unknown")
        output.append(
            {
                "id": f"rb_contract_v1_{len(output) + 1:05d}",
                "source_id": item.get("id"),
                "category": category,
                "training_role": "canonical_contract_v1_sft",
                "messages": [
                    {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))},
                    {"role": "assistant", "content": reply},
                ],
            }
        )
        stats["kept_rows"] += 1
        category_counts[category] += 1
    return output, stats, category_counts


def write_summary_markdown(summary, path):
    lines = [
        "# RightBrain canonical contract v1 訓練資料摘要",
        "",
        f"- 輸入：{summary['source_ref']}",
        f"- 原始列數：{summary['stats']['source_rows']}",
        f"- 保留訓練列數：{summary['stats']['kept_rows']}",
        f"- 與 model-gate 開發集重疊：{summary['stats'].get('skip_development_overlap', 0)}",
        f"- contract：{summary['contract_version']}",
        "- 資料身份：正式改列為 training corpus，不得再當 holdout 或獨立評測證據。",
        "- 原始中文輸入：不進入訓練 payload，只保留左腦日文 meaning。",
        "",
        "## 類別",
        "",
    ]
    for category, count in sorted(summary["category_counts"].items()):
        lines.append(f"- {category}: {count}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--exclude-development", default=RIGHTBRAIN_MODEL_GATE_DATASET_PATH)
    parser.add_argument("--output", default=RIGHTBRAIN_CONTRACT_V1_TRAIN_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_CONTRACT_V1_DATASET_SUMMARY_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_CONTRACT_V1_DATASET_SUMMARY_MD_PATH)
    args = parser.parse_args()

    source_path = Path(args.source)
    source_rows = json.loads(source_path.read_text(encoding="utf-8"))
    dev = json.loads(Path(args.exclude_development).read_text(encoding="utf-8"))
    excluded_inputs = {str(case.get("input") or "") for case in dev.get("cases") or []}
    output, stats, category_counts = build_dataset(source_rows, excluded_inputs)
    if len(output) < 500:
        raise RuntimeError(f"Too few clean training rows after filtering: {len(output)}")

    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source_ref": source_path.name,
        "source_sha256": _sha256(source_path),
        "output_ref": Path(args.output).name,
        "output_sha256": _sha256(args.output),
        "contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "source_role_change": "retired_evaluation_curriculum_to_training_corpus",
        "must_not_be_used_as_holdout": True,
        "development_exclusion_sha256": _sha256(args.exclude_development),
        "stats": dict(stats),
        "category_counts": dict(category_counts),
    }
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_summary_markdown(summary, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
