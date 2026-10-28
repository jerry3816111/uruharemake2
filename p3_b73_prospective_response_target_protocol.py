"""B73 prospective response-target schema, blinding views, and reliability gate."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from public_persona_contrast_coding_tool_v6 import nominal_krippendorff_alpha


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b73_prospective_response_target_protocol_v1.json"
EPISODE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{5,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"not_object:{path}")
    return value


def load_contract() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def validate_contract(contract: dict[str, Any] | None = None, *, root: Path = ROOT) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    if contract.get("schema") != "uruha_p3_b73_prospective_response_target_protocol_contract_v1":
        errors.append("schema")
    if contract.get("status") != "frozen_before_any_new_source_content_prediction_outcome_or_human_label":
        errors.append("status")
    for name, binding in (contract.get("bindings") or {}).items():
        path = Path(root) / str(binding.get("path") or "")
        if not path.is_file():
            errors.append(f"binding_missing:{name}")
        elif sha256_file(path) != binding.get("sha256"):
            errors.append(f"binding_hash:{name}")
    episode = contract.get("episode_contract") or {}
    required_episode_flags = {
        "prediction_view_excludes_outcome": True,
        "coder_view_includes_outcome_after_prediction_freeze": True,
        "condition_identity_or_prediction_visible_to_coder": False,
        "stimulus_response_boundary_required": True,
        "unusable_boundary_must_be_excluded_not_default_labeled": True,
        "acoustic_evidence_missing_must_be_unavailable": True,
    }
    if episode != required_episode_flags:
        errors.append("episode_contract")
    codebook = contract.get("codebook") or {}
    for field, minimum in (("response_moves", 8), ("interaction_goals", 9), ("stances", 7), ("literal_pragmatic_relations", 5)):
        values = codebook.get(field)
        if not isinstance(values, list) or len(values) < minimum or len(values) != len(set(values)):
            errors.append(f"codebook:{field}")
    if codebook.get("private_motive_inference_allowed") is not False or codebook.get("alternative_goals_max") != 2:
        errors.append("codebook:boundaries")
    pilot = contract.get("pilot_reliability") or {}
    if pilot.get("distinct_consenting_human_coder_count_exact") != 2 or pilot.get("episode_count_exact") != 18:
        errors.append("pilot:counts")
    if pilot.get("nominal_krippendorff_alpha_min_each_primary") != 0.667 or pilot.get("minimum_observed_categories_each_primary") != 2:
        errors.append("pilot:gate")
    if pilot.get("synthetic_or_llm_labels_authorize_human_reliability") is not False:
        errors.append("pilot:human_boundary")
    limits = contract.get("execution_limits") or {}
    if set(limits) != {"new_source_content_access_count", "new_prediction_or_outcome_access_count", "model_call_count", "human_label_count", "production_memory_write_count"} or any(value != 0 for value in limits.values()):
        errors.append("execution_limits")
    return {"valid": not errors, "errors": errors}


def validate_episode_packet(packet: dict[str, Any], contract: dict[str, Any] | None = None) -> list[str]:
    contract = contract or load_contract()
    errors: list[str] = []
    if packet.get("schema") != "uruha_p3_b73_response_episode_packet_v1":
        errors.append("schema")
    episode_id = packet.get("episode_id")
    if not isinstance(episode_id, str) or not EPISODE_ID_RE.fullmatch(episode_id):
        errors.append("episode_id")
    provenance = packet.get("provenance") or {}
    for field in ("source_id", "source_url", "publisher", "observed_at"):
        if not isinstance(provenance.get(field), str) or not provenance[field].strip():
            errors.append(f"provenance:{field}")
    stimulus = packet.get("stimulus") or {}
    for field in ("surface_form_id", "context_variant_id", "utterance_text", "pre_context_text"):
        if not isinstance(stimulus.get(field), str) or not stimulus[field].strip():
            errors.append(f"stimulus:{field}")
    if stimulus.get("boundary_status") != "usable_stimulus_response_pair":
        errors.append("stimulus:boundary_status")
    coverage = stimulus.get("pub_coverage_bucket")
    if coverage not in (contract.get("codebook") or {}).get("pub_coverage_buckets", []):
        errors.append("stimulus:coverage")
    modality = stimulus.get("modality") or {}
    if modality.get("text_available") is not True:
        errors.append("modality:text")
    acoustic_status = modality.get("acoustic_summary_status")
    acoustic_features = modality.get("acoustic_features")
    if acoustic_status not in {"available", "unavailable"}:
        errors.append("modality:acoustic_status")
    elif acoustic_status == "unavailable" and acoustic_features is not None:
        errors.append("modality:invented_acoustics")
    elif acoustic_status == "available" and (not isinstance(acoustic_features, dict) or not acoustic_features):
        errors.append("modality:missing_acoustics")
    outcome = packet.get("outcome") or {}
    if not isinstance(outcome.get("response_text"), str) or not outcome["response_text"].strip():
        errors.append("outcome:response_text")
    if not isinstance(outcome.get("response_start_ms"), int) or not isinstance(outcome.get("response_end_ms"), int) or outcome.get("response_end_ms", 0) <= outcome.get("response_start_ms", 0):
        errors.append("outcome:boundary")
    digest = outcome.get("response_text_sha256")
    expected = hashlib.sha256(str(outcome.get("response_text") or "").encode("utf-8")).hexdigest()
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest) or digest != expected:
        errors.append("outcome:response_hash")
    blinding = packet.get("blinding") or {}
    if blinding != {
        "prediction_frozen_before_outcome_access": True,
        "condition_identity_visible_to_coder": False,
        "model_prediction_visible_to_coder": False,
    }:
        errors.append("blinding")
    forbidden = {"baseline_prediction", "system_prediction", "condition", "score", "winner"}
    if forbidden.intersection(packet):
        errors.append("forbidden_prediction_fields")
    return errors


def build_prediction_view(packet: dict[str, Any], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    errors = validate_episode_packet(packet, contract)
    if errors:
        raise ValueError("invalid_packet:" + ";".join(errors))
    return {
        "schema": "uruha_p3_b73_prediction_view_v1",
        "episode_id": packet["episode_id"],
        "provenance": deepcopy(packet["provenance"]),
        "stimulus": deepcopy(packet["stimulus"]),
        "outcome_access_count": 0,
    }


def build_coder_view(packet: dict[str, Any], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    errors = validate_episode_packet(packet, contract)
    if errors:
        raise ValueError("invalid_packet:" + ";".join(errors))
    return {
        "schema": "uruha_p3_b73_coder_view_v1",
        "episode_id": packet["episode_id"],
        "stimulus": deepcopy(packet["stimulus"]),
        "outcome": deepcopy(packet["outcome"]),
        "condition_identity_visible": False,
        "model_prediction_visible": False,
    }


def validate_annotation_entry(entry: dict[str, Any], contract: dict[str, Any] | None = None) -> list[str]:
    contract = contract or load_contract()
    codebook = contract["codebook"]
    errors: list[str] = []
    if not isinstance(entry.get("episode_id"), str) or not EPISODE_ID_RE.fullmatch(entry["episode_id"]):
        errors.append("episode_id")
    moves = entry.get("response_moves")
    if not isinstance(moves, list) or not moves or len(moves) != len(set(moves)) or any(move not in codebook["response_moves"] for move in moves):
        errors.append("response_moves")
    goal = entry.get("primary_interaction_goal")
    if goal not in codebook["interaction_goals"]:
        errors.append("primary_interaction_goal")
    alternatives = entry.get("alternative_goals")
    if not isinstance(alternatives, list) or len(alternatives) > codebook["alternative_goals_max"] or len(alternatives) != len(set(alternatives)) or goal in alternatives or any(value not in codebook["interaction_goals"] for value in alternatives):
        errors.append("alternative_goals")
    if entry.get("stance") not in codebook["stances"]:
        errors.append("stance")
    if entry.get("literal_pragmatic_relation") not in codebook["literal_pragmatic_relations"]:
        errors.append("literal_pragmatic_relation")
    if not isinstance(entry.get("evidence_anchor_count"), int) or entry["evidence_anchor_count"] < 1:
        errors.append("evidence_anchor_count")
    if entry.get("private_motive_asserted") is not False:
        errors.append("private_motive_asserted")
    if entry.get("completed_without_prediction_visibility") is not True:
        errors.append("prediction_visibility")
    if entry.get("coder_kind") != "consenting_human":
        errors.append("coder_kind")
    return errors


def validate_ledger(ledger: dict[str, Any], episode_ids: list[str], contract: dict[str, Any] | None = None, *, require_complete: bool = True) -> list[str]:
    contract = contract or load_contract()
    errors: list[str] = []
    if ledger.get("schema") != "uruha_p3_b73_private_human_annotation_ledger_v1":
        errors.append("schema")
    pseudonym = ledger.get("coder_pseudonym")
    if not isinstance(pseudonym, str) or len(pseudonym.strip()) < 3:
        errors.append("coder_pseudonym")
    if ledger.get("coder_kind") != "consenting_human":
        errors.append("coder_kind")
    entries = ledger.get("entries")
    if not isinstance(entries, dict):
        return errors + ["entries"]
    expected = set(episode_ids)
    if set(entries).difference(expected):
        errors.append("unknown_episode")
    if require_complete and set(entries) != expected:
        errors.append("incomplete")
    for episode_id, entry in entries.items():
        if entry.get("episode_id") != episode_id:
            errors.append(f"entry_id:{episode_id}")
        errors.extend(f"entry:{episode_id}:{error}" for error in validate_annotation_entry(entry, contract))
    return errors


def _rounded_alpha(pairs: list[tuple[Any, Any]]) -> float | None:
    value = nominal_krippendorff_alpha(pairs)
    return None if value is None else round(value, 6)


def build_reliability_report(ledger_a: dict[str, Any], ledger_b: dict[str, Any], episode_ids: list[str], contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    pilot = contract["pilot_reliability"]
    errors_a = validate_ledger(ledger_a, episode_ids, contract)
    errors_b = validate_ledger(ledger_b, episode_ids, contract)
    distinct = ledger_a.get("coder_pseudonym") != ledger_b.get("coder_pseudonym")
    entries_a = ledger_a.get("entries") if isinstance(ledger_a.get("entries"), dict) else {}
    entries_b = ledger_b.get("entries") if isinstance(ledger_b.get("entries"), dict) else {}
    shared = [episode_id for episode_id in episode_ids if episode_id in entries_a and episode_id in entries_b]
    primary_values = {
        "response_move_set": [("|".join(sorted(entries_a[i]["response_moves"])), "|".join(sorted(entries_b[i]["response_moves"]))) for i in shared],
        "primary_interaction_goal": [(entries_a[i]["primary_interaction_goal"], entries_b[i]["primary_interaction_goal"]) for i in shared],
        "stance": [(entries_a[i]["stance"], entries_b[i]["stance"]) for i in shared],
        "literal_pragmatic_relation": [(entries_a[i]["literal_pragmatic_relation"], entries_b[i]["literal_pragmatic_relation"]) for i in shared],
    }
    alphas = {field: _rounded_alpha(pairs) for field, pairs in primary_values.items()}
    observed_categories = {field: len({value for pair in pairs for value in pair}) for field, pairs in primary_values.items()}
    move_alphas = {}
    for move in contract["codebook"]["response_moves"]:
        pairs = [(move in entries_a[i]["response_moves"], move in entries_b[i]["response_moves"]) for i in shared]
        move_alphas[move] = _rounded_alpha(pairs)
    complete = not errors_a and not errors_b and len(shared) == pilot["episode_count_exact"] == len(episode_ids)
    gate = complete and distinct and all(
        alphas[field] is not None
        and alphas[field] >= pilot["nominal_krippendorff_alpha_min_each_primary"]
        and observed_categories[field] >= pilot["minimum_observed_categories_each_primary"]
        for field in pilot["primary_fields"]
    )
    return {
        "schema": "uruha_p3_b73_response_target_reliability_report_v1",
        "episode_count": len(episode_ids),
        "paired_episode_count": len(shared),
        "coder_pseudonyms_distinct": distinct,
        "coder_a_pseudonym_sha256": hashlib.sha256(str(ledger_a.get("coder_pseudonym") or "").encode()).hexdigest(),
        "coder_b_pseudonym_sha256": hashlib.sha256(str(ledger_b.get("coder_pseudonym") or "").encode()).hexdigest(),
        "primary_nominal_krippendorff_alpha": alphas,
        "primary_observed_category_count": observed_categories,
        "per_response_move_binary_alpha": move_alphas,
        "gates": {
            "both_ledgers_complete_and_valid": complete,
            "coder_pseudonyms_distinct": distinct,
            "all_primary_alpha_and_diversity_pass": gate,
            "human_reliability_passed": gate,
            "new_source_prediction_authorized": gate,
        },
        "validation": {"coder_a_errors": errors_a, "coder_b_errors": errors_b},
        "synthetic_fixture_authorizes_human_reliability": False,
        "claim_boundary": contract["claim_boundary"],
    }


def build_readiness_result(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    validation = validate_contract(contract)
    if not validation["valid"]:
        raise ValueError("contract:" + ";".join(validation["errors"]))
    return {
        "schema": "uruha_p3_b73_prospective_response_target_protocol_readiness_v1",
        "version": "1.0.0",
        "status": "protocol_tooling_ready_human_reliability_not_started",
        "layers": ["observable_response_moves", "pragmatic_target", "surface_realization", "separate_subjective_preference"],
        "blinding": {"prediction_view_outcome_access_count": 0, "coder_condition_or_prediction_visibility": False},
        "pilot": {"required_distinct_humans": 2, "required_episodes_each": 18, "actual_human_labels": 0, "reliability_status": "not_started"},
        "execution_counts": deepcopy(contract["execution_limits"]),
        "next_gate": "two_distinct_humans_complete_blinded_18_episode_pilot_and_all_primary_alpha_at_least_0_667",
        "claim_boundary": contract["claim_boundary"],
    }
