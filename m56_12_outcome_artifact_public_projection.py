#!/usr/bin/env python3
"""M56.12 allowlisted public projection for private M56.10 scoring state.

Private outcome-derived artifacts are validated inside this module.  The only
sanctioned run-specific outputs are a small state-only projection, an
identical log/telemetry record, and HTML derived from that projection.  This
is a cooperative application boundary, not an OS security sandbox.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

import m56_4_separate_formal_scorer as scorer_m56
import m56_7_mac_full_sync_generation as durable_m56
import m56_8_durable_release_gated_scoring as gated_m56
import m56_10_crash_safe_outcome_join as crash_safe_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_12_outcome_artifact_public_projection_v1.json"
RESULT_PATH = ROOT / "analysis/m56_12_outcome_artifact_public_projection_result_2026-09-03.json"
PROJECTION_SCHEMA = "uruha_m56_public_scoring_state_projection_v1"
REHEARSAL_SCHEMA = "uruha_m56_outcome_artifact_public_projection_rehearsal_v1"
AUDIT_SCHEMA = "uruha_m56_outcome_artifact_public_projection_audit_v1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_contract(path: str | Path = CONTRACT_PATH) -> dict[str, Any]:
    return load_json(path)


def _public_functions() -> dict[str, Any]:
    return {
        "build_public_scoring_projection": build_public_scoring_projection,
        "build_public_log_record": build_public_log_record,
        "build_public_telemetry_record": build_public_telemetry_record,
        "render_public_dashboard": render_public_dashboard,
    }


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "single_changed_variable", "public_api",
        "frozen_dependencies", "projection_schema", "forbidden_public_keys",
        "surfaces", "authorization", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_outcome_artifact_public_projection_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_any_real_m56_target_outcome_access":
        errors.append("contract.status")
    public = contract.get("public_api") or {}
    expected_signatures = public.get("functions") or {}
    if set(expected_signatures) != set(_public_functions()):
        errors.append("public_api.functions")
    else:
        for name, function in _public_functions().items():
            if list(inspect.signature(function).parameters) != expected_signatures[name]:
                errors.append(f"public_api.signature:{name}")
    if public.get("private_artifact_projection_metric_decision_or_readiness_injection_allowed") is not False:
        errors.append("public_api.injection")
    if public.get("raw_run_id_in_public_output_allowed") is not False:
        errors.append("public_api.run_id")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 6:
        errors.append("dependencies.count")
    for relative_path, expected_hash in dependencies.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative_path}")
    schema = contract.get("projection_schema") or {}
    expected_projection_fields = [
        "schema", "version", "status", "phase", "state",
        "public_result_available", "retry_count", "fallback_count",
        "exposure_policy", "claim_boundary", "projection_hash",
    ]
    if schema.get("top_level_fields") != expected_projection_fields:
        errors.append("projection_schema.fields")
    expected_state_fields = [
        "mode_committed", "join_intent_committed", "private_checkpoint_committed",
        "canonical_private_report_committed", "result_commitment_committed",
        "terminal_failure_committed",
    ]
    if schema.get("state_fields") != expected_state_fields:
        errors.append("projection_schema.state")
    if len(schema.get("allowed_phases") or []) != 7:
        errors.append("projection_schema.phases")
    forbidden = contract.get("forbidden_public_keys") or []
    if len(forbidden) != len(set(forbidden)) or len(forbidden) < 20:
        errors.append("forbidden_public_keys")
    surfaces = contract.get("surfaces") or {}
    if not surfaces or any(value is not True for value in surfaces.values()):
        errors.append("surfaces")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _artifact_paths(run_id: str) -> dict[str, Path]:
    paths = crash_safe_m56._paths(run_id)
    return {
        "mode": paths["m56_10_mode"],
        "gate": paths["m56_8_gate"],
        "prescore_audit": paths["telemetry"] / scorer_m56.PRESCORE_AUDIT_FILENAME,
        "access_receipt": paths["commitments"] / scorer_m56.ACCESS_RECEIPT_FILENAME,
        "intent": paths["m56_10_intent"],
        "checkpoint": paths["m56_10_checkpoint"],
        "report": paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME,
        "result": paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME,
        "failure": paths["m56_10_failure"],
    }


def _load_if_exists(path: Path) -> dict[str, Any] | None:
    return load_json(path) if path.exists() else None


def _load_validated_private_state(run_id: str) -> dict[str, bool]:
    authorization = gated_m56.validate_durable_scoring_authorization(run_id)
    if not authorization.get("valid") or not authorization.get("scoring_ready"):
        raise PermissionError("M56.12 requires a valid scoring-ready M56.8 run")
    paths = _artifact_paths(run_id)
    artifacts = {name: _load_if_exists(path) for name, path in paths.items()}

    outcome_names = ("intent", "checkpoint", "report", "result", "failure")
    if artifacts["mode"] is None:
        if any(artifacts[name] is not None for name in ("gate", "prescore_audit", "access_receipt", *outcome_names)):
            raise PermissionError("M56.12 refuses outcome-related state without M56.10 mode")
        return {
            "mode_committed": False,
            "join_intent_committed": False,
            "private_checkpoint_committed": False,
            "canonical_private_report_committed": False,
            "result_commitment_committed": False,
            "terminal_failure_committed": False,
        }

    expected_mode = crash_safe_m56.build_mode_commitment(run_id, authorization)
    if artifacts["mode"] != expected_mode:
        raise ValueError("M56.12 private mode validation failed")
    if artifacts["gate"] is None:
        if any(artifacts[name] is not None for name in ("prescore_audit", "access_receipt", *outcome_names)):
            raise PermissionError("M56.12 refuses post-mode state without durable gate")
        return {
            "mode_committed": True,
            "join_intent_committed": False,
            "private_checkpoint_committed": False,
            "canonical_private_report_committed": False,
            "result_commitment_committed": False,
            "terminal_failure_committed": False,
        }

    gate_validation = gated_m56.validate_durable_scoring_gate(
        artifacts["gate"], run_id, authorization
    )
    if not gate_validation["valid"]:
        raise ValueError("M56.12 private durable gate validation failed")

    rows = authorization["rows"]
    expected_prescore = scorer_m56.build_prescore_audit(
        run_id, rows, authorization["prescore"]
    )
    if artifacts["prescore_audit"] is not None and artifacts["prescore_audit"] != expected_prescore:
        raise ValueError("M56.12 private prescore audit validation failed")
    expected_receipt = scorer_m56.build_scoring_access_receipt(run_id, rows, expected_prescore)
    if artifacts["access_receipt"] is not None and artifacts["access_receipt"] != expected_receipt:
        raise ValueError("M56.12 private access receipt validation failed")

    if artifacts["intent"] is None:
        if any(artifacts[name] is not None for name in ("checkpoint", "report", "result", "failure")):
            raise PermissionError("M56.12 refuses score state without immutable join intent")
    else:
        if artifacts["prescore_audit"] is None or artifacts["access_receipt"] is None:
            raise PermissionError("M56.12 refuses intent without its pre-outcome audit and receipt")
        expected_intent = crash_safe_m56.build_join_intent(
            run_id, expected_mode, artifacts["gate"], rows, artifacts["access_receipt"]
        )
        if artifacts["intent"] != expected_intent:
            raise ValueError("M56.12 private join intent validation failed")

    if artifacts["failure"] is not None:
        if artifacts["intent"] is None or any(
            artifacts[name] is not None for name in ("checkpoint", "report", "result")
        ):
            raise PermissionError("M56.12 refuses inconsistent terminal state")
        expected_failure = crash_safe_m56.build_terminal_failure(
            run_id, expected_mode, artifacts["intent"]
        )
        if artifacts["failure"] != expected_failure:
            raise ValueError("M56.12 private terminal failure validation failed")

    if artifacts["checkpoint"] is None:
        if artifacts["report"] is not None or artifacts["result"] is not None:
            raise PermissionError("M56.12 refuses report/result without private checkpoint")
    else:
        if artifacts["intent"] is None or artifacts["failure"] is not None:
            raise PermissionError("M56.12 refuses checkpoint without intent or with terminal failure")
        checkpoint_validation = crash_safe_m56.validate_score_checkpoint(
            artifacts["checkpoint"], run_id, expected_mode, artifacts["gate"], artifacts["intent"]
        )
        if not checkpoint_validation["valid"]:
            raise ValueError("M56.12 private checkpoint validation failed")
        if artifacts["report"] is not None:
            if artifacts["report"] != artifacts["checkpoint"]["score_report"]:
                raise ValueError("M56.12 canonical report differs from private checkpoint")
            report_validation = scorer_m56.validate_score_report(artifacts["report"])
            if not report_validation["valid"]:
                raise ValueError("M56.12 private score report validation failed")
        if artifacts["result"] is not None:
            if artifacts["report"] is None:
                raise PermissionError("M56.12 refuses result commitment without canonical report")
            result_validation = scorer_m56.validate_result_commitment(
                artifacts["result"], artifacts["report"]
            )
            if not result_validation["valid"]:
                raise ValueError("M56.12 private result commitment validation failed")

    return {
        "mode_committed": artifacts["mode"] is not None,
        "join_intent_committed": artifacts["intent"] is not None,
        "private_checkpoint_committed": artifacts["checkpoint"] is not None,
        "canonical_private_report_committed": artifacts["report"] is not None,
        "result_commitment_committed": artifacts["result"] is not None,
        "terminal_failure_committed": artifacts["failure"] is not None,
    }


def _phase_for_state(state: dict[str, bool]) -> str:
    if not state["mode_committed"]:
        return "pre_outcome_not_started"
    if not state["join_intent_committed"]:
        return "pre_outcome_mode_committed"
    if state["terminal_failure_committed"]:
        return "terminal_ambiguous_no_result"
    if not state["private_checkpoint_committed"]:
        return "private_join_incomplete_unknown_access"
    if not state["canonical_private_report_committed"]:
        return "private_checkpoint_committed"
    if not state["result_commitment_committed"]:
        return "private_report_committed"
    return "formal_result_committed"


def _exposure_policy() -> dict[str, bool | str]:
    return {
        "scope": "bounded_state_only",
        "raw_run_id_exposed": False,
        "private_artifact_hashes_exposed": False,
        "per_sample_records_exposed": False,
        "outcome_labels_exposed": False,
        "metrics_exposed": False,
        "decision_exposed": False,
        "source_or_raw_generation_exposed": False,
    }


def _find_forbidden_public_keys(value: Any, prefix: str = "") -> list[str]:
    forbidden = set(load_contract()["forbidden_public_keys"])
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(path)
            found.extend(_find_forbidden_public_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_public_keys(child, f"{prefix}[{index}]"))
    return found


def validate_public_projection(projection: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    schema = load_contract()["projection_schema"]
    expected_fields = set(schema["top_level_fields"])
    if not isinstance(projection, dict) or set(projection) != expected_fields:
        return {"valid": False, "errors": ["projection.fields"]}
    unhashed = {key: value for key, value in projection.items() if key != "projection_hash"}
    if projection.get("projection_hash") != digest(unhashed):
        errors.append("projection.hash")
    if projection.get("schema") != PROJECTION_SCHEMA or projection.get("version") != "1.0.0":
        errors.append("projection.schema")
    if projection.get("status") != "validated_private_state_bounded_public_projection":
        errors.append("projection.status")
    state = projection.get("state") or {}
    if list(state) != schema["state_fields"] or any(type(value) is not bool for value in state.values()):
        errors.append("projection.state")
    elif projection.get("phase") != _phase_for_state(state):
        errors.append("projection.phase")
    if projection.get("phase") not in schema["allowed_phases"]:
        errors.append("projection.phase_allowed")
    if projection.get("public_result_available") is not bool(state.get("result_commitment_committed")):
        errors.append("projection.result_availability")
    if projection.get("retry_count") != 0 or projection.get("fallback_count") != 0:
        errors.append("projection.retry_or_fallback")
    if projection.get("exposure_policy") != _exposure_policy():
        errors.append("projection.exposure_policy")
    errors.extend(f"projection.forbidden:{path}" for path in _find_forbidden_public_keys(projection))
    return {
        "valid": not errors,
        "errors": errors,
        "projection_hash": projection.get("projection_hash"),
    }


def build_public_scoring_projection(run_id: str) -> dict[str, Any]:
    """Validate private M56.10 state and return only the frozen public allowlist."""

    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise PermissionError("M56.12 contract invalid: " + "; ".join(contract_report["errors"]))
    state = _load_validated_private_state(run_id)
    value = {
        "schema": PROJECTION_SCHEMA,
        "version": "1.0.0",
        "status": "validated_private_state_bounded_public_projection",
        "phase": _phase_for_state(state),
        "state": state,
        "public_result_available": state["result_commitment_committed"],
        "retry_count": 0,
        "fallback_count": 0,
        "exposure_policy": _exposure_policy(),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["projection_hash"] = digest(value)
    validation = validate_public_projection(value)
    if not validation["valid"]:
        raise AssertionError("M56.12 public projection invalid: " + "; ".join(validation["errors"]))
    return value


def build_public_log_record(run_id: str) -> dict[str, Any]:
    return build_public_scoring_projection(run_id)


def build_public_telemetry_record(run_id: str) -> dict[str, Any]:
    return build_public_scoring_projection(run_id)


def _render_projection(projection: dict[str, Any]) -> str:
    validation = validate_public_projection(projection)
    if not validation["valid"]:
        raise PermissionError("M56.12 refuses invalid public projection")
    state = projection["state"]
    phase = html.escape(projection["phase"])
    state_cards = "".join(
        f'<div class="state {"yes" if value else "no"}"><b>{"✓" if value else "—"}</b><span>{html.escape(name.replace("_", " "))}</span></div>'
        for name, value in state.items()
    )
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.12 私密計分邊界</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131c;color:#effbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}section{{border:1px solid #31586c;border-radius:20px;background:#0c202c;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#173c48,#3a233e)}}.deny{{display:inline-block;padding:8px 12px;border-radius:999px;background:#672633;color:#ffdae0;font-weight:850}}h1{{font-size:clamp(30px,5vw,45px);margin:14px 0 8px}}p{{color:#c2dce5;line-height:1.65}}.membrane{{display:grid;grid-template-columns:1fr auto 1fr;gap:18px;align-items:stretch}}.private,.public{{border-radius:18px;padding:20px}}.private{{background:#291923;border:1px solid #9f4966}}.public{{background:#0b2b28;border:1px solid #3f987e}}.wall{{display:grid;place-items:center;color:#ffd481;font-weight:900;font-size:24px}}.states{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.state{{border:1px solid #31586c;border-radius:14px;background:#091a25;padding:14px;display:flex;gap:10px;align-items:center}}.state.yes b{{color:#70e5bd}}.state.no{{opacity:.68}}.phase{{font-size:22px;color:#7ce2c4;font-weight:800}}.boundary{{border-left:6px solid #e1a452;background:#272014}}@media(max-width:800px){{.membrane{{grid-template-columns:1fr}}.wall{{min-height:60px}}.states{{grid-template-columns:1fr}}}}
</style></head><body><main>
<section class="hero"><span class="deny">FORMAL SCIENCE DENIED NOW</span><h1>M56.12 · 私密答案算出的東西，不等於可以直接丟到公開畫面</h1><p>同一份經過驗證的安全投影，同時供 dashboard、log 與 telemetry 使用；任何 private report、sample、metric 或 decision 都不能由呼叫者塞進來。</p></section>
<section><h2>Private → Allowlist membrane → Public</h2><div class="membrane"><div class="private"><h3>只留在 private scoring</h3><p>checkpoint、完整 score report、30 個 pair、condition metrics、decision、artifact hashes</p></div><div class="wall">║ 只准狀態通過 ║</div><div class="public"><h3>公開面只看得到</h3><p>粗粒度 phase、六個存在狀態、是否有 result artifact、retry/fallback 為 0，以及限制聲明。</p></div></div></section>
<section><h2>這個 run 的安全狀態投影</h2><div class="phase">{phase}</div><div class="states">{state_cards}</div><p>公開結果可用：{"是（仍不公開分數與 decision）" if projection['public_result_available'] else "否"}</p></section>
<section class="boundary"><h2>仍然不能說的事</h2><p>{html.escape(projection['claim_boundary'])}</p></section>
</main></body></html>"""


