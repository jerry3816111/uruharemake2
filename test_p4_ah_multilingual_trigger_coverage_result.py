import json
from pathlib import Path

import p4_ah_multilingual_trigger_coverage_gate as gate
import uruha_multilingual_observable_trigger_p4 as coverage


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_ah_multilingual_trigger_coverage_evidence_2026-09-24.json"
RESULT = ROOT / "analysis" / "p4_ah_multilingual_trigger_coverage_result_2026-09-24.json"


def test_committed_p4_ah_result_matches_fail_closed_gate():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    committed = json.loads(RESULT.read_text(encoding="utf-8"))
    live = coverage.build_dataset_evidence_p4_ah(
        ROOT / gate.load_contract()["dataset"]["path"]
    )
    evaluated = gate.evaluate_evidence(gate.load_contract(), live)
    assert committed["status"] == "pass"
    assert committed["failed_gates"] == []
    assert evaluated["status"] == committed["status"]
    assert evaluated["failed_gates"] == committed["failed_gates"]
    assert evidence["dataset_sha256"] == live["dataset_sha256"]
    assert evidence["metrics"] == live["metrics"]
    assert evidence["integration"] == live["integration"]
    assert committed["formal_execution_count"] == 1
    assert committed["informed_correction_count"] == 0
