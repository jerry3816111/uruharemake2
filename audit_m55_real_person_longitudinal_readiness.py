#!/usr/bin/env python3
"""M55 read-only gate joining Equation V1 to the real-person data lane.

This audit never reads source media and never treats two local ledgers as two
independent humans unless each frozen ledger is complete and a separate
reliability lock exists.  It is a readiness measurement, not a data substitute.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from hashlib import sha256
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

import uruha_human_response_equation_m54 as m54
import m55_temporal_row_contract as temporal_m55
import public_persona_target_calibration_coding_v9 as v9


ROOT = Path(__file__).resolve().parent
V7_RESULT = ROOT / "configs/public_persona_contrast_coding_pilot_v7_result_lock.json"
V7_RELIABILITY = ROOT / "configs/public_persona_contrast_coding_pilot_v7_reliability_lock.json"
V9_RESULT = ROOT / "configs/public_persona_target_calibration_coding_v9_result_lock.json"
V9_FRAME = ROOT / "datasets/public_persona_target_calibration_sampling_frame_v9.json"
V9_SOURCES = ROOT / "datasets/public_persona_target_calibration_source_metadata_v9.json"
PRIVATE_V7_ROOT = ROOT / "analysis/local_public_persona_contrast_coding_v5"
DEFAULT_LEDGER_PATHS = (
    PRIVATE_V7_ROOT / "pilot-v7-coder-01.json",
    PRIVATE_V7_ROOT / "pilot-v7-coder-02.json",
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_sha256(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _binding_valid(binding):
    if not isinstance(binding, dict):
        return False
    path = Path(str(binding.get("path") or ""))
    if not path.is_absolute():
        path = ROOT / path
    return path.is_file() and file_sha256(path) == str(binding.get("sha256") or "")


def _ledger_progress(path, expected_slots=18):
    path = Path(path)
    if not path.is_file():
        return {"initialized": False, "completed": 0, "expected": expected_slots, "complete": False}
    ledger = load_json(path)
    entries = ledger.get("entries") or {}
    if isinstance(entries, list):
        completed = len(entries)
    else:
        completed = len(entries.keys()) if isinstance(entries, dict) else 0
    return {
        "initialized": True,
        "completed": completed,
        "expected": expected_slots,
        "complete": completed == expected_slots,
    }


def _reliability_status(path=V7_RELIABILITY):
    path = Path(path)
    if not path.is_file():
        return {"available": False, "passed": False, "decision": "not_available"}
    payload = load_json(path)
    passed = bool(payload.get("reliability_passed")) and payload.get("decision") == v9.REQUIRED_V7_DECISION
    return {"available": True, "passed": passed, "decision": str(payload.get("decision") or "")}


def _valid_iso_dates(rows):
    try:
        return all(date.fromisoformat(str(row.get("published_at") or "")) for row in rows)
    except ValueError:
        return False


def _compiled_temporal_status(result):
    if not isinstance(result, dict):
        return {
            "available": False,
            "valid": False,
            "real_public_observation": False,
            "prediction_row_count": 0,
            "future_leakage_violations": None,
            "dataset_hash": None,
            "audit_hash": None,
        }
    dataset = result.get("dataset") if isinstance(result.get("dataset"), dict) else {}
    audit = result.get("audit") if isinstance(result.get("audit"), dict) else {}
    try:
        temporal_report = temporal_m55.validate_temporal_dataset(dataset)
    except (KeyError, TypeError, ValueError):
        temporal_report = {"valid": False, "prediction_samples": 0, "future_leakage_violations": None}
    expected_dataset_hash = temporal_m55.digest(
        {key: value for key, value in dataset.items() if key != "dataset_hash"}
    )
    expected_audit_hash = temporal_m55.digest(
        {key: value for key, value in audit.items() if key != "audit_hash"}
    )
    real = audit.get("data_kind") == temporal_m55.REAL_KIND
    rows = int(temporal_report.get("prediction_samples") or 0)
    valid = (
        temporal_report.get("valid") is True
        and real
        and rows == 30
        and audit.get("record_count") == 30
        and audit.get("contract_hash") == temporal_m55.validate_contract_m55()["contract_hash"]
        and isinstance(audit.get("record_pack_hash"), str)
        and len(audit.get("record_pack_hash")) == 64
        and audit.get("independent_human_reviewed_record_count") == 30
        and isinstance(audit.get("minimum_independent_coder_count"), int)
        and not isinstance(audit.get("minimum_independent_coder_count"), bool)
        and audit.get("minimum_independent_coder_count") >= 2
        and audit.get("future_leakage_violations") == 0
        and audit.get("current_outcome_summary_leak_count") == 0
        and audit.get("raw_or_verbatim_content_count") == 0
        and audit.get("real_human_evidence_created_by_compiler") is False
        and audit.get("m56_authorized_by_compiler") is False
        and dataset.get("dataset_hash") == expected_dataset_hash
        and audit.get("audit_hash") == expected_audit_hash
    )
    return {
        "available": True,
        "valid": valid,
        "real_public_observation": real,
        "prediction_row_count": rows,
        "future_leakage_violations": temporal_report.get("future_leakage_violations"),
        "dataset_hash": dataset.get("dataset_hash") if valid else None,
        "audit_hash": audit.get("audit_hash") if valid else None,
    }


def build_readiness_m55(
    *,
    contract=None,
    v7_result=None,
    v9_result=None,
    frame=None,
    sources=None,
    ledger_paths=DEFAULT_LEDGER_PATHS,
    reliability_path=V7_RELIABILITY,
    compiled_temporal_result=None,
):
    contract = deepcopy(contract or m54.load_contract())
    v7_result = deepcopy(v7_result or load_json(V7_RESULT))
    v9_result = deepcopy(v9_result or load_json(V9_RESULT))
    frame = deepcopy(frame or load_json(V9_FRAME))
    sources = deepcopy(sources or load_json(V9_SOURCES))
    contract_validation = m54.validate_contract_m54(contract)
    temporal_contract_validation = temporal_m55.validate_contract_m55()
    temporal_boundary_gap = temporal_m55.audit_current_v9_boundary_gap()
    compiled_temporal = _compiled_temporal_status(compiled_temporal_result)
    source_rows = sources.get("sources") or []
    slots = frame.get("sampling_slots") or []
    source_ids = {str(row.get("source_id") or "") for row in source_rows}
    slot_source_ids = {str(row.get("source_id") or "") for row in slots}
    ledger_progress = [_ledger_progress(path) for path in ledger_paths]
    reliability = _reliability_status(reliability_path)
    v7_formal = v7_result.get("formal_result") or {}
    v9_formal = v9_result.get("formal_result") or {}
    v7_bindings = v7_result.get("frozen_artifacts") or {}
    v9_bindings = v9_result.get("frozen_artifacts") or {}
    forbidden_holdouts = sorted(slot_source_ids & v9.FORBIDDEN_HOLDOUT_SOURCE_IDS)
    gates = {
        "equation_contract_valid": contract_validation["valid"],
        "temporal_row_contract_valid": temporal_contract_validation["valid"],
        "v7_construction_frozen_and_bound": bool(v7_result.get("construction_passed"))
        and bool(v7_bindings)
        and all(_binding_valid(value) for value in v7_bindings.values()),
        "v9_sampling_frame_frozen_and_bound": bool(v9_result.get("protocol_passed"))
        and bool(v9_bindings)
        and all(_binding_valid(value) for value in v9_bindings.values()),
        "three_authorized_target_sources": source_ids == v9.AUTHORIZED_SOURCE_IDS,
        "target_source_publication_dates_available": len(source_rows) == 3 and _valid_iso_dates(source_rows),
        "thirty_balanced_target_slots": len(slots) == 30
        and slot_source_ids == v9.AUTHORIZED_SOURCE_IDS,
        "sealed_future_excluded": not forbidden_holdouts
        and int(v9_formal.get("final_holdout_source_count") or 0) == 0,
        "two_independent_v7_ledgers_complete": len(ledger_progress) == 2
        and all(row["complete"] for row in ledger_progress),
        "v7_reliability_passed": reliability["passed"],
        "target_events_independently_coded": int(v9_formal.get("independently_reviewed_event_count") or 0) == 30,
        "target_human_coder_count_is_two": int(v9_formal.get("human_coder_count") or 0) == 2,
        "thirty_temporally_valid_prediction_rows": compiled_temporal["valid"],
    }
    precontent_gate_names = (
        "equation_contract_valid",
        "temporal_row_contract_valid",
        "v7_construction_frozen_and_bound",
        "v9_sampling_frame_frozen_and_bound",
        "three_authorized_target_sources",
        "target_source_publication_dates_available",
        "thirty_balanced_target_slots",
        "sealed_future_excluded",
    )
    precontent_ready = all(gates[name] for name in precontent_gate_names)
    m55_complete = all(gates.values())
    blocker = None
    if not precontent_ready:
        blocker = "repair_precontent_contract"
    elif not gates["two_independent_v7_ledgers_complete"]:
        blocker = "complete_two_independent_v7_18_slot_ledgers"
    elif not gates["v7_reliability_passed"]:
        blocker = "compute_and_pass_frozen_v7_reliability"
    elif not gates["target_events_independently_coded"] or not gates["target_human_coder_count_is_two"]:
        blocker = "complete_two_independent_v9_30_slot_target_ledgers"
    elif not gates["thirty_temporally_valid_prediction_rows"]:
        blocker = "complete_prediction_boundary_extension_and_compile_thirty_temporal_rows"
    report = {
        "schema": "uruha_m55_real_person_longitudinal_readiness",
        "status": "m55_pilot_complete" if m55_complete else "blocked_before_real_person_pilot",
        "decision": "authorize_m56" if m55_complete else "do_not_run_m56",
        "equation_contract_hash": contract_validation["contract_hash"],
        "precontent_ready": precontent_ready,
        "m55_pilot_complete": m55_complete,
        "m56_authorized": m55_complete,
        "blocking_gate": blocker,
        "gates": gates,
        "counts": {
            "target_source_count": len(source_rows),
            "target_sampling_slot_count": len(slots),
            "v7_required_human_coders": int(v7_formal.get("required_human_coder_count") or 2),
            "v7_completed_ledgers": sum(row["complete"] for row in ledger_progress),
            "v7_completed_slots_by_ledger": [row["completed"] for row in ledger_progress],
            "v9_coded_target_event_count": int(v9_formal.get("coded_event_count") or 0),
            "v9_independently_reviewed_event_count": int(v9_formal.get("independently_reviewed_event_count") or 0),
            "v9_human_coder_count": int(v9_formal.get("human_coder_count") or 0),
            "temporally_valid_prediction_row_count": compiled_temporal["prediction_row_count"],
            "sealed_future_source_count_in_frame": len(forbidden_holdouts),
        },
        "reliability": reliability,
        "temporal_rows": {
            "contract_valid": temporal_contract_validation["valid"],
            "contract_hash": temporal_contract_validation["contract_hash"],
            "current_v9_alone_compilable": temporal_boundary_gap["current_v9_alone_compilable"],
            "boundary_extension_required": temporal_boundary_gap[
                "boundary_extension_required_before_target_temporal_compilation"
            ],
            "missing_boundary_fields": temporal_boundary_gap["missing_boundary_extension_fields"],
            "compiled_private_result_available": compiled_temporal["available"],
            "compiled_private_result_valid": compiled_temporal["valid"],
            "future_leakage_violations": compiled_temporal["future_leakage_violations"],
            "private_dataset_hash": compiled_temporal["dataset_hash"],
            "private_audit_hash": compiled_temporal["audit_hash"],
        },
        "privacy": {
            "private_ledger_contents_in_report": False,
            "private_temporal_row_contents_in_report": False,
            "raw_source_content_in_report": False,
            "model_generated_labels_count_as_human": False,
            "synthetic_tests_count_as_reliability": False,
        },
        "next_actions": [
            "two distinct consenting humans independently complete the same frozen V7 18 slots",
            "freeze V7 reliability only if temporal IoU and every nominal alpha meet the preregistered thresholds",
            "only after that, the same two-coder method may code the frozen 30 Uruha target-calibration slots",
            "the M55 boundary extension must separately mark observable input, prediction cutoff, and future behavior",
            "M56 remains forbidden until 30 independently coded events also compile into 30 leakage-free temporal rows under a separate M56 protocol",
        ],
        "claim_boundary": "precontent readiness and live human-work progress only; no real-person behavior, equation validity, persona similarity, or model advantage",
    }
    report["report_hash"] = m54.digest(report)
    return report


def render_readiness_m55(report):
    counts = report["counts"]
    stages = [
        ("M54 方程式契約", report["gates"]["equation_contract_valid"], "9個變數與claim boundary"),
        ("M55 時間切點契約", report["gates"]["temporal_row_contract_valid"], "輸入→cutoff→未見行為"),
        ("V7 分類可靠度", report["gates"]["v7_reliability_passed"], f"{counts['v7_completed_ledgers']}/2 位真人完成"),
        ("V9 Uruha 校準", report["gates"]["target_events_independently_coded"], f"{counts['v9_independently_reviewed_event_count']}/30 事件雙人編碼"),
        ("M55 時間列編譯", report["gates"]["thirty_temporally_valid_prediction_rows"], f"{counts['temporally_valid_prediction_row_count']}/30 cutoff→future rows"),
        ("M55 真實縱向 pilot", report["m55_pilot_complete"], "真人可靠度＋時間列都通過"),
        ("M56 公平模型比較", report["m56_authorized"], "M55通過前禁止啟動"),
    ]
    cards = "".join(
        '<div class="stage {}"><b>{}</b><span>{}</span><em>{}</em></div>'.format(
            "pass" if passed else "blocked",
            escape(label),
            escape(detail),
            "PASS" if passed else "BLOCKED",
        )
        for label, passed, detail in stages
    )
    return (
        "<!doctype html><html lang='zh-Hant'><meta charset='utf-8'><title>M55 真人資料閘門</title>"
        "<style>body{font-family:-apple-system,sans-serif;background:#07111f;color:#e6f3ff;margin:0;padding:36px}"
        "main{max-width:1380px;margin:auto}.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}"
        ".stage{padding:18px;border-radius:16px;min-height:125px;border:1px solid #334155;background:#111d31}"
        ".stage b,.stage span,.stage em{display:block}.stage span{margin:12px 0;color:#cbd5e1}.pass{border-color:#2dd4bf}"
        ".blocked{border-color:#fb7185}.stage em{font-style:normal;font-weight:700}.pass em{color:#5eead4}"
        ".blocked em{color:#fda4af}.boundary{margin-top:24px;padding:18px;border-radius:14px;background:#172033}"
        "</style><main><h1>M55 真實人物縱向資料閘門</h1><p>看得到準備完成，也看得到哪些證據不能由程式假造。</p>"
        f"<div class='flow'>{cards}</div><div class='boundary'><b>現在不能做M56的原因</b>：{escape(str(report['blocking_gate']))}<br>"
        f"3個官方校準來源／30個凍結槽已準備；真人可靠度、Uruha正式事件與時間列仍為0。"
        f"<br>現有V9只有整段事件框，M55契約要求另標輸入結束／預測cutoff／未見行為開始，禁止偷用行為資訊。"
        f"<br>{escape(report['claim_boundary'])}</div></main></html>"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "html", "temporal-html"), default="json")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=7903)
    args = parser.parse_args()
    report = build_readiness_m55()
    if args.serve:
        readiness_page = render_readiness_m55(report)
        temporal_page = temporal_m55.render_temporal_contract_m55(
            human_row_count=report["counts"]["temporally_valid_prediction_row_count"]
        )
        status_json = json.dumps(report, ensure_ascii=False, indent=2)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in ("/", "/readiness"):
                    body, content_type, status = readiness_page, "text/html; charset=utf-8", 200
                elif self.path == "/temporal":
                    body, content_type, status = temporal_page, "text/html; charset=utf-8", 200
                elif self.path == "/status.json":
                    body, content_type, status = status_json, "application/json; charset=utf-8", 200
                elif self.path == "/health":
                    body, content_type, status = "ok", "text/plain; charset=utf-8", 200
                else:
                    body, content_type, status = "not found", "text/plain; charset=utf-8", 404
                encoded = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, _format, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", int(args.port)), Handler)
        print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}/temporal"}), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return
    if args.format == "html":
        output = render_readiness_m55(report)
    elif args.format == "temporal-html":
        output = temporal_m55.render_temporal_contract_m55(
            human_row_count=report["counts"]["temporally_valid_prediction_row_count"]
        )
    else:
        output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)


if __name__ == "__main__":
    main()
