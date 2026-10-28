import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / "research" / "p4_n_real_source_bound_japanese_delivery_release_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RELEASE.read_text(encoding="utf-8"))


def test_release_binds_terminal_result_acceptance_and_test():
    release = _load()
    assert release["status"] == "released_terminal_source_bound_japanese_delivery_failure"
    for binding in release["result_checkpoint"].values():
        if isinstance(binding, dict):
            assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_release_preserves_failure_and_does_not_promote_restart_persistence_to_delivery():
    release = _load()
    evidence = release["terminal_evidence"]
    assert evidence["frozen_gate_status"] == "fail"
    assert evidence["profile_record_survived_restart"] is True
    assert evidence["bounded_japanese_identity_delivered"] is False
    assert evidence["retry_count"] == 0
    assert release["preserved_boundaries"]["same_case_rerun"] is False
    boundary = release["claim_boundary"]
    assert "failure" in boundary
    assert "not successful" in boundary


def test_next_stage_is_a_new_persisted_chroma_regression_not_same_case_rescue():
    next_stage = _load()["next_stage"]
    assert next_stage["id"] == "P4-O"
    assert next_stage["single_changed_variable"] == (
        "one shared non-null reference_time for the base P4-J read and additive P4-N re-read"
    )
    assert any("do not rerun" in item for item in next_stage["forbidden_change"])
    assert any("real temporary Chroma" in item for item in next_stage["requirements"])
