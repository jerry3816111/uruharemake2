from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from hashlib import sha256
import argparse
import fcntl
import inspect
import json
import os
from pathlib import Path
import platform
import stat
from typing import Any
from uuid import uuid4

import m56_3_lease_gated_generation_runner as runner_m56
import m56_5_crash_safe_no_retry_continuation as continuation_m56
import m56_6_single_writer_formal_generation as single_writer_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_7_mac_full_sync_generation_v1.json"
PRIVATE_ROOT = continuation_m56.PRIVATE_ROOT
MODE_FILENAME = "m56_7_full_sync_mode.json"
RELEASE_FILENAME = "m56_7_durable_generation_release.json"
F_FULLFSYNC = 51
AUDIT_SCHEMA = "uruha_m56_mac_full_sync_generation_audit_v1"
REHEARSAL_SCHEMA = "uruha_m56_mac_full_sync_generation_rehearsal_v1"

_ORIGINAL_ATOMIC_WRITE_JSON = runner_m56._atomic_write_json
_DURABLE_WRITER_ACTIVE: ContextVar[bool] = ContextVar("m56_7_durable_writer_active", default=False)
_DURABLE_DIRECTORY_CACHE: ContextVar[set[str] | None] = ContextVar(
    "m56_7_durable_directory_cache", default=None
)
_DURABILITY_EVENTS: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "m56_7_durability_events", default=None
)


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
        "schema", "version", "status", "single_changed_variable", "public_api",
        "frozen_dependencies", "durability_boundary", "entrypoint_boundary",
        "unchanged_scientific_semantics", "authorization", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_mac_full_sync_generation_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0" or contract.get("status") != "prospective_frozen_before_any_real_m56_generation_call":
        errors.append("contract.version_or_status")
    api = contract.get("public_api") or {}
    if api.get("function") != "execute_full_sync_formal_generation" or api.get("parameters") != ["run_id"]:
        errors.append("public_api.signature")
    if any(api.get(name) is not False for name in (
        "writer_injection_allowed", "provider_injection_allowed", "prediction_injection_allowed",
        "outcome_injection_allowed", "readiness_injection_allowed", "retry_or_fallback_override_allowed",
    )):
        errors.append("public_api.injection")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 6:
        errors.append("dependencies.count")
    for relative_path, expected_hash in dependencies.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative_path}")
    boundary = contract.get("durability_boundary") or {}
    if boundary.get("platform") != "Darwin":
        errors.append("durability.platform")
    if any(boundary.get(name) is not True for name in (
        "payload_write_complete_before_sync", "file_fsync_required", "file_f_fullfsync_required",
        "parent_directory_fsync_required", "parent_directory_f_fullfsync_required",
        "checkpoint_barrier_before_intent_removal", "mode_barrier_before_transport",
        "release_barrier_after_final_validation", "unsupported_barrier_fails_before_transport",
    )):
        errors.append("durability.required")
    if boundary.get("actual_power_cut_test_claimed") is not False:
        errors.append("durability.power_cut_claim")
    entry = contract.get("entrypoint_boundary") or {}
    if any(entry.get(name) is not True for name in (
        "m56_6_single_writer_lock_unchanged", "context_local_writer_dispatch",
        "mode_and_release_immutable",
    )):
        errors.append("entrypoint.required")
    if entry.get("older_entrypoints_gain_m56_7_authority") is not False:
        errors.append("entrypoint.legacy_authority")
    if entry.get("preexisting_m56_5_state_without_m56_7_mode_allowed") is not False:
        errors.append("entrypoint.preexisting_state")
    if entry.get("scoring_contract_changed") is not False:
        errors.append("entrypoint.scoring")
    unchanged = contract.get("unchanged_scientific_semantics") or {}
    if not unchanged or any(value is not True for value in unchanged.values()):
        errors.append("unchanged_scientific_semantics")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization.current")
    if list(inspect.signature(execute_full_sync_formal_generation).parameters) != ["run_id"]:
        errors.append("implementation.public_signature")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _record_event(kind: str, path: Path) -> None:
    events = _DURABILITY_EVENTS.get()
    if events is not None:
        events.append({"kind": kind, "path": str(path)})


