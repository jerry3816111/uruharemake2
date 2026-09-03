#!/usr/bin/env python3
"""Standalone M56.13 public snapshot reader with no M56 module imports."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


ROOT = Path(__file__).resolve().parent
M56_12_CONTRACT_PATH = ROOT / "configs/m56_12_outcome_artifact_public_projection_v1.json"
M56_13_CONTRACT_PATH = ROOT / "configs/m56_13_unidirectional_public_snapshot_v1.json"
SNAPSHOT_SCHEMA = "uruha_m56_public_scoring_snapshot_v1"
PROJECTION_SCHEMA = "uruha_m56_public_scoring_state_projection_v1"
PUBLIC_ROOT_ENV = "URUHA_M56_PUBLIC_SNAPSHOT_ROOT"
DEFAULT_PUBLIC_ROOT = Path("/tmp/uruha_m56_public_snapshots")


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


def _contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    m12 = load_json(M56_12_CONTRACT_PATH)
    m13 = load_json(M56_13_CONTRACT_PATH)
    expected_m12_hash = (m13.get("frozen_dependencies") or {}).get(
        "configs/m56_12_outcome_artifact_public_projection_v1.json"
    )
    if sha256_file(M56_12_CONTRACT_PATH) != expected_m12_hash:
        raise PermissionError("M56.13 public reader refuses changed M56.12 projection contract")
    if m13.get("schema") != "uruha_m56_unidirectional_public_snapshot_contract_v1":
        raise PermissionError("M56.13 public reader contract invalid")
    return m12, m13


def _public_root() -> Path:
    raw = os.environ.get(PUBLIC_ROOT_ENV)
    return Path(raw).resolve() if raw else DEFAULT_PUBLIC_ROOT.resolve()


def _validate_snapshot_id(snapshot_id: str) -> None:
    if not isinstance(snapshot_id, str) or re.fullmatch(r"[0-9a-f]{32}", snapshot_id) is None:
        raise ValueError("snapshot_id must be exactly 32 lowercase hexadecimal characters")


def _snapshot_path(snapshot_id: str) -> Path:
    _validate_snapshot_id(snapshot_id)
    root = _public_root()
    path = root / f"{snapshot_id}.json"
    if path.parent != root:
        raise ValueError("public snapshot path escapes configured root")
    return path


def _read_secure_snapshot_file(path: Path) -> dict[str, Any]:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        descriptor_stat = os.fstat(descriptor)
        path_stat = path.lstat()
        if not stat.S_ISREG(descriptor_stat.st_mode) or stat.S_ISLNK(path_stat.st_mode):
            raise PermissionError("public snapshot must be a regular non-symlink file")
        if descriptor_stat.st_uid != os.getuid():
            raise PermissionError("public snapshot must be owned by the current user")
        if descriptor_stat.st_nlink != 1:
            raise PermissionError("public snapshot must have exactly one hard link")
        if stat.S_IMODE(descriptor_stat.st_mode) & 0o077:
            raise PermissionError("public snapshot must not grant group or world permissions")
        if (descriptor_stat.st_dev, descriptor_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino):
            raise PermissionError("public snapshot descriptor/path identity changed")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            value = json.load(handle)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if not isinstance(value, dict):
        raise ValueError("public snapshot must be a JSON object")
    return value


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


def _expected_exposure_policy() -> dict[str, bool | str]:
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


def _find_forbidden_keys(value: Any, forbidden: set[str], prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(path)
            found.extend(_find_forbidden_keys(child, forbidden, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_keys(child, forbidden, f"{prefix}[{index}]"))
    return found


def validate_projection(projection: dict[str, Any]) -> dict[str, Any]:
    m12, _ = _contracts()
    errors: list[str] = []
    schema = m12["projection_schema"]
    if not isinstance(projection, dict) or set(projection) != set(schema["top_level_fields"]):
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
    if projection.get("exposure_policy") != _expected_exposure_policy():
        errors.append("projection.exposure_policy")
    forbidden = set(m12["forbidden_public_keys"])
    errors.extend(f"projection.forbidden:{path}" for path in _find_forbidden_keys(projection, forbidden))
    return {"valid": not errors, "errors": errors, "projection_hash": projection.get("projection_hash")}


def _expected_export_policy() -> dict[str, bool | str]:
    return {
        "immutable": True,
        "raw_run_id_exposed": False,
        "private_artifacts_exposed": False,
        "public_reader_private_access_required": False,
        "writer_authentication": "content_hash_only_not_malicious_host",
    }


def validate_snapshot(snapshot: dict[str, Any], snapshot_id: str) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "snapshot_id", "projection",
        "export_policy", "snapshot_hash",
    }
    if not isinstance(snapshot, dict) or set(snapshot) != expected_fields:
        return {"valid": False, "errors": ["snapshot.fields"]}
    unhashed = {key: value for key, value in snapshot.items() if key != "snapshot_hash"}
    if snapshot.get("snapshot_hash") != digest(unhashed):
        errors.append("snapshot.hash")
    if snapshot.get("schema") != SNAPSHOT_SCHEMA or snapshot.get("version") != "1.0.0":
        errors.append("snapshot.schema")
    if snapshot.get("status") != "immutable_allowlisted_public_scoring_snapshot":
        errors.append("snapshot.status")
    if snapshot.get("snapshot_id") != snapshot_id:
        errors.append("snapshot.id_binding")
    if snapshot.get("export_policy") != _expected_export_policy():
        errors.append("snapshot.export_policy")
    projection_validation = validate_projection(snapshot.get("projection") or {})
    errors.extend(f"snapshot.projection:{name}" for name in projection_validation["errors"])
    return {"valid": not errors, "errors": errors, "snapshot_hash": snapshot.get("snapshot_hash")}


def load_public_projection(snapshot_id: str) -> dict[str, Any]:
    """Load an immutable public snapshot without importing private scoring code."""

    path = _snapshot_path(snapshot_id)
    snapshot = _read_secure_snapshot_file(path)
    validation = validate_snapshot(snapshot, snapshot_id)
    if not validation["valid"]:
        raise PermissionError("invalid public scoring snapshot: " + "; ".join(validation["errors"]))
    return deepcopy(snapshot["projection"])


def build_public_log_record(snapshot_id: str) -> dict[str, Any]:
    return load_public_projection(snapshot_id)


def build_public_telemetry_record(snapshot_id: str) -> dict[str, Any]:
    return load_public_projection(snapshot_id)


def _render_projection(projection: dict[str, Any]) -> str:
    validation = validate_projection(projection)
    if not validation["valid"]:
        raise PermissionError("invalid public projection cannot be rendered")
    state_cards = "".join(
        f'<div class="state {"yes" if value else "no"}"><b>{"✓" if value else "—"}</b><span>{html.escape(name.replace("_", " "))}</span></div>'
        for name, value in projection["state"].items()
    )
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.13 Public Snapshot</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131c;color:#effbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1080px;margin:auto;padding:28px}}section{{border:1px solid #31586c;border-radius:20px;background:#0c202c;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#173c48,#2b3a25)}}.ok{{display:inline-block;padding:8px 12px;border-radius:999px;background:#174d41;color:#9cf3d4;font-weight:850}}h1{{font-size:clamp(30px,5vw,44px);margin:14px 0 8px}}p{{color:#c2dce5;line-height:1.65}}.phase{{font-size:25px;color:#7ce2c4;font-weight:900}}.states{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.state{{border:1px solid #31586c;border-radius:14px;background:#091a25;padding:14px;display:flex;gap:10px}}.state.yes b{{color:#70e5bd}}.state.no{{opacity:.65}}.boundary{{border-left:6px solid #e1a452;background:#272014}}@media(max-width:760px){{.states{{grid-template-columns:1fr}}}}
</style></head><body><main><section class="hero"><span class="ok">PUBLIC SNAPSHOT ONLY</span><h1>M56.13 · 公開程序不需要打開 private root</h1><p>這個畫面只讀 immutable allowlisted snapshot；它沒有 run id、sample、metric、decision 或 private artifact hash。</p></section><section><h2>目前公開狀態</h2><div class="phase">{html.escape(projection['phase'])}</div><div class="states">{state_cards}</div><p>result artifact 是否存在：{"是；內容仍不公開" if projection['public_result_available'] else "否"}</p></section><section class="boundary"><h2>證據邊界</h2><p>{html.escape(projection['claim_boundary'])}</p></section></main></body></html>"""


def render_public_dashboard(snapshot_id: str) -> str:
    return _render_projection(load_public_projection(snapshot_id))


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone M56.13 public snapshot reader")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--projection", metavar="SNAPSHOT_ID")
    group.add_argument("--log", metavar="SNAPSHOT_ID")
    group.add_argument("--telemetry", metavar="SNAPSHOT_ID")
    group.add_argument("--html", metavar="SNAPSHOT_ID")
    args = parser.parse_args()
    if args.projection:
        print(json.dumps(load_public_projection(args.projection), ensure_ascii=False))
    elif args.log:
        print(json.dumps(build_public_log_record(args.log), ensure_ascii=False))
    elif args.telemetry:
        print(json.dumps(build_public_telemetry_record(args.telemetry), ensure_ascii=False))
    else:
        print(render_public_dashboard(args.html))


if __name__ == "__main__":
    main()
