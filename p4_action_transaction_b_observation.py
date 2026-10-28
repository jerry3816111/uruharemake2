"""Reconstruct one B observation from a saved raw transaction stage, with zero calls.

This is an isolated component observation, not a transport attestation or Web
delivery.  The builder checks that the saved request/accounting record has the
fields needed for later verification.  The formal runner must separately check
the frozen prompt, payload, schema, options, model digest, and HTTP exchange.
"""

from __future__ import annotations

from copy import deepcopy
import json
import re
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

import p4_action_transaction_a_observation as a_raw
import p4_action_transaction_scoring as tx
import uruha_actionable_help_delivery_m45 as m45


_DIGEST_64 = re.compile(r"[0-9a-f]{64}\Z")
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _request_body_complete(body: object) -> bool:
    """Check presence/shape only; do not certify frozen request contents."""

    if not isinstance(body, dict) or type(body.get("model")) is not str or not body["model"]:
        return False
    messages = body.get("messages")
    if (not isinstance(messages, list) or len(messages) != 2
            or any(not isinstance(item, dict) for item in messages)
            or [item.get("role") for item in messages] != ["system", "user"]
            or any(type(item.get("content")) is not str or not item["content"]
                   for item in messages)):
        return False
    try:
        payload = json.loads(messages[1]["content"])
    except (TypeError, ValueError):
        return False
    if not isinstance(payload, dict) or not payload:
        return False
    if not isinstance(body.get("format"), dict) or not body["format"]:
        return False
    options = body.get("options")
    if not isinstance(options, dict):
        return False
    return bool(
        tx._valid_seconds(options.get("temperature"))
        and type(options.get("seed")) is int
        and type(options.get("num_ctx")) is int and options["num_ctx"] > 0
        and type(options.get("num_predict")) is int and options["num_predict"] > 0
    )


def _localhost_claim(identity: object) -> bool:
    """Read the recorded destination claim; this cannot prove the actual peer."""

    if not isinstance(identity, dict):
        return False
    endpoint = identity.get("endpoint")
    if type(endpoint) is not str:
        return False
    try:
        parsed = urlsplit(endpoint)
        return bool(parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS
                    and parsed.port is not None and parsed.path == "/api/chat"
                    and not parsed.username and not parsed.password)
    except ValueError:
        return False


