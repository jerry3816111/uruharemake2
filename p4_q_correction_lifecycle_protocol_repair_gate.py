#!/usr/bin/env python3
"""P4-Q gate: P4-P lifecycle semantics with a repaired frozen clock protocol."""

from __future__ import annotations

from copy import deepcopy
import datetime
import json
from pathlib import Path

import p4_p_cross_language_correction_lifecycle_gate as p4p


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_q_correction_lifecycle_protocol_repair_v1.json"


class P4QProtocolRepairGateError(RuntimeError):
    pass


def load_contract(path: Path = CONTRACT):
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def _parse(value):
    try:
        return datetime.datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise P4QProtocolRepairGateError("protocol_timestamp_invalid") from exc


def _as_p4p_contract(contract):
    adapted = deepcopy(contract)
    adapted["schema"] = "uruha_p4_p_cross_language_correction_lifecycle_offline_v1"
    return adapted


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_q_correction_lifecycle_protocol_repair_v1":
        raise P4QProtocolRepairGateError("contract_schema_invalid")
    boundary = _parse(
        (contract.get("protocol_time_boundary") or {}).get(
            "p4_p_post_execution_clock_observation"
        )
    )
    first = contract.get("process_1") or {}
    write_time = _parse(first.get("write_timestamp"))
    correction_time = _parse(first.get("correction_timestamp"))
    if not write_time < correction_time < boundary:
        raise P4QProtocolRepairGateError("timestamps_not_strictly_elapsed")
    if (contract.get("protocol_time_boundary") or {}).get(
        "require_write_and_correction_strictly_before_boundary"
    ) is not True:
        raise P4QProtocolRepairGateError("elapsed_time_requirement_missing")
    if (contract.get("failure_policy") or {}).get("p4_p_case_rerun_allowed") is not False:
        raise P4QProtocolRepairGateError("p4_p_rerun_not_forbidden")
    try:
        p4p.validate_contract(_as_p4p_contract(contract))
    except p4p.P4PCorrectionLifecycleGateError as exc:
        raise P4QProtocolRepairGateError(str(exc)) from exc


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    result = p4p.evaluate_evidence(_as_p4p_contract(contract), evidence)
    result["schema"] = "uruha_p4_q_correction_lifecycle_protocol_repair_gate_result_v1"
    result["claim_boundary"] = contract["claim_boundary"]
    return result


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
