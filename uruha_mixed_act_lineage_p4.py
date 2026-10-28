"""Opt-in, raw-free producer lineage for a bounded mixed dialogue act.

This is instrumentation, not an action arbiter.  A linked producer chain never
grants surface authority or certifies that either requested action was done.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib
from threading import Lock
import uuid

import uruha_adaptive_person_model as adaptive
import uruha_current_turn_source_role_p4 as source_role
import uruha_mixed_past_place_source_authority_p4 as past_place
from uruha_local_fact_answer_authority_p4 import _protected_or_other_route


LABEL = "mixed_act_lineage_p4"
SCHEMA = "uruha_mixed_act_lineage_p4_v1"
EVENT_KEY = "_mixed_act_lineage_event_p4"
PRODUCER_KEY = "mixed_act_producer_lineage_p4"
EVENT_NODE = "mixed_act_lineage_event_p4"
_ACTIVE = ContextVar("uruha_mixed_act_lineage_active_p4", default=None)
_REGISTRY: dict[str, dict] = {}
_REGISTRY_LOCK = Lock()
_MAX_REGISTERED_EVENTS = 4096
_INSTALLED = False
_ORIGINAL_INGEST = None
_ORIGINAL_TICK = None
_ORIGINAL_EMIT = None
_ORIGINAL_ROUTED_M31 = None
_ORIGINAL_PLAIN_M31 = None
_ORIGINAL_M32 = None


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _id() -> str:
    return uuid.uuid4().hex


def _actions(raw: str, role: dict, event_id: str) -> list[dict]:
    if role.get("act") != "mixed_request" or role.get("quote_role") != "rewrite_object":
        return []
    if past_place.classify_mixed_past_place_query_p4(raw).get("eligible") is not True:
        return []
    quote_span = role.get("quote_content_span_raw")
    outside_spans = role.get("outside_spans_raw")
    if not (
        isinstance(quote_span, list) and len(quote_span) == 2
        and isinstance(outside_spans, list) and len(outside_spans) == 2
    ):
        return []
    return [
        {
            "action_id": f"{event_id}:quoted_rewrite",
            "type": "quoted_rewrite",
            "raw_spans": [deepcopy(quote_span)],
            "span_scope": "quoted_object_not_instruction_clause",
            "coverage_status": "unverified",
        },
        {
            "action_id": f"{event_id}:past_user_place_recall",
            "type": "past_user_place_recall",
            "raw_spans": deepcopy(outside_spans),
            "span_scope": "outside_quote_not_exact_recall_clause",
            "coverage_status": "unverified",
        },
    ]


def _new_event(raw: str, cycle_index: int) -> dict:
    role = source_role.classify_current_turn_source_role_p4(raw, cycle_index=cycle_index)
    event_id = _id()
    return {
        "schema": SCHEMA,
        "event_id": event_id,
        "raw_input_sha256": _sha(raw),
        "cycle_index": cycle_index,
        "source_role_act": role.get("act"),
        "source_role_quote_sha256": role.get("quote_raw_sha256"),
        "actions": _actions(raw, role, event_id),
        "raw_dialogue_persisted": False,
        "model_calls_added": 0,
        "authority_transfer_permitted": False,
    }


def ingest_event_with_mixed_act_lineage_p4(self, user_input, input_context=None):
    event = _ORIGINAL_INGEST(self, user_input, input_context=input_context)
    if not isinstance(event, dict):
        return event
    raw = str(event.get("user_input") or "")
    cycle = getattr(getattr(self, "runtime", None), "cycle_index", None)
    if not isinstance(cycle, int) or cycle < 0:
        return event
    certificate = _new_event(raw, cycle)
    with _REGISTRY_LOCK:
        while certificate["event_id"] in _REGISTRY:
            certificate = _new_event(raw, cycle)
        _REGISTRY[certificate["event_id"]] = {
            "owner_id": id(self), "event_object_id": id(event),
            "raw_input_sha256": certificate["raw_input_sha256"],
            "cycle_index": cycle, "consumed": False,
        }
        while len(_REGISTRY) > _MAX_REGISTERED_EVENTS:
            _REGISTRY.pop(next(iter(_REGISTRY)))
    event[EVENT_KEY] = deepcopy(certificate)
    if callable(getattr(self, "_push_blackboard", None)):
        self._push_blackboard("ingest", EVENT_NODE, deepcopy(certificate), salience=0.97)
    return event


def _registered_context(self, event: dict) -> tuple[dict | None, str]:
    if not isinstance(event, dict):
        return None, "missing_event"
    certificate = event.get(EVENT_KEY)
    if not isinstance(certificate, dict) or certificate.get("schema") != SCHEMA:
        return None, "missing_event_certificate"
    event_id = certificate.get("event_id")
    raw = str(event.get("user_input") or "")
    with _REGISTRY_LOCK:
        record = _REGISTRY.get(event_id) if isinstance(event_id, str) else None
        if not record:
            return None, "unregistered_or_evicted_event"
        if record["consumed"]:
            return None, "replayed_event"
        if (
            record["owner_id"] != id(self)
            or record["event_object_id"] != id(event)
            or record["raw_input_sha256"] != _sha(raw)
            or certificate.get("raw_input_sha256") != _sha(raw)
            or record["cycle_index"] != certificate.get("cycle_index")
            or record["cycle_index"] != getattr(getattr(self, "runtime", None), "cycle_index", None)
            or certificate.get("raw_dialogue_persisted") is not False
            or certificate.get("authority_transfer_permitted") is not False
            or certificate.get("model_calls_added") != 0
        ):
            return None, "event_registration_mismatch"
        role = source_role.classify_current_turn_source_role_p4(
            raw, cycle_index=record["cycle_index"]
        )
        if (
            certificate.get("source_role_act") != role.get("act")
            or certificate.get("source_role_quote_sha256") != role.get("quote_raw_sha256")
            or certificate.get("actions") != _actions(raw, role, event_id)
        ):
            return None, "event_action_or_span_mismatch"
        record["consumed"] = True
    return {
        "certificate": deepcopy(certificate),
        "m31_ids": [], "m32_ids": [],
        "m31_output_object_ids": [],
        "m31_attempts": 0, "m32_attempts": 0,
    }, "registered"


def _stamp_m31(raw: str, plan, authorization):
    context = _ACTIVE.get()
    if not isinstance(context, dict):
        return plan, authorization
    context["m31_attempts"] += 1
    if not isinstance(authorization, dict):
        return plan, authorization
    event = context["certificate"]
    proposal_id = f"{event['event_id']}:m31:{_id()}"
    context["m31_ids"].append(proposal_id)
    stamp = {
        "schema": SCHEMA, "producer": "m31", "proposal_id": proposal_id,
        "parent_event_id": event["event_id"],
        "raw_input_sha256": _sha(raw),
        "cycle_index": event["cycle_index"],
        "status_at_return": authorization.get("status"),
        "action_coverage_status": "unverified",
        "raw_dialogue_persisted": False,
        "authority_transfer_permitted": False,
    }
    updated = deepcopy(authorization)
    updated[PRODUCER_KEY] = stamp
    context["m31_output_object_ids"].append(id(updated))
    if isinstance(plan, dict):
        plan = deepcopy(plan)
        nested = plan.get("semantic_authorization_m31")
        if isinstance(nested, dict):
            nested[PRODUCER_KEY] = deepcopy(stamp)
    return plan, updated


def authorize_routed_m31_with_mixed_act_lineage_p4(self, user_input, projection, route_context):
    return _stamp_m31(
        user_input,
        *_ORIGINAL_ROUTED_M31(self, user_input, projection, route_context),
    )


def authorize_plain_m31_with_mixed_act_lineage_p4(self, user_input, projection):
    return _stamp_m31(
        user_input,
        *_ORIGINAL_PLAIN_M31(self, user_input, projection),
    )


def build_m32_with_mixed_act_lineage_p4(authorization):
    plan, contract = _ORIGINAL_M32(authorization)
    context = _ACTIVE.get()
    if not isinstance(context, dict):
        return plan, contract
    context["m32_attempts"] += 1
    if not isinstance(contract, dict):
        return plan, contract
    event = context["certificate"]
    parent = (authorization or {}).get(PRODUCER_KEY) if isinstance(authorization, dict) else None
    proposal_id = f"{event['event_id']}:m32:{_id()}"
    context["m32_ids"].append(proposal_id)
    stamp = {
        "schema": SCHEMA, "producer": "m32", "proposal_id": proposal_id,
        "parent_m31_id": parent.get("proposal_id") if isinstance(parent, dict) else None,
        "parent_m31_direct_argument": (
            len(context["m31_output_object_ids"]) == 1
            and id(authorization) == context["m31_output_object_ids"][0]
        ),
        "parent_event_id": event["event_id"],
        "raw_input_sha256": event["raw_input_sha256"],
        "cycle_index": event["cycle_index"],
        "parent_m31_status_at_build": authorization.get("status") if isinstance(authorization, dict) else None,
        "status_at_return": contract.get("status"),
        "action_coverage_status": "unverified",
        "raw_dialogue_persisted": False,
        "authority_transfer_permitted": False,
    }
    updated = deepcopy(contract)
    updated[PRODUCER_KEY] = stamp
    if isinstance(plan, dict):
        plan = deepcopy(plan)
        nested = plan.get("semantic_commit_repair_m32")
        if isinstance(nested, dict):
            nested[PRODUCER_KEY] = deepcopy(stamp)
    return plan, updated


def verify_mixed_act_lineage_p4(
    event, logic, *, registered_context=None, registration_reason="unregistered_event",
    route_info=None, right_brain=None,
) -> dict:
    """Audit producer receipts; never infer completion from their answer text."""
    source = event if isinstance(event, dict) else {}
    certificate = source.get(EVENT_KEY) if isinstance(source.get(EVENT_KEY), dict) else {}
    plan = logic if isinstance(logic, dict) else {}
    m31 = plan.get("semantic_authorization_m31")
    m32 = plan.get("semantic_commit_repair_m32")
    m33 = plan.get("source_anchored_semantic_commit_m33")
    m31 = m31 if isinstance(m31, dict) else {}
    m32 = m32 if isinstance(m32, dict) else {}
    m33 = m33 if isinstance(m33, dict) else {}
    m31_stamp = m31.get(PRODUCER_KEY)
    m32_stamp = m32.get(PRODUCER_KEY)
    m31_stamp = m31_stamp if isinstance(m31_stamp, dict) else {}
    m32_stamp = m32_stamp if isinstance(m32_stamp, dict) else {}
    context = registered_context if isinstance(registered_context, dict) else None
    event_id = certificate.get("event_id")
    raw_sha = _sha(source.get("user_input") or "")
    actions = deepcopy(certificate.get("actions") or [])
    blockers = []
    if certificate.get("source_role_act") == "protected":
        blockers.append("protected_source_role")
    if _protected_or_other_route(plan, route_info or {}, right_brain):
        blockers.append("protected_or_other_route")
    if plan.get("memory_recall_contract") or plan.get("profile_grounding_shadow"):
        blockers.append("factual_memory_contract")
    if m33.get("surface_authority") is True:
        blockers.append("m33_authoritative")
    reason = registration_reason
    status = "rejected"
    edges = []
    if context is not None:
        expected = context.get("certificate") or {}
        if certificate != expected or certificate.get("raw_input_sha256") != raw_sha:
            reason = "event_certificate_or_digest_mismatch"
        elif context["m31_attempts"] == 0 and context["m32_attempts"] == 0:
            if (m31_stamp or m32_stamp or m31.get("surface_authority") is True
                    or m32.get("surface_authority") is True):
                reason = "unproduced_authoritative_or_stamped_contract"
            else:
                status, reason = "not_produced", "m31_m32_producers_not_run"
        elif context["m31_attempts"] != 1 or context["m32_attempts"] != 1:
            reason = "producer_attempt_count_not_one_each"
        elif len(context["m31_ids"]) != 1 or len(context["m32_ids"]) != 1:
            reason = "producer_receipt_count_not_one_each"
        else:
            m31_id, m32_id = context["m31_ids"][0], context["m32_ids"][0]
            ids = [event_id, m31_id, m32_id] + [a.get("action_id") for a in actions]
            common = {"schema": SCHEMA, "parent_event_id": event_id,
                      "raw_input_sha256": raw_sha, "cycle_index": certificate.get("cycle_index"),
                      "action_coverage_status": "unverified",
                      "authority_transfer_permitted": False}
            if len(ids) != len(set(ids)) or any(not isinstance(value, str) or not value for value in ids):
                reason = "duplicate_or_missing_id"
            elif (
                any(m31_stamp.get(key) != value for key, value in common.items())
                or any(m32_stamp.get(key) != value for key, value in common.items())
                or m31_stamp.get("producer") != "m31"
                or m32_stamp.get("producer") != "m32"
                or m31.get("schema") != adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31
                or m32.get("schema") != adaptive.SEMANTIC_COMMIT_REPAIR_SCHEMA_M32
                or m31_stamp.get("proposal_id") != m31_id
                or m32_stamp.get("proposal_id") != m32_id
                or m32_stamp.get("parent_m31_id") != m31_id
                or m32_stamp.get("parent_m31_direct_argument") is not True
                or m31.get("input_digest") != raw_sha[:16]
                or m31_stamp.get("status_at_return") is None
                or m32_stamp.get("parent_m31_status_at_build") != m31_stamp.get("status_at_return")
                or (m32.get("source_m31_status") not in (None, m31_stamp.get("status_at_return")))
            ):
                reason = "producer_parent_or_digest_mismatch"
            else:
                status, reason = "linked", "producer_parent_chain_verified"
                edges = [
                    {"from_id": event_id, "to_id": m31_id, "type": "event_to_m31"},
                    {"from_id": m31_id, "to_id": m32_id, "type": "m31_to_m32"},
                ]
    return {
        "schema": SCHEMA, "status": status, "reason": reason,
        "event_id": event_id if isinstance(event_id, str) else None,
        "raw_input_sha256": raw_sha,
        "cycle_index": certificate.get("cycle_index"),
        "source_role_act": certificate.get("source_role_act"),
        "actions": actions,
        "m31": {"status": "produced" if m31_stamp else "not_produced",
                "proposal_id": m31_stamp.get("proposal_id"),
                "surface_authority_retained": m31.get("surface_authority") is True},
        "m32": {"status": "produced" if m32_stamp else "not_produced",
                "proposal_id": m32_stamp.get("proposal_id"),
                "surface_authority_retained": m32.get("surface_authority") is True},
        "m33_authoritative": m33.get("surface_authority") is True,
        "authority_blockers": blockers,
        "producer_edges": edges,
        "action_coverage_status": "unverified",
        "authority_transfer_permitted": False,
        "reply_changed_by_lineage": False,
        "raw_dialogue_persisted": False,
        "model_calls_added": 0,
        "claim_boundary": "producer parent lineage only; action coverage, reply quality and authority transfer not certified",
    }


def cognitive_tick_with_mixed_act_lineage_p4(self, event):
    context, registration_reason = _registered_context(self, event)
    token = _ACTIVE.set(context)
    try:
        tick = _ORIGINAL_TICK(self, event)
    finally:
        _ACTIVE.reset(token)
    if not isinstance(tick, dict):
        return tick
    logic = tick.get("logic")
    receipt = verify_mixed_act_lineage_p4(
        event, logic, registered_context=context,
        registration_reason=registration_reason,
        route_info=tick.get("route_info"), right_brain=getattr(self, "right_brain", None),
    )
    if isinstance(logic, dict):
        logic[LABEL] = deepcopy(receipt)
    runtime = getattr(self, "runtime", None)
    if runtime is not None and callable(getattr(self, "_push_blackboard", None)):
        self._push_blackboard("verify", LABEL, deepcopy(receipt), salience=0.98)
    return tick


def emit_response_with_mixed_act_lineage_p4(self, event, tick_result):
    result = _ORIGINAL_EMIT(self, event, tick_result)
    if not isinstance(result, dict):
        return result
    logic = result.get("logic") or {}
    receipt = logic.get(LABEL) if isinstance(logic, dict) else None
    trace = result.get("runtime_trace")
    if isinstance(receipt, dict) and isinstance(trace, dict):
        trace[LABEL] = deepcopy(receipt)
        runtime = getattr(self, "runtime", None)
        if (
            runtime is not None and getattr(runtime, "turn_traces", None)
            and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index")
        ):
            runtime.turn_traces[-1] = deepcopy(trace)
    return result


def install_mixed_act_lineage_p4() -> bool:
    """Install last in the dedicated P4 product entry, with the prior chain intact."""
    global _INSTALLED, _ORIGINAL_INGEST, _ORIGINAL_TICK, _ORIGINAL_EMIT
    global _ORIGINAL_ROUTED_M31, _ORIGINAL_PLAIN_M31, _ORIGINAL_M32
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac
    import uruha_mixed_past_place_source_authority_p4 as previous
    import uruha_reported_ack_route_admission_p4 as route_admission
    import uruha_terminal_copula_commit_latency_p4 as terminal

    if _INSTALLED:
        if (
            UruhaBrainV4_Mac.ingest_event is ingest_event_with_mixed_act_lineage_p4
            and UruhaBrainV4_Mac.cognitive_tick is cognitive_tick_with_mixed_act_lineage_p4
            and UruhaBrainV4_Mac.emit_response_if_ready is emit_response_with_mixed_act_lineage_p4
            and LeftBrain.authorize_literal_topic_m31_with_route_context_p4 is authorize_routed_m31_with_mixed_act_lineage_p4
            and LeftBrain.authorize_literal_topic_m31 is authorize_plain_m31_with_mixed_act_lineage_p4
            and adaptive.build_deterministic_semantic_commit_m32 is build_m32_with_mixed_act_lineage_p4
        ):
            return False
        raise RuntimeError("mixed_act_lineage_install_chain_changed")
    if not (
        previous._INSTALLED and terminal._INSTALLED
        and UruhaBrainV4_Mac.cognitive_tick is previous.cognitive_tick_with_mixed_past_place_source_authority_p4
        and LeftBrain.authorize_literal_topic_m31_with_route_context_p4 is terminal.authorize_literal_topic_with_copula_certificate_p4
        and LeftBrain.authorize_literal_topic_m31 is route_admission.authorize_literal_topic_without_route_context_p4
        and adaptive.build_deterministic_semantic_commit_m32 is terminal.build_terminal_copula_commit_latency_p4
    ):
        raise RuntimeError("mixed_act_lineage_requires_frozen_producer_chain")
    _ORIGINAL_INGEST = UruhaBrainV4_Mac.ingest_event
    _ORIGINAL_TICK = UruhaBrainV4_Mac.cognitive_tick
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_ROUTED_M31 = LeftBrain.authorize_literal_topic_m31_with_route_context_p4
    _ORIGINAL_PLAIN_M31 = LeftBrain.authorize_literal_topic_m31
    _ORIGINAL_M32 = adaptive.build_deterministic_semantic_commit_m32
    UruhaBrainV4_Mac.ingest_event = ingest_event_with_mixed_act_lineage_p4
    UruhaBrainV4_Mac.cognitive_tick = cognitive_tick_with_mixed_act_lineage_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_with_mixed_act_lineage_p4
    LeftBrain.authorize_literal_topic_m31_with_route_context_p4 = authorize_routed_m31_with_mixed_act_lineage_p4
    LeftBrain.authorize_literal_topic_m31 = authorize_plain_m31_with_mixed_act_lineage_p4
    adaptive.build_deterministic_semantic_commit_m32 = build_m32_with_mixed_act_lineage_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "EVENT_KEY", "PRODUCER_KEY", "EVENT_NODE",
    "ingest_event_with_mixed_act_lineage_p4",
    "cognitive_tick_with_mixed_act_lineage_p4",
    "emit_response_with_mixed_act_lineage_p4",
    "verify_mixed_act_lineage_p4", "install_mixed_act_lineage_p4",
]
