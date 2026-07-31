#!/usr/bin/env python3
"""Audit V10 payload representation controls without model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from run_public_persona_payload_format_v10 import CONDITIONS, build_payload
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREGISTRATION = ROOT / "configs/public_persona_payload_format_v10_preregistration.json"
DATASET = ROOT / "datasets/public_persona_contract_v3_development.json"
V9_RESULT_LOCK = ROOT / "configs/public_persona_realization_audit_v9_result_lock.json"
DEFAULT_JSON = ROOT / "reports/public_persona_payload_format_v10_construction.json"
DEFAULT_MD = ROOT / "reports/public_persona_payload_format_v10_construction.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_report(preregistration, dataset, v9_lock):
    right_brain = RightBrain(load_model=False)
    rows = []
    for case in dataset["cases"]:
        control = build_payload(right_brain, case, CONDITIONS[0])
        treatment = build_payload(right_brain, case, CONDITIONS[1])
        control_logic, control_payload, control_text, control_meta = control
        treatment_logic, treatment_payload, treatment_text, treatment_meta = treatment
        serialized = f"{control_text}\n{treatment_text}"
        rows.append(
            {
                "case_id": case["case_id"],
                "logic_identity": control_logic == treatment_logic,
                "canonical_payload_identity": control_payload == treatment_payload,
                "canonical_hash_identity": control_meta["canonical_payload_sha256"]
                == treatment_meta["canonical_payload_sha256"],
                "control_exact": control_meta["control_exact_text_matches"] is True,
                "representation_differs": control_text != treatment_text,
                "control_integrity": control_meta["representation_integrity_pass"] is True,
                "treatment_integrity": treatment_meta["representation_integrity_pass"] is True,
                "leaf_count_identity": control_meta["canonical_leaf_count"]
                == treatment_meta["canonical_leaf_count"]
                == control_meta["represented_leaf_count"]
                == treatment_meta["represented_leaf_count"],
                "treatment_has_lines": "\n" in treatment_text,
                "scorer_exposed": any(
                    token in serialized
                    for token in (
                        '"ordered_pairs"',
                        '"entry_point"',
                        '"unsupported_concrete_markers"',
                        '"expected_pass"',
                        'reply_concept_hits',
                    )
                ),
            }
        )
    summary = {
        "case_count": len(rows),
        "logic_identity_count": sum(row["logic_identity"] for row in rows),
        "canonical_payload_identity_count": sum(row["canonical_payload_identity"] for row in rows),
        "canonical_hash_identity_count": sum(row["canonical_hash_identity"] for row in rows),
        "control_exact_count": sum(row["control_exact"] for row in rows),
        "representation_differs_count": sum(row["representation_differs"] for row in rows),
        "representation_integrity_count": sum(row["control_integrity"] + row["treatment_integrity"] for row in rows),
        "leaf_count_identity_count": sum(row["leaf_count_identity"] for row in rows),
        "treatment_has_lines_count": sum(row["treatment_has_lines"] for row in rows),
        "scorer_exposed_count": sum(row["scorer_exposed"] for row in rows),
        "model_call_count": 0,
        "holdout_content_review_count": 0,
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }
    checks = {
        "v9_dependency": v9_lock["authorizations"]["planned_role_realization_research"] is True,
        "case_accounting": summary["case_count"] == 20,
        "logic_identity": summary["logic_identity_count"] == 20,
        "canonical_payload_identity": summary["canonical_payload_identity_count"] == 20,
        "canonical_hash_identity": summary["canonical_hash_identity_count"] == 20,
        "control_exact": summary["control_exact_count"] == 20,
        "representation_differs": summary["representation_differs_count"] == 20,
        "representation_integrity": summary["representation_integrity_count"] == 40,
        "leaf_count_identity": summary["leaf_count_identity_count"] == 20,
        "treatment_has_lines": summary["treatment_has_lines_count"] == 20,
        "scorer_not_exposed": summary["scorer_exposed_count"] == 0,
        "no_model_holdout_memory_or_action": summary["model_call_count"] == 0
        and summary["holdout_content_review_count"] == 0
        and summary["production_memory_write_count"] == 0
        and summary["physical_vrm_action_count"] == 0,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_public_persona_payload_format_construction_v10",
        "experiment_id": preregistration["experiment_id"],
        "passed": passed,
        "decision": "authorize_merged_main_v10_model_screen_only" if passed else "repair_v10_construction",
        "summary": summary,
        "checks": checks,
        "rows": rows,
        "authorizations": {
            "merged_main_model_screen": passed,
            "source_disjoint_payload_format_holdout": False,
            "runtime_default_enable": False,
            "model_change": False,
            "training": False,
            "v2_holdout_unsealing": False,
            "persona_fidelity_claim": False,
        },
        "inputs": {
            "preregistration": {"sha256": sha(PREREGISTRATION)},
            "dataset": {"sha256": sha(DATASET)},
            "v9_result_lock": {"sha256": sha(V9_RESULT_LOCK)},
        },
        "evidence_boundary": preregistration["evidence_boundary"],
    }


def markdown(report):
    summary = report["summary"]
    return "\n".join(
        [
            "# Payload Format V10 建構稽核",
            "",
            f"- 決策：`{report['decision']}`",
            f"- canonical payload 完全一致：{summary['canonical_payload_identity_count']}/20",
            f"- 控制組精確重現 compact JSON：{summary['control_exact_count']}/20",
            f"- 兩種表示確實不同：{summary['representation_differs_count']}/20",
            f"- 表示完整性：{summary['representation_integrity_count']}/40",
            f"- leaf 數量一致：{summary['leaf_count_identity_count']}/20",
            f"- scorer 暴露：{summary['scorer_exposed_count']}",
            "- 模型呼叫、holdout、記憶寫入、實體動作：全部 0。",
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
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    for path in (args.output_json, args.output_md):
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"refusing to overwrite {path}")
    report = build_report(load(PREREGISTRATION), load(DATASET), load(V9_RESULT_LOCK))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(markdown(report) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "decision": report["decision"], "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if args.require_pass and not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
