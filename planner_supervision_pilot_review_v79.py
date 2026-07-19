"""Select a small, coverage-aware pilot for strict human planner review."""

from __future__ import annotations

import hashlib
from collections import Counter

import planner_supervision_session_review_v78 as v78
import planner_supervision_v76 as v76


def _selection_rank(candidate_id, seed):
    payload = f"{seed}\0{candidate_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate_binding(candidate):
    return {
        "id": candidate.get("id"),
        "source_sha256": (candidate.get("provenance") or {}).get("source_sha256"),
        "target_plan_sha256": candidate.get("target_plan_sha256"),
    }


def _candidate_is_bound(candidate):
    source_record = candidate.get("source_record")
    target_plan = candidate.get("target_plan")
    provenance = candidate.get("provenance") or {}
    checks = candidate.get("collection_checks") or {}
    return (
        isinstance(source_record, dict)
        and isinstance(target_plan, dict)
        and provenance.get("source_sha256") == v76.canonical_sha256(source_record)
        and candidate.get("target_plan_sha256") == v76.canonical_sha256(target_plan)
        and checks.get("session_quarantine_applied") is True
        and checks.get("evaluation_contaminated_session") is False
    )


def _distribution_distance(counts, total, population_counts, population_total):
    families = set(population_counts) | set(counts)
    return sum(
        abs((counts.get(family, 0) / total) - (population_counts.get(family, 0) / population_total))
        for family in families
    )


def select_pilot(candidates, manifest_rows, *, budget, seed):
    if budget <= 0:
        raise ValueError("pilot budget must be positive")
    candidates = list(candidates)
    current_units = {
        unit["source_session_id"]: unit for unit in v78.build_session_review_units(candidates)
    }
    manifest_by_session = v76._latest_by_key(manifest_rows, "session_id")
    certified_sessions = set()
    for session_id, row in manifest_by_session.items():
        if not v76._session_is_certified(session_id, manifest_rows):
            continue
        unit = current_units.get(session_id)
        if not unit:
            raise ValueError("certified session is absent from the current candidate queue")
        if (
            row.get("decision") != "certify_nonbenchmark"
            or row.get("candidate_set_sha256") != unit["candidate_set_sha256"]
            or row.get("session_summary_sha256") != unit["session_summary_sha256"]
        ):
            raise ValueError("certified session manifest does not bind the current candidate set")
        certified_sessions.add(session_id)

    eligible = []
    for candidate in candidates:
        if not _candidate_is_bound(candidate):
            raise ValueError("candidate queue contains an unbound candidate")
        session_id = str(candidate.get("source_session_id") or "")
        family = str(candidate.get("scenario_family") or "")
        if not session_id or not family or not candidate.get("id"):
            raise ValueError("candidate is missing pilot selection fields")
        if session_id in certified_sessions:
            eligible.append(candidate)

    available_families = {candidate["scenario_family"] for candidate in eligible}
    available_sessions = {candidate["source_session_id"] for candidate in eligible}
    if budget < max(len(available_families), len(available_sessions)):
        raise ValueError("pilot budget cannot cover all families and sessions")

    ranked = sorted(eligible, key=lambda row: _selection_rank(row["id"], seed))
    selected = []
    selected_ids = set()
    covered_families = set()
    covered_sessions = set()

    while (covered_families != available_families or covered_sessions != available_sessions) and len(selected) < budget:
        choices = [row for row in ranked if row["id"] not in selected_ids]
        if not choices:
            break
        row = min(
            choices,
            key=lambda item: (
                -int(item["scenario_family"] not in covered_families)
                - int(item["source_session_id"] not in covered_sessions),
                _selection_rank(item["id"], seed),
            ),
        )
        selected.append((row, "coverage"))
        selected_ids.add(row["id"])
        covered_families.add(row["scenario_family"])
        covered_sessions.add(row["source_session_id"])

    if covered_families != available_families or covered_sessions != available_sessions:
        raise ValueError("pilot selection failed required coverage")

    population_counts = Counter(row["scenario_family"] for row in eligible)
    selected_counts = Counter(row["scenario_family"] for row, _reason in selected)
    while len(selected) < min(budget, len(eligible)):
        choices = [row for row in ranked if row["id"] not in selected_ids]
        if not choices:
            break

        def fill_key(item):
            proposed = selected_counts.copy()
            proposed[item["scenario_family"]] += 1
            return (
                _distribution_distance(proposed, len(selected) + 1, population_counts, len(eligible)),
                _selection_rank(item["id"], seed),
            )

        row = min(choices, key=fill_key)
        selected.append((row, "distribution_fill"))
        selected_ids.add(row["id"])
        selected_counts[row["scenario_family"]] += 1

    units = []
    for index, (candidate, reason) in enumerate(selected, start=1):
        binding = _candidate_binding(candidate)
        session_binding_sha256 = v76.canonical_sha256(
            {"session_id": candidate["source_session_id"]}
        )
        units.append(
            {
                "schema": "uruha_planner_supervision_pilot_unit_v79",
                "pilot_index": index,
                "candidate_id": candidate["id"],
                "candidate_binding": binding,
                "candidate_binding_sha256": v76.canonical_sha256(binding),
                "session_binding_sha256": session_binding_sha256,
                "scenario_family": candidate["scenario_family"],
                "selection_reason": reason,
                "status": "pending_strict_human_plan_review",
            }
        )
    return eligible, units