def build_b_observation_from_stage(
    case: dict,
    raw_stage_record: dict,
    *,
    full_turn_seconds: object,
    retries: object = 0,
    fallback_kind: str | None = None,
) -> dict:
    """Reparse a single raw B stage; never trust its normalized/acceptance flags.

    ``raw_stage_record`` is retained in full, including unknown keys, so a
    caller-supplied flag remains auditable but cannot change the decision.  A
    complete metadata *record* is not proof that those fields describe the
    actual model or HTTP exchange.  Frozen identity verification belongs to
    the formal one-shot runner and is always reported as unverified here.
    """

    sources = a_raw._prepared(case)
    if not isinstance(raw_stage_record, dict):
        raise TypeError("B requires one raw stage record dictionary")
    if fallback_kind not in {None, "clarify", "unavailable"}:
        raise ValueError("fallback_kind must be clarify, unavailable, or None")
    record = deepcopy(raw_stage_record)
    # A formal raw artifact is JSON-serializable. Hashing the whole saved stage
    # also binds future metadata and unknown fields, not just its raw content.
    record_digest = m45.digest(record)
    raw = record.get("raw_content")
    parsed = tx.parse_transaction_json(raw)
    audit = tx.inspect_transaction(parsed, sources,
                                   raw_user_input=case["raw_user_input"])
    strict_schema_ok = bool(parsed is not None and Draft202012Validator(
        tx.transaction_schema(sources)).is_valid(parsed))
    json_contract_ok = bool(strict_schema_ok and audit["schema_shape_valid"])

    prompt_tokens = record.get("prompt_tokens")
    completion_tokens = record.get("completion_tokens")
    tokens_complete = tx._valid_usage(prompt_tokens, completion_tokens)
    token_budget_ok = bool(tokens_complete
                           and completion_tokens <= tx.MAX_B_COMPLETION_TOKENS)
    stage_seconds = record.get("wall_seconds")
    stage_wall_complete = bool(tx._valid_seconds(stage_seconds)
                               and tx._valid_seconds(full_turn_seconds))
    stage_wall_within_full_turn = bool(stage_wall_complete
                                       and stage_seconds <= full_turn_seconds)
    full_turn_budget_ok = bool(tx._valid_seconds(full_turn_seconds)
                               and full_turn_seconds <= tx.MAX_FULL_TURN_SECONDS)
    retries_complete = type(retries) is int and retries >= 0
    zero_retry = retries_complete and retries == 0
    accounting_complete = bool(tokens_complete and token_budget_ok
                               and stage_wall_within_full_turn
                               and full_turn_budget_ok and zero_retry)

    body = record.get("request_body")
    request_body_complete = _request_body_complete(body)
    outer_options = record.get("options")
    request_options_consistent = bool(
        outer_options is None or request_body_complete
        and isinstance(outer_options, dict)
        and outer_options == body["options"]
    )
    model_digest_complete = bool(type(record.get("model_digest")) is str
                                 and _DIGEST_64.fullmatch(record["model_digest"]))
    identity = record.get("http_identity")
    localhost_http_identity_claimed = _localhost_claim(identity)
    declared_model_consistent = bool(
        request_body_complete and isinstance(identity, dict)
        and type(identity.get("model")) is str
        and identity["model"] == body["model"]
    )
    transport = record.get("transport_metadata")
    transport_metadata_complete = bool(isinstance(transport, dict)
                                       and type(transport.get("http_status")) is int)
    transport_status_claimed_ok = bool(transport_metadata_complete
                                       and transport["http_status"] == 200)
    stage_kind_ok = record.get("stage") == "B_transaction"
    metadata_complete = bool(stage_kind_ok and request_body_complete
                             and request_options_consistent and model_digest_complete
                             and localhost_http_identity_claimed
                             and declared_model_consistent
                             and transport_metadata_complete
                             and transport_status_claimed_ok)

    accounting_violations = []
    if not tokens_complete:
        accounting_violations.append("stage_token_accounting_incomplete")
    elif not token_budget_ok:
        accounting_violations.append("stage_completion_token_budget_exceeded")
    if not stage_wall_within_full_turn:
        accounting_violations.append("stage_wall_not_within_full_turn")
    if not full_turn_budget_ok:
        accounting_violations.append("full_turn_budget_exceeded_or_invalid")
    if not zero_retry:
        accounting_violations.append("retry_contract_violated")
    metadata_violations = []
    for complete, name in (
        (stage_kind_ok, "stage_kind_missing_or_wrong"),
        (request_body_complete, "request_body_incomplete"),
        (request_options_consistent, "request_options_inconsistent"),
        (model_digest_complete, "model_digest_missing_or_malformed"),
        (localhost_http_identity_claimed, "localhost_http_identity_not_recorded"),
        (declared_model_consistent, "declared_model_identity_inconsistent"),
        (transport_metadata_complete, "transport_metadata_incomplete"),
        (transport_status_claimed_ok, "transport_status_not_successful"),
    ):
        if not complete:
            metadata_violations.append(name)
    guard = sorted(set(audit["guard_violations"] + accounting_violations
                       + metadata_violations))

    if parsed is None:
        raw_failure_stage = "transaction_parse"
    elif not audit["source_exact"]:
        raw_failure_stage = "transaction_source"
    elif not json_contract_ok:
        raw_failure_stage = "transaction_contract"
    elif audit["guard_violations"]:
        raw_failure_stage = "transaction_guard"
    elif not audit["would_deliver"]:
        raw_failure_stage = "model_abstain"
    else:
        raw_failure_stage = "none"
    if raw_failure_stage in {"none", "model_abstain"} and metadata_violations:
        failure = "metadata_guard"
    elif raw_failure_stage in {"none", "model_abstain"} and accounting_violations:
        failure = "accounting_guard"
    else:
        failure = raw_failure_stage
    deliver = bool(raw_failure_stage == "none" and metadata_complete
                   and accounting_complete)
    if parsed is not None and parsed.get("status") == "abstain" and json_contract_ok:
        reason = parsed["reason_code"]
    elif deliver:
        reason = "none"
    elif raw_failure_stage == "none":
        reason = "unknown_reason"
    else:
        reason = tx._guard_reason_code(audit["guard_violations"])
    resolved_fallback = None if deliver else (fallback_kind or "unavailable")
    return {
        "arm": "B_transaction",
        "decision": "action" if deliver else "abstain",
        "failure_stage": failure,
        "raw_transaction_failure_stage": raw_failure_stage,
        "reason_code": reason,
        "json_ok": parsed is not None,
        "json_contract_ok": json_contract_ok,
        "strict_json_schema_ok": strict_schema_ok,
        "source_exact": audit["source_exact"],
        "tokens_complete": tokens_complete,
        "token_budget_ok": token_budget_ok,
        "prompt_tokens": prompt_tokens if tokens_complete else None,
        "completion_tokens": completion_tokens if tokens_complete else None,
        "retries": retries,
        "retries_complete": retries_complete,
        "zero_retry": zero_retry,
        "full_turn_seconds": full_turn_seconds,
        "full_turn_budget_ok": full_turn_budget_ok,
        "stage_wall_complete": stage_wall_complete,
        "stage_wall_within_full_turn": stage_wall_within_full_turn,
        "accounting_complete": accounting_complete,
        "request_body_complete": request_body_complete,
        "request_options_consistent": request_options_consistent,
        "model_digest_complete": model_digest_complete,
        "localhost_http_identity_claimed": localhost_http_identity_claimed,
        "declared_model_consistent": declared_model_consistent,
        "transport_metadata_complete": transport_metadata_complete,
        "transport_status_claimed_ok": transport_status_claimed_ok,
        "stage_kind_ok": stage_kind_ok,
        "metadata_complete": metadata_complete,
        "raw_stage_complete": bool(metadata_complete and accounting_complete),
        "guard_violations": guard,
        "instruction_jp": parsed["instruction_jp"] if deliver else None,
        "fallback_kind": resolved_fallback,
        "fallback_reply_jp": (None if deliver else tx._fallback_reply(resolved_fallback)),
        "raw_output": raw,
        "raw_content_digest": m45.digest(raw) if type(raw) is str else None,
        "raw_stage_record": record,
        "raw_stage_record_digest": record_digest,
        "source_digest": m45.digest(sources),
        "raw_user_input_digest": m45.digest(case["raw_user_input"]),
        "transaction": deepcopy(parsed),
        "transaction_audit": deepcopy(audit),
        "frozen_request_verified_by_builder": False,
        "transport_identity_verified_by_builder": False,
        "formal_runner_verification_required": True,
        "model_calls_by_builder": 0,
        "semantic_gold_checked": False,
        "human_validated": False,
        "product_runtime_changed": False,
    }
