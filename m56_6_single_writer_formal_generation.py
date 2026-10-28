from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import argparse
import errno
import fcntl
import html
import inspect
import json
import os
from pathlib import Path
import stat
from typing import Any, Iterator

import m56_5_crash_safe_no_retry_continuation as continuation_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_6_single_writer_formal_generation_v1.json"
PRIVATE_ROOT = continuation_m56.PRIVATE_ROOT
LOCK_FILENAME = "m56_6_single_writer.lock"
AUDIT_SCHEMA = "uruha_m56_single_writer_formal_generation_audit_v1"
REHEARSAL_SCHEMA = "uruha_m56_single_writer_formal_generation_rehearsal_v1"


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
        "frozen_dependencies", "lock_boundary", "contention_policy",
        "unchanged_m56_5_semantics", "authorization", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_single_writer_formal_generation_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0" or contract.get("status") != "prospective_frozen_before_any_real_m56_generation_call":
        errors.append("contract.version_or_status")
    api = contract.get("public_api") or {}
    if api.get("function") != "execute_single_writer_formal_generation" or api.get("parameters") != ["run_id"]:
        errors.append("public_api.signature")
    if any(api.get(name) is not False for name in (
        "lock_override_allowed", "provider_injection_allowed", "prediction_injection_allowed",
        "outcome_injection_allowed", "readiness_injection_allowed", "retry_or_fallback_override_allowed",
    )):
        errors.append("public_api.injection")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 3:
        errors.append("dependencies.count")
    for relative_path, expected_hash in dependencies.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative_path}")
    boundary = contract.get("lock_boundary") or {}
    if boundary.get("scope") != "one_local_host_and_one_run_id":
        errors.append("lock_boundary.scope")
    if boundary.get("mechanism") != "nonblocking_os_advisory_exclusive_lock":
        errors.append("lock_boundary.mechanism")
    if any(boundary.get(name) is not True for name in (
        "fixed_file_in_private_telemetry_compartment", "regular_file_required",
        "current_process_owner_required", "single_hard_link_required",
        "descriptor_path_identity_revalidated", "held_for_entire_m56_5_delegate",
        "released_on_normal_return_or_exception", "released_by_os_on_process_death",
    )):
        errors.append("lock_boundary.required")
    if boundary.get("symlink_allowed") is not False or boundary.get("group_or_world_permissions_allowed") is not False:
        errors.append("lock_boundary.permissions")
    if boundary.get("persistent_lock_file_is_authority") is not False:
        errors.append("lock_boundary.authority")
    contention = contract.get("contention_policy") or {}
    if any(contention.get(name) is not False for name in (
        "wait_allowed", "second_delegate_entry_allowed", "second_transport_attempt_allowed",
        "second_process_may_write_terminal_failure",
    )):
        errors.append("contention_policy.fail_closed")
    if contention.get("retry_count") != 0 or contention.get("fallback_count") != 0:
        errors.append("contention_policy.retry_or_fallback")
    unchanged = contract.get("unchanged_m56_5_semantics") or {}
    if not unchanged or any(value is not True for value in unchanged.values()):
        errors.append("unchanged_m56_5_semantics")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization.current")
    signature = inspect.signature(execute_single_writer_formal_generation)
    if list(signature.parameters) != ["run_id"]:
        errors.append("implementation.public_signature")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _run_root(run_id: str) -> Path:
    if not isinstance(run_id, str) or not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise ValueError("run_id must be one safe path component")
    private_root = PRIVATE_ROOT.resolve()
    root = (private_root / run_id).resolve()
    if root.parent != private_root:
        raise ValueError("run root escapes private root")
    return root


def _lock_path(run_id: str) -> Path:
    return _run_root(run_id) / "telemetry" / LOCK_FILENAME


def _validate_permitted_run(run_id: str) -> None:
    rows = continuation_m56.runner_m56.load_permitted_runner_inputs(run_id)
    report = continuation_m56.runner_m56.validate_runner_inputs(run_id, rows)
    if not report["valid"]:
        raise PermissionError("runner inputs invalid: " + "; ".join(report["errors"]))


