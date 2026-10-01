import json
from pathlib import Path

from p4_z_source_bound_proposition_gate import evaluate_evidence, load_contract


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_z_source_bound_proposition_evidence_2026-09-23.json"
RESULT = ROOT / "analysis" / "p4_z_source_bound_proposition_result_2026-09-23.json"


def test_p4_z_committed_evidence_passes_frozen_gate():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    expected = evaluate_evidence(load_contract(), evidence)
    committed = json.loads(RESULT.read_text(encoding="utf-8"))
    assert expected == committed
    assert committed["status"] == "pass"
    assert committed["failed_gates"] == []
