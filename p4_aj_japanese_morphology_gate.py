import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_aj_japanese_morphology_v1.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    path, digest = contract["dataset"]
    assert _sha(ROOT / path) == digest
    for path, digest in contract["predecessors"].values():
        assert _sha(ROOT / path) == digest
    return contract


def load_dataset(contract):
    return json.loads((ROOT / contract["dataset"][0]).read_text(encoding="utf-8"))


def evaluate_evidence(contract, evidence):
    dataset = load_dataset(contract)
    expected = [*dataset["development_cases"], *dataset["fresh_positive_cases"], *dataset["fresh_control_cases"]]
    failures = []
    rows = evidence.get("cases") or []
    if evidence.get("dataset_sha256") != contract["dataset"][1]: failures.append("dataset_hash")
    if len(rows) != len(expected): failures.append("case_count")
    else:
        for frozen, row in zip(expected, rows):
            if row.get("case_id") != frozen["case_id"] or row.get("detected") is not frozen["expected"]:
                failures.append(f"{frozen['case_id']}:mismatch")
    for key, target in contract["gates"].items():
        if (evidence.get("metrics") or {}).get(key) != target: failures.append(f"metric:{key}")
    return {"schema": "uruha_p4_aj_gate_result_v1", "status": "pass" if not failures else "fail", "failed_gates": failures, "claim_boundary": contract["claim_boundary"]}
