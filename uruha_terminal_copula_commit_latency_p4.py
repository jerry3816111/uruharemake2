"""Opt-in, source-aligned terminal-copula realization for the existing M32.

This is a narrowly bounded surface operation, not semantic inference.  The
actual source utterance is inspected only at the M31 method boundary; M32 gets
an input-bound, raw-free certificate and still delegates every commit check to
the unchanged original implementation.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import math
import re

import uruha_adaptive_person_model as adaptive
import uruha_reported_ack_route_admission_p4 as route_admission


SCHEMA = "uruha_terminal_copula_commit_latency_p4_v1"
SOURCE_KEY = "terminal_copula_source_alignment_p4"
COMMIT_KEY = "terminal_copula_commit_latency_p4"
_ORIGINAL_M32 = adaptive.build_deterministic_semantic_commit_m32
_ORIGINAL_ROUTED_M31 = None
_INSTALLED = False

# Deliberately excludes a second clause, quotes, dialogue punctuation and a
# second topic marker.  We do not normalize Unicode or trim the user's source.
_SIMPLE_ASSERTION = re.compile(
    r"(?P<subject>[ぁ-んァ-ヶー一-龠々]{2,48})"
    r"は(?P<stem>[ぁ-んァ-ヶー一-龠々]{2,48})だよ。"
)
_NEGATION = re.compile(r"(?:じゃない|ではない|ではなく|じゃなく|ない|なく|なかった|ません|無い)")
_TIME_OR_QUANTITY = re.compile(
    r"(?:今日|昨日|明日|今朝|今晩|今夜|来週|先週|来月|先月|来年|"
    r"午前|午後|時|分|週間|さっき|前に|後で|[0-9０-９一二三四五六七八九十百千])"
)
_M31_ALLOWED_FAILED = frozenset(
    {"proposal_or_repair_path_valid", "safe_surface_anchors_visible"}
)
_M31_REQUIRED_CHECKS = frozenset(
    {
        "proposal_or_repair_path_valid",
        "unsupported_addition_absent",
        "local_unsupported_addition_absent",
        "canonical_source_fields_present",
        "source_polarity_canonical",
        "safe_japanese_surface_present",
        "safe_foreign_script_absent",
        "safe_casual_register_only",
        "safe_surface_anchors_visible",
        "safe_surface_anchors_grounded_in_canonical",
        "confidence_gte_0_80",
        "required_observable_act_preserved",
        "joint_complaint_topic_anchor_present",
        "joint_complaint_not_generic_presence_or_question",
        "joint_complaint_topic_not_participant",
    }
)
_M32_REQUIRED_CHECKS = frozenset(
    {
        "canonical_subject_present",
        "canonical_predicate_present",
        "canonical_summary_present",
        "polarity_canonical",
        "casual_register_only",
        "japanese_surface_present",
        "at_least_two_grounded_anchors",
        "all_anchors_visible",
        "unsupported_addition_absent",
    }
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_m31_rejection(authorization: dict, candidate: dict) -> bool:
    """Require a complete source-first canonical and only surface failures."""
    checks = authorization.get("authorization_checks")
    if not isinstance(checks, dict) or set(checks) != _M31_REQUIRED_CHECKS:
        return False
    failed = {key for key, value in checks.items() if value is False}
    if any(value is not True and value is not False for value in checks.values()):
        return False
    if not failed or not failed.issubset(_M31_ALLOWED_FAILED):
        return False
    if not (
        authorization.get("schema") == adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31
        and authorization.get("status") == "semantic_authority_rejected"
        and authorization.get("reason") == "one_or_more_semantic_authorization_checks_failed"
        and authorization.get("surface_authority") is False
        and authorization.get("source_first_fast_path") is True
        and authorization.get("model_call_completed") is True
        and authorization.get("required_observable_act") is None
        and authorization.get("source_polarity") == "affirmed"
        and authorization.get("polarity") == "affirmed"
        and authorization.get("raw_dialogue_persisted") is False
        and authorization.get("model_response_raw_persisted") is False
        and candidate.get("schema") == "uruha_semantic_commit_repair_candidate_m32"
        and candidate.get("canonical_ready") is True
        and candidate.get("source_first_fast_path") is True
        and candidate.get("time_jp") == ""
        and candidate.get("polarity") == "affirmed"
        and candidate.get("raw_dialogue_persisted") is False
        and candidate.get("model_response_raw_persisted") is False
        and set(candidate.get("failed_authorization_checks") or []) == failed
    ):
        return False
    confidence = authorization.get("confidence")
    return bool(
        isinstance(confidence, (int, float))
        and not isinstance(confidence, bool)
        and math.isfinite(confidence)
        and confidence >= 0.80
    )


def source_alignment_certificate_p4(
    user_input, projection, authorization, context
) -> dict:
    """Prove exact lexical alignment from the real source, never a digest alone."""
    raw = user_input if isinstance(user_input, str) else ""
    raw_sha = _sha(raw)
    digest = raw_sha[:16]
    certificate = {
        "schema": SCHEMA,
        "status": "rejected",
        "reason": "source_or_contract_not_aligned",
        "input_sha256": raw_sha,
        "input_digest": digest,
        "source_grammar": "exact_unquoted_subject_wa_predicate_stem_da_yo",
        "raw_dialogue_persisted": False,
        "model_response_raw_persisted": False,
        "model_calls_added": 0,
        "claim_boundary": "exact source-to-M31 lexical alignment only; no new fact inference",
    }
    if not (
        isinstance(projection, dict)
        and isinstance(authorization, dict)
        and isinstance(context, dict)
        and projection.get("schema") == adaptive.LITERAL_TOPIC_PROJECTION_SCHEMA_M29
        and projection.get("status") == "projection_candidate"
        and projection.get("projection_required") is True
        and projection.get("surface_authority") is False
        and projection.get("input_digest") == digest
        and authorization.get("input_digest") == digest
        and authorization.get("proposal_status") == projection.get("status")
        and context.get("schema") == route_admission.CONTEXT_SCHEMA
        and context.get("input_digest") == digest
    ):
        certificate["reason"] = "same_turn_source_provenance_missing_or_mismatched"
        return certificate
    match = _SIMPLE_ASSERTION.fullmatch(raw)
    if (
        not match
        or _NEGATION.search(raw)
        or _TIME_OR_QUANTITY.search(raw)
        or "は" in match.group("subject")
        or "は" in match.group("stem")
        or "である" in match.group("stem")
        or "だよ" in match.group("stem")
    ):
        certificate["reason"] = "outside_bounded_affirmed_source_grammar"
        return certificate
    candidate = authorization.get("m32_repair_candidate")
    if not isinstance(candidate, dict) or not _safe_m31_rejection(
        authorization, candidate
    ):
        certificate["reason"] = "m31_canonical_or_authorization_not_safe"
        return certificate

    subject, stem = match.group("subject", "stem")
    predicate = f"{stem}だ"
    summary = str(candidate.get("literal_summary_jp") or "")
    if not (
        candidate.get("subject_jp") == subject
        and candidate.get("predicate_jp") == predicate
        and summary in {f"{subject}は{stem}である", f"{subject}は{stem}である。"}
    ):
        certificate["reason"] = "source_canonical_lexical_mismatch"
        return certificate
    certificate.update(
        {
            "status": "source_aligned",
            "reason": "exact_source_subject_predicate_and_terminal_copula_match",
            "subject_sha256": _sha(subject),
            "predicate_sha256": _sha(predicate),
            "original_summary_sha256": _sha(summary),
            "terminal_copula": "である_to_だ",
        }
    )
    return certificate


def authorize_literal_topic_with_copula_certificate_p4(
    self, user_input, projection, context
):
    """Observe the original M31 result without changing its authority."""
    if not callable(_ORIGINAL_ROUTED_M31):
        raise RuntimeError("terminal_copula_original_routed_m31_unavailable")
    plan, authorization = _ORIGINAL_ROUTED_M31(
        self, user_input, projection, context
    )
    if not isinstance(authorization, dict):
        return plan, authorization
    certificate = source_alignment_certificate_p4(
        user_input, projection, authorization, context
    )
    updated = deepcopy(authorization)
    updated[SOURCE_KEY] = certificate
    if isinstance(plan, dict) and isinstance(plan.get("semantic_authorization_m31"), dict):
        plan = deepcopy(plan)
        plan["semantic_authorization_m31"][SOURCE_KEY] = deepcopy(certificate)
    return plan, updated


def build_terminal_copula_commit_latency_p4(authorization):
    """Retry only one failed M32 anchor check with a copied, aligned summary."""
    original_plan, original_contract = _ORIGINAL_M32(authorization)
    if not isinstance(authorization, dict) or not isinstance(original_contract, dict):
        return original_plan, original_contract
    candidate = authorization.get("m32_repair_candidate")
    certificate = authorization.get(SOURCE_KEY)
    checks = original_contract.get("commit_checks")
    if not (
        isinstance(candidate, dict)
        and isinstance(certificate, dict)
        and _safe_m31_rejection(authorization, candidate)
        and certificate.get("schema") == SCHEMA
        and certificate.get("status") == "source_aligned"
        and certificate.get("terminal_copula") == "である_to_だ"
        and certificate.get("input_sha256", "")[:16]
        == authorization.get("input_digest") == certificate.get("input_digest")
        and certificate.get("subject_sha256") == _sha(str(candidate.get("subject_jp") or ""))
        and certificate.get("predicate_sha256") == _sha(str(candidate.get("predicate_jp") or ""))
        and certificate.get("original_summary_sha256") == _sha(str(candidate.get("literal_summary_jp") or ""))
        and original_plan is None
        and original_contract.get("schema") == adaptive.SEMANTIC_COMMIT_REPAIR_SCHEMA_M32
        and original_contract.get("status") == "repair_rejected"
        and original_contract.get("reason") == "deterministic_commit_checks_failed"
        and isinstance(checks, dict)
        and set(checks) == _M32_REQUIRED_CHECKS
        and checks.get("at_least_two_grounded_anchors") is False
        and all(value is True for key, value in checks.items() if key != "at_least_two_grounded_anchors")
        and set(original_contract.get("rejection_checks_m31") or [])
        == set(candidate.get("failed_authorization_checks") or [])
    ):
        return original_plan, original_contract

    summary = str(candidate.get("literal_summary_jp") or "")
    subject = str(candidate.get("subject_jp") or "")
    predicate = str(candidate.get("predicate_jp") or "")
    if not (
        summary.endswith("である") or summary.endswith("である。")
    ) or not predicate.endswith("だ"):
        return original_plan, original_contract
    stem = predicate[:-1]
    if not (
        stem
        and summary in {f"{subject}は{stem}である", f"{subject}は{stem}である。"}
        and predicate not in summary.rstrip("。")
    ):
        return original_plan, original_contract
    new_summary = f"{subject}は{predicate}" + ("。" if summary.endswith("。") else "")
    retry_authorization = deepcopy(authorization)
    retry_authorization["m32_repair_candidate"]["literal_summary_jp"] = new_summary
    retry_plan, retry_contract = _ORIGINAL_M32(retry_authorization)
    retry_checks = retry_contract.get("commit_checks") if isinstance(retry_contract, dict) else None
    if not (
        isinstance(retry_plan, dict)
        and isinstance(retry_contract, dict)
        and retry_contract.get("status") == "deterministic_commit_repaired"
        and retry_contract.get("surface_authority") is True
        and isinstance(retry_checks, dict)
        and set(retry_checks) == _M32_REQUIRED_CHECKS
        and all(value is True for value in retry_checks.values())
        and subject in str(retry_contract.get("response_jp") or "")
        and predicate in str(retry_contract.get("response_jp") or "")
    ):
        return original_plan, original_contract
    receipt = {
        "schema": SCHEMA,
        "status": "terminal_copula_surface_committed",
        "source_alignment_status": certificate["status"],
        "input_sha256": certificate["input_sha256"],
        "original_summary_sha256": _sha(summary),
        "committed_summary_sha256": _sha(new_summary),
        "original_m32_status": original_contract["status"],
        "original_m32_reason": original_contract["reason"],
        "original_failed_checks": ["at_least_two_grounded_anchors"],
        "retry_m32_status": retry_contract["status"],
        "retry_original_checks_all_passed": True,
        "model_calls_added": 0,
        "raw_dialogue_persisted": False,
        "claim_boundary": "source-bound copula surface only; unchanged M32 owns final checks",
    }
    committed = deepcopy(retry_contract)
    committed[COMMIT_KEY] = receipt
    plan = deepcopy(retry_plan)
    plan["semantic_commit_repair_m32"] = deepcopy(committed)
    return plan, committed


def install_terminal_copula_commit_latency_p4() -> bool:
    """Install only after the known route overlay and exact original M32."""
    global _INSTALLED, _ORIGINAL_ROUTED_M31
    from uruha_brain_mac import LeftBrain

    if _INSTALLED:
        if (
            LeftBrain.authorize_literal_topic_m31_with_route_context_p4
            is authorize_literal_topic_with_copula_certificate_p4
            and adaptive.build_deterministic_semantic_commit_m32
            is build_terminal_copula_commit_latency_p4
        ):
            return False
        raise RuntimeError("terminal_copula_install_chain_changed")
    if not (
        route_admission._INSTALLED
        and LeftBrain.authorize_literal_topic_m31_with_route_context_p4
        is route_admission.authorize_literal_topic_with_route_context_p4
        and adaptive.build_deterministic_semantic_commit_m32 is _ORIGINAL_M32
    ):
        raise RuntimeError("terminal_copula_requires_frozen_m31_m32_chain")
    _ORIGINAL_ROUTED_M31 = route_admission.authorize_literal_topic_with_route_context_p4
    LeftBrain.authorize_literal_topic_m31_with_route_context_p4 = (
        authorize_literal_topic_with_copula_certificate_p4
    )
    adaptive.build_deterministic_semantic_commit_m32 = (
        build_terminal_copula_commit_latency_p4
    )
    _INSTALLED = True
    return True


__all__ = [
    "SCHEMA",
    "SOURCE_KEY",
    "COMMIT_KEY",
    "source_alignment_certificate_p4",
    "authorize_literal_topic_with_copula_certificate_p4",
    "build_terminal_copula_commit_latency_p4",
    "install_terminal_copula_commit_latency_p4",
]
