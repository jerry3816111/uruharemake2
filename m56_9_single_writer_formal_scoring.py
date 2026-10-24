#!/usr/bin/env python3
"""M56.9 same-host single-writer wrapper for durable formal scoring.

The sanctioned entry validates a standard M56.8 run, owns one nonblocking
per-run OS lock across the unchanged M56.8 delegate, and rejects overlapping
callers before they can enter the private-outcome path.  It deliberately does
not claim exactly-once access across later sequential invocations.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import errno
import fcntl
from hashlib import sha256
import html
import inspect
import json
import os
from pathlib import Path
import stat
from typing import Any, Iterator

import m56_4_separate_formal_scorer as scorer_m56
import m56_8_durable_release_gated_scoring as gated_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_9_single_writer_formal_scoring_v1.json"
PRIVATE_ROOT = scorer_m56.PRIVATE_ROOT
LOCK_FILENAME = "m56_9_single_writer_scoring.lock"
AUDIT_SCHEMA = "uruha_m56_single_writer_formal_scoring_audit_v1"
REHEARSAL_SCHEMA = "uruha_m56_single_writer_formal_scoring_rehearsal_v1"


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
        "sequential_replay_boundary", "unchanged_m56_8_semantics", "authorization",
        "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_single_writer_formal_scoring_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_any_real_m56_target_outcome_access":
        errors.append("contract.status")
    api = contract.get("public_api") or {}
    if api.get("function") != "execute_single_writer_durable_release_gated_formal_scoring":
        errors.append("public_api.function")
    if api.get("parameters") != ["run_id"]:
        errors.append("public_api.parameters")
    if any(api.get(name) is not False for name in (
        "lock_or_wait_override_allowed", "prediction_or_outcome_injection_allowed",
        "result_or_readiness_injection_allowed",
        "metric_threshold_retry_fallback_or_bypass_injection_allowed",
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
        "fixed_file_in_private_telemetry_compartment",
        "valid_m56_8_run_required_before_lock_file_creation", "regular_file_required",
        "current_process_owner_required", "single_hard_link_required",
        "descriptor_path_identity_revalidated", "held_for_entire_m56_8_delegate",
        "released_on_normal_return_or_exception", "released_by_os_on_process_death",
    )):
        errors.append("lock_boundary.required")
    if boundary.get("symlink_allowed") is not False:
        errors.append("lock_boundary.symlink")
    if boundary.get("group_or_world_permissions_allowed") is not False:
        errors.append("lock_boundary.permissions")
    if boundary.get("persistent_lock_file_is_authority") is not False:
        errors.append("lock_boundary.authority")
    contention = contract.get("contention_policy") or {}
    if contention.get("simultaneous_same_run_delegate_entries") != 1:
        errors.append("contention_policy.delegate_count")
    if contention.get("simultaneous_same_run_private_outcome_loads") != 1:
        errors.append("contention_policy.outcome_count")
    if any(contention.get(name) is not False for name in (
        "wait_allowed", "contender_m56_8_entry_allowed",
        "contender_private_outcome_access_allowed", "contender_score_or_result_write_allowed",
    )):
        errors.append("contention_policy.denials")
    if contention.get("retry_count") != 0 or contention.get("fallback_count") != 0:
        errors.append("contention_policy.retry_or_fallback")
    sequential = contract.get("sequential_replay_boundary") or {}
    if sequential.get("overlapping_duplicate_outcome_join_prevented") is not True:
        errors.append("sequential_boundary.concurrent")
    if sequential.get("sequential_invocation_after_lock_release_may_reopen_outcome") is not True:
        errors.append("sequential_boundary.honesty")
    if any(sequential.get(name) is not False for name in (
        "exactly_once_outcome_access_across_process_lifetimes", "distributed_lock_claimed",
        "same_host_malicious_access_cryptographically_prevented",
    )):
        errors.append("sequential_boundary.overclaim")
    unchanged = contract.get("unchanged_m56_8_semantics") or {}
    if not unchanged or any(value is not True for value in unchanged.values()):
        errors.append("unchanged_m56_8_semantics")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization.current")
    if list(inspect.signature(execute_single_writer_durable_release_gated_formal_scoring).parameters) != ["run_id"]:
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
    report = gated_m56.validate_durable_scoring_authorization(run_id)
    if not report["valid"]:
        raise PermissionError(
            "M56.9 requires a valid standard M56.8 run before lock creation: "
            + "; ".join(report["errors"])
        )


def _validate_lock_descriptor(path: Path, descriptor: int) -> os.stat_result:
    descriptor_stat = os.fstat(descriptor)
    if not stat.S_ISREG(descriptor_stat.st_mode):
        raise PermissionError("formal scoring lock must be a regular file")
    if descriptor_stat.st_uid != os.getuid():
        raise PermissionError("formal scoring lock must be owned by the current user")
    if descriptor_stat.st_nlink != 1:
        raise PermissionError("formal scoring lock must have exactly one hard link")
    if stat.S_IMODE(descriptor_stat.st_mode) & 0o077:
        raise PermissionError("formal scoring lock must not grant group or world permissions")
    path_stat = path.lstat()
    if stat.S_ISLNK(path_stat.st_mode):
        raise PermissionError("formal scoring lock may not be a symlink")
    if (descriptor_stat.st_dev, descriptor_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino):
        raise PermissionError("formal scoring lock descriptor/path identity changed")
    return descriptor_stat


@contextmanager
def _exclusive_scoring_lock(path: Path) -> Iterator[dict[str, int]]:
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
                raise PermissionError("formal scoring run already has an active local owner") from exc
            raise
        locked = True
        descriptor_stat = _validate_lock_descriptor(path, descriptor)
        yield {"device": int(descriptor_stat.st_dev), "inode": int(descriptor_stat.st_ino)}
    finally:
        if locked:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def execute_single_writer_durable_release_gated_formal_scoring(run_id: str) -> dict[str, Any]:
    """Run unchanged M56.8 while owning the one local scoring lock for this run id."""

    _validate_permitted_run(run_id)
    with _exclusive_scoring_lock(_lock_path(run_id)):
        return gated_m56.execute_durable_release_gated_formal_scoring(run_id)


def build_synthetic_rehearsal() -> dict[str, Any]:
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "cooperative_same_host_concurrency_fixture_only",
        "pre_change": {
            "overlapping_callers": 2,
            "m56_8_delegate_entries": 2,
            "private_outcome_loader_calls": 2,
            "late_result_file_collision": 1,
        },
        "post_change": {
            "overlapping_callers": 2,
            "lock_holders": 1,
            "m56_8_delegate_entries": 1,
            "private_outcome_loader_calls": 1,
            "rejected_before_m56_8": 1,
            "contender_score_or_result_writes": 0,
        },
        "sequential_replay_can_reopen_outcome": True,
        "exactly_once_across_process_lifetimes": False,
        "human_evidence_count": 0,
        "formal_model_call_count": 0,
        "real_target_outcome_access_count": 0,
        "formal_result_created": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["rehearsal_hash"] = digest(value)
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    upstream = gated_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "single_writer_scoring_denied_waiting_for_human_chain",
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "active_formal_scoring_lock_holders": 0,
        "m56_8_gate_created": False,
        "formal_scoring_authorized": False,
        "formal_model_calls": 0,
        "target_outcome_access_count": 0,
        "formal_result_created": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def build_live_report() -> dict[str, Any]:
    return {
        "schema": "uruha_m56_single_writer_formal_scoring_live_report_v1",
        "status": "single_writer_scoring_denied_waiting_for_human_chain",
        "audit": build_live_audit(),
        "synthetic_rehearsal": build_synthetic_rehearsal(),
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    audit = report["audit"]
    counts = audit["counts"]
    rehearsal = report["synthetic_rehearsal"]
    before = rehearsal["pre_change"]
    after = rehearsal["post_change"]
    boundary = html.escape(audit["claim_boundary"])
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.9 正式評分單一執行者</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131c;color:#eefaff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1220px;margin:auto;padding:28px}}section{{border:1px solid #31586c;border-radius:20px;background:#0b202d;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#153c48,#351e3d)}}.deny{{display:inline-block;background:#672633;color:#ffdae0;border-radius:999px;padding:8px 12px;font-weight:850}}h1{{font-size:clamp(30px,5vw,45px);margin:14px 0 8px}}p{{color:#b8d7e1;line-height:1.62}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;border:0;background:none;padding:0}}.metric,.lane,.step,.limit{{border:1px solid #31586c;border-radius:16px;background:#0a1b27;padding:17px}}.metric strong{{display:block;color:#78e0c2;font-size:28px}}.compare{{display:grid;grid-template-columns:1fr auto 1fr;gap:16px;align-items:stretch}}.arrow{{display:grid;place-items:center;font-size:38px;color:#70dbbc}}.bad{{border-color:#a84e60}}.good{{border-color:#2b806a}}.count{{font-size:42px;font-weight:900}}.bad .count{{color:#ff8193}}.good .count{{color:#70e0bd}}.flow{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.step b{{display:grid;place-items:center;width:34px;height:34px;border-radius:50%;background:#245e6b;color:#8af0d3}}.owner{{border-color:#2b806a}}.reject{{border-color:#a84e60}}.limit{{border-left:6px solid #e1a452;background:#272014}}code{{color:#88e8ce}}@media(max-width:850px){{.metrics,.compare,.flow{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg)}}}}
</style></head><body><main>
<section class="hero"><span class="deny">DENIED NOW · 0 REAL OUTCOME READS</span><h1>M56.9 · 同一份正式答案，同一時間只准一個評分者開啟</h1><p>M56.8 已確保答案前的耐久授權，但兩個評分程式若同時啟動，舊路徑會把同一份答案打開兩次。M56.9 在整段 M56.8 外圍加上每個 run 專屬的作業系統鎖。</p></section>
<section class="metrics"><div class="metric"><strong>{counts['v7_slots_by_ledger'][0]}/18</strong><small>真人 A</small></div><div class="metric"><strong>{counts['v7_slots_by_ledger'][1]}/18</strong><small>真人 B</small></div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong><small>正式時間列</small></div><div class="metric"><strong>0</strong><small>正式答案／結果</small></div></section>
<section><h2>真正重現到的並行錯誤</h2><div class="compare"><div class="lane bad"><h3>修改前 · M56.8</h3><div class="count">{before['private_outcome_loader_calls']} 次</div><p>{before['overlapping_callers']} 個呼叫都進入 private outcome loader；其中一個直到寫結果檔時才碰撞失敗，拒絕已經太晚。</p></div><div class="arrow">→</div><div class="lane good"><h3>修改後 · M56.9</h3><div class="count">{after['private_outcome_loader_calls']} 次</div><p>只有唯一 owner 進 M56.8；另一個在答案前被拒絕，額外結果寫入 {after['contender_score_or_result_writes']}。</p></div></div></section>
<section><h2>新的四步邊界</h2><div class="flow"><div class="step"><b>1</b><h3>只讀驗證</h3><p>先證明這是標準且有效的 M56.8 run；無效 run 不建立 lock。</p></div><div class="step owner"><b>2</b><h3>取得 owner</h3><p>同機、同 run 的 nonblocking OS lock 只讓一個程序持有。</p></div><div class="step"><b>3</b><h3>完整 M56.8</h3><p>持鎖完成 durable gate、答案 join、七組計分與 result commitment。</p></div><div class="step reject"><b>×</b><h3>同時競爭者</h3><p>不等待、不重試、不進 M56.8、不開答案，也不寫第二份結果。</p></div></div></section>
<section class="limit"><h2>誠實限制：這還不是「永遠只開一次」</h2><p>這次只修重疊執行。第一個程序結束並釋放 lock 後，稍晚再啟動一次，凍結的 M56.8 仍可能重新讀答案。要做到跨重啟 exactly-once，還需要另一個可耐久恢復的 scoring completion／outcome-access 狀態機，不能把它偷算進 M56.9。</p></section>
<section class="bad"><h2>證據邊界</h2><p>{boundary}</p></section>
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
    parser = argparse.ArgumentParser(description="M56.9 single-writer durable formal scorer")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--serve", type=int)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.run_id:
        print(json.dumps(
            execute_single_writer_durable_release_gated_formal_scoring(args.run_id),
            ensure_ascii=False,
            indent=2,
        ))
    elif args.rehearsal:
        print(json.dumps(build_synthetic_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
