"""Zero-model contracts for one source-bound terminal-copula M32 retry."""

from copy import deepcopy
import hashlib

import pytest

import uruha_adaptive_person_model as adaptive
import uruha_reported_ack_route_admission_p4 as route_admission
import uruha_terminal_copula_commit_latency_p4 as copula
from uruha_brain_mac import LeftBrain


SOURCE = "港の目印は青い旗の隣だよ。"
SUBJECT = "港の目印"
STEM = "青い旗の隣"


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _projection(source=SOURCE):
    return {
        "schema": adaptive.LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
        "status": "projection_candidate",
        "projection_required": True,
        "surface_authority": False,
        "input_digest": _digest(source),
    }


def _context(source=SOURCE):
    return {
        "schema": route_admission.CONTEXT_SCHEMA,
        "input_digest": _digest(source),
    }


def _authorization(source=SOURCE, subject=SUBJECT, stem=STEM, period=False):
    checks = {key: True for key in copula._M31_REQUIRED_CHECKS}
    checks["proposal_or_repair_path_valid"] = False
    checks["safe_surface_anchors_visible"] = False
    candidate = {
        "schema": "uruha_semantic_commit_repair_candidate_m32",
        "canonical_ready": True,
        "subject_jp": subject,
        "predicate_jp": stem + "だ",
        "time_jp": "",
        "polarity": "affirmed",
        "literal_summary_jp": f"{subject}は{stem}である" + ("。" if period else ""),
        "failed_authorization_checks": [
            "proposal_or_repair_path_valid", "safe_surface_anchors_visible"
        ],
        "source_first_fast_path": True,
        "raw_dialogue_persisted": False,
        "model_response_raw_persisted": False,
    }
    return {
        "schema": adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
        "status": "semantic_authority_rejected",
        "reason": "one_or_more_semantic_authorization_checks_failed",
        "surface_authority": False,
        "input_digest": _digest(source),
        "proposal_status": "projection_candidate",
        "source_first_fast_path": True,
        "model_call_completed": True,
        "required_observable_act": None,
        "source_polarity": "affirmed",
        "polarity": "affirmed",
        "confidence": 0.95,
        "authorization_checks": checks,
        "m32_repair_candidate": candidate,
        "raw_dialogue_persisted": False,
        "model_response_raw_persisted": False,
    }


def _qualified(source=SOURCE, authorization=None, projection=None, context=None):
    authorization = deepcopy(authorization or _authorization(source))
    projection = deepcopy(projection or _projection(source))
    context = deepcopy(context or _context(source))
    authorization[copula.SOURCE_KEY] = copula.source_alignment_certificate_p4(
        source, projection, authorization, context
    )
    return authorization


@pytest.mark.parametrize("period", [False, True])
def test_source_aligned_terminal_copula_uses_original_m32_guards(period):
    authorization = _authorization(period=period)
    old_plan, old_contract = adaptive.build_deterministic_semantic_commit_m32(
        authorization
    )
    assert old_plan is None
    assert old_contract["status"] == "repair_rejected"
    assert [key for key, value in old_contract["commit_checks"].items() if value is False] == [
        "at_least_two_grounded_anchors"
    ]

    authorization = _qualified(authorization=authorization)
    source_cert = authorization[copula.SOURCE_KEY]
    assert source_cert["status"] == "source_aligned"
    assert source_cert["input_sha256"] == hashlib.sha256(SOURCE.encode()).hexdigest()
    assert SOURCE not in repr(source_cert)
    plan, contract = copula.build_terminal_copula_commit_latency_p4(authorization)

    assert contract["status"] == "deterministic_commit_repaired"
    assert contract["surface_authority"] is True
    assert all(contract["commit_checks"].values())
    assert contract["response_jp"] == f"{SUBJECT}は{STEM}だね。"
    assert plan["core_message_jp"] == contract["response_jp"]
    receipt = contract[copula.COMMIT_KEY]
    assert receipt["status"] == "terminal_copula_surface_committed"
    assert receipt["original_summary_sha256"] != receipt["committed_summary_sha256"]
    assert receipt["original_failed_checks"] == ["at_least_two_grounded_anchors"]
    assert receipt["model_calls_added"] == 0
    assert SOURCE not in repr(receipt)
    assert plan["semantic_commit_repair_m32"] == contract
    # The wrapper must not write changed canonical text into M31 input.
    assert authorization["m32_repair_candidate"]["literal_summary_jp"].endswith("である" + ("。" if period else ""))


