from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_case03_dual_condition_output_lock as lock_module
from p3_case03_dual_condition_output_lock import (
    _write_product_intent,
    append_product_prefix,
    build_preflight,
    build_views,
    load_config,
)
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs/p3_case03_dual_condition_output_lock_v1.json"


def test_case03_lock_projects_exact_four_turns_without_annotations():
    config = load_config(CONFIG)
    source = config["_source"]

    assert [turn["turn_id"] for turn in source["turns"]] == [
        "p3-smoke-03-u1", "p3-smoke-03-u2",
        "p3-smoke-03-u3", "p3-smoke-03-u4",
    ]
    assert source["annotations_included"] is False
    assert "annotations" not in source
    assert config["execution_boundary"]["b15_calls_reused_or_counted"] is False
    assert config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False


def test_case03_view_pairs_share_prefix_and_do_not_write_back_baseline():
    config = load_config(CONFIG)
    prefix = []
    for index, turn in enumerate(config["_source"]["turns"]):
        views = build_views(prefix, turn)
        product = views["product_system"]
        direct = views["full_history_direct"]

        assert product["source_history_sha256"] == direct["source_history_sha256"]
        assert product["input_sha256"] == direct["input_sha256"]
        assert len(product["visible_prefix"]) == len(direct["visible_prefix"]) == index * 2
        assert all("baseline" not in row["content"] for row in direct["visible_prefix"])
        append_product_prefix(prefix, turn, f"product reply {index}")


def test_case03_product_turn_intent_is_no_retry(tmp_path):
    config = load_config(CONFIG)
    turn = config["_source"]["turns"][0]
    views = build_views([], turn)
    intent = tmp_path / "product" / turn["turn_id"] / "intent.json"

    _write_product_intent(intent, config, turn, views)
    with pytest.raises(P3ContractError) as error:
        _write_product_intent(intent, config, turn, views)

    assert error.value.code == "p3_b16_product_turn_checkpoint_exists_no_retry"


def test_case03_config_rejects_annotation_access_drift(tmp_path, monkeypatch):
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["execution_boundary"]["annotation_access"] = True
    path = tmp_path / "configs" / CONFIG.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        lock_module,
        "_ref",
        lambda _repo, _value, expected, _code: ROOT / expected["path"],
    )

    with pytest.raises(P3ContractError) as error:
        load_config(path)

    assert error.value.code == "p3_b16_boundary_mismatch"


def test_case03_preflight_is_ready_and_zero_call():
    result = build_preflight(CONFIG)

    assert result["status"] == "ready_for_case03_output_lock_review"
    assert result["turn_ids"] == [
        "p3-smoke-03-u1", "p3-smoke-03-u2",
        "p3-smoke-03-u3", "p3-smoke-03-u4",
    ]
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_accessed"] == result["confirmation_accessed"] == 0
    assert result["production_database_accessed"] is False
    assert all(result["checks"].values())
