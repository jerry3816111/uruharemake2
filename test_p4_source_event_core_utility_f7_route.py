"""f7 zero-provider full-turn route and graph contract."""

from __future__ import annotations

import json
from pathlib import Path

from test_p4_direct_reply_act_m29_priority import _isolated


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_source_event_core_utility_f7_probe_2026-10-24.json").read_text()
)


def test_f7_same_fake_compact_candidates_change_only_selection_and_trace(tmp_path):
    observed = _isolated(tmp_path, """
        import hashlib
        import io
        import json
        import os
        from contextlib import redirect_stdout
        from types import SimpleNamespace

        import uruha_brain_mac as runtime
        import uruha_compact_planner_p2 as compact
        import uruha_contextual_expression_commit_p2 as expression
        import uruha_web_ui_product_p4_direct_reply_act_m29_priority as product_entry
        from uruha_brain_mac import LeftBrain, RightBrain
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        source = json.load(open("datasets/p4_source_event_core_utility_f7_probe_2026-10-24.json"))["source"]
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
        compact.install_compact_planner_p2()
        expression.install_contextual_expression_commit_p2()
        product_entry.install_product_chain()
        os.environ["URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"] = "control"
        os.environ[compact._SCHEMA_ARM_ENV] = "1"
        os.environ["URUHA_P4_REPAIR_CUE_BOUNDARY"] = "1"
        plans = [
            {"scene": "support", "core_message_jp": "おめでとう、いいじゃん！", "response_mode": "direct_answer"},
            {"scene": "support", "core_message_jp": "庭のベンチを塗り直したんだ、いいじゃん！", "response_mode": "direct_answer"},
            {"scene": "support", "core_message_jp": "頑張ったね、応援してる。", "response_mode": "direct_answer"},
        ]
        results = []
        for enabled in (False, True, "downstream_override"):
            if enabled:
                os.environ["URUHA_P4_SOURCE_EVENT_CORE_UTILITY"] = "1"
            else:
                os.environ.pop("URUHA_P4_SOURCE_EVENT_CORE_UTILITY", None)
            if enabled == "downstream_override":
                original_apply = runtime.ufu.apply_hypothesis_to_plan
                def replace_selected_core(*args, **kwargs):
                    result = original_apply(*args, **kwargs)
                    result["core_message_jp"] = "少し確認させて。"
                    return result
                runtime.ufu.apply_hypothesis_to_plan = replace_selected_core
            calls = []
            def create(**kwargs):
                calls.append(kwargs)
                return SimpleNamespace(choices=[SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
                    finish_reason="stop",
                )])
            brain = _IsolatedContractBrain()
            left = LeftBrain(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
            def fit(plan, *_args):
                return 1.0 if plan.get("core_message_jp") == plans[0]["core_message_jp"] else 0.75
            for name in ("_persona_fit_score", "_psyche_fit_score", "_continuity_fit_score",
                         "_human_fit_score", "_belief_gap_fit_score", "_procedural_fit_score"):
                setattr(left, name, fit)
            left._critique_plan = lambda *_args: {"needs_revision": False, "issues": [], "internal_note": ""}
            think_results = []
            original_think = left.think
            def traced_think(*args, **kwargs):
                result = original_think(*args, **kwargs)
                think_results.append({
                    "core": result.get("core_message_jp"),
                    "status": (result.get("bounded_slow_path_m21") or {}).get("status"),
                    "error_type": (result.get("bounded_slow_path_m21") or {}).get("error_type"),
                    "audit": result.get("source_event_core_utility_p4"),
                })
                return result
            left.think = traced_think
            brain.left_brain = left
            brain.right_brain = RightBrain(load_model=False)
            logs = io.StringIO()
            with redirect_stdout(logs):
                turn = brain.run_turn_debug(source)
            logic = turn["logic"]
            rows = turn["runtime_trace"]["blackboard"]
            results.append({
                "enabled": enabled,
                "model_calls": len(calls),
                "prompt_sha256": hashlib.sha256(calls[0]["messages"][0]["content"].encode()).hexdigest(),
                "response_format": calls[0]["response_format"]["type"],
                "compact": (logic.get("bounded_slow_path_m21") or {}).get("compact_general_plan_p2"),
                "m21": (logic.get("bounded_slow_path_m21") or {}).get("route"),
                "core": logic.get("core_message_jp"),
                "think_results": think_results,
                "errors": [line for line in logs.getvalue().splitlines() if "Ollama Left Brain Error" in line],
                "audit": logic.get("source_event_core_utility_p4"),
                "graph_count": sum(row.get("label") == "source_event_core_utility_p4" for row in rows),
                "graph_audit": next((row.get("payload") for row in rows if row.get("label") == "source_event_core_utility_p4"), None),
                "reply_equals_episode": turn["reply"] == brain.memory.saved_episodes[-1]["reply"],
            })
        print(json.dumps(results, ensure_ascii=False))
    """)
    off, on, overridden = observed
    assert off["model_calls"] == on["model_calls"] == overridden["model_calls"] == 1
    assert off["prompt_sha256"] == on["prompt_sha256"] == overridden["prompt_sha256"]
    assert off["response_format"] == on["response_format"] == overridden["response_format"] == "json_schema"
    assert off["compact"]["completed"] is on["compact"]["completed"] is overridden["compact"]["completed"] is True
    assert off["m21"] == on["m21"] == overridden["m21"] == "full_planner"
    assert off["think_results"][0]["status"] == on["think_results"][0]["status"] == overridden["think_results"][0]["status"] == "completed_within_budget"
    assert not off["errors"] and not on["errors"] and not overridden["errors"]
    assert off["core"] == "おめでとう、いいじゃん！", (off, on)
    assert off["audit"] is None and off["graph_count"] == 0
    assert on["core"] == "庭のベンチを塗り直したんだ、いいじゃん！"
    assert on["audit"]["manipulation_status"] == "selection_changed"
    assert on["audit"]["old_index"] == 0 and on["audit"]["new_index"] == 1
    assert on["graph_count"] == 1 and on["graph_audit"] == on["audit"]
    assert overridden["core"] == "少し確認させて。"
    assert overridden["audit"]["manipulation_status"] == "not_exercised"
    assert overridden["audit"]["downstream_core_changed"] is True
    assert overridden["audit"]["final_core_matches_winner"] is False
    assert overridden["graph_count"] == 1 and overridden["graph_audit"] == overridden["audit"]
    assert DATA["source"] not in repr(on["audit"])
    assert all(row["core_message_jp"] not in repr(on["audit"]) for row in (
        {"core_message_jp": "おめでとう、いいじゃん！"},
        {"core_message_jp": "庭のベンチを塗り直したんだ、いいじゃん！"},
    ))
    assert off["reply_equals_episode"] and on["reply_equals_episode"] and overridden["reply_equals_episode"]


