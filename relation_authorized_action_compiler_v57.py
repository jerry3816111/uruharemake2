#!/usr/bin/env python3
"""Compile frozen V56 event states into grounded, provenance-bearing action plans."""

from action_candidate_perception_v47 import load_v47_anchor_ontology
from action_ontology_grounding_v38 import find_action_anchors
from action_selective_deliberation_v37 import (
    FRAME_TO_CALL,
    _call_key,
    _overlaps,
    _substring_spans,
)
from relation_bound_event_graph_v56 import (
    COORDINATE_CONNECTOR_RE,
    _request_force,
    _terminal_assertion,
)


PRIMARY_RELATIONS = {"local_directive", "shared_directive"}
BLOCKING_RELATIONS = {
    "execution_prohibition",
    "conditional_governance",
    "local_pending_scope",
    "local_hypothetical_scope",
    "cross_event_replacement",
}


def _target_id(frame):
    return f"{frame.get('domain')}.{frame.get('value')}"


def _relation_types(state):
    graph = (state or {}).get("v56_relation_graph") or {}
    return set(graph.get("relation_types") or [])


def _focus_clauses(state):
    rows = []
    seen = set()
    event_map = (state or {}).get("event_map") or {}
    for occurrence in event_map.get("focus_occurrences") or []:
        key = (
            occurrence.get("sentence_index"),
            occurrence.get("clause_index"),
            occurrence.get("clause_text"),
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "sentence_index": occurrence.get("sentence_index"),
                "clause_index": occurrence.get("clause_index"),
                "clause_text": str(occurrence.get("clause_text") or ""),
                "sentence_text": str(occurrence.get("sentence_text") or ""),
            }
        )
    return rows


def _authorization(target_id, state):
    if not state:
        return None, ["missing_v56_state"]
    if not state.get("resolved"):
        return None, ["unresolved_model_only_request"]
    if state.get("commitment") != "requested":
        return None, ["v56_state_not_requested"]

    relation_types = _relation_types(state)
    blockers = sorted(relation_types & BLOCKING_RELATIONS)
    if blockers:
        return None, [f"blocking_relation:{name}" for name in blockers]

    directives = sorted(relation_types & PRIMARY_RELATIONS)
    if directives:
        return {
            "type": "typed_event_relation",
            "relation_types": directives,
            "resolution_rule": state.get("resolution_rule"),
        }, []

    rule = state.get("resolution_rule")
    if rule == "positive_idle_request" and target_id == "motion.idle":
        return {
            "type": "positive_idle_state",
            "relation_types": [],
            "resolution_rule": rule,
        }, []

    if rule == "explicit_request_force":
        for row in _focus_clauses(state):
            clause = row["clause_text"].strip()
            sentence = row["sentence_text"].strip()
            if _request_force(clause):
                return {
                    "type": "legacy_local_request_force",
                    "relation_types": [],
                    "resolution_rule": rule,
                    "clause_index": row["clause_index"],
                }, []
            coordinated = (
                COORDINATE_CONNECTOR_RE.search(clause)
                and _request_force(sentence)
                and not _terminal_assertion(clause)
            )
            if coordinated:
                return {
                    "type": "legacy_coordination_bridge",
                    "relation_types": [],
                    "resolution_rule": rule,
                    "clause_index": row["clause_index"],
                }, []
    return None, ["requested_state_lacks_event_authorization"]


def _ground_frame(user_input, frame, ontology):
    evidence_spans = _substring_spans(
        str(user_input or ""), str(frame.get("evidence") or "")
    )
    anchors = find_action_anchors(
        user_input, frame.get("domain"), frame.get("value"), ontology
    )
    overlapping = [
        anchor
        for anchor in anchors
        if any(
            _overlaps((anchor["start"], anchor["end"]), span)
            for span in evidence_spans
        )
    ]
    return {
        "all_target_anchors": anchors,
        "evidence_spans": [
            {"start": start, "end": end} for start, end in evidence_spans
        ],
        "evidence_overlapping_anchors": overlapping,
    }


