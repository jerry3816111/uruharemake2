"""Zero-provider full-turn negative routes for the opt-in f7 selector."""

from __future__ import annotations

import pytest

from test_p4_direct_reply_act_m29_priority import _isolated


@pytest.mark.parametrize("scenario", ["non_full_rule", "compact_failure", "all_generic"])
def test_f7_flag_on_does_not_license_unavailable_or_ungrounded_candidates(tmp_path, scenario):
    observed = _isolated(tmp_path, f"""
        import json
        import os
        from types import SimpleNamespace

        import uruha_brain_mac as runtime
        import uruha_compact_planner_p2 as compact
        import uruha_contextual_expression_commit_p2 as expression
        import uruha_direct_reply_act_m29_priority_p4 as direct
        import uruha_web_ui_product_p4_direct_reply_act_m29_priority as product_entry
        from uruha_brain_mac import LeftBrain, RightBrain
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        scenario = {scenario!r}
        source = json.load(open("datasets/p4_source_event_core_utility_f7_probe_2026-10-24.json"))["source"]
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
        compact.install_compact_planner_p2()
        expression.install_contextual_expression_commit_p2()
        product_entry.install_product_chain()
        os.environ["URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"] = "control"
        os.environ[compact._SCHEMA_ARM_ENV] = "1"
        os.environ["URUHA_P4_REPAIR_CUE_BOUNDARY"] = "1"

        generic_plans = [
            {{"scene": "support", "core_message_jp": "おめでとう、いいじゃん！", "response_mode": "direct_answer"}},
            {{"scene": "support", "core_message_jp": "よく頑張ったね。", "response_mode": "direct_answer"}},
            {{"scene": "support", "core_message_jp": "その調子でいけるよ。", "response_mode": "direct_answer"}},
        ]
        outcomes = []
        for enabled in ((False, True) if scenario == "all_generic" else (True,)):
            if enabled:
                os.environ["URUHA_P4_SOURCE_EVENT_CORE_UTILITY"] = "1"
            else:
                os.environ.pop("URUHA_P4_SOURCE_EVENT_CORE_UTILITY", None)
            calls = []
            def create(**kwargs):
                calls.append(kwargs)
                if scenario == "non_full_rule":
                    raise AssertionError("non-full route called fake provider")
                if scenario == "compact_failure":
                    content = json.dumps({{"plans": []}})
                else:
                    content = json.dumps({{"plans": generic_plans}}, ensure_ascii=False)
                return SimpleNamespace(choices=[SimpleNamespace(
                    message=SimpleNamespace(content=content), finish_reason="stop",
                )])

            brain = _IsolatedContractBrain()
            left = LeftBrain(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
            if scenario == "non_full_rule":
                rule_plan = left._fallback_plan()
                rule_plan.update({{
                    "intent": "chat", "scene": "support", "response_mode": "direct_answer",
                    "core_message_jp": "おめでとう、いいじゃん！",
                }})
                left._rule_based_plan = lambda *_args: rule_plan
            if scenario == "all_generic":
                def fit(plan, *_args):
                    return 1.0 if plan.get("core_message_jp") == generic_plans[0]["core_message_jp"] else 0.75
                for name in ("_persona_fit_score", "_psyche_fit_score", "_continuity_fit_score",
                             "_human_fit_score", "_belief_gap_fit_score", "_procedural_fit_score"):
                    setattr(left, name, fit)
                left._critique_plan = lambda *_args: {{"needs_revision": False, "issues": [], "internal_note": ""}}
            brain.left_brain = left
            brain.right_brain = RightBrain(load_model=False)
            result = brain.run_turn_debug(source)
            logic = result["logic"]
            m21 = logic.get("bounded_slow_path_m21") or {{}}
            audit = logic.get("source_event_core_utility_p4")
            outcomes.append({{
                "enabled": enabled,
                "model_calls": len(calls),
                "m29_act": ((logic.get("literal_topic_projection_m29") or {{}})
                            .get(direct.LABEL) or {{}}).get("requested_act"),
                "m33_status": (logic.get("source_semantic_atoms_m33") or {{}}).get("status"),
                "route": m21.get("route"),
                "status": m21.get("status"),
                "model_call_completed": m21.get("model_call_completed"),
                "fallback_used": m21.get("fallback_used"),
                "compact": m21.get("compact_general_plan_p2"),
                "core": logic.get("core_message_jp"),
                "audit": audit,
                "graph_count": sum(row.get("label") == "source_event_core_utility_p4"
                                   for row in result["runtime_trace"]["blackboard"]),
                "reply_equals_episode": result["reply"] == brain.memory.saved_episodes[-1]["reply"],
            }})
        print(json.dumps(outcomes, ensure_ascii=False))
    """)

    assert all(row["m29_act"] == "brief_encouragement" for row in observed)
    assert all(row["m33_status"] == "not_applicable" for row in observed)
    assert all(row["reply_equals_episode"] for row in observed)
    if scenario == "non_full_rule":
        row, = observed
        assert row["route"] == "deterministic_rule_plan"
        assert row["model_calls"] == 0
        assert row["model_call_completed"] is False
        assert row["audit"] is None and row["graph_count"] == 0
    elif scenario == "compact_failure":
        row, = observed
        assert row["route"] == "full_planner"
        assert row["status"] == "error_fallback"
        assert row["model_calls"] == 1
        assert row["model_call_completed"] is False and row["fallback_used"] is True
        assert row["compact"]["completed"] is False
        assert row["compact"]["failure_code"] == "candidate_count"
        assert row["audit"] is None and row["graph_count"] == 0
    else:
        off, on = observed
        assert off["model_calls"] == on["model_calls"] == 1
        assert off["core"] == on["core"]
        assert off["audit"] is None and off["graph_count"] == 0
        assert on["route"] == "full_planner"
        assert on["model_call_completed"] is True and on["fallback_used"] is False
        assert on["compact"]["completed"] is True and on["compact"]["candidate_count"] == 3
        assert on["audit"]["status"] == "no_grounded_candidate"
        assert on["audit"]["manipulation_status"] == "no_grounded_candidate"
        assert on["audit"]["old_index"] == on["audit"]["new_index"]
        assert not any(row["grounded"] for row in on["audit"]["candidate_coverage"])
        assert on["graph_count"] == 1
