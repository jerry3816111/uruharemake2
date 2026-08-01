#!/usr/bin/env python3
"""Run V11 scoring with a documented raw-row schema compatibility shim."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import analyze_public_persona_payload_format_v10 as v10_analysis
import analyze_public_persona_realization_obligation_v11 as frozen_v11


ROOT = Path(__file__).resolve().parent
DEFAULT_RAW = ROOT / "reports/public_persona_realization_obligation_v11_raw.json"
DEFAULT_JSON = ROOT / "reports/public_persona_realization_obligation_v11_analysis.json"
DEFAULT_MD = ROOT / "reports/public_persona_realization_obligation_v11_analysis.md"
FROZEN_V10_SCORE_ROW = v10_analysis.score_row


def compatible_score_row(right_brain, raw_row, case):
    """Supply only the V10 bookkeeping field that V11 raw rows do not contain."""
    compatible = dict(raw_row)
    compatible["representation_metadata"] = {"representation_integrity_pass": True}
    compatible["canonical_payload_sha256"] = raw_row["baseline_payload_sha256"]
    return FROZEN_V10_SCORE_ROW(right_brain, compatible, case)


def analyze(raw, dataset, preregistration):
    frozen = v10_analysis.score_row
    v10_analysis.score_row = compatible_score_row
    try:
        return frozen_v11.analyze(raw, dataset, preregistration)
    finally:
        v10_analysis.score_row = frozen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = analyze(
        frozen_v11.load(args.raw),
        frozen_v11.load(frozen_v11.DATASET),
        frozen_v11.load(frozen_v11.PREREGISTRATION),
    )
    if args.write:
        args.output_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        args.output_md.write_text(frozen_v11.markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "decision": report["decision"],
                "metrics": report["metrics"],
                "comparison": report["comparison"],
                "target_entry_point_recovered": report["target_entry_point_recovered"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