def compile_relation_authorized_v57(
    user_input,
    parsed,
    states_by_target,
    ontology=None,
):
    """Compile requested frames without reinterpreting their semantic commitment."""

    ontology = ontology or load_v47_anchor_ontology()
    parsed = parsed or {}
    frames = parsed.get("frames") or []
    if not parsed.get("parse_success"):
        return {
            "accepted_calls": [],
            "accepted_frames": [],
            "execution_plan": [],
            "blocked_frames": [
                {"frame": frame, "reasons": ["fatal_frame_parse_error"]}
                for frame in frames
            ],
            "same_domain_sequences": [],
            "authorization_provenance_coverage": 1.0,
            "ungrounded_execution_count": 0,
            "unresolved_model_only_execution_count": 0,
            "commitment_mutation_count": 0,
            "fail_closed": True,
        }

    accepted = []
    blocked_frames = []
    seen_calls = set()
    for source_index, frame in enumerate(frames):
        target_id = _target_id(frame)
        reasons = []
        mapping = FRAME_TO_CALL.get((frame.get("domain"), frame.get("value")))
        if frame.get("commitment") != "requested":
            reasons.append("frame_not_requested")
        if mapping is None or frame.get("value") == "unsupported":
            reasons.append("frame_not_allowlisted")
        if not frame.get("evidence_valid"):
            reasons.append("frame_lacks_exact_evidence")

        state = states_by_target.get(target_id)
        authorization, authorization_errors = _authorization(target_id, state)
        if frame.get("commitment") == "requested":
            reasons.extend(authorization_errors)

        grounding = None
        if mapping is not None and frame.get("commitment") == "requested":
            grounding = _ground_frame(user_input, frame, ontology)
            if not grounding["evidence_spans"]:
                reasons.append("frame_evidence_not_exact_substring")
            if not grounding["evidence_overlapping_anchors"]:
                reasons.append("target_not_grounded_in_evidence")

        call_key = _call_key(mapping) if mapping is not None else None
        if call_key in seen_calls:
            reasons.append("duplicate_compiled_call")
        if reasons:
            blocked_frames.append(
                {
                    "target_id": target_id,
                    "frame": frame,
                    "reasons": list(dict.fromkeys(reasons)),
                    "authorization": authorization,
                    "grounding": grounding,
                }
            )
            continue

        seen_calls.add(call_key)
        matched_anchor = grounding["evidence_overlapping_anchors"][0]
        accepted.append(
            {
                "source_index": source_index,
                "target_id": target_id,
                "frame": {**frame, "matched_anchor": matched_anchor},
                "call": mapping,
                "authorization": authorization,
                "matched_anchor": matched_anchor,
            }
        )

    accepted.sort(
        key=lambda row: (
            row["matched_anchor"]["start"],
            row["matched_anchor"]["end"],
            row["source_index"],
        )
    )
    domain_rows = {}
    for row in accepted:
        domain_rows.setdefault(row["frame"]["domain"], []).append(row)
    same_domain_sequences = [
        {
            "domain": domain,
            "target_ids": [row["target_id"] for row in rows],
            "order_rule": "grounded_mention_order",
        }
        for domain, rows in sorted(domain_rows.items())
        if len({row["frame"]["value"] for row in rows}) > 1
    ]
    execution_plan = [
        {
            "step": index,
            "target_id": row["target_id"],
            "call": row["call"],
            "authorization": row["authorization"],
            "matched_anchor": row["matched_anchor"],
        }
        for index, row in enumerate(accepted, start=1)
    ]
    accepted_frames = [row["frame"] for row in accepted]
    authorization_count = sum(
        bool(row.get("authorization")) for row in execution_plan
    )
    unresolved_model_only_execution_count = sum(
        not (states_by_target.get(row["target_id"]) or {}).get("resolved")
        for row in accepted
    )
    return {
        "accepted_calls": [row["call"] for row in accepted],
        "accepted_frames": accepted_frames,
        "execution_plan": execution_plan,
        "blocked_frames": blocked_frames,
        "same_domain_sequences": same_domain_sequences,
        "authorization_provenance_coverage": (
            authorization_count / len(execution_plan) if execution_plan else 1.0
        ),
        "ungrounded_execution_count": sum(
            not frame.get("matched_anchor") for frame in accepted_frames
        ),
        "unresolved_model_only_execution_count": (
            unresolved_model_only_execution_count
        ),
        "commitment_mutation_count": 0,
        "fail_closed": False,
    }
