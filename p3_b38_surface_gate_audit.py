#!/usr/bin/env python3
"""P3-B39 immutable quotation-aware audit of the failed B38 surface gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from p3_product_comparison import canonical_sha256, write_new_json
from p3_strict_visible_surface_v2 import strict_japanese_visible_surface_contract


EXPECTED_RESULT_SHA256 = "10236fc37c2f87acc081a74ee326a500923429f2f9a468eef04fd06355d6a0a4"
EXPECTED_SCHEMA = "uruha_p3_prospective_case02_output_lock_result_v1"
EXPECTED_CASE_ID = "p3-prospective-v2-excitement-en"


class SurfaceAuditError(ValueError):
    pass


def _text_and_digest(condition: str, row: Mapping[str, Any]) -> tuple[str, str]:
    if condition == "product_system":
        return str(row.get("visible_reply") or ""), str(row.get("visible_reply_sha256") or "")
    final = row.get("final") or {}
    return str(final.get("content") or ""), str(final.get("content_sha256") or "")


def build_audit(path: str | Path) -> dict[str, Any]:
    result_path = Path(path)
    raw = result_path.read_bytes()
    result_hash = hashlib.sha256(raw).hexdigest()
    if result_hash != EXPECTED_RESULT_SHA256:
        raise SurfaceAuditError("b38_result_hash_mismatch")
    result = json.loads(raw)
    if (
        result.get("schema") != EXPECTED_SCHEMA
        or result.get("case_id") != EXPECTED_CASE_ID
        or result.get("status") != "prospective_case02_output_lock_failed_retained"
    ):
        raise SurfaceAuditError("b38_result_identity_mismatch")

    rows: list[dict[str, Any]] = []
    for condition, key in (
        ("product_system", "product_turns"),
        ("full_history_direct", "direct_turns"),
    ):
        condition_rows = result.get(key)
        if not isinstance(condition_rows, list) or len(condition_rows) != 4:
            raise SurfaceAuditError("b38_turn_count_mismatch")
        for row in condition_rows:
            text, digest = _text_and_digest(condition, row)
            if canonical_sha256(text) != digest:
                raise SurfaceAuditError("b38_visible_output_hash_mismatch")
            original = dict(row.get("surface_contract") or {})
            revised = strict_japanese_visible_surface_contract(text)
            failures = [name for name, passed in revised.items() if not passed]
            rows.append({
                "condition": condition,
                "turn_id": row.get("turn_id"),
                "visible_reply_sha256": digest,
                "original_surface_pass": all(original.values()),
                "original_failure_reasons": [name for name, passed in original.items() if not passed],
                "quotation_aware_surface": revised,
                "quotation_aware_surface_pass": not failures,
                "quotation_aware_failure_reasons": failures,
            })

    original_failures = [row for row in rows if not row["original_surface_pass"]]
    revised_failures = [row for row in rows if not row["quotation_aware_surface_pass"]]
    checks = {
        "b38_result_hash_matches": True,
        "eight_outputs_hash_verified": len(rows) == 8,
        "original_single_quote_failure_retained": (
            len(original_failures) == 1
            and original_failures[0]["condition"] == "full_history_direct"
            and original_failures[0]["turn_id"] == "p3-prospective-v2-02-u3"
            and original_failures[0]["original_failure_reasons"]
            == ["no_quote_or_translation_wrapper"]
        ),
        "quotation_aware_audit_complete": len(rows) == 8,
        "annotations_remained_closed": result.get("annotations_accessed") == 0,
        "generation_not_repeated": True,
    }
    return {
        "schema": "uruha_p3_b38_quotation_aware_surface_audit_v1",
        "phase": "P3-B39",
        "status": "b38_quote_gate_false_positive_retained" if not revised_failures
        else "b38_additional_surface_failures_retained",
        "input": {"path": str(result_path), "sha256": result_hash, "case_id": EXPECTED_CASE_ID},
        "checks": checks,
        "rows": rows,
        "original_surface_failure_count": len(original_failures),
        "quotation_aware_pass_count": len(rows) - len(revised_failures),
        "quotation_aware_failure_count": len(revised_failures),
        "original_runner_status_preserved": result["status"],
        "comparison_quality_ready": False,
        "real_model_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "annotations_accessed": 0,
        "claim_boundary": (
            "Post-lock surface audit only. It may identify a validator false positive but cannot "
            "rewrite the preregistered failed run, grade pragmatics, choose a winner, or authorize regeneration."
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