def test_m31_route_boundary_uses_actual_raw_and_preserves_original_authority(monkeypatch):
    original = _authorization()
    calls = []

    def old_routed(_self, source, projection, context):
        calls.append((source, projection, context))
        return None, original

    monkeypatch.setattr(copula, "_ORIGINAL_ROUTED_M31", old_routed)
    projection, context = _projection(), _context()
    plan, authorization = copula.authorize_literal_topic_with_copula_certificate_p4(
        None, SOURCE, projection, context
    )
    assert plan is None
    assert len(calls) == 1 and calls[0] == (SOURCE, projection, context)
    assert authorization["status"] == "semantic_authority_rejected"
    assert authorization["surface_authority"] is False
    assert authorization[copula.SOURCE_KEY]["status"] == "source_aligned"
    assert copula.SOURCE_KEY not in original


@pytest.mark.parametrize(
    "source",
    [
        "「港の目印は青い旗の隣だよ。」って自然？",
        "港の目印は青い旗の隣じゃないよ。",
        "明日の目印は青い旗の隣だよ。",
        "港の目印は青い旗の隣だよ。別の話もある。",
        "港の目印は青い旗の隣であるだよ。",
        "港の目印は青い旗の隣だよ？",
    ],
)
def test_quote_negation_time_multiclause_and_non_simple_sources_fail_closed(source):
    authorization = _authorization(source=source)
    cert = copula.source_alignment_certificate_p4(
        source, _projection(source), authorization, _context(source)
    )
    assert cert["status"] == "rejected"
    authorization[copula.SOURCE_KEY] = cert
    original = adaptive.build_deterministic_semantic_commit_m32(authorization)
    assert copula.build_terminal_copula_commit_latency_p4(authorization) == original


@pytest.mark.parametrize(
    "source,subject,stem",
    [
        ("明日の目印は青い旗の隣だよ。", "明日の目印", STEM),
        ("港の目印は青い旗の隣であるだよ。", SUBJECT, "青い旗の隣である"),
        ("港の目印は青い旗の隣は安全だよ。", SUBJECT, "青い旗の隣は安全"),
        ("Harborは青い旗の隣だよ。", "Harbor", STEM),
    ],
)
def test_even_lexically_matching_time_nested_copula_second_topic_or_latin_rejects(
    source, subject, stem
):
    authorization = _authorization(source=source, subject=subject, stem=stem)
    cert = copula.source_alignment_certificate_p4(
        source, _projection(source), authorization, _context(source)
    )
    assert cert["status"] == "rejected"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda a: a["m32_repair_candidate"].update(subject_jp="丘の目印"),
        lambda a: a["m32_repair_candidate"].update(predicate_jp="赤い旗の隣だ"),
        lambda a: a["m32_repair_candidate"].update(literal_summary_jp="港の目印は青い旗の隣である場所"),
        lambda a: a["m32_repair_candidate"].update(literal_summary_jp="港の目印は青い旗の隣だ"),
        lambda a: a["m32_repair_candidate"].update(time_jp="明日"),
        lambda a: a["m32_repair_candidate"].update(polarity="negated"),
        lambda a: a.update(polarity="negated"),
        lambda a: a.update(confidence=0.79),
        lambda a: a.update(source_first_fast_path=False),
        lambda a: a["m32_repair_candidate"].update(canonical_ready=False),
        lambda a: a["authorization_checks"].update(local_unsupported_addition_absent=False),
        lambda a: a["authorization_checks"].update(confidence_gte_0_80=False),
        lambda a: a.update(required_observable_act="joint_complaint"),
        lambda a: a.pop("m32_repair_candidate"),
        lambda a: a.pop("authorization_checks"),
    ],
)
def test_canonical_mismatch_low_confidence_or_unprotected_check_rejects(mutation):
    authorization = _authorization()
    mutation(authorization)
    cert = copula.source_alignment_certificate_p4(
        SOURCE, _projection(), authorization, _context()
    )
    assert cert["status"] == "rejected"


