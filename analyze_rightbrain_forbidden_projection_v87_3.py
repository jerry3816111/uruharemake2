#!/usr/bin/env python3
"""Analyze the frozen V87.3 normalized-scope regression."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import analyze_rightbrain_forbidden_projection_v87_2 as v872_analyzer
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87
import rightbrain_forbidden_projection_v87_3 as v873
import run_rightbrain_forbidden_projection_v87 as v87_runner
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_forbidden_projection_v87_3_preregistration.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze(contract, stored_rows, metadata, expected_rows, source_checks):
    report = v872_analyzer.analyze(contract, stored_rows, metadata, expected_rows, source_checks)
    report["schema"] = "uruha_rightbrain_forbidden_projection_analysis_v87_3"
    report["experiment_id"] = contract["experiment_id"]
    report["integrity_checks"]["normalized_scope_oracle_recorded"] = (
        metadata.get("oracle_normalization") == contract["oracle_normalization"]
        and int(metadata.get("normalized_scope_oracle_count", -1)) == int(contract["scope"]["case_count"])
        and all(row.get("normalized_scope_oracle_applied") is True for row in stored_rows)
    )
    report["integrity_passed"] = all(report["integrity_checks"].values())
    report["decision"], report["advance_gate_checks"] = v872_analyzer.decision(
        contract,
        report["integrity_passed"],
        report["summary"],
    )
    report["evidence_boundary"] = contract["evidence_boundary"]
    return report


def render_markdown(report):
    return v872_analyzer.render_markdown(report).replace(
        "# V87.2 Corrected Forbidden-Conflict Projection Regression",
        "# V87.3 Normalized-Scope Forbidden-Conflict Projection Regression",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=ROOT / "reports/rightbrain_forbidden_projection_v87_3.json")
    parser.add_argument("--md", type=Path, default=ROOT / "reports/rightbrain_forbidden_projection_v87_3.md")
    args = parser.parse_args()
    contract = load_json(PREREG_PATH)
    local = {name: ROOT / value for name, value in contract["local_paths"].items()}
    stored_rows = v76.load_jsonl(local["paired_rows"])
    metadata = load_json(local["run_metadata"])
    source_checks = v87.verify_sources(contract, ROOT)
    packets, raw_rows, candidates = v87_runner.load_sources(contract)
    expected_rows = v873.evaluate_all(RightBrain(load_model=False), packets, raw_rows, candidates, contract)
    report = analyze(contract, stored_rows, metadata, expected_rows, source_checks)
    local["local_analysis"].parent.mkdir(parents=True, exist_ok=True)
    local["local_analysis"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "integrity": report["integrity_passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
