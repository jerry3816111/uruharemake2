#!/usr/bin/env python3
"""Close the interrupted V81 run without scoring partial model outcomes."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

import planner_supervision_executable_view_v81 as v81
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v81_executable_view_contract.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v81_executable_view.json"
MARKDOWN_PATH = ROOT / "reports/planner_supervision_v81_executable_view.md"
RUNTIME_PATHS = ("uruha_brain_mac.py", "uruha_web_ui.py", "uruha_memory_runtime.py", "memory_consolidation.py")


def _runtime_files_changed(parent_commit):
    output = subprocess.check_output(
        ["git", "diff", "--name-only", parent_commit, "--", *RUNTIME_PATHS],
        cwd=ROOT,
        text=True,
    )
    return len([line for line in output.splitlines() if line.strip()])


def _parse_error_category(row, contract):
    try:
        v81.parse_judgment(row.get("parsed"), contract)
        return "parsed"
    except Exception:
        message = str(row.get("parse_error") or "")
        if "invalid keys" in message:
            return "invalid_output_keys"
        if "Expecting" in message or "JSON" in message or "delimiter" in message:
            return "malformed_json"
        return "other_parse_failure"


def audit_completed_prefix(packets, raw_rows, contract):
    sequence = v81.expected_run_sequence(packets, contract)
    judges = {row["model"]: row for row in contract["judges"]}
    checks = Counter()
    parse_categories = Counter()
    completed_by_model = Counter()
    completed_by_condition = Counter()
    completed_by_variant = Counter()
    for index, row in enumerate(raw_rows):
        if index >= len(sequence):
            raise ValueError("V81 raw rows exceed frozen sequence")
        judge, packet, condition, variant = sequence[index]
        model = judge["model"]
        expected_identity = (packet["candidate_id"], condition, variant, model)
        observed_identity = (row.get("candidate_id"), row.get("condition"), row.get("variant"), row.get("model"))
        if observed_identity != expected_identity:
            raise ValueError("V81 completed prefix order mismatch")
        checks["identity"] += 1
        if row.get("model_digest") != judges[model]["digest"]:
            raise ValueError("V81 completed prefix model digest mismatch")
        checks["model_digest"] += 1
        if row.get("packet_view_sha256") != packet["view_sha256"][condition]:
            raise ValueError("V81 completed prefix view hash mismatch")
        checks["view_hash"] += 1
        request = v81.build_request(packet, contract, model, condition, variant)
        if row.get("request_sha256") != v76.canonical_sha256(request):
            raise ValueError("V81 completed prefix request hash mismatch")
        checks["request_hash"] += 1
        if row.get("done") is True:
            checks["done"] += 1
        if row.get("response_model") == model:
            checks["response_model"] += 1
        parse_categories[_parse_error_category(row, contract)] += 1
        completed_by_model[model] += 1
        completed_by_condition[condition] += 1
        completed_by_variant[variant] += 1
    next_attempt = None
    if len(raw_rows) < len(sequence):
        judge, packet, condition, variant = sequence[len(raw_rows)]
        next_attempt = {
            "ordinal": len(raw_rows) + 1,
            "model": judge["model"],
            "fresh_index": packet["fresh_index"],
            "condition": condition,
            "variant": variant,
        }
    return {
        "completed_prefix_hash_binding_passed": True,
        "completed_count": len(raw_rows),
        "expected_count": len(sequence),
        "binding_check_counts": dict(sorted(checks.items())),
        "parse_category_counts": dict(sorted(parse_categories.items())),
        "completed_by_model": dict(sorted(completed_by_model.items())),
        "completed_by_condition": dict(sorted(completed_by_condition.items())),
        "completed_by_variant": dict(sorted(completed_by_variant.items())),
        "interrupted_attempt": next_attempt,
    }


def build_abort_report(prefix_audit, contract, runtime_files_changed):
    return {
        "schema": "uruha_planner_executable_view_abort_v81",
        "contract_sha256": v76.canonical_sha256(contract),
        "formal_run_status": "aborted",
        "abort_reasons": [
            "output_generation_length_was_not_bounded",
            "one_request_exceeded_600_seconds_and_required_manual_interrupt",
            "completed_prefix_already_contained_parser_incompatibility",
        ],
        "prefix_audit": prefix_audit,
        "production_runtime_files_changed": runtime_files_changed,
        "capability_metrics_authorized": False,
        "planner_training_authorized": False,
        "production_runtime_change_authorized": False,
        "decision": "close_v81_without_scoring_and_require_new_holdout_with_hard_generation_bound",
        "evidence_boundary": (
            "V81 proves only that this frozen proxy-review harness was not safely terminable or parser-compatible. "
            "The 48 completed rows are an interrupted prefix and cannot support condition accuracy, agreement, "
            "latency, human-likeness, planner quality, training, or runtime-change claims."
        ),
    }


def _markdown(report):
    audit = report["prefix_audit"]
    categories = audit["parse_category_counts"]
    return "\n".join(
        [
            "# V81 可執行 Plan 視圖實驗：中止",
            "",
            f"- 完成：{audit['completed_count']}/{audit['expected_count']}",
            f"- 可解析：{categories.get('parsed', 0)}/{audit['completed_count']}",
            f"- 無效欄位格式：{categories.get('invalid_output_keys', 0)}",
            f"- JSON 損壞：{categories.get('malformed_json', 0)}",
            "- 第 49 次呼叫超過 600 秒後人工中止",
            "- 正式 runtime 修改：0",
            "- 能力與成功率：不計算",
            "",
            "原因是評測契約沒有固定最大生成長度，且 qwen3.5 的關閉思考模式與輸出 schema 不相容。",
            "這是評測方法失敗，不是聊天系統能力失敗；48 筆部分結果不得用來主張任一條件較好。",
            "",
        ]
    )


def main():
    contract = v76.load_json(CONTRACT_PATH)
    paths = {key: ROOT / value for key, value in contract["local_paths"].items()}
    packets = v81.build_packets(
        v76.load_jsonl(paths["candidate_queue"]),
        v76.load_jsonl(paths["session_manifest"]),
        v76.load_jsonl(paths["v79_pilot_queue"]),
        contract,
    )
    prefix_audit = audit_completed_prefix(packets, v76.load_jsonl(paths["raw_results"]), contract)
    report = build_abort_report(prefix_audit, contract, _runtime_files_changed(contract["parent_commit"]))
    v76.atomic_write(paths["local_analysis"], json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    v76.atomic_write(REPORT_PATH, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    v76.atomic_write(MARKDOWN_PATH, _markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
