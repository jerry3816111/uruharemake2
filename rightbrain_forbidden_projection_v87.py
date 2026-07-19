"""Deterministic V87 candidate-gate regression utilities."""

from __future__ import annotations

import copy
import hashlib
import json

import diagnose_rightbrain_memory_surface_v86 as v86_diagnosis
import planner_supervision_v76 as v76
import rightbrain_memory_surface_v86 as v86


C0 = "c0_projection_disabled"
T1 = "t1_projection_enabled"
CONDITIONS = (C0, T1)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sources(contract, root):
    checks = {}
    for section in ("private_sources", "prior_evidence"):
        for name, artifact in contract[section].items():
            path = root / artifact["path"]
            checks[f"{section}.{name}"] = path.is_file() and file_sha256(path) == artifact["sha256"]
    if not all(checks.values()):
        raise ValueError(f"V87 source drift: {checks}")
    return checks


def bind_cases(packets, raw_rows, candidates, contract):
    if len(packets) != int(contract["scope"]["case_count"]):
        raise ValueError("V87 packet count mismatch")
    treatment_rows = [row for row in raw_rows if row.get("condition") == v86.T2]
    if len(treatment_rows) != int(contract["scope"]["case_count"]):
        raise ValueError("V87 frozen treatment-row count mismatch")
    packet_by_id = {packet["candidate_id"]: packet for packet in packets}
    candidate_by_id = {candidate["id"]: candidate for candidate in candidates}
    if len(packet_by_id) != len(packets):
        raise ValueError("V87 packet identities are not unique")
    bound = []
    for row in treatment_rows:
        candidate_id = row["candidate_id"]
        packet = packet_by_id.get(candidate_id)
        candidate = candidate_by_id.get(candidate_id)
        if packet is None or candidate is None:
            raise ValueError("V87 source identity is missing")
        if row.get("packet_sha256") != packet.get("packet_sha256"):
            raise ValueError("V87 row-to-packet binding mismatch")
        logic = candidate.get("target_plan") or {}
        if candidate.get("target_plan_sha256") != v76.canonical_sha256(logic):
            raise ValueError("V87 target plan hash mismatch")
        bound.append((packet, row, candidate))
    return bound


def _evaluate_condition(right_brain, packet, row, candidate, enabled):
    logic = copy.deepcopy(candidate["target_plan"])
    reply = str(row.get("raw_reply") or "")
    reply_sha256 = hashlib.sha256(reply.encode("utf-8")).hexdigest()
    previous = right_brain.forbidden_conflict_projection_enabled
    right_brain.forbidden_conflict_projection_enabled = enabled
    try:
        reasons = right_brain._model_candidate_rejection_reasons(
            reply,
            logic,
            int(packet["outcome_contract"]["maximum_reply_chars"]),
        )
        effective = right_brain._model_surface_forbidden_markers(logic)
        trace = copy.deepcopy(logic.get("model_surface_forbidden_projection") or {})
    finally:
        right_brain.forbidden_conflict_projection_enabled = previous
    return {
        "accepted": not reasons,
        "rejection_reasons": list(reasons),
        "reply_sha256": reply_sha256,
        "original_forbidden_count": len(list(dict.fromkeys(candidate["target_plan"].get("must_avoid") or []))),
        "effective_forbidden_count": len(effective),
        "effective_forbidden_sha256": v76.canonical_sha256(effective),
        "dropped_marker_count": int(trace.get("dropped_stale_recent_opening_count") or 0),
    }


def evaluate_pair(right_brain, packet, row, candidate):
    control = _evaluate_condition(right_brain, packet, row, candidate, False)
    treatment = _evaluate_condition(right_brain, packet, row, candidate, True)
    diagnosed_conflicts = v86_diagnosis.stale_opening_conflicts(packet, candidate)
    original_forbidden = list(dict.fromkeys(candidate["target_plan"].get("must_avoid") or []))
    expected_effective = [marker for marker in original_forbidden if marker not in set(diagnosed_conflicts)]
    removed_reasons = sorted(set(control["rejection_reasons"]) - set(treatment["rejection_reasons"]))
    added_reasons = sorted(set(treatment["rejection_reasons"]) - set(control["rejection_reasons"]))
    projection_scope_matches = (
        treatment["dropped_marker_count"] == len(diagnosed_conflicts)
        and treatment["effective_forbidden_sha256"] == v76.canonical_sha256(expected_effective)
        and control["effective_forbidden_sha256"] == v76.canonical_sha256(original_forbidden)
    )
    conflict_only_recovered = (
        control["rejection_reasons"] == ["must_avoid_violation"]
        and treatment["accepted"]
        and bool(diagnosed_conflicts)
    )
    return {
        "schema": "uruha_rightbrain_forbidden_projection_pair_v87",
        "candidate_id": packet["candidate_id"],
        "packet_sha256": packet["packet_sha256"],
        "source_reply_sha256": hashlib.sha256(str(row.get("raw_reply") or "").encode("utf-8")).hexdigest(),
        "conditions": {C0: control, T1: treatment},
        "diagnosed_conflict_count": len(diagnosed_conflicts),
        "projection_scope_matches": projection_scope_matches,
        "removed_reasons": removed_reasons,
        "added_reasons": added_reasons,
        "conflict_only_recovered": conflict_only_recovered,
        "nonconflict_decision_identical": bool(diagnosed_conflicts) or control["accepted"] == treatment["accepted"],
        "reply_hash_matches": control["reply_sha256"] == treatment["reply_sha256"],
        "production_memory_write_count": 0,
        "physical_vrm_action_count": 0,
    }


def evaluate_all(right_brain, packets, raw_rows, candidates, contract):
    bound = bind_cases(packets, raw_rows, candidates, contract)
    rows = [evaluate_pair(right_brain, packet, row, candidate) for packet, row, candidate in bound]
    if right_brain.forbidden_conflict_projection_enabled:
        raise ValueError("V87 evaluation did not restore runtime flag")
    return rows
