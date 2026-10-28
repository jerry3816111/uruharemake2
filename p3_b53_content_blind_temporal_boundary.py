"""Choose a prospective source boundary without accessing source content."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b53_content_blind_temporal_boundary_v1.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b53_content_blind_temporal_boundary_implementation_freeze_2026-09-17.json"
)


class B53ContractError(ValueError):
    pass


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_contract():
    return load_json(CONFIG_PATH)


def validate_contract(contract=None, *, root=ROOT):
    contract = deepcopy(contract or load_contract())
    errors = []
    if contract.get("schema") != "uruha_p3_b53_content_blind_temporal_boundary_v1":
        errors.append("schema_mismatch")
    binding = (contract.get("binding") or {}).get("source_release") or {}
    path = Path(root) / str(binding.get("path") or "")
    if not path.is_file():
        errors.append("source_release_missing")
        release = {}
    else:
        observed_hash = sha256_bytes(path.read_bytes())
        if observed_hash != str(binding.get("sha256") or ""):
            errors.append("source_release_hash_mismatch")
        release = load_json(path)
    selected = release.get("selected_source") or {}
    source = contract.get("source") or {}
    if source.get("source_id") != selected.get("source_id"):
        errors.append("source_id_binding_mismatch")
    if source.get("video_id") != selected.get("video_id"):
        errors.append("video_id_binding_mismatch")
    if source.get("duration_seconds") != selected.get("duration_seconds"):
        errors.append("duration_binding_mismatch")
    if release and release.get("status") != "source_reserved_postcheck_passed":
        errors.append("source_release_not_eligible")
    policy = contract.get("boundary_policy") or {}
    positive_integer_fields = (
        "head_margin_seconds",
        "tail_margin_seconds",
        "observable_context_seconds",
        "prediction_to_behavior_gap_seconds",
        "hidden_future_seconds",
        "cutoff_grid_step_seconds",
        "minimum_candidate_count",
    )
    for field in positive_integer_fields:
        value = policy.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"invalid_positive_integer:{field}")
    boundary = contract.get("execution_boundary") or {}
    if any(value != 0 for value in boundary.values()):
        errors.append("execution_boundary_nonzero")
    return {"valid": not errors, "errors": errors}


def validate_implementation_freeze(*, root=ROOT):
    freeze_path = Path(root) / FREEZE_PATH.relative_to(ROOT)
    freeze = load_json(freeze_path)
    errors = []
    if freeze.get("status") != "frozen_before_boundary_selection_or_media_access":
        errors.append("freeze_status_invalid")
    for artifact_id, artifact in (freeze.get("frozen_artifacts") or {}).items():
        path = Path(root) / str((artifact or {}).get("path") or "")
        if not path.is_file():
            errors.append(f"frozen_artifact_missing:{artifact_id}")
            continue
        if sha256_bytes(path.read_bytes()) != str((artifact or {}).get("sha256") or ""):
            errors.append(f"frozen_artifact_hash_mismatch:{artifact_id}")
    if errors:
        raise B53ContractError(";".join(errors))
    return {
        "valid": True,
        "boundary_selection_count_at_freeze": freeze.get(
            "boundary_selection_count_at_freeze"
        ),
        "media_request_count_at_freeze": freeze.get(
            "media_request_count_at_freeze"
        ),
        "target_segment_access_count_at_freeze": freeze.get(
            "target_segment_access_count_at_freeze"
        ),
    }


def generate_cutoff_candidates(source, policy):
    duration = source.get("duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
        raise B53ContractError("invalid_source_duration")
    first_cutoff = (
        int(policy["head_margin_seconds"])
        + int(policy["observable_context_seconds"])
    )
    latest_cutoff = (
        duration
        - int(policy["tail_margin_seconds"])
        - int(policy["prediction_to_behavior_gap_seconds"])
        - int(policy["hidden_future_seconds"])
    )
    step = int(policy["cutoff_grid_step_seconds"])
    if first_cutoff > latest_cutoff:
        raise B53ContractError("source_too_short_for_frozen_windows")
    candidates = list(range(first_cutoff, latest_cutoff + 1, step))
    if len(candidates) < int(policy["minimum_candidate_count"]):
        raise B53ContractError("insufficient_cutoff_candidates")
    return candidates


def select_temporal_boundary(contract=None):
    contract = deepcopy(contract or load_contract())
    report = validate_contract(contract)
    if not report["valid"]:
        raise B53ContractError(";".join(report["errors"]))
    source = contract["source"]
    policy = contract["boundary_policy"]
    candidates = generate_cutoff_candidates(source, policy)
    seed = policy["selection_seed"]
    scored = [
        (
            sha256_bytes(
                f"{seed}|{source['source_id']}|{cutoff}".encode("utf-8")
            ),
            cutoff,
        )
        for cutoff in candidates
    ]
    scored.sort(key=lambda item: (item[0], item[1]))
    winning_score, cutoff = scored[0]
    observable_start = cutoff - int(policy["observable_context_seconds"])
    behavior_start = cutoff + int(policy["prediction_to_behavior_gap_seconds"])
    behavior_end = behavior_start + int(policy["hidden_future_seconds"])
    event_start = observable_start
    event_end = behavior_end
    candidate_set_hash = sha256_bytes(canonical_json(candidates).encode("utf-8"))
    material = {
        "schema": "uruha_p3_b53_content_blind_temporal_boundary_receipt_v1",
        "source_release_hash": contract["binding"]["source_release"]["sha256"],
        "source_id": source["source_id"],
        "source_duration_seconds": source["duration_seconds"],
        "selection_seed": seed,
        "candidate_set_hash": candidate_set_hash,
        "candidate_count": len(candidates),
        "selection_score": winning_score,
        "event_start_seconds": event_start,
        "observable_input_start_seconds": observable_start,
        "prediction_cutoff_seconds": cutoff,
        "observable_behavior_start_seconds": behavior_start,
        "observable_behavior_end_seconds": behavior_end,
        "event_end_seconds": event_end,
    }
    receipt = {
        **material,
        "receipt_hash": sha256_bytes(canonical_json(material).encode("utf-8")),
        "head_margin_observed_seconds": observable_start,
        "tail_margin_observed_seconds": source["duration_seconds"] - behavior_end,
        **deepcopy(contract["execution_boundary"]),
        "claim_boundary": contract["claim_boundary"],
    }
    validate_boundary_receipt(receipt, contract)
    return receipt


def validate_boundary_receipt(receipt, contract=None):
    contract = deepcopy(contract or load_contract())
    policy = contract["boundary_policy"]
    source = contract["source"]
    ordered = (
        receipt["event_start_seconds"]
        <= receipt["observable_input_start_seconds"]
        < receipt["prediction_cutoff_seconds"]
        < receipt["observable_behavior_start_seconds"]
        < receipt["observable_behavior_end_seconds"]
        <= receipt["event_end_seconds"]
    )
    if not ordered:
        raise B53ContractError("temporal_order_invalid")
    if receipt["observable_input_start_seconds"] < policy["head_margin_seconds"]:
        raise B53ContractError("head_margin_violated")
    if source["duration_seconds"] - receipt["observable_behavior_end_seconds"] < policy[
        "tail_margin_seconds"
    ]:
        raise B53ContractError("tail_margin_violated")
    if (
        receipt["prediction_cutoff_seconds"]
        - receipt["observable_input_start_seconds"]
        != policy["observable_context_seconds"]
    ):
        raise B53ContractError("observable_context_length_mismatch")
    if (
        receipt["observable_behavior_start_seconds"]
        - receipt["prediction_cutoff_seconds"]
        != policy["prediction_to_behavior_gap_seconds"]
    ):
        raise B53ContractError("prediction_gap_mismatch")
    if (
        receipt["observable_behavior_end_seconds"]
        - receipt["observable_behavior_start_seconds"]
        != policy["hidden_future_seconds"]
    ):
        raise B53ContractError("hidden_future_length_mismatch")
    return {"valid": True}


if __name__ == "__main__":
    validate_implementation_freeze()
    print(json.dumps(select_temporal_boundary(), ensure_ascii=False, indent=2))
