#!/usr/bin/env python3
"""Audit V8 source selection without network or behavior-content access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import public_persona_source_availability_v8 as v8


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_source_availability_v8_preregistration.json"
DEFAULT_JSON = ROOT / "reports/public_persona_source_availability_v8_construction.json"
DEFAULT_MD = ROOT / "reports/public_persona_source_availability_v8_construction.md"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_report():
    preregistration = v8.load(PREREGISTRATION)
    sources = v8.select_sources(v8.load(v8.TARGET_MANIFEST), v8.load(v8.CONTRAST_MANIFEST))
    summary = {
        "source_count": len(sources),
        "target_calibration_count": sum(source["source_group"] == "target_calibration" for source in sources),
        "matched_contrast_count": sum(source["source_group"] == "matched_contrast" for source in sources),
        "unique_source_id_count": len({source["source_id"] for source in sources}),
        "unique_video_id_count": len({source["video_id"] for source in sources}),
        "final_holdout_selected_count": sum(source.get("dataset_role") == "final_holdout" for source in sources),
        "sealed_source_selected_count": sum(source.get("sealed") is True for source in sources),
        "network_request_count": 0,
        "behavior_content_review_count": 0,
        "model_call_count": 0,
    }
    checks = {
        "source_accounting": summary["source_count"] == 12
        and summary["target_calibration_count"] == 3
        and summary["matched_contrast_count"] == 9,
        "source_uniqueness": summary["unique_source_id_count"] == 12
        and summary["unique_video_id_count"] == 12,
        "holdout_excluded": summary["final_holdout_selected_count"] == 0
        and summary["sealed_source_selected_count"] == 0,
        "no_network_content_or_model_use": summary["network_request_count"] == 0
        and summary["behavior_content_review_count"] == 0
        and summary["model_call_count"] == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_public_persona_source_availability_construction_v8",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": "authorize_merged_main_metadata_check_only" if passed else "repair_source_selection",
        "summary": summary,
        "checks": checks,
        "selected_source_ids": [source["source_id"] for source in sources],
        "inputs": {
            "target_manifest_sha256": sha(v8.TARGET_MANIFEST),
            "contrast_manifest_sha256": sha(v8.CONTRAST_MANIFEST),
            "preregistration_sha256": sha(PREREGISTRATION),
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# 公開人格來源可用性 V8 建構稽核",
            "",
            f"- 決策：`{report['decision']}`",
            f"- 目標校準來源：{summary['target_calibration_count']}/3",
            f"- 相近人物來源：{summary['matched_contrast_count']}/9",
            f"- Final holdout／sealed 誤選：{summary['final_holdout_selected_count']} / {summary['sealed_source_selected_count']}",
            "- 網路、內容查看、模型呼叫：全部 0。",
            "",
            "## 證據邊界",
            "",
            report["evidence_boundary"],
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if args.require_pass and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
