import copy
import json
from pathlib import Path

import pytest

from uruha_semantic_persona_surface_eval_m39 import evaluate, validate_reserve


def _development_fixture():
    return {
        "schema": "uruha_m39_semantic_persona_surface_reserve_v1",
        "case_count": 3,
        "cases": [
            {
                "case_id": "dev-role",
                "language": "en",
                "category": "speaker_role_inversion",
                "source_utterance": "I feel dizzy and need you to listen.",
                "selected_policy_id": "listen_presence",
                "semantic_route_selected_type": "emotional_bid",
                "proposed_reply_jp": "私は頭が痛くて、話を聞いてほしいんだね。",
                "expected_action": "repair",
                "required_policy_act": "listen_presence",
            },
            {
                "case_id": "dev-safe",
                "language": "ja",
                "category": "safe_noninterference",
                "source_utterance": "ここにいて。",
                "selected_policy_id": "share_arousal",
                "semantic_route_selected_type": "emotional_bid",
                "proposed_reply_jp": "うん、ここにいる。",
                "expected_action": "accept",
                "required_policy_act": "share_arousal",
            },
            {
                "case_id": "dev-protected",
                "language": "zh",
                "category": "protected_route_noninterference",
                "source_utterance": "你記得我的名字嗎？",
                "selected_policy_id": None,
                "semantic_route_selected_type": "factual_or_memory",
                "proposed_reply_jp": "呼び方はJerryだろ。",
                "expected_action": "not_applicable",
                "required_policy_act": None,
            },
        ],
    }


def _protocol():
    return json.loads(
        (Path(__file__).resolve().parent / "research/m39_semantic_persona_surface_protocol_v1.json").read_text(encoding="utf-8")
    )


def test_development_fixture_evaluates_without_raw_rows():
    result = evaluate(_development_fixture(), _protocol())
    assert result["metrics"]["system_expected_action_accuracy"] == 1.0
    assert result["metrics"]["baseline_expected_action_accuracy"] < 1.0
    assert result["raw_source_or_reply_text_in_result_rows"] is False
    encoded_rows = json.dumps(result["rows"], ensure_ascii=False)
    assert "I feel dizzy" not in encoded_rows
    assert "私は頭が痛くて" not in encoded_rows


def test_validator_rejects_duplicate_case_ids():
    dataset = _development_fixture()
    dataset["cases"].append(copy.deepcopy(dataset["cases"][0]))
    dataset["case_count"] += 1
    validation = validate_reserve(dataset, _protocol())
    assert validation["valid"] is False
    assert "duplicate_case_id" in validation["errors"]


def test_formal_result_refuses_overwrite(tmp_path):
    output = tmp_path / "result.json"
    output.write_text("existing", encoding="utf-8")
    dataset_path = tmp_path / "development.json"
    protocol_path = tmp_path / "protocol.json"
    dataset_path.write_text(json.dumps(_development_fixture()), encoding="utf-8")
    protocol_path.write_text(json.dumps(_protocol()), encoding="utf-8")
    from uruha_semantic_persona_surface_eval_m39 import main

    with pytest.raises(FileExistsError):
        main(
            [
                "--dataset",
                str(dataset_path),
                "--protocol",
                str(protocol_path),
                "--output",
                str(output),
            ]
        )
