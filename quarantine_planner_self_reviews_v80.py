#!/usr/bin/env python3
"""Reversibly quarantine non-expert V79 self-reviews from strict planner training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
STRICT_PATH = ROOT / "analysis/planner_supervision_annotations_v75.jsonl"
PILOT_PATH = ROOT / "analysis/local_planner_supervision_v76/pilot_review_queue_v79.jsonl"
ARCHIVE_PATH = ROOT / "analysis/local_planner_supervision_v76/revoked_self_reviews_v80.jsonl"
LOCAL_REPORT_PATH = ROOT / "analysis/local_planner_supervision_v76/self_review_quarantine_v80.json"
REPORT_PATH = ROOT / "reports/planner_supervision_v80_self_review_quarantine.json"
MARKDOWN_PATH = ROOT / "reports/planner_supervision_v80_self_review_quarantine.md"
REASON = "reviewer_declared_insufficient_expertise_and_delegated_future_plan_judgment"


def quarantine_rows(strict_rows, pilot_rows, *, reviewer_id):
    pilot_ids = {str(row.get("candidate_id") or "") for row in pilot_rows}
    quarantined = []
    retained = []
    for row in strict_rows:
        review = row.get("human_review") or {}
        if str(row.get("id") or "") in pilot_ids and str(review.get("reviewer_id") or "") == reviewer_id:
            quarantined.append(
                {
                    "schema": "uruha_planner_self_review_revocation_v80",
                    "reason": REASON,
                    "original_row_sha256": v76.canonical_sha256(row),
                    "original_row": row,
                }
            )
        else:
            retained.append(row)
    return retained, quarantined


def aggregate_report(before_count, retained, quarantined):
    return {
        "schema": "uruha_planner_self_review_quarantine_report_v80",
        "strict_rows_before": before_count,
        "pilot_self_review_rows_quarantined": len(quarantined),
        "strict_rows_after": len(retained),
        "training_rows_removed": before_count - len(retained),
        "raw_archive_gitignored": True,
        "review_log_preserved": True,
        "reason": REASON,
        "v80_formal_integrity_reclassified_as_pass": False,
        "decision": "do_not_train_quarantined_nonexpert_self_reviews",
        "evidence_boundary": "This correction removes explicitly disclaimed self-reviews from strict planner training eligibility while preserving a private reversible archive. It does not validate proxy judges or create replacement labels.",
    }


def _markdown(report):
    return "\n".join(
        [
            "# V80 非專家自評隔離",
            "",
            f"- 隔離前 strict 資料：{report['strict_rows_before']} 筆",
            f"- 隔離：{report['pilot_self_review_rows_quarantined']} 筆",
            f"- 隔離後 strict 資料：{report['strict_rows_after']} 筆",
            "- 原始資料：保留於 gitignored 本機 archive",
            "- V80 正式完整性：仍為失敗，不因事後隔離改判",
            "",
            "使用者已明確表示不具備可靠的 plan 品質判斷能力，因此這批快速自評不能作為研究級訓練標籤。",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer-id", default="jerry")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    strict_rows = v76.load_jsonl(STRICT_PATH)
    retained, quarantined = quarantine_rows(
        strict_rows,
        v76.load_jsonl(PILOT_PATH),
        reviewer_id=args.reviewer_id,
    )
    report = aggregate_report(len(strict_rows), retained, quarantined)
    if args.apply:
        if ARCHIVE_PATH.exists():
            raise SystemExit("private revocation archive already exists")
        v76.write_jsonl(ARCHIVE_PATH, quarantined)
        v76.write_jsonl(STRICT_PATH, retained)
        v76.atomic_write(LOCAL_REPORT_PATH, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        v76.atomic_write(REPORT_PATH, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        v76.atomic_write(MARKDOWN_PATH, _markdown(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
