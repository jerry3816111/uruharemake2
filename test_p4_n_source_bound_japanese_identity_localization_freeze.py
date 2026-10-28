import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_n_source_bound_japanese_identity_localization_freeze_2026-09-22.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_freeze_binds_prechange_contract_and_terminal_p4_m_release():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_implementation"
    for group in ("implementation_checkpoint", "design_bindings"):
        for binding in freeze[group].values():
            if isinstance(binding, dict) and "path" in binding:
                assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_freeze_limits_product_change_and_forbids_p4_m_retuning():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["single_changed_variable"] == (
        "source_provenance_bounded_japanese_identity_localization"
    )
    assert freeze["allowed_product_files"] == ["uruha_typed_current_preference_recall_p4.py"]
    assert any("do not add 柚子茶" in item for item in freeze["forbidden_change"])
    assert any("do not rerun P4-M" in item for item in freeze["forbidden_change"])
    assert freeze["authorized_external_effects"]["safari_product_turns"] == 0


def test_real_product_confirmation_requires_a_separate_freeze():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert any("separate real-product acceptance freeze" in item for item in freeze["execution_order"])
    assert "cannot erase the P4-M failure" in freeze["claim_boundary"]