def render_public_dashboard(run_id: str) -> str:
    return _render_projection(build_public_scoring_projection(run_id))


def _count_key(value: Any, wanted: str) -> int:
    if isinstance(value, dict):
        return sum((1 if key == wanted else 0) + _count_key(child, wanted) for key, child in value.items())
    if isinstance(value, list):
        return sum(_count_key(child, wanted) for child in value)
    return 0


def _private_canaries(checkpoint: dict[str, Any], report: dict[str, Any]) -> set[str]:
    values = {
        str(row["sample_id"])
        for row in report["primary_comparison"]["pairs"]
    }
    for key, value in checkpoint.items():
        if key.endswith("_hash") and isinstance(value, str):
            values.add(value)
    for key, value in report.items():
        if key.endswith("_hash") and isinstance(value, str):
            values.add(value)
    values.add(report["decision"])
    return {value for value in values if value}


def build_synthetic_containment_rehearsal() -> dict[str, Any]:
    """Measure the public membrane on one temporary forged completed run."""

    from test_m56_9_single_writer_formal_scoring import materialize_scoring_run, m569_private_roots

    started = perf_counter()
    with TemporaryDirectory(prefix="uruha-m56-12-containment-") as temp:
        root = Path(temp).resolve()
        run_id = "m56-12-forged-containment-rehearsal"
        with m569_private_roots(root):
            run_root = materialize_scoring_run(root, run_id)
            crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
            checkpoint = load_json(run_root / "scoring" / crash_safe_m56.CHECKPOINT_FILENAME)
            report = load_json(run_root / "scoring" / scorer_m56.SCORE_REPORT_FILENAME)
            naive = {"checkpoint": checkpoint, "report": report}
            projection = build_public_scoring_projection(run_id)
            log_record = build_public_log_record(run_id)
            telemetry_record = build_public_telemetry_record(run_id)
            page = render_public_dashboard(run_id)
    public_serialized = canonical({
        "projection": projection,
        "log": log_record,
        "telemetry": telemetry_record,
        "html": page,
    })
    canaries = _private_canaries(checkpoint, report)
    canary_hits = sorted(value for value in canaries if value in public_serialized)
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "all_public_surfaces_use_validated_state_only_projection",
        "contract_hash": validate_contract()["contract_hash"],
        "fixture_kind": "temporary_forged_30_row_completed_run_only",
        "before": {
            "sanctioned_run_specific_public_projection_existed": False,
            "naive_checkpoint_plus_report_utf8_bytes": len(canonical(naive).encode("utf-8")),
            "sample_id_occurrences": _count_key(naive, "sample_id"),
            "primary_pair_record_occurrences": 2 * len(report["primary_comparison"]["pairs"]),
            "condition_metric_blocks": 2 * len(report["condition_metrics"]),
            "outcome_key_hash_occurrences": _count_key(naive, "outcome_key_hash"),
            "decision_occurrences": _count_key(naive, "decision"),
        },
        "after": {
            "projection_utf8_bytes": len(canonical(projection).encode("utf-8")),
            "phase": projection["phase"],
            "public_top_level_field_count": len(projection),
            "sample_id_occurrences": _count_key(projection, "sample_id"),
            "primary_pair_record_occurrences": _count_key(projection, "pairs"),
            "condition_metric_blocks": _count_key(projection, "condition_metrics"),
            "outcome_key_hash_occurrences": _count_key(projection, "outcome_key_hash"),
            "decision_occurrences": _count_key(projection, "decision"),
        },
        "surfaces": {
            "projection_log_telemetry_byte_identical": canonical(projection) == canonical(log_record) == canonical(telemetry_record),
            "projection_forbidden_key_hits": _find_forbidden_public_keys(projection),
            "log_forbidden_key_hits": _find_forbidden_public_keys(log_record),
            "telemetry_forbidden_key_hits": _find_forbidden_public_keys(telemetry_record),
            "html_private_canary_hit_count": len(canary_hits),
            "all_surface_private_canary_hit_count": len(canary_hits),
        },
        "elapsed_seconds": perf_counter() - started,
        "scorer_model_call_count": 0,
        "real_target_outcome_access_count": 0,
        "formal_result_created": False,
        "claim_boundary": load_contract()["claim_boundary"],
        "public_projection": projection,
    }
    value["rehearsal_hash"] = digest(value)
    validation = validate_rehearsal(value)
    if not validation["valid"]:
        raise AssertionError("M56.12 rehearsal invalid: " + "; ".join(validation["errors"]))
    return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "contract_hash", "fixture_kind", "before",
        "after", "surfaces", "elapsed_seconds", "scorer_model_call_count",
        "real_target_outcome_access_count", "formal_result_created", "claim_boundary",
        "public_projection", "rehearsal_hash",
    }
    if set(value) != expected_fields:
        errors.append("rehearsal.fields")
    unhashed = {key: child for key, child in value.items() if key != "rehearsal_hash"}
    if value.get("rehearsal_hash") != digest(unhashed):
        errors.append("rehearsal.hash")
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "all_public_surfaces_use_validated_state_only_projection":
        errors.append("rehearsal.schema_or_status")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract_hash")
    before = value.get("before") or {}
    after = value.get("after") or {}
    if before.get("sanctioned_run_specific_public_projection_existed") is not False:
        errors.append("rehearsal.before")
    for name in (
        "sample_id_occurrences", "primary_pair_record_occurrences", "condition_metric_blocks",
        "outcome_key_hash_occurrences", "decision_occurrences",
    ):
        if not isinstance(before.get(name), int) or before[name] <= 0:
            errors.append(f"rehearsal.before:{name}")
        if after.get(name) != 0:
            errors.append(f"rehearsal.after:{name}")
    if after.get("phase") != "formal_result_committed":
        errors.append("rehearsal.after:phase")
    surfaces = value.get("surfaces") or {}
    if surfaces.get("projection_log_telemetry_byte_identical") is not True:
        errors.append("rehearsal.surfaces:consistency")
    for name in ("projection_forbidden_key_hits", "log_forbidden_key_hits", "telemetry_forbidden_key_hits"):
        if surfaces.get(name) != []:
            errors.append(f"rehearsal.surfaces:{name}")
    if surfaces.get("html_private_canary_hit_count") != 0 or surfaces.get("all_surface_private_canary_hit_count") != 0:
        errors.append("rehearsal.surfaces:canary")
    projection_validation = validate_public_projection(value.get("public_projection") or {})
    errors.extend(f"rehearsal.projection:{name}" for name in projection_validation["errors"])
    if value.get("scorer_model_call_count") != 0 or value.get("real_target_outcome_access_count") != 0:
        errors.append("rehearsal.real_or_model_access")
    if value.get("formal_result_created") is not False:
        errors.append("rehearsal.formal_result")
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    upstream = crash_safe_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "public_projection_engineering_only_formal_scoring_denied",
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "formal_scoring_authorized": False,
        "formal_model_calls": 0,
        "target_outcome_access_count": 0,
        "formal_result_created": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def load_saved_rehearsal(path: str | Path = RESULT_PATH) -> dict[str, Any]:
    value = load_json(path)
    validation = validate_rehearsal(value)
    if not validation["valid"]:
        raise PermissionError("M56.12 saved rehearsal invalid: " + "; ".join(validation["errors"]))
    return value


