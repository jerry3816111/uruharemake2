"""Isolated full-route contract for the f6 audited CJK language boundary."""

from __future__ import annotations

import json
from pathlib import Path

from test_p4_direct_reply_act_m29_priority import _isolated
from test_semantic_preserving_japanese_repair_m49 import _brain


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_visible_japanese_guard_f6_probe_2026-10-24.json").read_text()
)


def test_f6_support_m49_stays_protected_and_final_guard_fails_closed():
    brain = _brain()
    raw = "頑張ったね。頑張り继续！そのくらいでいいだろ。"
    source = "初めて自分でシャツのボタンを付け直せた。今は一言だけ励まして。"
    logic = {
        "intent": "chat",
        "scene": "support",
        "surface_act": "direct_chat_answer",
        "core_message_jp": "頑張ったね。頑張り继续！",
    }
    candidate, trace = brain._repair_user_visible_semantics_m49(
        raw, logic, source, memory_data={}
    )
    visible = brain.right_brain.enforce_user_visible_japanese(
        candidate, logic, user_input=source, memory_data={}
    )

    assert trace["status"] == "protected_route_not_repaired"
    assert trace["reason"] == "protected_scene:support"
    assert trace["model_call_attempted"] is False
    assert brain.left_brain.calls == []
    assert "nonstandard_cjk_surface" in logic["visible_language_guard"]["initial_rejection_reasons"]
    assert "继续" not in visible


def test_f6_full_route_rejects_simplified_candidate_before_episode(tmp_path):
    observed = _isolated(tmp_path, """
        import json
        import os
        from types import SimpleNamespace

        import uruha_brain_mac as runtime
        import uruha_compact_planner_p2 as compact
        import uruha_contextual_expression_commit_p2 as expression
        import uruha_direct_reply_act_planner_handoff_p4 as handoff
        import uruha_web_ui_product_p4_direct_reply_act_m29_priority as product_entry
        from uruha_brain_mac import LeftBrain, RightBrain
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        with open("datasets/p4_visible_japanese_guard_f6_probe_2026-10-24.json") as stream:
            source = json.load(stream)["source"]
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
        compact.install_compact_planner_p2()
        expression.install_contextual_expression_commit_p2()
        os.environ[handoff.ARM_ENV] = "control"
        os.environ["URUHA_P4_REPAIR_CUE_BOUNDARY"] = "1"
        os.environ[compact._SCHEMA_ARM_ENV] = "1"
        product_entry.install_product_chain()
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            plans = [
                {"scene": "support", "core_message_jp": "初めて小皿を焼けたんだな。继续頑張れ！", "response_mode": "direct_answer"},
                {"scene": "support", "core_message_jp": "陶芸の小皿、焼き上げたんだな。继续頑張れ！", "response_mode": "direct_answer"},
                {"scene": "support", "core_message_jp": "小皿を自分で焼いたのか。继续頑張れ！", "response_mode": "direct_answer"},
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
        print(json.dumps({
            "compact_completed": ((logic.get("bounded_slow_path_m21") or {}).get("compact_general_plan_p2") or {}).get("completed"),
            "guard_reasons": (logic.get("visible_language_guard") or {}).get("initial_rejection_reasons"),
            "guard_changed": (logic.get("visible_language_guard") or {}).get("changed"),
            "reply": result["reply"],
            "reply_equals_episode": result["reply"] == brain.memory.saved_episodes[-1]["reply"],
            "episode_count": len(brain.memory.saved_episodes),
            "fake_model_calls": len(calls),
            "request_format": calls[0]["response_format"]["type"],
        }, ensure_ascii=False))
    """)
    assert DATA["schema"] == "p4_visible_japanese_guard_f6_developer_probe_v1"
    assert observed["compact_completed"] is True
    assert "nonstandard_cjk_surface" in observed["guard_reasons"]
    assert observed["guard_changed"] is True
    assert "继续" not in observed["reply"]
    assert observed["reply_equals_episode"] is True
    assert observed["episode_count"] == observed["fake_model_calls"] == 1
    assert observed["request_format"] == "json_schema"
