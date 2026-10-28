#!/usr/bin/env python3
"""M56.8 durable-generation-release-gated formal scoring.

The new sanctioned scoring entry accepts only a run id.  It validates the
frozen M56.4 pre-score state and the exact M56.7 mode/release, durably commits a
pre-outcome authorization gate, and only then delegates to the unchanged M56.4
scorer.  Historical M56.4 results do not retroactively gain this authority.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import inspect
import json
from pathlib import Path
from typing import Any

import m56_4_separate_formal_scorer as scorer_m56
import m56_7_mac_full_sync_generation as durable_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_8_durable_release_gated_scoring_v1.json"
GATE_FILENAME = "m56_8_durable_scoring_gate.json"
AUDIT_SCHEMA = "uruha_m56_durable_release_gated_scoring_audit_v1"
REHEARSAL_SCHEMA = "uruha_m56_durable_release_gated_scoring_rehearsal_v1"


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
        "frozen_dependencies", "authorization_chain", "retroactive_boundary",
        "unchanged_scientific_semantics", "authorization", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_durable_release_gated_scoring_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_any_real_m56_target_outcome_access":
        errors.append("contract.status")
    api = contract.get("public_api") or {}
    if api.get("function") != "execute_durable_release_gated_formal_scoring":
        errors.append("public_api.function")
    if api.get("parameters") != ["run_id"]:
        errors.append("public_api.parameters")
    if any(api.get(name) is not False for name in (
        "mode_or_release_injection_allowed", "prediction_or_outcome_injection_allowed",
        "result_or_readiness_injection_allowed", "metric_threshold_or_bypass_injection_allowed",
    )):
        errors.append("public_api.injection")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 6:
        errors.append("dependencies.count")
    for relative_path, expected_hash in dependencies.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative_path}")
    chain = contract.get("authorization_chain") or {}
    if any(chain.get(name) is not True for name in (
        "m56_4_prescore_integrity_required", "m56_7_mode_exact_match_required",
        "m56_7_durable_release_exact_match_required", "m56_8_gate_before_private_outcome_access",
        "m56_8_gate_file_and_directory_fullsync_required", "unchanged_m56_4_scorer_after_gate",
    )):
        errors.append("authorization_chain.required")
    if chain.get("scorer_model_call_count") != 0:
        errors.append("authorization_chain.model_calls")
    retroactive = contract.get("retroactive_boundary") or {}
    if any(retroactive.get(name) is not False for name in (
        "preexisting_m56_4_access_without_m56_8_gate_allowed",
        "preexisting_m56_4_report_without_m56_8_gate_allowed",
        "preexisting_m56_4_result_without_m56_8_gate_allowed",
        "historical_m56_4_direct_result_gains_m56_8_authority",
        "same_host_filesystem_access_cryptographically_prevented",
    )):
        errors.append("retroactive_boundary.denials")
    if retroactive.get("identical_gate_restart_allowed") is not True:
        errors.append("retroactive_boundary.restart")
    unchanged = contract.get("unchanged_scientific_semantics") or {}
    if not unchanged or any(value is not True for value in unchanged.values()):
        errors.append("unchanged_scientific_semantics")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization.current")
    if list(inspect.signature(execute_durable_release_gated_formal_scoring).parameters) != ["run_id"]:
        errors.append("implementation.public_signature")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
    }


def _paths(run_id: str) -> dict[str, Path]:
    scoring = scorer_m56._paths(run_id)
    durable = durable_m56._run_paths(run_id)
    if scoring["root"] != durable["root"]:
        raise RuntimeError("M56.4 and M56.7 private run roots differ")
    return {
        **scoring,
        "m56_7_mode": durable["m56_7_mode"],
        "m56_7_release": durable["m56_7_release"],
        "m56_8_gate": scoring["commitments"] / GATE_FILENAME,
    }


def _expected_m56_7_release(
    run_id: str, mode: dict[str, Any], rows: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    return durable_m56.build_durable_release(
        run_id,
        mode,
        {
            "submission_hash": rows["submission"]["submission_hash"],
            "commitment_hash": rows["commitment"]["commitment_hash"],
            "scoring_release_hash": rows["release"]["release_hash"],
            "model_call_count": rows["commitment"]["model_call_count"],
        },
    )


def validate_durable_scoring_authorization(run_id: str) -> dict[str, Any]:
    errors: list[str] = []
    contract_report = validate_contract()
    errors.extend(f"contract:{name}" for name in contract_report["errors"])
    durable_contract = durable_m56.validate_contract()
    errors.extend(f"m56_7_contract:{name}" for name in durable_contract["errors"])
    try:
        paths = _paths(run_id)
        rows = scorer_m56.load_prescore_inputs(run_id)
        prescore = scorer_m56.validate_prescore_inputs(run_id, rows)
        errors.extend(f"prescore:{name}" for name in prescore["errors"])
        mode = load_json(paths["m56_7_mode"])
        release = load_json(paths["m56_7_release"])
        expected_mode = durable_m56.build_mode_commitment(
            run_id, rows["lease"]["lease_hash"], paths["telemetry"]
        )
        expected_release = _expected_m56_7_release(run_id, expected_mode, rows)
        if mode != expected_mode:
            errors.append("m56_7_mode.content_or_hash")
        if release != expected_release:
            errors.append("m56_7_release.content_or_hash")
    except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError, RuntimeError, ValueError) as exc:
        return {
            "valid": False,
            "scoring_ready": False,
            "errors": errors + [f"inputs:{exc}"],
            "blockers": [],
            "target_outcome_access_count": 0,
        }
    return {
        "valid": not errors,
        "scoring_ready": not errors and prescore["scoring_ready"],
        "errors": errors,
        "blockers": deepcopy(prescore["blockers"]),
        "target_outcome_access_count": 0,
        "rows": rows,
        "mode": mode,
        "release": release,
        "prescore": prescore,
        "m56_7_mode_commitment_hash": mode.get("mode_commitment_hash"),
        "m56_7_durable_release_hash": release.get("durable_release_hash"),
        "authorization_hash": digest({
            "contract_hash": contract_report["contract_hash"],
            "run_id": run_id,
            "prescore_hash": prescore.get("prescore_hash"),
            "mode_commitment_hash": mode.get("mode_commitment_hash"),
            "durable_release_hash": release.get("durable_release_hash"),
        }),
    }


def build_durable_scoring_gate(run_id: str, validation: dict[str, Any]) -> dict[str, Any]:
    if not validation.get("valid") or not validation.get("scoring_ready"):
        raise PermissionError("M56.8 gate requires valid, scoring-ready M56.4 and M56.7 inputs")
    rows = validation["rows"]
    value = {
        "schema": "uruha_m56_durable_release_scoring_gate_v1",
        "version": "1.0.0",
        "status": "durable_generation_release_validated_before_private_outcome_access",
        "run_id": run_id,
        "contract_hash": validate_contract()["contract_hash"],
        "m56_4_scorer_contract_hash": scorer_m56.validate_contract()["contract_hash"],
        "m56_7_generation_contract_hash": durable_m56.validate_contract()["contract_hash"],
        "m56_4_prescore_hash": validation["prescore"]["prescore_hash"],
        "m56_7_mode_commitment_hash": validation["m56_7_mode_commitment_hash"],
        "m56_7_durable_release_hash": validation["m56_7_durable_release_hash"],
        "lease_hash": rows["lease"]["lease_hash"],
        "submission_hash": rows["submission"]["submission_hash"],
        "prediction_commitment_hash": rows["commitment"]["commitment_hash"],
        "scoring_release_hash": rows["release"]["release_hash"],
        "generation_model_call_count": rows["commitment"]["model_call_count"],
        "scorer_model_call_count": 0,
        "target_outcome_access_before_gate": 0,
        "file_fsync_required": True,
        "file_f_fullfsync_required": True,
        "directory_fsync_required": True,
        "directory_f_fullfsync_required": True,
        "formal_result_claim_authorized_before_m56_4_result": False,
        "production_memory_write_authorized": False,
        "external_deployment_authorized": False,
    }
    value["gate_hash"] = digest(value)
    return value


def validate_durable_scoring_gate(
    gate: dict[str, Any], run_id: str, validation: dict[str, Any]
) -> dict[str, Any]:
    expected = build_durable_scoring_gate(run_id, validation)
    errors = [] if gate == expected else ["gate.content_or_hash"]
    return {
        "valid": not errors,
        "errors": errors,
        "gate_hash": gate.get("gate_hash") if isinstance(gate, dict) else None,
    }


def _preexisting_m56_4_outcome_artifacts(paths: dict[str, Path]) -> list[str]:
    candidates = (
        paths["commitments"] / scorer_m56.ACCESS_RECEIPT_FILENAME,
        paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME,
        paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME,
    )
    return [path.name for path in candidates if path.exists()]


def _commit_or_validate_gate(
    paths: dict[str, Path], run_id: str, validation: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    expected = build_durable_scoring_gate(run_id, validation)
    gate_path = paths["m56_8_gate"]
    if gate_path.exists():
        existing = load_json(gate_path)
        report = validate_durable_scoring_gate(existing, run_id, validation)
        if not report["valid"]:
            raise ValueError("existing immutable M56.8 scoring gate differs")
        return existing, "validated_existing_identical"
    prior = _preexisting_m56_4_outcome_artifacts(paths)
    if prior:
        raise PermissionError(
            "preexisting M56.4 outcome-access/result state cannot be retroactively certified: "
            + ", ".join(prior)
        )
    try:
        durable_m56._durable_atomic_write_json(gate_path, expected, exclusive=True)
        return expected, "created_before_private_outcome_access"
    except FileExistsError:
        existing = load_json(gate_path)
        report = validate_durable_scoring_gate(existing, run_id, validation)
        if not report["valid"]:
            raise ValueError("concurrent immutable M56.8 scoring gate differs")
        return existing, "validated_concurrent_identical"


def _validate_delegated_result(
    run_id: str, paths: dict[str, Path], gate: dict[str, Any], result: dict[str, Any]
) -> None:
    if result.get("status") != "formal_scoring_complete_result_committed":
        return
    report = load_json(paths["scoring"] / scorer_m56.SCORE_REPORT_FILENAME)
    commitment = load_json(paths["commitments"] / scorer_m56.RESULT_COMMITMENT_FILENAME)
    report_validation = scorer_m56.validate_score_report(report)
    commitment_validation = scorer_m56.validate_result_commitment(commitment, report)
    if not report_validation["valid"] or not commitment_validation["valid"]:
        raise ValueError("M56.4 delegated result validation failed")
    expected = {
        "run_id": run_id,
        "submission_hash": gate["submission_hash"],
        "prediction_commitment_hash": gate["prediction_commitment_hash"],
        "scoring_release_hash": gate["scoring_release_hash"],
    }
    if any(report.get(name) != value for name, value in expected.items()):
        raise ValueError("M56.4 result does not match the M56.8 gate")
    if result.get("result_commitment_hash") != commitment.get("result_commitment_hash"):
        raise ValueError("M56.4 returned result commitment hash differs from disk")


def execute_durable_release_gated_formal_scoring(run_id: str) -> dict[str, Any]:
    """Authorize scoring only after the exact M56.7 durable release is proven."""

    paths = _paths(run_id)
    validation = validate_durable_scoring_authorization(run_id)
    if not validation["valid"]:
        raise PermissionError(
            "M56.8 durable-release authorization failed: " + "; ".join(validation["errors"])
        )
    if not validation["scoring_ready"]:
        result = scorer_m56.execute_formal_scoring(run_id)
        return {
            **result,
            "m56_8_gate_created": False,
            "m56_8_scoring_authorized": False,
            "m56_7_durable_release_hash": validation["m56_7_durable_release_hash"],
        }
    gate, gate_status = _commit_or_validate_gate(paths, run_id, validation)
    result = scorer_m56.execute_formal_scoring(run_id)
    _validate_delegated_result(run_id, paths, gate, result)
    return {
        **result,
        "m56_8_gate_hash": gate["gate_hash"],
        "m56_8_gate_write": gate_status,
        "m56_8_gate_created": True,
        "m56_8_scoring_authorized": result.get("formal_result_created") is True,
        "m56_7_durable_release_hash": validation["m56_7_durable_release_hash"],
    }


def build_synthetic_rehearsal() -> dict[str, Any]:
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "authorization_chain_mechanics_only",
        "stages": [
            "m56_4_prescore_integrity",
            "m56_7_mode_and_durable_release_exact_validation",
            "m56_8_durable_gate_commitment",
            "unchanged_m56_4_outcome_join_and_result",
        ],
        "historical_m56_4_direct_result_gains_m56_8_authority": False,
        "same_host_historical_api_cryptographically_disabled": False,
        "human_evidence_count": 0,
        "formal_model_call_count": 0,
        "target_outcome_access_count": 0,
        "formal_result_created": False,
        "claim_boundary": "State-machine composition only; no human data, formal call, outcome access or result.",
    }
    value["rehearsal_hash"] = digest(value)
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    generation = durable_m56.build_live_audit()
    scoring = scorer_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "durable_release_gated_scoring_denied_waiting_for_human_chain",
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "counts": deepcopy(generation["counts"]),
        "m56_7_durable_release_available": False,
        "m56_8_gate_created": False,
        "formal_scoring_authorized": False,
        "formal_model_calls": 0,
        "target_outcome_access_count": 0,
        "formal_result_created": False,
        "blocking_gates": sorted(set(generation["blocking_gates"] + scoring["blocking_gates"])),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def build_live_report() -> dict[str, Any]:
    return {
        "schema": "uruha_m56_durable_release_gated_scoring_live_report_v1",
        "status": "durable_release_gated_scoring_denied_waiting_for_human_chain",
        "audit": build_live_audit(),
        "synthetic_rehearsal": build_synthetic_rehearsal(),
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_live_report())
    counts = report["audit"]["counts"]
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.8 耐久放行後才可正式計分</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131b;color:#f1fbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1240px;margin:auto;padding:28px}}section{{border:1px solid #31566b;border-radius:20px;background:#0b202c;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#153747,#321c3b)}}.deny{{display:inline-block;background:#662532;color:#ffd8df;border-radius:999px;padding:8px 12px;font-weight:850}}h1{{font-size:clamp(30px,5vw,46px);margin:14px 0 8px}}p{{color:#b9d6df;line-height:1.6}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;border:0;background:none;padding:0}}.metric,.step,.box{{border:1px solid #31566b;border-radius:16px;background:#0a1b25;padding:17px}}.metric strong{{display:block;color:#7de0c2;font-size:28px}}.flow{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.step b{{display:grid;place-items:center;width:32px;height:32px;border-radius:50%;background:#245e68;color:#83f0d1}}.step.gate{{border-color:#d09b4d}}.step.private{{border-color:#a45261}}.compare{{display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:center}}.arrow{{font-size:34px;color:#74dbc0}}.bad{{border-left:5px solid #e8788c}}.good{{border-left:5px solid #67d7ad}}code{{color:#8be8d0}}@media(max-width:860px){{.metrics,.flow,.compare{{grid-template-columns:1fr}}.arrow{{text-align:center;transform:rotate(90deg)}}}}
</style></head><body><main>
<section class="hero"><span class="deny">DENIED NOW · 0 OUTCOME READS</span><h1>M56.8 · 先證明預測真的耐久落盤，才准打開答案</h1><p>M56.7 已補上 Mac 斷電邊界，但舊 M56.4 計分器比它更早凍結。M56.8 把兩段正式串起來，阻止「用舊路徑計完分，再事後說它具備新耐久證據」。</p></section>
<section class="metrics"><div class="metric"><strong>{counts['v7_slots_by_ledger'][0]}/18</strong><small>真人 A</small></div><div class="metric"><strong>{counts['v7_slots_by_ledger'][1]}/18</strong><small>真人 B</small></div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong><small>正式時間列</small></div><div class="metric"><strong>0</strong><small>正式呼叫／結果</small></div></section>
<section><h2>新的不可跳步授權鏈</h2><div class="flow"><div class="step"><b>1</b><h3>M56.4 預檢</h3><p>210 列、資源、承諾都正確。</p></div><div class="step"><b>2</b><h3>M56.7 Mode</h3><p>確認從一開始就走 full-sync。</p></div><div class="step"><b>3</b><h3>Durable Release</h3><p>綁定同一 submission 與 commitment。</p></div><div class="step gate"><b>4</b><h3>M56.8 Gate</h3><p>答案前把授權本身完整落盤。</p></div><div class="step private"><b>5</b><h3>Private Score</h3><p>才交給未改動的 M56.4 開答案。</p></div></div></section>
<section><h2>修改前後差異</h2><div class="compare"><div class="box bad"><h3>舊 M56.4</h3><p>沒有任何 M56.7 產物，機制測試仍可直接產生 M56.4 result。</p></div><div class="arrow">→</div><div class="box good"><h3>目前授權入口</h3><p>缺 mode、release、exact binding 或答案早已開過，全部在 outcome 前拒絕。</p></div></div></section>
<section><h2>什麼叫「不能事後補證明」？</h2><p>如果已出現 M56.4 access receipt、score report 或 result commitment，卻沒有更早存在的 M56.8 gate，該 run 會被標為不可追溯授權，不允許補一個檔案把歷史包裝成合格。</p></section>
<section class="bad"><h2>證據邊界</h2><p>這是合作式應用流程與研究授權，不是 OS sandbox。能直接改程式或讀本機檔案的人仍可呼叫歷史 M56.4；那份結果只是不具 M56.8 authority，並非物理上無法讀取。現在也沒有真人資料、正式模型呼叫或人類方程式證據。</p></section>
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
    parser = argparse.ArgumentParser(description="M56.8 durable-release-gated formal scorer")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--serve", type=int)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.run_id:
        print(json.dumps(execute_durable_release_gated_formal_scoring(args.run_id), ensure_ascii=False, indent=2))
    elif args.rehearsal:
        print(json.dumps(build_synthetic_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
