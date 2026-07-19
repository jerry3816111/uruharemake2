#!/usr/bin/env python3
"""Compare V76 row-only filtering with V77 mixed-session quarantine."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/planner_supervision_v77_session_quarantine_contract.json"
REPORT_JSON_PATH = ROOT / "reports/planner_supervision_v77_session_quarantine.json"
REPORT_MD_PATH = ROOT / "reports/planner_supervision_v77_session_quarantine.md"
RUNTIME_PATHS = ["uruha_brain_mac.py", "uruha_web_ui.py"]


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_files_changed(parent_commit):
    output = subprocess.check_output(
        ["git", "diff", "--name-only", parent_commit, "--", *RUNTIME_PATHS],
        cwd=ROOT,
        text=True,
    )
    return len([line for line in output.splitlines() if line.strip()])


def build_diagnostic(web_log_path):
    web_log_path = Path(web_log_path)
    contract = v76.load_json(CONTRACT_PATH)
    source_sha256 = _file_sha256(web_log_path)
    expected_sha256 = contract["problem_evidence"]["private_historical_log_sha256"]
    if source_sha256 != expected_sha256:
        raise ValueError("private historical Web log hash does not match the frozen V77 contract")

    records = v76.load_jsonl(web_log_path)
    protected_inputs = v76.protected_inputs_from_v75()
    v76_contract = v76.load_json(v76.CONTRACT_PATH)
    threshold = float(v76_contract["near_evaluation_overlap_threshold"])
    contaminated_sessions, _ = v76.evaluation_contaminated_sessions(records, protected_inputs, threshold)
    control = v76.build_candidates(
        records,
        protected_inputs=protected_inputs,
        contract=v76_contract,
        quarantine_contaminated_sessions=False,
    )
    treatment = v76.build_candidates(
        records,
        protected_inputs=protected_inputs,
        contract=v76_contract,
        quarantine_contaminated_sessions=True,
    )
    surviving_contaminated = [
        row for row in treatment["candidates"] if row["source_session_id"] in contaminated_sessions
    ]
    observed = {
        "source_record_count": len(records),
        "candidate_count_before_quarantine": control["summary"]["candidate_count"],
        "candidate_count_after_quarantine": treatment["summary"]["candidate_count"],
        "evaluation_contaminated_session_count": len(contaminated_sessions),
        "otherwise_valid_records_quarantined": treatment["summary"]["otherwise_valid_records_quarantined"],
        "candidates_from_contaminated_sessions": len(surviving_contaminated),
        "training_rows_created": treatment["summary"]["training_rows_created"],
        "additional_model_calls": treatment["summary"]["additional_model_calls"],
        "runtime_files_changed": _runtime_files_changed(contract["parent_commit"]),
    }
    expected = contract["success_gates"]
    checks = {key: observed.get(key) == value for key, value in expected.items()}
    checks["private_source_hash_matches_contract"] = source_sha256 == expected_sha256
    return {
        "schema": "uruha_planner_supervision_session_quarantine_report_v77",
        "contract_path": str(CONTRACT_PATH.relative_to(ROOT)),
        "contract_sha256": v76.canonical_sha256(contract),
        "private_source": {
            "sha256": source_sha256,
            "record_count": len(records),
            "raw_content_committed": False,
            "raw_session_ids_committed": False,
        },
        "control": {
            "condition": "V76 row-level overlap filtering only",
            "candidate_count": control["summary"]["candidate_count"],
            "training_rows_created": control["summary"]["training_rows_created"],
        },
        "treatment": {
            "condition": "V77 row-level filtering plus mixed-session quarantine",
            "candidate_count": treatment["summary"]["candidate_count"],
            "training_rows_created": treatment["summary"]["training_rows_created"],
        },
        "observed": observed,
        "success_gates": {"passed": all(checks.values()), "checks": checks},
        "hypothesis_supported": all(checks.values()),
        "evidence_boundary": contract["evidence_boundary"],
    }


def _markdown(report):
    observed = report["observed"]
    return "\n".join(
        [
            "# V77 混合 Session 隔離結果",
            "",
            f"- 私有來源 SHA-256：`{report['private_source']['sha256']}`",
            f"- 原始紀錄：{observed['source_record_count']} 筆",
            f"- V76 控制組候選：{observed['candidate_count_before_quarantine']} 筆",
            f"- V77 Session 隔離後：{observed['candidate_count_after_quarantine']} 筆",
            f"- 受污染 Session：{observed['evaluation_contaminated_session_count']} 個",
            f"- 額外隔離的原本合格候選：{observed['otherwise_valid_records_quarantined']} 筆",
            f"- 隔離後仍來自受污染 Session：{observed['candidates_from_contaminated_sessions']} 筆",
            f"- 建立訓練資料：{observed['training_rows_created']} 筆",
            f"- 額外模型呼叫：{observed['additional_model_calls']} 次",
            f"- Runtime 修改：{observed['runtime_files_changed']} 個檔案",
            f"- 成功門檻：{'通過' if report['success_gates']['passed'] else '未通過'}",
            "",
            "這只證明已知測驗污染會連同整個 Session 被隔離；剩餘候選仍需人工確認 Session 來源與計畫合理性。",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-log", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = build_diagnostic(args.web_log)
    if args.write:
        v76.atomic_write(REPORT_JSON_PATH, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        v76.atomic_write(REPORT_MD_PATH, _markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["success_gates"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