def _require_bound_platform() -> None:
    if platform.system() != "Darwin":
        raise OSError("M56.7 requires the frozen Darwin F_FULLFSYNC boundary")


def _sync_file_descriptor(descriptor: int, path: Path) -> None:
    _require_bound_platform()
    os.fsync(descriptor)
    _record_event("file_fsync", path)
    fcntl.fcntl(descriptor, F_FULLFSYNC)
    _record_event("file_f_fullfsync", path)


def _sync_directory(path: Path) -> None:
    _require_bound_platform()
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        mode = os.fstat(descriptor).st_mode
        if not stat.S_ISDIR(mode):
            raise NotADirectoryError(path)
        os.fsync(descriptor)
        _record_event("directory_fsync", path)
        fcntl.fcntl(descriptor, F_FULLFSYNC)
        _record_event("directory_f_fullfsync", path)
    finally:
        os.close(descriptor)


def _validate_directory(path: Path) -> None:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise PermissionError(f"durable artifact parent must be a real directory: {path}")


def _ensure_durable_directory(path: Path) -> None:
    cache = _DURABLE_DIRECTORY_CACHE.get()
    key = str(path.resolve(strict=False))
    if cache is not None and key in cache:
        return
    if path.exists():
        _validate_directory(path)
    else:
        parent = path.parent
        if parent == path:
            raise PermissionError("cannot create a durable filesystem root")
        _ensure_durable_directory(parent)
        os.mkdir(path, 0o700)
        _validate_directory(path)
    _sync_directory(path)
    if path.parent != path:
        _sync_directory(path.parent)
    if cache is not None:
        cache.add(key)


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("short durable artifact write")
        view = view[written:]


def _durable_atomic_write_json(path: Path, value: dict[str, Any], *, exclusive: bool = False) -> None:
    path = Path(path)
    _ensure_durable_directory(path.parent)
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    target = path
    if exclusive:
        flags |= os.O_EXCL
    else:
        target = path.with_name(f".{path.name}.m56-7-{os.getpid()}-{uuid4().hex}.tmp")
        flags |= os.O_EXCL
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(target, flags, 0o600)
        created = True
        _write_all(descriptor, payload)
        _record_event("file_payload_complete", target)
        _sync_file_descriptor(descriptor, target)
        os.close(descriptor)
        descriptor = None
        if not exclusive:
            os.replace(target, path)
            target = path
        _sync_directory(path.parent)
        _record_event("artifact_commit_complete", path)
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                target.unlink(missing_ok=True)
                _sync_directory(target.parent)
            except OSError:
                pass
        raise


def _atomic_write_dispatch(path: Path, value: dict[str, Any], *, exclusive: bool = False) -> None:
    if _DURABLE_WRITER_ACTIVE.get():
        _durable_atomic_write_json(path, value, exclusive=exclusive)
        return
    _ORIGINAL_ATOMIC_WRITE_JSON(path, value, exclusive=exclusive)


def _install_context_dispatcher() -> None:
    current = runner_m56._atomic_write_json
    if current is _ORIGINAL_ATOMIC_WRITE_JSON:
        runner_m56._atomic_write_json = _atomic_write_dispatch
    elif current is not _atomic_write_dispatch:
        raise RuntimeError("M56 writer function changed outside the frozen M56.7 dispatcher")


def _run_paths(run_id: str) -> dict[str, Path]:
    paths = continuation_m56._paths(run_id)
    paths["m56_7_mode"] = paths["telemetry"] / MODE_FILENAME
    paths["m56_7_release"] = paths["commitments"] / RELEASE_FILENAME
    return paths