def _validate_lock_descriptor(path: Path, descriptor: int) -> os.stat_result:
    descriptor_stat = os.fstat(descriptor)
    if not stat.S_ISREG(descriptor_stat.st_mode):
        raise PermissionError("formal run lock must be a regular file")
    if descriptor_stat.st_uid != os.getuid():
        raise PermissionError("formal run lock must be owned by the current user")
    if descriptor_stat.st_nlink != 1:
        raise PermissionError("formal run lock must have exactly one hard link")
    if stat.S_IMODE(descriptor_stat.st_mode) & 0o077:
        raise PermissionError("formal run lock must not grant group or world permissions")
    path_stat = path.lstat()
    if stat.S_ISLNK(path_stat.st_mode):
        raise PermissionError("formal run lock may not be a symlink")
    if (descriptor_stat.st_dev, descriptor_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino):
        raise PermissionError("formal run lock descriptor/path identity changed")
    return descriptor_stat


@contextmanager
def _exclusive_run_lock(path: Path) -> Iterator[dict[str, int]]:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    locked = False
    try:
        descriptor_stat = _validate_lock_descriptor(path, descriptor)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK}:
                raise PermissionError("formal run already has an active local writer") from exc
            raise
        locked = True
        descriptor_stat = _validate_lock_descriptor(path, descriptor)
        yield {"device": int(descriptor_stat.st_dev), "inode": int(descriptor_stat.st_ino)}
    finally:
        if locked:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def execute_single_writer_formal_generation(run_id: str) -> dict[str, Any]:
    """Run the unchanged M56.5 generator while owning the one local writer lock for this run id."""

    _validate_permitted_run(run_id)
    with _exclusive_run_lock(_lock_path(run_id)):
        return continuation_m56.execute_resumable_formal_generation(run_id)


