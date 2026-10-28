"""Frozen f4 carrier-only contracts; no real model or Safari call."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import p4_direct_reply_act_m29_priority_detached_control as controller
import uruha_compact_planner_p2 as compact
from test_compact_planner_p2 import request, response_content


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_compact_schema_f4_probe_2026-10-24.json").read_text()
)


def test_f4_source_only_classifier_does_not_claim_private_state():
    from uruha_direct_reply_act_m29_priority_p4 import classify_direct_reply_act_p4

    result = classify_direct_reply_act_p4(DATA["user_input"])
    assert result["status"] == "direct"
    assert result["requested_act"] == DATA["expected_direct_reply_act"]
    assert result["private_state_truth_claimed"] is False


def test_opt_in_schema_changes_only_compact_response_format(monkeypatch):
    before = compact.compact_request(request())
    assert before["response_format"] == {"type": "json_object"}
    monkeypatch.setenv("URUHA_P4_COMPACT_JSON_SCHEMA", "1")
    after = compact.compact_request(request())
    assert {k: v for k, v in after.items() if k != "response_format"} == {
        k: v for k, v in before.items() if k != "response_format"
    }
    assert after["response_format"]["type"] == "json_schema"
    wrapper = after["response_format"]["json_schema"]
    assert wrapper["strict"] is True
    schema = wrapper["schema"]
    assert schema["type"] == "object" and schema["additionalProperties"] is False
    assert schema["required"] == ["plans"]
    plans = schema["properties"]["plans"]
    assert plans["minItems"] == plans["maxItems"] == 3
    candidate = plans["items"]
    assert candidate["additionalProperties"] is False
    assert set(candidate["required"]) == {"scene", "core_message_jp", "response_mode"}
    assert set(candidate["properties"]["scene"]["enum"]) == compact._SCENES
    assert set(candidate["properties"]["response_mode"]["enum"]) == compact._MODES
    core = candidate["properties"]["core_message_jp"]
    assert core["minLength"] == 1 and core["maxLength"] == 32


def test_opt_in_keeps_strict_parser_fail_closed_without_extra_model_call(monkeypatch):
    monkeypatch.setenv("URUHA_P4_COMPACT_JSON_SCHEMA", "1")
    invalid = response_content()
    invalid["plans"][0].pop("response_mode")
    with pytest.raises(ValueError) as failure:
        compact.expand_compact_response(json.dumps(invalid), "stop")
    assert failure.value.compact_failure == {
        "failure_code": "candidate_missing_fields", "candidate_index": 0, "missing_field_count": 1
    }


def test_controller_flag_only_reaches_product_child_not_preflight(monkeypatch, tmp_path):
    layout = {"runtime_root": tmp_path, "memory_db": tmp_path / "memory_db",
              "session_db": tmp_path / "session_db", "web_logs": tmp_path / "web_logs",
              "jsonl_log": tmp_path / "web_logs/conversation.jsonl",
              "text_log": tmp_path / "web_logs/conversation.txt"}
    observed = []

    def preflight(**kwargs):
        observed.append(("preflight_input", dict(kwargs["environ"])))
        return {}, dict(kwargs["environ"]), layout, False, None

    def no_launch(argv):
        base = controller.launchd._isolated_env(layout, port=None)
        allowed = controller.launchd._isolated_env(layout, port=7931)
        child = None
        if argv[0] == "start" and "product" in argv:
            _, child, _, _, _ = controller.product_launcher.preflight_preference_fallback(
                environ=base, prewarm=False
            )
        observed.append(("action", list(argv), base, allowed, child))
        return 0

    monkeypatch.setattr(controller.product_launcher, "preflight_preference_fallback", preflight)
    monkeypatch.setattr(controller.prior.base_controller, "main", no_launch)
    monkeypatch.setenv("URUHA_P4_COMPACT_JSON_SCHEMA", "1")
    assert controller.main(["prepare"]) == 0
    assert "URUHA_P4_COMPACT_JSON_SCHEMA" not in observed[-1][3]
    assert controller.main(["start", "--mode", "product"]) == 0
    assert "URUHA_P4_COMPACT_JSON_SCHEMA" not in observed[-1][3]
    assert controller.main([
        "--compact-json-schema", "--product-port", "7931", "start", "--mode", "product"
    ]) == 0
    action = observed[-1]
    assert action[1] == ["start", "--mode", "product"]
    assert "URUHA_P4_COMPACT_JSON_SCHEMA" not in action[2]
    assert action[3]["URUHA_P4_COMPACT_JSON_SCHEMA"] == "1"
    assert action[4]["URUHA_P4_COMPACT_JSON_SCHEMA"] == "1"
    assert "URUHA_P4_COMPACT_JSON_SCHEMA" not in observed[-2][1]
    for rejected in (["--compact-json-schema", "prepare"],
                     ["--compact-json-schema", "status", "--runtime-root", str(tmp_path)],
                     ["--compact-json-schema", "start", "--mode", "inert"]):
        with pytest.raises(SystemExit):
            controller.main(rejected)
