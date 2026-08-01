#!/usr/bin/env python3
"""Run the one-shot V8 metadata-only source availability audit."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import public_persona_source_availability_v8 as v8


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_source_availability_v8_preregistration.json"
LOCK = ROOT / "configs/public_persona_source_availability_v8_harness_lock.json"
CONSTRUCTION = ROOT / "reports/public_persona_source_availability_v8_construction.json"
DEFAULT_JSON = ROOT / "reports/public_persona_source_availability_v8_result.json"
DEFAULT_MD = ROOT / "reports/public_persona_source_availability_v8_result.md"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()


def verify_lock(lock):
    drift = []
    for artifact in lock["frozen_artifacts"].values():
        path = ROOT / artifact["path"]
        if not path.is_file() or sha(path) != artifact["sha256"]:
            drift.append(artifact["path"])
    if drift:
        raise ValueError(f"V8 frozen artifact drift: {drift}")


def run_preflight(lock):
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_public_persona_source_availability_v8.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1"},
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    observed = int(match.group(1)) if match else None
    expected = int(lock["preflight"]["expected_test_count"])
    return {
        "returncode": completed.returncode,
        "observed_test_count": observed,
        "expected_test_count": expected,
        "passed": completed.returncode == 0 and observed == expected,
    }


def atomic_write(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def evaluate(summary, preregistration, selection_integrity_pass):
    gates = preregistration["pass_gates"]
    return {
        "selection_integrity": selection_integrity_pass is gates["selection_integrity_pass"],
        "oembed_resolution": summary["oembed_resolution_count"] == gates["public_oembed_resolution_count_exact"],
        "watch_metadata_resolution": summary["watch_metadata_resolution_count"] == gates["watch_metadata_resolution_count_exact"],
        "publisher_channel_match": summary["publisher_channel_match_count"] == gates["publisher_channel_match_count_exact"],
        "publication_date_match": summary["publication_date_match_count"] == gates["publication_date_match_count_exact"],
        "request_errors": summary["request_error_count"] <= gates["request_error_count_max"],
        "holdout_excluded": summary["final_holdout_source_request_count"] == gates["final_holdout_source_request_count_exact"],
        "behavior_content_not_reviewed": summary["behavior_content_review_count"] == gates["behavior_content_review_count_exact"],
        "titles_not_stored": summary["stored_title_count"] == gates["stored_title_count_exact"],
        "transcripts_not_stored": summary["stored_transcript_count"] == gates["stored_transcript_count_exact"],
    }


def markdown(report):
    summary = report["summary"]
    lines = [
        "# 公開人格來源可用性 V8 結果",
        "",
        f"- 決策：`{report['decision']}`",
        "",
        "| 檢查 | 通過 |",
        "|---|---:|",
        f"| 可公開解析 | {summary['oembed_resolution_count']}/12 |",
        f"| Watch metadata 可解析 | {summary['watch_metadata_resolution_count']}/12 |",
        f"| 官方頻道一致 | {summary['publisher_channel_match_count']}/12 |",
        f"| 發布日期一致 | {summary['publication_date_match_count']}/12 |",
        f"| 請求錯誤 | {summary['request_error_count']} |",
        f"| Final holdout 存取 | {summary['final_holdout_source_request_count']} |",
        f"| 內容／標題／逐字稿保存 | {summary['behavior_content_review_count']} / {summary['stored_title_count']} / {summary['stored_transcript_count']} |",
        "",
        "## 逐筆狀態",
        "",
        "| 來源 | 群組 | 公開 | 頻道 | 日期 |",
        "|---|---|---:|---:|---:|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['source_id']} | {row['source_group']} | "
            f"{row['oembed_resolved'] and row['watch_metadata_resolved']} | "
            f"{row['channel_match']} | {row['published_date_match']} |"
        )
    lines.extend(["", "## 證據邊界", "", report["evidence_boundary"]])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    if git("branch", "--show-current") != "main":
        raise SystemExit("formal V8 source audit requires merged main")
    if git("status", "--porcelain"):
        raise SystemExit("formal V8 source audit requires a clean worktree")
    if git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
        raise SystemExit("formal V8 source audit requires HEAD at origin/main")
    if args.output_json.exists() or args.output_md.exists():
        raise SystemExit("V8 source result already exists; refusing a second formal run")

    preregistration = v8.load(PREREGISTRATION)
    lock = v8.load(LOCK)
    construction = v8.load(CONSTRUCTION)
    verify_lock(lock)
    preflight = run_preflight(lock)
    if not preflight["passed"] or not construction["passed"]:
        raise SystemExit("V8 source preflight or construction audit failed")
    sources = v8.select_sources(v8.load(v8.TARGET_MANIFEST), v8.load(v8.CONTRAST_MANIFEST))
    rows = []
    for index, source in enumerate(sources, start=1):
        row = v8.verify_source(
            source, timeout_seconds=preregistration["request_policy"]["timeout_seconds"]
        )
        rows.append(row)
        partial = {
            "schema": "uruha_public_persona_source_availability_result_v8",
            "experiment_id": preregistration["experiment_id"],
            "formal_git_head": git("rev-parse", "HEAD"),
            "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "completed_source_count": len(rows),
            "expected_source_count": len(sources),
            "rows": rows,
        }
        atomic_write(args.output_json, partial)
        print(f"[{index}/{len(sources)}] {source['source_id']} errors={len(row['errors'])}", flush=True)

    summary = v8.summarize(rows)
    checks = evaluate(summary, preregistration, construction["passed"])
    passed = all(checks.values())
    report = {
        "schema": "uruha_public_persona_source_availability_result_v8",
        "experiment_id": preregistration["experiment_id"],
        "formal_git_head": git("rev-parse", "HEAD"),
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "passed": passed,
        "decision": preregistration["decision_policy"]["pass" if passed else "fail"],
        "summary": summary,
        "checks": checks,
        "preflight": preflight,
        "inputs": {
            "preregistration_sha256": sha(PREREGISTRATION),
            "harness_lock_sha256": sha(LOCK),
            "construction_sha256": sha(CONSTRUCTION),
            "target_manifest_sha256": sha(v8.TARGET_MANIFEST),
            "contrast_manifest_sha256": sha(v8.CONTRAST_MANIFEST),
        },
        "rows": rows,
        "authorizations": {
            "existing_v7_human_coding_source_access": passed,
            "holdout_unsealing": False,
            "model_execution": False,
            "runtime_change": False,
            "training": False,
            "persona_fidelity_claim": False,
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }
    atomic_write(args.output_json, report)
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "decision": report["decision"], "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
