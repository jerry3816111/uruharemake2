import json
from pathlib import Path

import p4_p_cross_language_correction_lifecycle_probe as probe
import uruha_multilingual_current_preference_p4 as p4i
import uruha_preference_scope_canonicalization_p4 as p4l


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_p_cross_language_correction_lifecycle_offline_v1.json"


def test_frozen_pair_is_extractable_without_running_persistent_lifecycle():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    first = contract["process_1"]
    write = p4l.canonicalize_preference_scope_extraction_p4(
        p4i.extract_explicit_current_preference_p4(first["write_input"])
    )
    correction = p4l.canonicalize_preference_scope_extraction_p4(
        p4i.extract_explicit_current_preference_p4(first["correction_input"])
    )
    assert write["current_value"] == contract["development_pair"]["old_value"]
    assert correction["previous_value"] == contract["development_pair"]["old_value"]
    assert correction["current_value"] == contract["development_pair"]["new_value"]
    assert write["scope"] == correction["scope"] == "drink"
    assert write[p4l.LABEL]["alias_id"] == "drink:zh-Hant:v1"
    assert correction[p4l.LABEL]["alias_id"] == "drink:ja:v1"


def test_probe_uses_two_subprocesses_and_one_temporary_persistent_db():
    source = Path(probe.__file__).read_text(encoding="utf-8")
    assert "subprocess.run" in source
    assert 'TemporaryDirectory(prefix="uruha_p4_p_lifecycle_")' in source
    assert 'get_or_create_collection(COLLECTION)' in source
    assert source.count('_run_worker("') == 2


def test_probe_calls_released_p4_o_path_without_supplying_reference_time():
    source = Path(probe.__file__).read_text(encoding="utf-8")
    call = "p4o.build_with_persisted_reference_time_p4(\n        second[\"recall_input\"], collection\n    )"
    assert call in source
    assert "retry" not in probe._run_worker.__code__.co_names
