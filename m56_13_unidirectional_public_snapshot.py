#!/usr/bin/env python3
"""M56.13 one-way exporter from private validation to public-only snapshot."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
import inspect
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
from unittest import mock

import m56_7_mac_full_sync_generation as durable_m56
import m56_12_outcome_artifact_public_projection as projection_m56
import m56_13_public_snapshot_reader as public_reader


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_13_unidirectional_public_snapshot_v1.json"
RESULT_PATH = ROOT / "analysis/m56_13_unidirectional_public_snapshot_result_2026-09-04.json"
PUBLIC_ROOT_ENV = public_reader.PUBLIC_ROOT_ENV
SNAPSHOT_SCHEMA = public_reader.SNAPSHOT_SCHEMA
RECEIPT_SCHEMA = "uruha_m56_public_scoring_snapshot_export_receipt_v1"
REHEARSAL_SCHEMA = "uruha_m56_unidirectional_public_snapshot_rehearsal_v1"
AUDIT_SCHEMA = "uruha_m56_unidirectional_public_snapshot_audit_v1"


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


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "single_changed_variable",
        "private_exporter_api", "public_reader_api", "frozen_dependencies",
        "snapshot", "consumer_isolation", "failure_policy", "authorization",
        "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_unidirectional_public_snapshot_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_any_real_m56_target_outcome_access":
        errors.append("contract.status")
    exporter = contract.get("private_exporter_api") or {}
    if exporter.get("function") != "export_public_scoring_snapshot" or exporter.get("parameters") != ["run_id"]:
        errors.append("private_exporter_api")
    if exporter.get("snapshot_id_or_public_root_projection_private_artifact_metric_decision_or_readiness_injection_allowed") is not False:
        errors.append("private_exporter_api.injection")
    if list(inspect.signature(export_public_scoring_snapshot).parameters) != ["run_id"]:
        errors.append("private_exporter_api.signature")
    reader = contract.get("public_reader_api") or {}
    expected_reader_functions = {
        "load_public_projection": public_reader.load_public_projection,
        "build_public_log_record": public_reader.build_public_log_record,
        "build_public_telemetry_record": public_reader.build_public_telemetry_record,
        "render_public_dashboard": public_reader.render_public_dashboard,
    }
    if set(reader.get("functions") or {}) != set(expected_reader_functions):
        errors.append("public_reader_api.functions")
    else:
        for name, function in expected_reader_functions.items():
            if list(inspect.signature(function).parameters) != reader["functions"][name]:
                errors.append(f"public_reader_api.signature:{name}")
    if reader.get("private_root_parameter_or_environment_dependency_allowed") is not False:
        errors.append("public_reader_api.private_root")
    if reader.get("m56_python_module_import_allowed") is not False:
        errors.append("public_reader_api.import")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 4:
        errors.append("dependencies.count")
    for relative_path, expected_hash in dependencies.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative_path}")
    snapshot = contract.get("snapshot") or {}
    if snapshot.get("schema") != SNAPSHOT_SCHEMA or snapshot.get("snapshot_id_entropy_bits") != 128:
        errors.append("snapshot.schema_or_entropy")
    if snapshot.get("snapshot_id_regex") != "^[0-9a-f]{32}$":
        errors.append("snapshot.id")
    required_true = (
        "immutable_exclusive_full_sync_write", "regular_same_owner_single_link_required",
        "projection_must_validate_against_frozen_m56_12_allowlist",
    )
    if any(snapshot.get(name) is not True for name in required_true):
        errors.append("snapshot.required")
    required_false = (
        "snapshot_id_derived_from_run_id", "raw_run_id_in_snapshot_or_receipt_allowed",
        "symlink_allowed", "group_or_world_permissions_allowed",
        "public_root_inside_private_run_root_allowed",
    )
    if any(snapshot.get(name) is not False for name in required_false):
        errors.append("snapshot.denials")
    isolation = contract.get("consumer_isolation") or {}
    if isolation.get("fresh_child_processes_required") != 4:
        errors.append("consumer_isolation.children")
    if isolation.get("private_canary_hits_allowed") != 0 or isolation.get("private_m56_imports_allowed") != 0:
        errors.append("consumer_isolation.exposure")
    if any(isolation.get(name) is not True for name in (
        "private_root_permissions_removed_during_child_reads",
        "projection_log_telemetry_identical", "dashboard_derived_only_from_projection",
    )):
        errors.append("consumer_isolation.required")
    failure = contract.get("failure_policy") or {}
    if failure.get("retry_count") != 0 or failure.get("fallback_count") != 0:
        errors.append("failure_policy.retry")
    if any(failure.get(name) is not False for name in (
        "automatic_latest_pointer", "replacement_or_revocation", "orphan_recovery",
        "cryptographic_writer_authentication",
    )):
        errors.append("failure_policy.absent")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _public_root() -> Path:
    raw = os.environ.get(PUBLIC_ROOT_ENV)
    return Path(raw).resolve() if raw else public_reader.DEFAULT_PUBLIC_ROOT.resolve()


def _build_snapshot(snapshot_id: str, projection: dict[str, Any]) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{32}", snapshot_id) is None:
        raise ValueError("invalid generated public snapshot id")
    projection_validation = projection_m56.validate_public_projection(projection)
    if not projection_validation["valid"]:
        raise ValueError("M56.13 exporter requires a valid M56.12 projection")
    value = {
        "schema": SNAPSHOT_SCHEMA,
        "version": "1.0.0",
        "status": "immutable_allowlisted_public_scoring_snapshot",
        "snapshot_id": snapshot_id,
        "projection": deepcopy(projection),
        "export_policy": {
            "immutable": True,
            "raw_run_id_exposed": False,
            "private_artifacts_exposed": False,
            "public_reader_private_access_required": False,
            "writer_authentication": "content_hash_only_not_malicious_host",
        },
    }
    value["snapshot_hash"] = digest(value)
    return value


def _validate_export_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "snapshot_id", "snapshot_hash",
        "projection_hash", "public_snapshot_created", "private_artifacts_exported",
        "retry_count", "fallback_count", "claim_boundary", "receipt_hash",
    }
    if set(receipt) != expected_fields:
        errors.append("receipt.fields")
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    if receipt.get("receipt_hash") != digest(unhashed):
        errors.append("receipt.hash")
    if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("status") != "public_snapshot_export_committed":
        errors.append("receipt.schema_or_status")
    if re.fullmatch(r"[0-9a-f]{32}", str(receipt.get("snapshot_id") or "")) is None:
        errors.append("receipt.snapshot_id")
    if receipt.get("public_snapshot_created") is not True or receipt.get("private_artifacts_exported") is not False:
        errors.append("receipt.export")
    if receipt.get("retry_count") != 0 or receipt.get("fallback_count") != 0:
        errors.append("receipt.retry")
    forbidden = projection_m56._find_forbidden_public_keys(receipt)
    errors.extend(f"receipt.forbidden:{name}" for name in forbidden)
    return {"valid": not errors, "errors": errors, "receipt_hash": receipt.get("receipt_hash")}


def export_public_scoring_snapshot(run_id: str) -> dict[str, Any]:
    """Validate one private run and emit one immutable allowlisted public snapshot."""

    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise PermissionError("M56.13 contract invalid: " + "; ".join(contract_report["errors"]))
    private_run_root = projection_m56.crash_safe_m56._paths(run_id)["root"].resolve()
    public_root = _public_root()
    if public_root == private_run_root or private_run_root in public_root.parents:
        raise PermissionError("public snapshot root must not be inside the private run root")
    projection = projection_m56.build_public_scoring_projection(run_id)
    snapshot_id = secrets.token_hex(16)
    snapshot = _build_snapshot(snapshot_id, projection)
    public_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = public_root / f"{snapshot_id}.json"
    durable_m56._durable_atomic_write_json(path, snapshot, exclusive=True)
    loaded = public_reader.load_public_projection(snapshot_id)
    if loaded != projection:
        raise AssertionError("public snapshot post-write validation changed projection")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "version": "1.0.0",
        "status": "public_snapshot_export_committed",
        "snapshot_id": snapshot_id,
        "snapshot_hash": snapshot["snapshot_hash"],
        "projection_hash": projection["projection_hash"],
        "public_snapshot_created": True,
        "private_artifacts_exported": False,
        "retry_count": 0,
        "fallback_count": 0,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    receipt["receipt_hash"] = digest(receipt)
    validation = _validate_export_receipt(receipt)
    if not validation["valid"]:
        raise AssertionError("M56.13 export receipt invalid: " + "; ".join(validation["errors"]))
    return receipt


def _reader_import_count() -> int:
    source = (ROOT / "m56_13_public_snapshot_reader.py").read_text(encoding="utf-8")
    return sum(
        1 for line in source.splitlines()
        if re.match(r"\s*(?:from|import)\s+m56_", line)
    )


def _run_public_children(snapshot_id: str, public_root: Path, disabled_private_root: Path) -> dict[str, Any]:
    env = dict(os.environ)
    env[PUBLIC_ROOT_ENV] = str(public_root)
    env["URUHA_M56_PRIVATE_ROOT"] = str(disabled_private_root)
    modes = ("projection", "log", "telemetry", "html")
    outputs: dict[str, str] = {}
    exit_codes: dict[str, int] = {}
    stderrs_empty: dict[str, bool] = {}
    started = perf_counter()
    for mode in modes:
        child = subprocess.run(
            [sys.executable, str(ROOT / "m56_13_public_snapshot_reader.py"), f"--{mode}", snapshot_id],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        outputs[mode] = child.stdout
        exit_codes[mode] = child.returncode
        stderrs_empty[mode] = child.stderr == ""
    projection = json.loads(outputs["projection"])
    log = json.loads(outputs["log"])
    telemetry = json.loads(outputs["telemetry"])
    return {
        "outputs": outputs,
        "exit_codes": exit_codes,
        "stderrs_empty": stderrs_empty,
        "projection": projection,
        "log": log,
        "telemetry": telemetry,
        "elapsed_seconds": perf_counter() - started,
    }


def build_synthetic_snapshot_rehearsal() -> dict[str, Any]:
    """Export forged state, remove private permissions, and run four public children."""

    from test_m56_9_single_writer_formal_scoring import materialize_scoring_run, m569_private_roots

    started = perf_counter()
    with TemporaryDirectory(prefix="uruha-m56-13-snapshot-") as temp:
        base = Path(temp).resolve()
        private_root = base / "private"
        public_root = base / "public"
        run_id = "m56-13-forged-public-snapshot-rehearsal"
        old_public_root = os.environ.get(PUBLIC_ROOT_ENV)
        os.environ[PUBLIC_ROOT_ENV] = str(public_root)
        try:
            with m569_private_roots(private_root):
                run_root = materialize_scoring_run(private_root, run_id)
                projection_m56.crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
                checkpoint = projection_m56.load_json(
                    run_root / "scoring" / projection_m56.crash_safe_m56.CHECKPOINT_FILENAME
                )
                report = projection_m56.load_json(
                    run_root / "scoring" / projection_m56.scorer_m56.SCORE_REPORT_FILENAME
                )
                original_private_loader = projection_m56._load_validated_private_state
                with mock.patch.object(
                    projection_m56,
                    "_load_validated_private_state",
                    wraps=original_private_loader,
                ) as private_validator:
                    export_started = perf_counter()
                    receipt = export_public_scoring_snapshot(run_id)
                    export_seconds = perf_counter() - export_started
                    private_validation_calls = private_validator.call_count
            snapshot_path = public_root / f"{receipt['snapshot_id']}.json"
            snapshot_bytes = snapshot_path.stat().st_size
            prior_mode = stat.S_IMODE(private_root.stat().st_mode)
            os.chmod(private_root, 0)
            permission_bits_during_children = stat.S_IMODE(private_root.stat().st_mode)
            try:
                children = _run_public_children(receipt["snapshot_id"], public_root, private_root)
            finally:
                os.chmod(private_root, prior_mode)
            canaries = projection_m56._private_canaries(checkpoint, report)
            combined = "".join(children["outputs"].values())
            canary_hits = [value for value in canaries if value in combined]
            public_files = sorted(path.name for path in public_root.iterdir())
        finally:
            if old_public_root is None:
                os.environ.pop(PUBLIC_ROOT_ENV, None)
            else:
                os.environ[PUBLIC_ROOT_ENV] = old_public_root
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "public_children_succeeded_with_private_root_permissions_removed",
        "contract_hash": validate_contract()["contract_hash"],
        "fixture_kind": "temporary_forged_30_row_completed_run_only",
        "snapshot_id": receipt["snapshot_id"],
        "snapshot_id_length": len(receipt["snapshot_id"]),
        "snapshot_id_lower_hex": re.fullmatch(r"[0-9a-f]{32}", receipt["snapshot_id"]) is not None,
        "snapshot_id_contains_run_id": run_id in receipt["snapshot_id"],
        "private_validation_calls_during_export": private_validation_calls,
        "public_snapshot_file_count": len(public_files),
        "public_snapshot_utf8_bytes": snapshot_bytes,
        "private_root_permission_bits_during_children": permission_bits_during_children,
        "public_child_process_count": 4,
        "public_child_exit_codes": children["exit_codes"],
        "public_child_stderr_empty": children["stderrs_empty"],
        "all_children_reaped": True,
        "projection_log_telemetry_identical": (
            canonical(children["projection"])
            == canonical(children["log"])
            == canonical(children["telemetry"])
        ),
        "public_reader_m56_import_count": _reader_import_count(),
        "public_surface_private_canary_hit_count": len(canary_hits),
        "export_receipt_forbidden_key_hits": projection_m56._find_forbidden_public_keys(receipt),
        "snapshot_export_seconds": export_seconds,
        "four_public_children_seconds": children["elapsed_seconds"],
        "total_rehearsal_seconds": perf_counter() - started,
        "retry_count": 0,
        "fallback_count": 0,
        "scorer_model_call_count": 0,
        "real_target_outcome_access_count": 0,
        "formal_result_created": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["rehearsal_hash"] = digest(value)
    validation = validate_rehearsal(value)
    if not validation["valid"]:
        raise AssertionError("M56.13 rehearsal invalid: " + "; ".join(validation["errors"]))
    return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "contract_hash", "fixture_kind", "snapshot_id",
        "snapshot_id_length", "snapshot_id_lower_hex", "snapshot_id_contains_run_id",
        "private_validation_calls_during_export", "public_snapshot_file_count",
        "public_snapshot_utf8_bytes", "private_root_permission_bits_during_children",
        "public_child_process_count", "public_child_exit_codes", "public_child_stderr_empty",
        "all_children_reaped", "projection_log_telemetry_identical",
        "public_reader_m56_import_count", "public_surface_private_canary_hit_count",
        "export_receipt_forbidden_key_hits", "snapshot_export_seconds",
        "four_public_children_seconds", "total_rehearsal_seconds", "retry_count",
        "fallback_count", "scorer_model_call_count", "real_target_outcome_access_count",
        "formal_result_created", "claim_boundary", "rehearsal_hash",
    }
    if set(value) != expected_fields:
        errors.append("rehearsal.fields")
    unhashed = {key: child for key, child in value.items() if key != "rehearsal_hash"}
    if value.get("rehearsal_hash") != digest(unhashed):
        errors.append("rehearsal.hash")
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "public_children_succeeded_with_private_root_permissions_removed":
        errors.append("rehearsal.schema_or_status")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract_hash")
    if value.get("snapshot_id_length") != 32 or value.get("snapshot_id_lower_hex") is not True:
        errors.append("rehearsal.snapshot_id")
    if value.get("snapshot_id_contains_run_id") is not False:
        errors.append("rehearsal.snapshot_id_binding")
    if value.get("private_validation_calls_during_export") != 1:
        errors.append("rehearsal.private_validation_calls")
    if value.get("public_snapshot_file_count") != 1:
        errors.append("rehearsal.public_file_count")
    if value.get("private_root_permission_bits_during_children") != 0:
        errors.append("rehearsal.private_permissions")
    if value.get("public_child_process_count") != 4 or value.get("all_children_reaped") is not True:
        errors.append("rehearsal.children")
    exit_codes = value.get("public_child_exit_codes") or {}
    stderr = value.get("public_child_stderr_empty") or {}
    if set(exit_codes) != {"projection", "log", "telemetry", "html"} or any(code != 0 for code in exit_codes.values()):
        errors.append("rehearsal.child_exit_codes")
    if set(stderr) != set(exit_codes) or any(flag is not True for flag in stderr.values()):
        errors.append("rehearsal.child_stderr")
    if value.get("projection_log_telemetry_identical") is not True:
        errors.append("rehearsal.surface_consistency")
    if value.get("public_reader_m56_import_count") != 0:
        errors.append("rehearsal.public_imports")
    if value.get("public_surface_private_canary_hit_count") != 0:
        errors.append("rehearsal.canary")
    if value.get("export_receipt_forbidden_key_hits") != []:
        errors.append("rehearsal.receipt")
    if value.get("retry_count") != 0 or value.get("fallback_count") != 0:
        errors.append("rehearsal.retry")
    if value.get("scorer_model_call_count") != 0 or value.get("real_target_outcome_access_count") != 0:
        errors.append("rehearsal.real_or_model")
    if value.get("formal_result_created") is not False:
        errors.append("rehearsal.formal_result")
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    upstream = projection_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "public_snapshot_engineering_only_formal_scoring_denied",
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
        raise PermissionError("invalid saved M56.13 rehearsal: " + "; ".join(validation["errors"]))
    return value


def render_demo_dashboard(result: dict[str, Any] | None = None) -> str:
    result = deepcopy(result or load_saved_rehearsal())
    validation = validate_rehearsal(result)
    if not validation["valid"]:
        raise PermissionError("invalid M56.13 demo evidence")
    boundary = html.escape(result["claim_boundary"])
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.13 單向公開 Snapshot</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131c;color:#effbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1200px;margin:auto;padding:28px}}section{{border:1px solid #31586c;border-radius:20px;background:#0c202c;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#173c48,#2c283f)}}.deny{{display:inline-block;padding:8px 12px;border-radius:999px;background:#672633;color:#ffdae0;font-weight:850}}h1{{font-size:clamp(30px,5vw,44px);margin:14px 0 8px}}p{{color:#c2dce5;line-height:1.65}}.flow{{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:14px;align-items:center}}.box{{border-radius:18px;padding:20px;min-height:150px}}.private{{background:#291923;border:1px solid #9f4966}}.snapshot{{background:#282616;border:1px solid #a89341}}.public{{background:#0b2b28;border:1px solid #3f987e}}.arrow{{color:#ffd481;font-size:34px;font-weight:900}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.metric{{background:#091a25;border:1px solid #31586c;border-radius:15px;padding:16px}}.metric strong{{display:block;font-size:28px;color:#7ce2c4}}.compare{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.bad{{border-color:#9f4966}}.good{{border-color:#3f987e}}.boundary{{border-left:6px solid #e1a452;background:#272014}}@media(max-width:850px){{.flow{{grid-template-columns:1fr}}.arrow{{text-align:center}}.grid{{grid-template-columns:1fr 1fr}}.compare{{grid-template-columns:1fr}}}}
</style></head><body><main><section class="hero"><span class="deny">DENIED NOW · 0 REAL OUTCOME READS</span><h1>M56.13 · 公開頁現在只拿得到單向 Snapshot</h1><p>private exporter 驗證一次，寫出不含 run id、sample、metric、decision 的 immutable snapshot；四個全新 public process 在 private root 權限為 000 時仍成功。</p></section><section><h2>能力切割</h2><div class="flow"><div class="box private"><h3>PRIVATE EXPORTER</h3><p>唯一一次 private validation</p></div><div class="arrow">→</div><div class="box snapshot"><h3>IMMUTABLE SNAPSHOT</h3><p>{result['public_snapshot_utf8_bytes']:,} bytes · random 128-bit id</p></div><div class="arrow">→</div><div class="box public"><h3>PUBLIC READER</h3><p>0 M56 private imports · projection/log/telemetry/HTML</p></div></div></section><section><h2>修改前後</h2><div class="compare"><div class="box bad"><h3>M56.12 consumer</h3><p>private loader關閉：<strong>0/3</strong> surface可用；每個surface都重驗private state。</p></div><div class="box good"><h3>M56.13 consumer</h3><p>private root mode 000：<strong>4/4</strong> fresh child成功；private canary hit 0。</p></div></div></section><section><h2>實測</h2><div class="grid"><div class="metric"><strong>{result['private_validation_calls_during_export']}</strong>private validation</div><div class="metric"><strong>{result['public_child_process_count']}/4</strong>public children</div><div class="metric"><strong>{result['public_reader_m56_import_count']}</strong>private imports</div><div class="metric"><strong>{result['public_surface_private_canary_hit_count']}</strong>canary hits</div></div></section><section class="boundary"><h2>仍然不能說的事</h2><p>{boundary}</p></section></main></body></html>"""


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
    parser = argparse.ArgumentParser(description="M56.13 one-way public snapshot exporter")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--serve", type=int)
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.rehearsal:
        print(json.dumps(build_synthetic_snapshot_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
