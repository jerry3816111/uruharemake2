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
import json
from pathlib import Path

import uruha_human_response_equation_m54 as m54
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


def build_readiness_m55(
    *,
    contract=None,
    v7_result=None,
    v9_result=None,
    frame=None,
    sources=None,
    ledger_paths=DEFAULT_LEDGER_PATHS,
    reliability_path=V7_RELIABILITY,
):
    contract = deepcopy(contract or m54.load_contract())
    v7_result = deepcopy(v7_result or load_json(V7_RESULT))
    v9_result = deepcopy(v9_result or load_json(V9_RESULT))
    frame = deepcopy(frame or load_json(V9_FRAME))
    sources = deepcopy(sources or load_json(V9_SOURCES))
    contract_validation = m54.validate_contract_m54(contract)
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
    }
    precontent_gate_names = (
        "equation_contract_valid",
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
            "sealed_future_source_count_in_frame": len(forbidden_holdouts),
        },
        "reliability": reliability,
        "privacy": {
            "private_ledger_contents_in_report": False,
            "raw_source_content_in_report": False,
            "model_generated_labels_count_as_human": False,
            "synthetic_tests_count_as_reliability": False,
        },
        "next_actions": [
            "two distinct consenting humans independently complete the same frozen V7 18 slots",
            "freeze V7 reliability only if temporal IoU and every nominal alpha meet the preregistered thresholds",
            "only after that, the same two-coder method may code the frozen 30 Uruha target-calibration slots",
            "M56 remains forbidden until M55 has real independently coded target events",
        ],
        "claim_boundary": "precontent readiness and live human-work progress only; no real-person behavior, equation validity, persona similarity, or model advantage",
    }
    report["report_hash"] = m54.digest(report)
    return report


def render_readiness_m55(report):
    counts = report["counts"]
    stages = [
        ("M54 方程式契約", report["gates"]["equation_contract_valid"], "9個變數與claim boundary"),
        ("V7 分類可靠度", report["gates"]["v7_reliability_passed"], f"{counts['v7_completed_ledgers']}/2 位真人完成"),
        ("V9 Uruha 校準", report["gates"]["target_events_independently_coded"], f"{counts['v9_independently_reviewed_event_count']}/30 事件雙人編碼"),
        ("M55 真實縱向 pilot", report["m55_pilot_complete"], "只用cutoff以前資料預測後續可觀察行為"),
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
        "main{max-width:1180px;margin:auto}.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}"
        ".stage{padding:18px;border-radius:16px;min-height:125px;border:1px solid #334155;background:#111d31}"
        ".stage b,.stage span,.stage em{display:block}.stage span{margin:12px 0;color:#cbd5e1}.pass{border-color:#2dd4bf}"
        ".blocked{border-color:#fb7185}.stage em{font-style:normal;font-weight:700}.pass em{color:#5eead4}"
        ".blocked em{color:#fda4af}.boundary{margin-top:24px;padding:18px;border-radius:14px;background:#172033}"
        "</style><main><h1>M55 真實人物縱向資料閘門</h1><p>看得到準備完成，也看得到哪些證據不能由程式假造。</p>"
        f"<div class='flow'>{cards}</div><div class='boundary'><b>現在不能做M56的原因</b>：{escape(str(report['blocking_gate']))}<br>"
        f"3個官方校準來源／30個凍結槽已準備；真人可靠度與Uruha正式事件仍為0。<br>{escape(report['claim_boundary'])}</div></main></html>"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args()
    report = build_readiness_m55()
    print(render_readiness_m55(report) if args.format == "html" else json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