def _prior_generation_state(paths: dict[str, Path]) -> list[str]:
    candidates = [
        paths["mode"], paths["schedule"], paths["equation"], paths["submission"], paths["ledger"],
        paths["commitment"], paths["release"], paths["failure"], paths["m56_7_release"],
    ]
    found = [path.name for path in candidates if path.exists()]
    checkpoint_dir = paths["checkpoints"]
    if checkpoint_dir.exists() and any(checkpoint_dir.iterdir()):
        found.append(checkpoint_dir.name)
    return sorted(set(found))


def build_mode_commitment(run_id: str, lease_hash: str, telemetry: Path) -> dict[str, Any]:
    device = int(telemetry.stat().st_dev)
    value = {
        "schema": "uruha_m56_mac_full_sync_generation_mode_v1",
        "version": "1.0.0",
        "status": "full_sync_mode_committed_before_m56_5_generation_state",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m56_6_contract_hash": single_writer_m56.validate_contract()["contract_hash"],
        "m56_5_contract_hash": continuation_m56.validate_contract()["contract_hash"],
        "lease_hash": lease_hash,
        "filesystem_device": device,
        "platform": "Darwin",
        "file_barrier": ["flush_payload", "fsync", "F_FULLFSYNC"],
        "directory_barrier": ["fsync", "F_FULLFSYNC"],
        "checkpoint_barrier_before_intent_removal": True,
        "retry_count": 0,
        "fallback_count": 0,
        "generation_target_outcome_access_count": 0,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["mode_commitment_hash"] = digest(value)
    return value


def _write_or_validate_identical(path: Path, value: dict[str, Any]) -> str:
    if path.exists():
        if load_json(path) != value:
            raise FileExistsError(f"immutable M56.7 artifact differs: {path.name}")
        return "validated_existing_identical"
    _durable_atomic_write_json(path, value, exclusive=True)
    return "created"


def build_durable_release(run_id: str, mode: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": "uruha_m56_mac_full_sync_generation_release_v1",
        "version": "1.0.0",
        "status": "m56_5_generation_complete_under_full_sync_mode",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "mode_commitment_hash": mode["mode_commitment_hash"],
        "submission_hash": result["submission_hash"],
        "prediction_commitment_hash": result["commitment_hash"],
        "scoring_release_hash": result["scoring_release_hash"],
        "file_fsync_required": True,
        "file_f_fullfsync_required": True,
        "directory_fsync_required": True,
        "directory_f_fullfsync_required": True,
        "model_call_count": result["model_call_count"],
        "retry_count": 0,
        "fallback_count": 0,
        "generation_target_outcome_access_count": 0,
        "formal_result_claim_authorized": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["durable_release_hash"] = digest(value)
    return value


def execute_full_sync_formal_generation(run_id: str) -> dict[str, Any]:
    """Execute unchanged M56.5 under M56.6 lock and the M56.7 macOS full-sync writer."""

    single_writer_m56._validate_permitted_run(run_id)
    paths = _run_paths(run_id)
    with single_writer_m56._exclusive_run_lock(single_writer_m56._lock_path(run_id)):
        rows = runner_m56.load_permitted_runner_inputs(run_id)
        validation = runner_m56.validate_runner_inputs(run_id, rows)
        if not validation["valid"]:
            raise PermissionError("runner inputs invalid: " + "; ".join(validation["errors"]))
        if not paths["m56_7_mode"].exists():
            prior = _prior_generation_state(paths)
            if prior:
                raise PermissionError(
                    "preexisting M56.5 generation state lacks M56.7 full-sync mode: " + ", ".join(prior)
                )
        _install_context_dispatcher()
        events: list[dict[str, Any]] = []
        active_token = _DURABLE_WRITER_ACTIVE.set(True)
        cache_token = _DURABLE_DIRECTORY_CACHE.set(set())
        events_token = _DURABILITY_EVENTS.set(events)
        try:
            mode = build_mode_commitment(run_id, rows["lease"]["lease_hash"], paths["telemetry"])
            _write_or_validate_identical(paths["m56_7_mode"], mode)
            result = continuation_m56.execute_resumable_formal_generation(run_id)
            release = build_durable_release(run_id, mode, result)
            _write_or_validate_identical(paths["m56_7_release"], release)
            if load_json(paths["m56_7_release"]) != release:
                raise ValueError("M56.7 durable release validation failed")
            return {
                **result,
                "m56_7_mode_commitment_hash": mode["mode_commitment_hash"],
                "m56_7_durable_release_hash": release["durable_release_hash"],
                "m56_7_durable_artifact_commits_this_process": sum(
                    event["kind"] == "artifact_commit_complete" for event in events
                ),
                "m56_7_file_fullsyncs_this_process": sum(
                    event["kind"] == "file_f_fullfsync" for event in events
                ),
                "m56_7_directory_fullsyncs_this_process": sum(
                    event["kind"] == "directory_f_fullfsync" for event in events
                ),
            }
        finally:
            _DURABILITY_EVENTS.reset(events_token)
            _DURABLE_DIRECTORY_CACHE.reset(cache_token)
            _DURABLE_WRITER_ACTIVE.reset(active_token)


def build_synthetic_rehearsal() -> dict[str, Any]:
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "syscall_order_and_fault_fixture_only",
        "intent_file_and_directory_barrier_before_transport": True,
        "checkpoint_file_and_directory_barrier_before_intent_removal": True,
        "unsupported_fullsync_rejected_before_delegate": True,
        "checkpoint_plus_intent_restart_action": "reuse_without_model_recall",
        "intent_only_restart_action": "terminal_no_recall",
        "human_evidence_count": 0,
        "formal_model_call_count": 0,
        "target_outcome_access_count": 0,
        "actual_power_cut_performed": False,
        "formal_result_created": False,
        "claim_boundary": "Syscall-order and forged-path mechanics only; no actual outage, human data, formal model call, score, or result.",
    }
    value["rehearsal_hash"] = digest(value)
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    upstream = single_writer_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": (
            "full_sync_entry_ready_for_authorized_run"
            if upstream["formal_generation_authorized"]
            else "full_sync_entry_denied_waiting_for_human_chain"
        ),
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "platform_observed": platform.system(),
        "f_fullfsync_command": F_FULLFSYNC,
        "counts": deepcopy(upstream["counts"]),
        "formal_generation_authorized": upstream["formal_generation_authorized"],
        "formal_model_calls": 0,
        "generation_target_outcome_access_count": 0,
        "m56_7_mode_created": False,
        "m56_7_durable_release_created": False,
        "formal_result_created": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def build_live_report() -> dict[str, Any]:
    return {
        "schema": "uruha_m56_mac_full_sync_generation_live_report_v1",
        "status": "full_sync_entry_denied_waiting_for_human_chain",
        "audit": build_live_audit(),
        "synthetic_rehearsal": build_synthetic_rehearsal(),
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    audit = report["audit"]
    counts = audit["counts"]
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.7 Mac Full-Sync Generation Commit</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131b;color:#f1fbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}section{{border:1px solid #31566b;border-radius:20px;background:#0b202c;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#153747,#271c3b)}}.deny{{display:inline-block;background:#662532;color:#ffd8df;border-radius:999px;padding:8px 12px;font-weight:850}}h1{{font-size:clamp(30px,5vw,44px);margin:14px 0 8px}}p{{color:#afd0dc;line-height:1.6}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;border:0;background:none;padding:0}}.metric,.step,.state{{border:1px solid #31566b;border-radius:16px;background:#0a1b25;padding:16px}}.metric strong{{display:block;color:#7de0c2;font-size:27px}}.flow{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.step b{{display:grid;place-items:center;width:31px;height:31px;border-radius:50%;background:#245e68;color:#83f0d1}}.step.good{{border-color:#3a8d76}}.step.call{{border-color:#92714b}}.states{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.state.good{{border-color:#3a8d76}}.state.bad{{border-color:#a45261}}.beforeafter{{display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:center}}.box{{border:1px solid #386278;border-radius:17px;background:#0a1b25;padding:18px;min-height:145px}}.arrow{{font-size:34px;color:#74dbc0}}.boundary{{border-left:5px solid #e8788c;background:#281820;color:#ffdce2}}code{{color:#8be8d0}}@media(max-width:850px){{.metrics,.flow,.states,.beforeafter{{grid-template-columns:1fr}}.arrow{{text-align:center;transform:rotate(90deg)}}}}
</style></head><body><main>
<section class="hero"><span class="deny">DENIED NOW · 0 FORMAL CALLS</span><h1>M56.7 · 模型回答後，先真的落盤再往下走</h1><p>M56.5 能從程式崩潰續跑，M56.6 能阻止重複啟動；M56.7 補上 Mac 突然斷電時最關鍵的檔案與目錄同步邊界。</p></section>
<section class="metrics"><div class="metric"><strong>{counts['v7_slots_by_ledger'][0]}/18</strong><small>真人 A</small></div><div class="metric"><strong>{counts['v7_slots_by_ledger'][1]}/18</strong><small>真人 B</small></div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong><small>正式時間列</small></div><div class="metric"><strong>0</strong><small>正式呼叫／結果</small></div></section>
<section><h2>為什麼只同步檔案還不夠？</h2><div class="beforeafter"><div class="box"><h3>修改前</h3><p>checkpoint 內容做了 <code>fsync</code>，但「這個檔名存在於資料夾中」沒有同步。突然斷電後可能只剩 intent。</p></div><div class="arrow">→</div><div class="box"><h3>修改後</h3><p>檔案與父資料夾都做 <code>fsync + F_FULLFSYNC</code>；兩道 barrier 完成後，才允許清掉 intent。</p></div></div></section>
<section><h2>一次模型步驟的完整落盤順序</h2><div class="flow"><div class="step good"><b>1</b><h3>Intent</h3><p>呼叫前先完整同步。</p></div><div class="step call"><b>2</b><h3>Model</h3><p>維持一次 transport、零 retry。</p></div><div class="step good"><b>3</b><h3>Checkpoint</h3><p>結果與資源一起寫入。</p></div><div class="step good"><b>4</b><h3>File + Dir</h3><p>檔案及目錄都 full-sync。</p></div><div class="step good"><b>5</b><h3>Clear intent</h3><p>只有 barrier 成功後才進行。</p></div></div></section>
<section><h2>重開機後只有三種可解釋狀態</h2><div class="states"><div class="state good"><h3>checkpoint</h3><p>已完整落盤，直接沿用，不重呼模型。</p></div><div class="state good"><h3>checkpoint + intent</h3><p>刪除尚未持久化也安全；驗證 checkpoint 後沿用。</p></div><div class="state bad"><h3>只有 intent</h3><p>不知道模型是否回覆，維持 terminal、禁止重呼。</p></div></div></section>
<section><h2>代價與沒有改變的實驗</h2><p>每個新增正式產物多了檔案與目錄的穩定儲存同步，會增加 I/O 延遲；但 prediction、prompt、模型、token、順序、score、human gate 與 outcome isolation 全部不變。工程 fixture 仍不是正式結果。</p></section>
<section class="boundary"><strong>證據邊界：</strong>測試可證明程式依序呼叫 macOS 最強的本機同步 API，但沒有真的拔電，也不能保證故障硬碟或控制器一定遵守。這不增加真人資料、模型分數、Equation V1 證據、人類方程式成立或 production 授權。</section>
</main></body></html>"""


def serve_demo(port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    page = render_dashboard().encode("utf-8")

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
    parser = argparse.ArgumentParser(description="M56.7 macOS full-sync formal generation entry")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--serve", type=int)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.run_id:
        print(json.dumps(execute_full_sync_formal_generation(args.run_id), ensure_ascii=False, indent=2))
    elif args.rehearsal:
        print(json.dumps(build_synthetic_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
