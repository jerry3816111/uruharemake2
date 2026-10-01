from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_direct_v2_surface_canary as canary_module
from p3_direct_v2_surface_canary import _runtime_config, build_preflight, load_canary
from p3_product_comparison import FakeExactTokenCounter, P3ContractError
from p3_product_worker import execute_canary_baselines


ROOT = Path(__file__).resolve().parent
CANARY = ROOT / "configs/p3_direct_v2_surface_canary_v1.json"


def test_direct_canary_loads_product_result_by_digest_not_json_content(monkeypatch):
    original_read = canary_module._read
    loaded_names: list[str] = []

    def observed(path: Path):
        loaded_names.append(path.name)
        return original_read(path)

    monkeypatch.setattr(canary_module, "_read", observed)
    canary = load_canary(CANARY)

    assert "p3_b15_product_canary_result_2026-09-15.json" not in loaded_names
    assert canary["locked_product_result"]["content_not_loaded_by_runner"] is True
    assert canary["_source"]["turn_id"] == "p3-smoke-03-u1"
    assert canary["_source"]["visible_prefix"] == []


def test_direct_canary_is_one_call_same_source_and_non_authorizing():
    canary = load_canary(CANARY)
    runtime = _runtime_config(canary)

    assert runtime["conditions"] == ["full_history_direct"]
    assert runtime["generation"]["model"] == "qwen2.5:7b"
    assert runtime["execution_boundary"]["provider_calls_exact"] == 1
    assert canary["generation"]["completion_cap"] == 768
    assert canary["execution_boundary"]["future_turn_access"] is False
    assert canary["execution_boundary"]["annotation_access"] is False
    assert canary["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False


def test_direct_canary_contract_fake_executes_one_surface_valid_call(tmp_path):
    canary = load_canary(CANARY)
    runtime = _runtime_config(canary)
    requests = []

    def transport(request):
        requests.append(request)
        return {
            "content": "最後だけ答えられなかったの、ちょっと引っかかるよな。",
            "usage": {
                "prompt_tokens": request["prompt_tokens"],
                "completion_tokens": 12,
                "wall_seconds": 0.001,
            },
            "model": request["model"],
            "backend": request["backend"],
            "network_calls": 0,
            "real_model_calls": 0,
        }

    result = execute_canary_baselines(
        config=runtime,
        token_counter=FakeExactTokenCounter(),
        transport=transport,
        checkpoint_root=tmp_path,
        evidence_kind="contract_fake",
    )

    assert result["status"] == "offline_canary_baselines_contract_pass"
    assert len(requests) == 1
    assert [message["role"] for message in requests[0]["messages"]] == ["system", "user"]
    assert requests[0]["messages"][1]["content"] == canary["_source"]["content"]
    assert result["source"]["content_sha256"] == canary["_source"]["content_sha256"]
    assert all(result["checks"].values())


def test_direct_canary_rejects_product_content_access_flag_drift(tmp_path, monkeypatch):
    raw = json.loads(CANARY.read_text(encoding="utf-8"))
    raw["locked_product_result"]["content_not_loaded_by_runner"] = False
    path = tmp_path / "configs" / CANARY.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        canary_module,
        "_ref",
        lambda _repo, _value, expected, _code: ROOT / expected["path"],
    )

    with pytest.raises(P3ContractError) as error:
        load_canary(path)

    assert error.value.code == "p3_b15_direct_product_result_mismatch"


def test_direct_canary_preflight_is_ready_and_zero_call():
    result = build_preflight(CANARY)

    assert result["status"] == "ready_for_direct_v2_surface_canary_review"
    assert result["offline_prompt_tokens"] > 0
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["future_turns_accessed"] == result["annotations_accessed"] == 0
    assert result["product_result_content_loaded"] is False
    assert all(result["checks"].values())
