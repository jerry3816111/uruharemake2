"""Audit the frozen semantic-recall evaluation artifact against its source contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from project_paths import LONGMEMEVAL_S_CLEANED_DATASET_PATH


ROOT = Path(__file__).resolve().parent
AUDITOR = Path(__file__).resolve()
CASES = ROOT / "configs/semantic_memory_recall_support_v1_holdout_cases.json"
RUBRIC = ROOT / "configs/semantic_memory_recall_support_v1_evidence_contract_audit_rubric.json"
REPORT_JSON = ROOT / "reports/semantic_memory_recall_support_v1_evidence_contract_audit.json"
REPORT_MD = ROOT / "reports/semantic_memory_recall_support_v1_evidence_contract_audit.md"
RESULT_LOCK = ROOT / "configs/semantic_memory_recall_support_v1_evidence_contract_audit_result_lock.json"

KANA_RE = re.compile(r"[\u3040-\u30ff]")
HAN_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")
SIMPLIFIED_ONLY = frozenset("这时个举办规帮荐谱么说话间过还没给发为会国东门车书后从")
STOPWORDS = frozenset(
    {
        "a", "about", "an", "and", "are", "as", "at", "be", "but", "by",
        "did", "do", "does", "for", "from", "had", "has", "have", "he",
        "her", "his", "how", "i", "in", "is", "it", "me", "my", "of",
        "on", "or", "she", "that", "the", "their", "them", "they", "this",
        "to", "was", "were", "what", "when", "where", "which", "who", "why",
        "with", "you", "your",
    }
)


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_dataset(path):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("LongMemEval source must be a JSON list")
    return data, {
        "path": str(path),
        "sha256": file_sha256(path),
        "bytes": path.stat().st_size,
        "row_count": len(data),
    }


def content_tokens(text):
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_-]*", str(text or "").lower())
        if token not in STOPWORDS and len(token) > 1
    }


def relevant_excerpt(session, timestamp, question, answer=None, max_turns=8):
    query_tokens = content_tokens(question)
    answer_text = json.dumps(answer, ensure_ascii=False).strip('"').lower()
    ranked = []
    for index, turn in enumerate(session):
        content = re.sub(r"\s+", " ", str(turn.get("content") or "")).strip()
        if not content:
            continue
        overlap = len(query_tokens & content_tokens(content))
        answer_hit = bool(answer_text and answer_text in content.lower())
        ranked.append((int(answer_hit), overlap, index))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    selected_indices = sorted(item[2] for item in ranked[:max_turns])
    lines = [f"Time: {timestamp}"]
    for index in selected_indices:
        turn = session[index]
        role = "User" if turn.get("role") == "user" else "Assistant"
        content = re.sub(r"\s+", " ", str(turn.get("content") or "")).strip()
        lines.append(f"{role}: {content[:900]}")
    return "\n".join(lines)


def timestamp_signature(text):
    numbers = [int(value) for value in re.findall(r"\d+", str(text).splitlines()[0])]
    return numbers[:5] if len(numbers) >= 5 else numbers


def witness_groups_present(text, groups):
    folded = str(text).casefold()
    group_results = [any(str(item).casefold() in folded for item in group) for group in groups]
    return {
        "passed": all(group_results),
        "group_results": group_results,
        "matched_group_count": sum(group_results),
        "required_group_count": len(groups),
    }


def language_contract(language, text):
    text = str(text)
    if language == "English":
        violations = [] if LATIN_RE.search(text) and not HAN_RE.search(text) else ["not_english_script"]
    elif language == "Japanese":
        violations = [] if KANA_RE.search(text) else ["missing_japanese_kana"]
    elif language == "Traditional Chinese":
        violations = []
        if not HAN_RE.search(text) or KANA_RE.search(text):
            violations.append("not_chinese_script")
        simplified = sorted(set(text) & SIMPLIFIED_ONLY)
        if simplified:
            violations.append("simplified_chinese_markers:" + "".join(simplified))
    else:
        violations = ["unsupported_language"]
    return {"passed": not violations, "violations": violations}


def source_record(row, session_id):
    index = row["haystack_session_ids"].index(session_id)
    return {
        "session_id": session_id,
        "timestamp": row["haystack_dates"][index],
        "session": row["haystack_sessions"][index],
    }


def source_fidelity(language, frozen_text, source_text, manual_value):
    if language == "English":
        return {
            "passed": frozen_text == source_text,
            "method": "exact_source_excerpt_match",
        }
    return {
        "passed": bool(manual_value),
        "method": "documented_posthoc_bilingual_audit",
        "mechanically_verifiable_from_v1_artifact": False,
    }


def audit_case(case, row, rubric_case):
    language = case["language"]
    groups = rubric_case["answer_witness_groups"]
    target_source = source_record(row, case["target"]["official_session_id"])
    negative_source = source_record(row, case["hard_negative"]["official_session_id"])
    source_target_text = relevant_excerpt(
        target_source["session"],
        target_source["timestamp"],
        row["question"],
        row["answer"],
    )
    source_negative_text = relevant_excerpt(
        negative_source["session"],
        negative_source["timestamp"],
        row["question"],
    )

    target_id_ok = case["target"]["official_session_id"] in row["answer_session_ids"]
    negative_id_ok = case["hard_negative"]["official_session_id"] not in row["answer_session_ids"]
    target_date_ok = timestamp_signature(case["target"]["text"]) == timestamp_signature(
        target_source["timestamp"]
    )
    negative_date_ok = timestamp_signature(case["hard_negative"]["text"]) == timestamp_signature(
        negative_source["timestamp"]
    )
    source_answer = witness_groups_present(source_target_text, groups)
    target_answer = witness_groups_present(case["target"]["text"], groups)
    negative_answer = witness_groups_present(case["hard_negative"]["text"], groups)
    replacement_answer = witness_groups_present(case["replacement"]["text"], groups)
    field_languages = {
        field: language_contract(language, text)
        for field, text in {
            "question": case["question"],
            "target": case["target"]["text"],
            "hard_negative": case["hard_negative"]["text"],
            "replacement": case["replacement"]["text"],
        }.items()
    }
    target_fidelity = source_fidelity(
        language,
        case["target"]["text"],
        source_target_text,
        rubric_case["manual_target_source_fidelity"],
    )
    negative_fidelity = source_fidelity(
        language,
        case["hard_negative"]["text"],
        source_negative_text,
        rubric_case["manual_hard_negative_source_fidelity"],
    )
    replacement_fact_ok = bool(rubric_case["manual_replacement_fact_preservation"])

    checks = {
        "target_session_id_alignment": target_id_ok,
        "hard_negative_session_id_alignment": negative_id_ok,
        "target_timestamp_alignment": target_date_ok,
        "hard_negative_timestamp_alignment": negative_date_ok,
        "source_excerpt_answer_bearing": source_answer["passed"],
        "target_answer_bearing": target_answer["passed"],
        "hard_negative_answer_absent": not negative_answer["passed"],
        "replacement_answer_bearing": replacement_answer["passed"],
        "all_fields_match_requested_language": all(
            result["passed"] for result in field_languages.values()
        ),
        "target_source_fidelity": target_fidelity["passed"],
        "hard_negative_source_fidelity": negative_fidelity["passed"],
        "replacement_preserves_material_facts": replacement_fact_ok,
    }
    return {
        "case_id": case["case_id"],
        "official_question_id": case["official_question_id"],
        "language": language,
        "official_answer": case["official_answer"],
        "strict_contract_valid": all(checks.values()),
        "checks": checks,
        "diagnostics": {
            "target_source_timestamp": target_source["timestamp"],
            "frozen_target_timestamp_signature": timestamp_signature(case["target"]["text"]),
            "hard_negative_source_timestamp": negative_source["timestamp"],
            "frozen_hard_negative_timestamp_signature": timestamp_signature(
                case["hard_negative"]["text"]
            ),
            "source_answer_witness": source_answer,
            "target_answer_witness": target_answer,
            "hard_negative_answer_witness": negative_answer,
            "replacement_answer_witness": replacement_answer,
            "field_language_contracts": field_languages,
            "target_source_fidelity": target_fidelity,
            "hard_negative_source_fidelity": negative_fidelity,
            "target_characters": len(case["target"]["text"]),
            "replacement_characters": len(case["replacement"]["text"]),
            "replacement_to_target_character_ratio": round(
                len(case["replacement"]["text"]) / len(case["target"]["text"]), 6
            ),
            "manual_note": rubric_case["manual_note"],
        },
    }


def build_report(cases_payload, rubric_payload, data, data_evidence):
    rows = {row["question_id"]: row for row in data}
    audited = []
    for case in cases_payload["cases"]:
        question_id = case["official_question_id"]
        audited.append(
            audit_case(case, rows[question_id], rubric_payload["case_rubric"][question_id])
        )
    check_names = list(audited[0]["checks"])
    counts = {
        name: sum(item["checks"][name] for item in audited)
        for name in check_names
    }
    strict_count = sum(item["strict_contract_valid"] for item in audited)
    contradicted = [
        item["case_id"]
        for item in audited
        if not item["checks"]["target_source_fidelity"]
        or not item["checks"]["target_timestamp_alignment"]
    ]
    return {
        "schema": "uruha_semantic_memory_recall_support_evidence_contract_audit_report_v1",
        "audit_id": rubric_payload["audit_id"],
        "status": "evaluation_artifact_invalid_locked",
        "decision": "invalidate_v1_cases_for_architecture_or_capacity_claims",
        "scope": rubric_payload["scope"],
        "source": data_evidence,
        "observed": {
            "case_count": len(audited),
            "strict_contract_valid_count": strict_count,
            "strict_contract_valid_rate": strict_count / len(audited),
            "check_pass_counts": counts,
            "target_source_contradiction_case_ids": contradicted,
        },
        "cases": audited,
        "affected_conclusions": {
            "semantic_memory_recall_support_v1_holdout": "The selector outputs remain historical observations, but malformed case construction prevents broad answer-bearing-memory conclusions.",
            "answer_bearing_memory_span_v1_development": "The negative result cannot isolate span extraction because expected-safe replacement records often do not retain the answer.",
            "answer_bearing_memory_span_model_capacity_v1": "The capacity screen is exploratory only; it used the same malformed cases and cannot select or reject a production model.",
        },
        "authorization": {
            "runtime_change": False,
            "production_enablement": False,
            "benchmark_claim": False,
            "model_selection": False,
            "reuse_v1_cases_as_holdout": False,
            "build_source_preserving_v2_on_disjoint_rows": True,
        },
        "research_boundary": rubric_payload["research_boundary"],
    }


def markdown_report(report):
    observed = report["observed"]
    counts = observed["check_pass_counts"]
    lines = [
        "# Semantic Memory Recall V1 評測資料證據契約稽核",
        "",
        "## 結論",
        "",
        "這批 8 題不能再用來判斷記憶架構或模型容量。問題出在評測資料建構，而不是聊天 runtime。",
        "",
        f"- 完整通過資料契約：{observed['strict_contract_valid_count']}/{observed['case_count']}",
        f"- target 含答案證據：{counts['target_answer_bearing']}/{observed['case_count']}",
        f"- replacement 保留答案：{counts['replacement_answer_bearing']}/{observed['case_count']}",
        f"- 所有欄位符合指定語言：{counts['all_fields_match_requested_language']}/{observed['case_count']}",
        f"- replacement 保留主要事實：{counts['replacement_preserves_material_facts']}/{observed['case_count']}",
        "",
        "## 逐題結果",
        "",
        "| 題目 | 語言 | Target 有答案 | Replacement 有答案 | 來源對齊 | 語言正確 | 完整有效 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in report["cases"]:
        checks = item["checks"]
        source_ok = checks["target_source_fidelity"] and checks["target_timestamp_alignment"]
        language_ok = checks["all_fields_match_requested_language"]
        mark = lambda value: "通過" if value else "失敗"
        lines.append(
            f"| {item['official_question_id']} | {item['language']} | "
            f"{mark(checks['target_answer_bearing'])} | "
            f"{mark(checks['replacement_answer_bearing'])} | {mark(source_ok)} | "
            f"{mark(language_ok)} | {mark(item['strict_contract_valid'])} |"
        )
    lines.extend(
        [
            "",
            "## 主要錯誤",
            "",
            "1. 4 題英文 replacement 只保留長對話的一小段，3 題連官方答案都遺失。",
            "2. 題目 8550ddae 的 target 與 hard negative 在翻譯時交叉，Session ID 與實際內容不一致。",
            "3. 日文題中有英文問題與中文 replacement；繁體中文題也混入簡體字。",
            "4. V1 沒有保存翻譯前後的逐段來源映射，因此非英文內容無法只靠機器重建證據鏈。",
            "",
            "## 既有結果如何解讀",
            "",
            "PR #396、#397、#398 的執行紀錄仍可保留，但不能再用來主張某種記憶架構或模型容量較好。下一版必須使用未曝光的官方題目、保存原文與雜湊，並在執行前驗證答案、語言與來源映射。",
            "",
            "本稽核不授權 runtime 修改、正式上線、模型選擇或測驗分數主張。",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    outputs = (REPORT_JSON, REPORT_MD, RESULT_LOCK)
    if not args.overwrite and any(path.exists() for path in outputs):
        raise SystemExit("Audit outputs already exist; use --overwrite for an intentional rebuild")

    cases_payload = json.loads(CASES.read_text(encoding="utf-8"))
    rubric_payload = json.loads(RUBRIC.read_text(encoding="utf-8"))
    if file_sha256(CASES) != rubric_payload["scope"]["cases_sha256"]:
        raise SystemExit("Frozen cases hash drift")
    data, evidence = load_dataset(LONGMEMEVAL_S_CLEANED_DATASET_PATH)
    if evidence["sha256"] != rubric_payload["scope"]["source_dataset_sha256"]:
        raise SystemExit("Official source dataset hash drift")

    report = build_report(cases_payload, rubric_payload, data, evidence)
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_MD.write_text(markdown_report(report), encoding="utf-8")
    lock = {
        "schema": "uruha_semantic_memory_recall_support_evidence_contract_audit_result_lock_v1",
        "audit_id": report["audit_id"],
        "status": report["status"],
        "decision": report["decision"],
        "observed": report["observed"],
        "artifacts": {
            path.relative_to(ROOT).as_posix(): file_sha256(path)
            for path in (AUDITOR, CASES, RUBRIC, REPORT_JSON, REPORT_MD)
        },
        "authorization": report["authorization"],
        "next_required_step": "Preregister a source-preserving V2 builder and select disjoint official rows before any new model call.",
        "evidence_boundary": "The audit invalidates the V1 case artifact for causal architecture and model-capacity claims. It does not establish that the runtime memory architecture is good or bad.",
    }
    RESULT_LOCK.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(lock, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
