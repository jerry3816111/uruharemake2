import json
from pathlib import Path

import p4_p_cross_language_correction_lifecycle_probe as p4p_probe
import p4_q_correction_lifecycle_protocol_repair_probe as probe
import uruha_multilingual_current_preference_p4 as p4i
import uruha_preference_scope_canonicalization_p4 as p4l


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_q_correction_lifecycle_protocol_repair_v1.json"


def test_new_pair_is_extractable_without_executing_persistent_lifecycle():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    first = contract["process_1"]
    write = p4l.canonicalize_preference_scope_extraction_p4(
        p4i.extract_explicit_current_preference_p4(first["write_input"])
    )
    correction = p4l.canonicalize_preference_scope_extraction_p4(
        p4i.extract_explicit_current_preference_p4(first["correction_input"])
    )
    assert write["current_value"] == "洛神花茶"
    assert correction["previous_value"] == "洛神花茶"
    assert correction["current_value"] == "はと麦茶"
    assert write["scope"] == correction["scope"] == "drink"


def test_wrapper_reuses_unchanged_p4_p_write_and_recall_mechanics():
    source = Path(probe.__file__).read_text(encoding="utf-8")
    assert "p4p_probe._write_phase(args.db, contract)" in source
    assert "p4p_probe._recall_phase(args.db, contract)" in source
    assert p4p_probe._write_phase is not None
    assert p4p_probe._recall_phase is not None
    assert source.count('_run_worker("') == 2


def test_wrapper_uses_fresh_temporary_persistent_database_and_no_retry_name():
    source = Path(probe.__file__).read_text(encoding="utf-8")
    assert 'TemporaryDirectory(prefix="uruha_p4_q_lifecycle_")' in source
    assert "retry" not in probe._run_worker.__code__.co_names