def render_demo_dashboard(result: dict[str, Any] | None = None) -> str:
    result = deepcopy(result or load_saved_rehearsal())
    validation = validate_rehearsal(result)
    if not validation["valid"]:
        raise PermissionError("M56.12 refuses invalid demo evidence")
    before = result["before"]
    after = result["after"]
    projection = result["public_projection"]
    boundary = html.escape(result["claim_boundary"])
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.12 公開投影驗證</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131c;color:#effbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1220px;margin:auto;padding:28px}}section{{border:1px solid #31586c;border-radius:20px;background:#0c202c;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#173c48,#3a233e)}}.deny{{display:inline-block;padding:8px 12px;border-radius:999px;background:#672633;color:#ffdae0;font-weight:850}}h1{{font-size:clamp(30px,5vw,45px);margin:14px 0 8px}}p{{color:#c2dce5;line-height:1.65}}.compare{{display:grid;grid-template-columns:1fr auto 1fr;gap:16px;align-items:stretch}}.box{{border-radius:18px;padding:20px}}.bad{{background:#291923;border:1px solid #9f4966}}.good{{background:#0b2b28;border:1px solid #3f987e}}.arrow{{display:grid;place-items:center;font-size:36px;color:#ffd481}}.big{{font-size:36px;font-weight:900}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.metric{{background:#091a25;border:1px solid #31586c;border-radius:15px;padding:16px}}.metric strong{{display:block;font-size:28px;color:#7ce2c4}}.membrane{{display:grid;grid-template-columns:1fr auto 1fr;gap:16px;align-items:center}}.wall{{color:#ffd481;font-weight:900}}.boundary{{border-left:6px solid #e1a452;background:#272014}}@media(max-width:820px){{.compare,.membrane{{grid-template-columns:1fr}}.grid{{grid-template-columns:1fr 1fr}}}}
</style></head><body><main>
<section class="hero"><span class="deny">DENIED NOW · 0 REAL OUTCOME READS</span><h1>M56.12 · 私密計分結果只能穿過一張白名單</h1><p>先驗證完整 private state，再只把「進行到哪裡」投影給 dashboard、log、telemetry；不是把 report 隱藏在摺疊欄位。</p></section>
<section><h2>修改前後</h2><div class="compare"><div class="box bad"><h3>Naive：checkpoint + report 直接序列化</h3><div class="big">{before['naive_checkpoint_plus_report_utf8_bytes']:,} bytes</div><p>{before['sample_id_occurrences']} 次 sample ID · {before['primary_pair_record_occurrences']} 個 pair occurrences · {before['condition_metric_blocks']} 組 condition metrics · {before['decision_occurrences']} 個 decision</p></div><div class="arrow">→</div><div class="box good"><h3>M56.12：validated state-only projection</h3><div class="big">{after['projection_utf8_bytes']:,} bytes</div><p>sample、pair、metrics、private hash、decision 全部 0；phase = {html.escape(after['phase'])}</p></div></div></section>
<section><h2>三個公開面，共用同一份投影</h2><div class="grid"><div class="metric"><strong>1</strong>allowlist projection</div><div class="metric"><strong>3/3</strong>dashboard / log / telemetry</div><div class="metric"><strong>0</strong>private canary hits</div><div class="metric"><strong>0</strong>retry / model call</div></div></section>
<section><h2>資料膜</h2><div class="membrane"><div class="box bad"><b>PRIVATE</b><p>完整 checkpoint、report、metrics、pairs、decision、hashes</p></div><div class="wall">║ validate → allowlist ║</div><div class="box good"><b>PUBLIC</b><p>{html.escape(projection['phase'])} + 六個存在狀態 + result 是否存在；分數與決策仍不公開。</p></div></div></section>
<section class="boundary"><h2>仍然不能說的事</h2><p>{boundary}</p></section>
</main></body></html>"""


def serve_demo(port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    page = render_demo_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/dashboard"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="M56.12 private-to-public scoring projection")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--serve", type=int)
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.rehearsal:
        print(json.dumps(build_synthetic_containment_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
