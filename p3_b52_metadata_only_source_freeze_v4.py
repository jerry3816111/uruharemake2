"""TLS-only repair for the reviewed P3-B52 V3 Atom flow."""

from __future__ import annotations

import json
import ssl
import urllib.request
from copy import deepcopy
from pathlib import Path

import certifi

import p3_b52_metadata_only_source_freeze as v1
import p3_b52_metadata_only_source_freeze_v3 as v3


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b52_metadata_only_source_selection_v4.json"
FREEZE_PATH = (
    ROOT
    / "research"
    / "p3_b52_metadata_only_source_selection_v4_implementation_freeze_2026-09-17.json"
)


def load_config():
    return v1.load_json(CONFIG_PATH)


def _verify_binding(binding, binding_id):
    path = ROOT / str((binding or {}).get("path") or "")
    if not path.is_file():
        raise v1.B52ContractError(f"binding_missing:{binding_id}")
    if v1.sha256_bytes(path.read_bytes()) != str((binding or {}).get("sha256") or ""):
        raise v1.B52ContractError(f"binding_hash_mismatch:{binding_id}")
    return path


def validate_contract(config=None):
    config = deepcopy(config or load_config())
    errors = []
    if config.get("schema") != "uruha_p3_b52_metadata_only_source_selection_v4":
        errors.append("schema_mismatch")
    for binding_id, binding in (config.get("bindings") or {}).items():
        try:
            _verify_binding(binding, binding_id)
        except v1.B52ContractError as exc:
            errors.append(str(exc))
    tls = config.get("tls_transport") or {}
    if tls.get("ca_source") != "certifi.where()":
        errors.append("ca_source_changed")
    if tls.get("certificate_verification_enabled") is not True:
        errors.append("certificate_verification_disabled")
    if tls.get("hostname_verification_enabled") is not True:
        errors.append("hostname_verification_disabled")
    if tls.get("insecure_context_forbidden") is not True:
        errors.append("insecure_context_not_forbidden")
    if any(
        tls.get(key) is not False
        for key in ("http_endpoint_change", "proxy_change", "request_header_change")
    ):
        errors.append("non_tls_transport_change_detected")
    boundary = config.get("execution_boundary") or {}
    if boundary.get("maximum_v4_atom_retrievals") != 1:
        errors.append("atom_retrieval_count_not_one")
    if boundary.get("maximum_selected_id_postchecks") != 1:
        errors.append("postcheck_count_not_one")
    if any(
        boundary.get(key) is not False
        for key in (
            "raw_response_storage",
            "target_segment_access",
            "future_response_access",
            "gold_annotation",
            "model_generation",
            "formal_m56_artifact_change",
            "production_memory_write",
            "external_deployment",
        )
    ):
        errors.append("execution_boundary_open")
    v3_report = v3.validate_contract()
    if not v3_report["valid"]:
        errors.append("bound_v3_contract_invalid")
    return {"valid": not errors, "errors": errors, "v3_contract_valid": v3_report["valid"]}


def validate_implementation_freeze():
    freeze = v1.load_json(FREEZE_PATH)
    errors = []
    if freeze.get("status") != "frozen_before_v4_atom_or_postcheck_network_access":
        errors.append("freeze_status_invalid")
    for artifact_id, binding in (freeze.get("frozen_artifacts") or {}).items():
        try:
            _verify_binding(binding, artifact_id)
        except v1.B52ContractError as exc:
            errors.append(str(exc).replace("binding_", "frozen_artifact_", 1))
    if errors:
        raise v1.B52ContractError(";".join(errors))
    return {
        "valid": True,
        "v3_response_bytes_retained": freeze.get("v3_response_bytes_retained"),
        "v4_atom_retrieval_count_at_freeze": freeze.get(
            "v4_atom_retrieval_count_at_freeze"
        ),
        "selected_id_postcheck_count_at_freeze": freeze.get(
            "selected_id_postcheck_count_at_freeze"
        ),
    }


def build_verified_ssl_context():
    cafile = Path(certifi.where())
    if not cafile.is_file():
        raise v1.B52ContractError("certifi_ca_bundle_missing")
    context = ssl.create_default_context(cafile=str(cafile))
    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise v1.B52ContractError("verified_tls_context_not_enforced")
    return context


def fetch_atom_metadata(config=None):
    config = deepcopy(config or load_config())
    v3_config = v3.load_config()
    request = urllib.request.Request(
        v3_config["target"]["official_atom_endpoint"],
        headers={"User-Agent": v3.USER_AGENT},
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
            context=build_verified_ssl_context(),
        ) as response:
            payload = response.read()
            status = int(response.status)
    except Exception as exc:
        raise v1.B52ContractError(
            f"atom_retrieval_failed:{type(exc).__name__}"
        ) from exc
    if status != 200:
        raise v1.B52ContractError(f"atom_http_status:{status}")
    return v3.parse_atom_metadata(payload, v3_config)


def execute_v4():
    validate_implementation_freeze()
    report = validate_contract()
    if not report["valid"]:
        raise v1.B52ContractError(";".join(report["errors"]))
    v3_config = v3.load_config()
    rows = fetch_atom_metadata()
    preselection = v3.select_atom_source(rows, v3_config)
    try:
        selected_metadata = v3.fetch_selected_metadata(preselection, v3_config)
    except v1.B52ContractError as exc:
        return {
            "schema": "uruha_p3_b52_metadata_only_source_freeze_result_v4",
            "status": "selected_source_postcheck_transport_failed_no_replacement",
            **preselection,
            "postcheck_accepted": False,
            "postcheck_reasons": [str(exc)],
            "automatic_replacement_performed": False,
            "atom_retrieval_count": 1,
            "selected_id_postcheck_count": 1,
            "stored_title_count": 0,
            "stored_description_count": 0,
            "stored_transcript_count": 0,
            "target_segment_access_count": 0,
            "future_response_access_count": 0,
            "gold_annotation_count": 0,
            "model_call_count": 0,
            "formal_m56_artifact_change_count": 0,
            "claim_boundary": load_config()["claim_boundary"],
        }
    return {
        **preselection,
        **v3.finalize_no_replacement(preselection, selected_metadata, v3_config),
        "schema": "uruha_p3_b52_metadata_only_source_freeze_result_v4",
        "transport_repair": "verified_certifi_ca_bundle_only",
    }


if __name__ == "__main__":
    print(json.dumps(execute_v4(), ensure_ascii=False, indent=2))