@pytest.mark.parametrize("target", ["projection", "authorization", "context"])
def test_all_three_digest_links_are_required(target):
    authorization, projection, context = _authorization(), _projection(), _context()
    {"projection": projection, "authorization": authorization, "context": context}[target][
        "input_digest"
    ] = "0" * 16
    certificate = copula.source_alignment_certificate_p4(
        SOURCE, projection, authorization, context
    )
    assert certificate["status"] == "rejected"
    assert certificate["reason"] == "same_turn_source_provenance_missing_or_mismatched"


def test_missing_or_tampered_source_certificate_cannot_rewrite_old_m32_failure():
    source = _authorization()
    original = adaptive.build_deterministic_semantic_commit_m32(source)
    assert copula.build_terminal_copula_commit_latency_p4(source) == original
    source = _qualified()
    source[copula.SOURCE_KEY]["original_summary_sha256"] = "0" * 64
    assert copula.build_terminal_copula_commit_latency_p4(source) == original
    source = _qualified()
    source[copula.SOURCE_KEY]["input_sha256"] = "0" * 64
    assert copula.build_terminal_copula_commit_latency_p4(source) == original


def test_old_m32_success_and_nonunique_failure_are_not_rewritten():
    already_good = _authorization()
    already_good["m32_repair_candidate"]["literal_summary_jp"] = f"{SUBJECT}は{STEM}だ"
    original_plan, original_contract = adaptive.build_deterministic_semantic_commit_m32(
        already_good
    )
    assert original_contract["status"] == "deterministic_commit_repaired"
    assert copula.build_terminal_copula_commit_latency_p4(already_good) == (
        original_plan, original_contract
    )
    bad = _qualified()
    bad["m32_repair_candidate"]["polarity"] = "wrong"
    original = adaptive.build_deterministic_semantic_commit_m32(bad)
    assert original[1]["commit_checks"]["polarity_canonical"] is False
    assert copula.build_terminal_copula_commit_latency_p4(bad) == original


def test_opt_in_installer_is_idempotent_and_chain_mismatch_fails_closed(monkeypatch):
    assert adaptive.build_deterministic_semantic_commit_m32 is copula._ORIGINAL_M32
    monkeypatch.setattr(
        adaptive, "build_deterministic_semantic_commit_m32", copula._ORIGINAL_M32
    )
    monkeypatch.setattr(route_admission, "_INSTALLED", True)
    monkeypatch.setattr(
        LeftBrain,
        "authorize_literal_topic_m31_with_route_context_p4",
        route_admission.authorize_literal_topic_with_route_context_p4,
        raising=False,
    )
    monkeypatch.setattr(copula, "_INSTALLED", False)
    monkeypatch.setattr(copula, "_ORIGINAL_ROUTED_M31", None)
    assert copula.install_terminal_copula_commit_latency_p4() is True
    assert copula.install_terminal_copula_commit_latency_p4() is False
    assert adaptive.build_deterministic_semantic_commit_m32 is copula.build_terminal_copula_commit_latency_p4
    monkeypatch.setattr(adaptive, "build_deterministic_semantic_commit_m32", lambda _: (None, {}))
    with pytest.raises(RuntimeError, match="install_chain_changed"):
        copula.install_terminal_copula_commit_latency_p4()


def test_installer_refuses_absent_prior_route_chain(monkeypatch):
    monkeypatch.setattr(copula, "_INSTALLED", False)
    monkeypatch.setattr(route_admission, "_INSTALLED", False)
    with pytest.raises(RuntimeError, match="requires_frozen_m31_m32_chain"):
        copula.install_terminal_copula_commit_latency_p4()


def test_uninstalled_default_m32_remains_the_old_behavior():
    assert adaptive.build_deterministic_semantic_commit_m32 is copula._ORIGINAL_M32
    result = adaptive.build_deterministic_semantic_commit_m32(_authorization())
    assert result[0] is None
    assert result[1]["status"] == "repair_rejected"
