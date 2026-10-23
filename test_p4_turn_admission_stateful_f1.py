"""Frozen f1 source-only route check; no real model or Web claim."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_p4_direct_reply_act_m29_priority import _isolated


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_turn_admission_stateful_f1_probe_2026-10-24.json").read_text()
)


@pytest.mark.xfail(strict=True, reason="f1 frozen go/no-go failed: embedded え selects repair_check")
def test_f1_fake_full_turn_reaches_expected_route_and_episode(tmp_path):
    observed = _isolated(tmp_path, """
        import json
        import os
        from types import SimpleNamespace

        import uruha_brain_mac as runtime
        import uruha_compact_planner_p2 as compact
        import uruha_contextual_expression_commit_p2 as expression
        import uruha_direct_reply_act_m29_priority_p4 as direct
        import uruha_direct_reply_act_planner_handoff_p4 as handoff
        from uruha_brain_mac import LeftBrain, RightBrain
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        with open("datasets/p4_turn_admission_stateful_f1_probe_2026-10-24.json") as stream:
            source = json.load(stream)["user_input"]
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
        compact.install_compact_planner_p2()
        expression.install_contextual_expression_commit_p2()
        direct.install_direct_reply_act_m29_priority_p4()
        os.environ[handoff.ARM_ENV] = "control"
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            plans = [
                {"scene": "support", "core_message_jp": "庭の草取り、終わらせたんだな。よくやった！", "response_mode": "direct_answer"},
                {"scene": "support", "core_message_jp": "ちゃんと終わらせたんだな。えらいじゃん！", "response_mode": "direct_answer"},
                {"scene": "support", "core_message_jp": "また続けられるだろ！", "response_mode": "direct_answer"},
            ]
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
                finish_reason="stop",
            )])

        brain = _IsolatedContractBrain()
        brain.left_brain = LeftBrain(SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        ))
        brain.right_brain = RightBrain(load_model=False)
        result = brain.run_turn_debug(source)
        logic = result["logic"]
        m29 = logic.get("literal_topic_projection_m29") or {}
        speech_plan = logic.get("human_speech_plan") or {}
        print(json.dumps({
            "direct": direct.classify_direct_reply_act_p4(source).get("requested_act"),
            "m29_direct": (m29.get(direct.LABEL) or {}).get("requested_act"),
            "m29_projection_required": m29.get("projection_required"),
            "m33": (logic.get("source_semantic_atoms_m33") or {}).get("status"),
            "m18_applied": (logic.get("adaptive_planner_fast_path_m18") or {}).get("applied"),
            "m21_route": (logic.get("bounded_slow_path_m21") or {}).get("route"),
            "compact_completed": ((logic.get("bounded_slow_path_m21") or {}).get("compact_general_plan_p2") or {}).get("completed"),
            "scene": logic.get("scene"),
            "act": speech_plan.get("dialogue_act"),
            "reply_equals_episode": result["reply"] == brain.memory.saved_episodes[-1]["reply"],
            "episode_count": len(brain.memory.saved_episodes),
            "fake_model_calls": len(calls),
        }, ensure_ascii=False))
    """)
    assert observed["direct"] == DATA["expected_direct_reply_act"]
    assert observed["m29_direct"] == DATA["expected_direct_reply_act"]
    assert observed["m29_projection_required"] is False
    assert observed["m33"] == DATA["expected_m33"]
    assert observed["m18_applied"] is not True
    assert observed["m21_route"] == DATA["expected_route"]
    assert observed["compact_completed"] is True
    assert observed["scene"] == DATA["expected_scene"]
    assert observed["act"] == DATA["expected_dialogue_act"], json.dumps(observed, ensure_ascii=False)
    assert observed["reply_equals_episode"] is True
    assert observed["episode_count"] == 1
    assert observed["fake_model_calls"] == 1
