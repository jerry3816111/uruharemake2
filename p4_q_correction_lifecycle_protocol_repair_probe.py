#!/usr/bin/env python3
"""Run the P4-Q repaired protocol with P4-P's unchanged lifecycle mechanics."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import p4_p_cross_language_correction_lifecycle_probe as p4p_probe
import p4_q_correction_lifecycle_protocol_repair_gate as gate


def _run_worker(phase, db_path):
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", phase, "--db", db_path]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return {
            "status": "worker_failed",
            "phase": phase,
            "returncode": completed.returncode,
            "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        }
    return json.loads(completed.stdout)


def run_frozen_probe():
    contract = gate.load_contract()
    with tempfile.TemporaryDirectory(prefix="uruha_p4_q_lifecycle_") as tempdir:
        db_path = str(Path(tempdir) / "memory_db")
        first = _run_worker("write", db_path)
        if first.get("status") == "worker_failed":
            evidence = {"process_1": first}
        else:
            second = _run_worker("recall", db_path)
            evidence = {
                "schema": "uruha_p4_q_correction_lifecycle_protocol_repair_evidence_v1",
                "process_1": first,
                "process_2": second,
                "restart": {
                    "old_process_exit_observed": True,
                    "old_pid": first.get("pid"),
                    "new_pid": second.get("pid"),
                    "old_session_id": first.get("session_id"),
                    "new_session_id": second.get("session_id"),
                    "same_persistent_db": True,
                },
                "accounting": {
                    "process_starts": 2,
                    "true_process_restart_count": 1,
                    "retry_count": 0,
                    "fallback_count": 0,
                    "model_call_count": 0,
                    "paid_api_call_count": 0,
                    "external_deployment_count": 0,
                    "production_memory_access_count": 0,
                },
            }
        evidence["gate_evaluation"] = gate.evaluate_evidence(contract, evidence)
        evidence["claim_boundary"] = contract["claim_boundary"]
        return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("write", "recall"))
    parser.add_argument("--db")
    args = parser.parse_args()
    contract = gate.load_contract()
    if args.worker:
        if not args.db:
            raise SystemExit("--db is required for a worker")
        result = (
            p4p_probe._write_phase(args.db, contract)
            if args.worker == "write"
            else p4p_probe._recall_phase(args.db, contract)
        )
    else:
        result = run_frozen_probe()
    result.setdefault("worker_pid", os.getpid())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
