#!/usr/bin/env python3
"""Build local session provenance review units from quarantined V76 candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import planner_supervision_session_review_v78 as v78
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
TRACKED_REPORT_PATH = ROOT / "reports/planner_supervision_v78_session_review_readiness.json"
TRACKED_MARKDOWN_PATH = ROOT / "reports/planner_supervision_v78_session_review_readiness.md"


def _file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_files_changed(parent_commit):
    output = subprocess.check_output(
        ["git", "diff", "--name-only", parent_commit, "--", "uruha_brain_mac.py", "uruha_web_ui.py"],
        cwd=ROOT,
        text=True,
    )
    return len([line for line in output.splitlines() if line.strip()])


def build_readiness(candidate_path, queue_path, local_report_path, manifest_path):
    contract = v76.load_json(v78.CONTRACT_PATH)
    candidates = v76.load_jsonl(candidate_path)
    units = v78.build_session_review_units(candidates)
    build_report = v78.write_session_review_outputs(units, queue_path, local_report_path)
    status = v78.session_review_status(units, v76.load_jsonl(manifest_path))
    observed = {
        "pending_candidate_count": build_report["pending_candidate_count"],
        "session_review_unit_count": build_report["session_review_unit_count"],
        "repeated_provenance_decisions_removed": build_report["repeated_provenance_decisions_removed"],
        "initial_certified_session_count": status["certified_session_count"],
        "initial_quarantined_session_count": status["quarantined_session_count"],
        "initial_pending_session_count": status["pending_session_count"],
        "initial_training_rows_created": status["training_rows_created"],
        "additional_model_calls": 0,
        "runtime_files_changed": _runtime_files_changed(contract["parent_commit"]),
    }
    expected = contract["success_gates"]
    construction_keys = [
        "pending_candidate_count",
        "session_review_unit_count",
        "repeated_provenance_decisions_removed",
        "initial_certified_session_count",
        "initial_quarantined_session_count",
        "initial_pending_session_count",
        "initial_training_rows_created",
        "additional_model_calls",
        "runtime_files_changed",
    ]
    checks = {key: observed[key] == expected[key] for key in construction_keys}
    return {
        "schema": "uruha_planner_supervision_session_review_readiness_v78",
        "contract_path": str(v78.CONTRACT_PATH.relative_to(ROOT)),
        "contract_sha256": v76.canonical_sha256(contract),
        "private_candidate_queue": {
            "sha256": _file_sha256(candidate_path),
            "raw_content_committed": False,
            "raw_session_ids_committed": False,
        },
        "observed": observed,
        "construction_gates": {"passed": all(checks.values()), "checks": checks},
        "fixture_gates_verified_by": "test_planner_supervision_v78_session_review.py",
        "decision": "ready_for_six_human_session_provenance_decisions" if all(checks.values()) else "not_ready",
        "evidence_boundary": contract["evidence_boundary"],
    }


def _markdown(report):
    observed = report["observed"]
    return "\n".join(
        [
            "# V78 Session 來源審核準備度",
            "",
            f"- 待審候選：{observed['pending_candidate_count']} 筆",
            f"- Session 審核單位：{observed['session_review_unit_count']} 個",
            f"- 省去重複來源判斷：{observed['repeated_provenance_decisions_removed']} 次",
            f"- 已認證 Session：{observed['initial_certified_session_count']} 個",
            f"- 已隔離 Session：{observed['initial_quarantined_session_count']} 個",
            f"- 待判斷 Session：{observed['initial_pending_session_count']} 個",
            f"- 建立訓練資料：{observed['initial_training_rows_created']} 筆",
            f"- 額外模型呼叫：{observed['additional_model_calls']} 次",
            f"- Runtime 修改：{observed['runtime_files_changed']} 個檔案",
            f"- 建構門檻：{'通過' if report['construction_gates']['passed'] else '未通過'}",
            "",
            "程式只整理來源；是否為普通聊天必須由人類判斷。認證後仍需逐筆審核計畫，現在不會建立訓練資料。",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-queue", type=Path)
    parser.add_argument("--tracked-report", action="store_true")
    args = parser.parse_args()
    contract = v76.load_json(v78.CONTRACT_PATH)
    paths = contract["local_paths"]
    candidate_path = args.candidate_queue or ROOT / paths["candidate_queue"]
    queue_path = ROOT / paths["session_review_queue"]
    local_report_path = ROOT / paths["session_review_report"]
    manifest_path = ROOT / paths["session_manifest"]
    report = build_readiness(candidate_path, queue_path, local_report_path, manifest_path)
    if args.tracked_report:
        v76.atomic_write(TRACKED_REPORT_PATH, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        v76.atomic_write(TRACKED_MARKDOWN_PATH, _markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["construction_gates"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