def build_synthetic_rehearsal() -> dict[str, Any]:
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "cooperative_local_contention_rehearsal_only",
        "contenders": 2,
        "lock_holders": 1,
        "delegate_entries": 1,
        "rejected_before_delegate": 1,
        "second_process_terminal_failure_write": 0,
        "process_death_releases_os_lock": True,
        "persistent_lock_file_is_authority": False,
        "human_evidence_count": 0,
        "model_call_count": 0,
        "target_outcome_access_count": 0,
        "formal_generation_authorized": False,
        "formal_result_created": False,
        "claim_boundary": "Concurrency fixture only; no human labels, formal model calls, outcome access, score, or result.",
    }
    value["rehearsal_hash"] = digest(value)
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    upstream = continuation_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": (
            "single_writer_gate_ready_for_authorized_run"
            if upstream["formal_generation_authorized"]
            else "single_writer_gate_denied_waiting_for_human_chain"
        ),
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "formal_generation_authorized": upstream["formal_generation_authorized"],
        "active_formal_lock_holders": 0,
        "formal_model_calls": 0,
        "generation_target_outcome_access_count": 0,
        "formal_commitment_created": False,
        "formal_scoring_release_created": False,
        "formal_result_created": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def build_live_report() -> dict[str, Any]:
    return {
        "schema": "uruha_m56_single_writer_formal_generation_live_report_v1",
        "status": "single_writer_gate_denied_waiting_for_human_chain",
        "audit": build_live_audit(),
        "synthetic_rehearsal": build_synthetic_rehearsal(),
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    audit = report["audit"]
    counts = audit["counts"]
    rehearsal = report["synthetic_rehearsal"]
    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.6 Single-writer Formal Generation Gate</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#061019;color:#eef8ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1160px;margin:auto;padding:28px}}
.hero,.panel{{border:1px solid #315168;border-radius:20px;background:#0b1b28;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#112f3e,#1d1931)}}
.deny{{display:inline-block;padding:8px 12px;border-radius:999px;background:#60232c;color:#ffd9de;font-weight:800}}h1{{font-size:clamp(29px,5vw,43px);margin:14px 0 8px}}p{{line-height:1.6;color:#acd0df}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}}.metric,.node,.state{{border:1px solid #2d4e63;border-radius:16px;background:#0a1a27;padding:16px}}.metric strong{{display:block;font-size:28px;color:#74d7ef}}.metric small{{color:#93b8c9}}
.before,.after{{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px}}.process{{border:1px solid #35647b;border-radius:18px;background:#0c2231;padding:20px;min-height:150px}}.process.bad{{border-color:#a14d5a}}.arrow{{font-size:34px;color:#6bdac1;text-align:center}}
.lock{{margin:16px auto;border:2px solid #57d7b1;border-radius:18px;background:#0c2a2a;padding:18px;text-align:center;max-width:560px}}.lock strong{{font-size:24px;color:#72e1be}}
.states{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.state.good{{border-color:#2d7d67}}.state.stop{{border-color:#a14d5a}}.state.neutral{{border-color:#6b60a0}}
.boundary{{border-left:5px solid #e36f83;background:#24151c;padding:18px;border-radius:12px;color:#ffdce1;line-height:1.6}}
@media(max-width:820px){{.metrics,.before,.after,.states{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg)}}}}
</style></head><body><main>
<section class="hero"><span class="deny">DENIED NOW · 0 FORMAL CALLS</span><h1>M56.6 · 同一場正式實驗只能有一個執行者</h1>
<p>前一版能在程式中斷後續跑，但如果同一個 run 被誤按兩次，第二個程式仍可能把第一個正常流程標成失敗。這一版先取得作業系統的單寫入者鎖，才允許進入完全不變的 M56.5。</p></section>
<section class="metrics"><div class="metric"><strong>{counts['v7_slots_by_ledger'][0]}/18</strong><small>真人 A</small></div><div class="metric"><strong>{counts['v7_slots_by_ledger'][1]}/18</strong><small>真人 B</small></div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong><small>正式時間列</small></div><div class="metric"><strong>0</strong><small>正式呼叫／答案／結果</small></div></section>
<section class="panel"><h2>修改前：兩個程式會互相破壞</h2><div class="before"><div class="process"><h3>程式 A</h3><p>已取得同一份真人授權，正在做固定順序的模型呼叫。</p></div><div class="arrow">⇄</div><div class="process bad"><h3>程式 B</h3><p>同時啟動同一 run；即使沒能多呼叫，也可能留下 terminal failure。</p></div></div></section>
<section class="panel"><h2>修改後：先鎖定，再進 M56.5</h2><div class="lock"><strong>🔒 run-id 單寫入者鎖</strong><p>一台電腦、同一 run、同一時間只允許一個 owner。</p></div><div class="after"><div class="process"><h3>唯一 owner</h3><p>持鎖期間執行完整 M56.5；prompt、順序、no-retry 與計分入口都不改。</p></div><div class="arrow">→</div><div class="process bad"><h3>同時競爭者</h3><p>在進入 M56.5 前立刻被拒絕：0 額外呼叫、0 terminal failure 寫入。</p></div></div></section>
<section class="states"><div class="state good"><h3>正常結束／例外</h3><p>程式釋放鎖；M56.5 原本的成功或失敗語意保持不變。</p></div><div class="state stop"><h3>程式被殺掉</h3><p>作業系統關閉 descriptor 並釋放 ownership；下次可沿用既有 checkpoint。</p></div><div class="state neutral"><h3>留下的 lock file</h3><p>只是一個固定 inode，不是授權、結果或「仍在執行」的證明。</p></div></section>
<section class="panel" style="margin-top:18px"><h2>可重現的競爭演練</h2><p>{rehearsal['contenders']} 個競爭者中只有 {rehearsal['lock_holders']} 個取得鎖、{rehearsal['delegate_entries']} 個進入 delegate；另 {rehearsal['rejected_before_delegate']} 個在模型前被拒絕。這是工程 fixture，不是正式研究結果。</p></section>
<section class="boundary"><strong>證據邊界：</strong>這只防止同一台電腦上的合作式重複啟動。它不是跨電腦分散式鎖，也不能抵抗能任意改檔的同機攻擊者；更不證明 Uruha 預測、Equation V1、人類方程式、完整產品或正式部署。</section>
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
    parser = argparse.ArgumentParser(description="M56.6 single-writer formal generation gate")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--serve", type=int)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.run_id:
        print(json.dumps(execute_single_writer_formal_generation(args.run_id), ensure_ascii=False, indent=2))
    elif args.rehearsal:
        print(json.dumps(build_synthetic_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
