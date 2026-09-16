#!/usr/bin/env python3
"""P3-B36 immutable post-lock audit of the B35 Japanese surface gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from p3_product_comparison import canonical_sha256, write_new_json
from p3_strict_visible_surface import strict_japanese_visible_surface_contract


EXPECTED_RESULT_SHA256 = "c6654e438a2950e98fb7c4749f91d57db43eaf8d8031cd24dd0d30315a7f080d"
EXPECTED_SCHEMA = "uruha_p3_prospective_case01_output_lock_result_v1"
EXPECTED_CASE_ID = "p3-prospective-v2-overwhelm-company-zh"


class SurfaceAuditError(ValueError):
    pass


def _read(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _visible_text(condition: str, row: Mapping[str, Any]) -> str:
    if condition == "product_system":
        return str(row.get("visible_reply") or "")
    return str((row.get("final") or {}).get("content") or "")


def _stored_digest(condition: str, row: Mapping[str, Any]) -> str:
    if condition == "product_system":
        return str(row.get("visible_reply_sha256") or "")
    return str((row.get("final") or {}).get("content_sha256") or "")


def build_audit(path: str | Path) -> dict[str, Any]:
    result_path = Path(path)
    raw_bytes = result_path.read_bytes()
    result_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if result_sha256 != EXPECTED_RESULT_SHA256:
        raise SurfaceAuditError("b35_result_hash_mismatch")
    result = json.loads(raw_bytes)
    if (
        result.get("schema") != EXPECTED_SCHEMA
        or result.get("case_id") != EXPECTED_CASE_ID
        or result.get("status") != "prospective_case01_outputs_locked"
    ):
        raise SurfaceAuditError("b35_result_identity_mismatch")

    rows: list[dict[str, Any]] = []
    for condition, key in (
        ("product_system", "product_turns"),
        ("full_history_direct", "direct_turns"),
    ):
        condition_rows = result.get(key)
        if not isinstance(condition_rows, list) or len(condition_rows) != 4:
            raise SurfaceAuditError("b35_turn_count_mismatch")
        for row in condition_rows:
            text = _visible_text(condition, row)
            if canonical_sha256(text) != _stored_digest(condition, row):
                raise SurfaceAuditError("b35_visible_output_hash_mismatch")
            strict = strict_japanese_visible_surface_contract(text)
            failed = [name for name, passed in strict.items() if not passed]
            rows.append({
                "condition": condition,
                "turn_id": row.get("turn_id"),
                "visible_reply_sha256": canonical_sha256(text),
                "legacy_surface_claimed_pass": all(
                    bool(value) for value in (row.get("surface_contract") or {}).values()
                ),
                "strict_surface": strict,
                "strict_surface_pass": not failed,
                "failure_reasons": failed,
            })

    failures = [row for row in rows if not row["strict_surface_pass"]]
    checks = {
        "b35_result_hash_matches": True,
        "eight_outputs_hash_verified": len(rows) == 8,
        "b35_legacy_claimed_all_eight_pass": all(
            row["legacy_surface_claimed_pass"] for row in rows
        ),
        "strict_audit_complete_for_all_eight": len(rows) == 8,
        "annotations_remained_closed": result.get("annotations_accessed") == 0,
        "generation_not_repeated": True,
    }
    return {
        "schema": "uruha_p3_b35_strict_surface_gate_audit_v1",
        "phase": "P3-B36",
        "status": (
            "b35_surface_gate_false_positive_retained"
            if failures else "b35_strict_surface_gate_pass"
        ),
        "input": {
            "path": str(result_path),
            "sha256": result_sha256,
            "case_id": EXPECTED_CASE_ID,
        },
        "checks": checks,
        "rows": rows,
        "strict_pass_count": len(rows) - len(failures),
        "strict_failure_count": len(failures),
        "failed_outputs": [
            {
                "condition": row["condition"],
                "turn_id": row["turn_id"],
                "failure_reasons": row["failure_reasons"],
            }
            for row in failures
        ],
        "comparison_quality_ready": not failures and all(checks.values()),
        "real_model_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "annotations_accessed": 0,
        "claim_boundary": (
            "Immutable source/output surface audit only. A failure blocks comparative quality "
            "readiness; it does not grade pragmatics, choose a winner, or authorize regeneration."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    payload = build_audit(args.input)
    write_new_json(output, payload)
    return 0 if all(payload["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