def pilot_status(units, review_rows, strict_rows):
    selected_ids = {unit["candidate_id"] for unit in units}
    reviews = {
        str(row.get("candidate_id")): row
        for row in review_rows
        if str(row.get("candidate_id") or "") in selected_ids
    }
    strict_ids = {str(row.get("id")) for row in strict_rows}
    accepted = sum(
        1
        for candidate_id, review in reviews.items()
        if review.get("decision") == "accept" and candidate_id in strict_ids
    )
    rejected = sum(1 for review in reviews.values() if review.get("decision") == "reject")
    reviewed = len(reviews)
    return {
        "reviewed_count": reviewed,
        "accepted_count": accepted,
        "rejected_count": rejected,
        "pending_count": len(units) - reviewed,
        "training_rows_created": accepted,
    }


def build_aggregate_report(candidates, eligible, units, review_rows, strict_rows, contract):
    selected_families = Counter(unit["scenario_family"] for unit in units)
    eligible_families = Counter(row["scenario_family"] for row in eligible)
    selected_session_hashes = {unit["session_binding_sha256"] for unit in units}
    eligible_session_hashes = {
        v76.canonical_sha256({"session_id": row["source_session_id"]}) for row in eligible
    }
    status = pilot_status(units, review_rows, strict_rows)
    pilot_bindings = [
        {
            "candidate_binding_sha256": unit["candidate_binding_sha256"],
            "session_binding_sha256": unit["session_binding_sha256"],
            "scenario_family": unit["scenario_family"],
        }
        for unit in units
    ]
    return {
        "schema": "uruha_planner_supervision_pilot_review_report_v79",
        "contract_sha256": v76.canonical_sha256(contract),
        "source_candidate_count": len(candidates),
        "certified_candidate_count": len(eligible),
        "pilot_candidate_count": len(units),
        "available_scenario_family_count": len(eligible_families),
        "covered_scenario_family_count": len(selected_families),
        "available_session_count": len(eligible_session_hashes),
        "covered_session_count": len(selected_session_hashes),
        "available_family_counts": dict(sorted(eligible_families.items())),
        "pilot_family_counts": dict(sorted(selected_families.items())),
        "pilot_set_sha256": v76.canonical_sha256(pilot_bindings),
        "initial_reviewed_count": status["reviewed_count"],
        "initial_training_rows_created": status["training_rows_created"],
        **status,
        "additional_model_calls": 0,
        "raw_dialogue_committed": False,
        "raw_session_ids_committed": False,
        "evidence_boundary": contract["evidence_boundary"],
    }