def test_f7_critique_rebuild_cannot_relicense_same_grounded_model_candidate(tmp_path):
    observed = _isolated(tmp_path, """
        import json
        from copy import deepcopy
        from types import SimpleNamespace

        import uruha_brain_mac as runtime
        from uruha_brain_mac import LeftBrain
        from test_p4_source_event_core_utility_f7 import _handoff

        source = "自分で木の椅子を磨いた。今は一言だけ励まして。"
        handoff = _handoff(source)
        plans = [
            {"candidate_label": "default", "scene": "support", "response_mode": "direct_answer", "core_message_jp": "おめでとう、いいじゃん！"},
            {"candidate_label": "softer", "scene": "support", "response_mode": "direct_answer", "core_message_jp": "木の椅子を磨いたんだ、いいじゃん！"},
            {"candidate_label": "sharper", "scene": "support", "response_mode": "direct_answer", "core_message_jp": "頑張ったな。"},
        ]
        left = LeftBrain(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: None))))
        def fit(plan, *_args):
            return 1.0 if plan.get("core_message_jp") == plans[0]["core_message_jp"] else 0.75
        for name in ("_persona_fit_score", "_psyche_fit_score", "_continuity_fit_score",
                     "_human_fit_score", "_belief_gap_fit_score", "_procedural_fit_score"):
            setattr(left, name, fit)
        calls = [0]
        def critique(*_args):
            calls[0] += 1
            return {"needs_revision": calls[0] == 1, "issues": ["test"] if calls[0] == 1 else [], "internal_note": ""}
        left._critique_plan = critique
        left._revise_plan_from_critique = lambda plan, *_args: {**deepcopy(plan), "core_message_jp": "言い換える"}
        left._derive_bayesian_candidates = lambda *_args: deepcopy(plans)
        token = runtime._P4_SOURCE_EVENT_CORE_HANDOFF.set(handoff)
        try:
            final = left._run_multitick_planner(
                plans, source, {"working_memory_items": []}, {"mood": "neutral", "trust": 0.5},
                internal_monologue="one", tick_budget=2,
            )
        finally:
            runtime._P4_SOURCE_EVENT_CORE_HANDOFF.reset(token)
        print(json.dumps({
            "core": final["core_message_jp"],
            "audit": final.get("source_event_core_utility_p4"),
            "revision": final["planner_repair_applied"],
            "ticks": final["planner_tick_count"],
        }, ensure_ascii=False))
    """)
    assert observed["core"] == "おめでとう、いいじゃん！"
    assert observed["revision"] is True and observed["ticks"] == 2
    audit = observed["audit"]
    assert audit["eligible"] is True
    assert audit["old_index"] == 0 and audit["new_index"] == 1
    assert audit["candidate_set_scope"] == "initial_model_candidates_only"
    assert audit["manipulation_status"] == "not_exercised"
    assert audit["final_core_matches_winner"] is False
