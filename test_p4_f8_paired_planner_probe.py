"""No-provider guards for the one-shot f8 planner-boundary probe."""

from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

import p4_f8_paired_planner_probe as probe


def _request():
    return {
        "model": probe.MODEL,
        "temperature": 0.1,
        "max_tokens": 256,
        "timeout": 20.0,
        "response_format": {"type": "json_schema", "json_schema": {"name": "same"}},
        "messages": [
            {"role": "system", "content": "unchanged system"},
            {"role": "user", "content": "User Input: same current source"},
        ],
    }


def test_frozen_f8_plan_and_data_still_match_preimplementation_freeze():
    assert probe._verify_frozen_sources() == "初めて自分で夜の星を撮った。今は一言だけ励まして。"


def test_on_is_allowed_only_when_exact_suffix_is_the_sole_request_difference():
    off = _request()
    segment = "\n[Current User completed event — source-bound]\n"
    assert probe._paired_request_check(off, None, segment) == off
    on = deepcopy(off)
    on["messages"][0]["content"] += segment
    assert probe._paired_request_check(on, off, segment) == off
    assert off["messages"][0]["content"] == "unchanged system"


@pytest.mark.parametrize("mutate", [
    lambda request: request.update(temperature=0.2),
    lambda request: request.update(max_tokens=255),
    lambda request: request["messages"][1].update(content="User Input: changed"),
    lambda request: request["response_format"]["json_schema"].update(name="changed"),
    lambda request: request["messages"][0].update(content="changed system\n[Current User completed event — source-bound]\n"),
])
def test_any_non_treatment_drift_rejects_before_on_model_call(mutate):
    off = _request()
    segment = "\n[Current User completed event — source-bound]\n"
    on = deepcopy(off)
    on["messages"][0]["content"] += segment
    mutate(on)
    with pytest.raises(RuntimeError):
        probe._paired_request_check(on, off, segment)


def test_missing_on_suffix_or_contaminated_off_rejects():
    off = _request()
    segment = "\n[Current User completed event — source-bound]\n"
    with pytest.raises(RuntimeError, match="on_arm_not_injected"):
        probe._paired_request_check(off, off, segment)
    injected_off = deepcopy(off)
    injected_off["messages"][0]["content"] += segment
    with pytest.raises(RuntimeError, match="off_arm_was_injected"):
        probe._paired_request_check(injected_off, None, segment)
    mid_injected_off = deepcopy(off)
    mid_injected_off["messages"][0]["content"] = "prefix" + segment + "suffix"
    with pytest.raises(RuntimeError, match="off_arm_was_injected"):
        probe._paired_request_check(mid_injected_off, None, segment)


def test_private_evidence_cannot_be_created_inside_any_safe_worktree():
    for parent in (probe.HERE, probe.HERE.parent):
        with pytest.raises(ValueError, match="inside_worktree_collection_prohibited"):
            probe._private_root(parent)


def test_cli_without_execute_cannot_start_a_model(monkeypatch):
    monkeypatch.setattr(probe, "_model_digest", lambda: (_ for _ in ()).throw(AssertionError("network")))
    with pytest.raises(SystemExit) as exit_info:
        probe.main([])
    assert exit_info.value.code == 2


def test_preflight_checks_frozen_handoff_without_generation(monkeypatch, capsys):
    monkeypatch.setattr(probe, "_model_digest", lambda: probe.MODEL_DIGEST)
    monkeypatch.setattr(probe, "_one_arm", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("generation")))
    assert probe.main(["--preflight-only"]) == 0
    assert '"status": "preflight_only_no_generation"' in capsys.readouterr().out


def test_live_arm_wiring_uses_real_compact_route_but_fake_provider(monkeypatch, tmp_path):
    import openai
    import uruha_brain_mac as runtime
    import uruha_compact_planner_p2 as compact
    from uruha_source_event_candidate_formation_p4 import build_source_event_constraint_p4

    source = probe._verify_frozen_sources()
    handoff = probe._handoff(source)
    segment, _receipt = build_source_event_constraint_p4(source, handoff)
    memory, psyche = probe._initial_state()
    state_hash = probe._sha_bytes(probe._canonical({
        "source": source, "memory": memory, "psyche": psyche, "handoff": handoff,
    }))
    compact.install_compact_planner_p2()
    runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = probe.MAX_PLANNER_SECONDS
    monkeypatch.setattr(probe, "_model_digest", lambda: probe.MODEL_DIGEST)
    model_requests = []
    checked_suffixes = []
    original_request_check = probe._paired_request_check

    def checked_request(request, off, suffix):
        checked_suffixes.append((off is None, suffix))
        return original_request_check(request, off, suffix)

    monkeypatch.setattr(probe, "_paired_request_check", checked_request)

    def fake_create(**kwargs):
        model_requests.append(deepcopy(kwargs))
        usage = SimpleNamespace(
            prompt_tokens=100, completion_tokens=20, total_tokens=120,
            model_dump=lambda: {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        )
        plans = [
            {"scene": "support", "core_message_jp": "うん、よくやった。", "response_mode": "direct_answer"},
            {"scene": "support", "core_message_jp": "夜の星を撮ったんだね、いいね。", "response_mode": "direct_answer"},
            {"scene": "casual", "core_message_jp": "それはやるじゃん。", "response_mode": "direct_answer"},
        ]
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
            finish_reason="stop",
        )], usage=usage)

    monkeypatch.setattr(openai, "OpenAI", lambda **_kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    ))
    off, off_request = probe._one_arm(
        arm="off", source=source, memory=deepcopy(memory), psyche=deepcopy(psyche),
        handoff=deepcopy(handoff), expected_state_hash=state_hash,
        segment=segment, off_request=None, private_root=tmp_path,
    )
    on, _ = probe._one_arm(
        arm="on", source=source, memory=deepcopy(memory), psyche=deepcopy(psyche),
        handoff=deepcopy(handoff), expected_state_hash=state_hash,
        segment=segment, off_request=off_request, private_root=tmp_path,
    )
    assert len(model_requests) == 2
    assert checked_suffixes == [(True, segment), (False, segment)]
    assert off["request_argument_without_treatment_sha256"] == on["request_argument_without_treatment_sha256"]
    assert off["source_prompt_receipt"] is None
    assert on["source_prompt_receipt"]["prompt_injected"] is True
    assert off["actual_candidate_count"] == on["actual_candidate_count"] == 3
    assert off["provider_total_tokens"] == on["provider_total_tokens"] == 120
    assert (tmp_path / "off_raw_response.json").is_file()
    assert (tmp_path / "on_raw_response.json").is_file()
