"""V87.3 replay with a scope oracle aligned to production normalization."""

from __future__ import annotations

import diagnose_rightbrain_memory_surface_v86 as v86_diagnosis
import planner_supervision_v76 as v76
import rightbrain_forbidden_projection_v87 as v87
import rightbrain_forbidden_projection_v87_2 as v872


def normalized_forbidden(values):
    return list(
        dict.fromkeys(
            str(value or "").strip()
            for value in values or []
            if str(value or "").strip()
        )
    )


def evaluate_all(right_brain, packets, raw_rows, candidates, contract):
    bound = v87.bind_cases(packets, raw_rows, candidates, contract)
    rows = v872.evaluate_all(right_brain, packets, raw_rows, candidates, contract)
    for result, (packet, _row, candidate) in zip(rows, bound):
        original = normalized_forbidden(candidate["target_plan"].get("must_avoid") or [])
        diagnosed = {
            str(marker or "").strip()
            for marker in v86_diagnosis.stale_opening_conflicts(packet, candidate)
            if str(marker or "").strip()
        }
        expected_effective = [marker for marker in original if marker not in diagnosed]
        control = result["conditions"][v87.C0]
        treatment = result["conditions"][v87.T1]
        result["projection_scope_matches"] = (
            control["effective_forbidden_sha256"] == v76.canonical_sha256(original)
            and treatment["effective_forbidden_sha256"] == v76.canonical_sha256(expected_effective)
            and treatment["dropped_marker_count"] == len(original) - len(expected_effective)
        )
        result["normalized_scope_oracle_applied"] = True
    return rows
