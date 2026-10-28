"""Source-only P4 terminal-punctuation mechanism and route go/no-go."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_p4_direct_reply_act_m29_priority import _isolated
from uruha_brain_mac import RightBrain


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_direct_chat_terminal_punctuation_probe_2026-10-23.json").read_text()
)


def _logic(core, *, act="direct_chat_answer", scene="support"):
    return {
        "intent": "chat",
        "scene": scene,
        "core_message_jp": core,
        "human_speech_plan": {"dialogue_act": act},
    }


@pytest.mark.parametrize("vector", DATA["mechanism_vectors"], ids=lambda row: row["core"])
def test_support_direct_chat_joins_selected_core_without_extra_stop(vector):
    brain = RightBrain(load_model=False)
    variants = brain._speech_plan_variants(
        "", _logic(vector["core"]), DATA["user_input"]
    )
    assert variants == [vector["expected_variant"]]
    assert variants[0].startswith(vector["core"])


def test_other_act_and_existing_topic_exception_are_unchanged():
    brain = RightBrain(load_model=False)
    assert brain._speech_plan_variants(
        "", _logic("よくやった！", act="emotional_containment"), DATA["user_input"]
    ) == [
        "そのまま抱え込むなって。今は少し止まれ。",
        "しんどいなら一回ここで止まれ。無理に整えるな。",
    ]
    assert brain._speech_plan_variants(
        "", _logic("軽い話題でいい。", scene="casual"), DATA["user_input"]
    ) == [
        "じゃあ軽い話題でいいだろ。最近どうしてたんだよ。",
        "話題なら軽く近況でいい。最近どうしてたんだよ。",
    ]


@pytest.mark.parametrize("raw", ["よくやった！。そのくらいでいいだろ。", "次もいける？。そのくらいでいいだろ。"])
def test_visible_guard_still_rejects_direct_malformed_input(raw):
    brain = RightBrain(load_model=False)
    logic = _logic("よくやった！")
    final = brain.enforce_user_visible_japanese(
        raw, logic, user_input=DATA["user_input"], memory_data={}
    )
    audit = logic["visible_language_guard"]
    assert "malformed_japanese_punctuation" in audit["initial_rejection_reasons"]
    assert audit["repair_action"] == "safe_japanese_persona_fallback"
    assert final == "しんどいなら、今日は無理すんな。"


def test_e0_full_turn_route_reaches_support_legacy_variant_without_real_model(tmp_path):
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

        source = json.load(open(
            "datasets/p4_direct_chat_terminal_punctuation_probe_2026-10-23.json"
        ))["user_input"]
        runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
        compact.install_compact_planner_p2()
        expression.install_contextual_expression_commit_p2()
        direct.install_direct_reply_act_m29_priority_p4()
        os.environ[handoff.ARM_ENV] = "control"
        captured = []

        def create(**kwargs):
            captured.append(kwargs)
            plans = [
                {"scene": "support", "core_message_jp": "よくやった！", "response_mode": "direct_answer"},
                {"scene": "support", "core_message_jp": "そこまで進んだじゃん！", "response_mode": "direct_answer"},
                {"scene": "support", "core_message_jp": "一枚描き直せたんだな！", "response_mode": "direct_answer"},
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
        original_variants = RightBrain._speech_plan_variants
        actual_variant_calls = []
        def watch_variants(self, reply, logic_data, user_input, memory_data=None):
            variants = original_variants(
                self, reply, logic_data, user_input, memory_data=memory_data
            )
            if (
                logic_data.get("scene") == "support"
                and logic_data.get("dialogue_act") == "direct_chat_answer"
                and str(logic_data.get("core_message_jp") or "").endswith("！")
            ):
                actual_variant_calls.append(variants)
            return variants
        RightBrain._speech_plan_variants = watch_variants
        result = brain.run_turn_debug(source)
        logic = result["logic"]
        m29 = logic.get("literal_topic_projection_m29") or {}
        receipt = logic.get(handoff.LABEL) or {}
        surface = RightBrain(load_model=False)
        speech_plan = logic.get("human_speech_plan") or {}
        core = str(logic.get("core_message_jp") or "")
        p2_eligible, p2_reason, _ = expression.expression_commit_scope(
            surface, logic, source
        )
        print(json.dumps({
            "direct": direct.classify_direct_reply_act_p4(source).get("requested_act"),
            "m29_direct": (m29.get(direct.LABEL) or {}).get("requested_act"),
            "projection_required": m29.get("projection_required"),
            "m33": (logic.get("source_semantic_atoms_m33") or {}).get("status"),
            "m18_applied": (logic.get("adaptive_planner_fast_path_m18") or {}).get("applied"),
            "route": (logic.get("bounded_slow_path_m21") or {}).get("route"),
            "compact_completed": ((logic.get("bounded_slow_path_m21") or {}).get("compact_general_plan_p2") or {}).get("completed"),
            "handoff": receipt.get("status"),
            "scene": logic.get("scene"),
            "act": speech_plan.get("dialogue_act"),
            "p2_eligible": p2_eligible,
            "p2_reason": p2_reason,
            "core": core,
            "actual_variant_calls": actual_variant_calls,
            "reply": result["reply"],
            "guard_repair": (logic.get("visible_language_guard") or {}).get("repair_action"),
            "guard_initial_reasons": (logic.get("visible_language_guard") or {}).get("initial_rejection_reasons"),
            "episode_reply": brain.memory.saved_episodes[-1]["reply"],
            "episode_count": len(brain.memory.saved_episodes),
            "calls": len(captured),
        }, ensure_ascii=False))
    """)
    assert observed["direct"] == "brief_encouragement"
    assert observed["m29_direct"] == "brief_encouragement"
    assert observed["projection_required"] is False
    assert observed["m33"] == "not_applicable"
    assert observed["m18_applied"] is not True
    assert observed["route"] == "full_planner"
    assert observed["compact_completed"] is True
    assert observed["handoff"] == "control_no_handoff"
    assert observed["scene"] == "support"
    assert observed["act"] == "direct_chat_answer"
    assert observed["p2_eligible"] is False
    assert observed["p2_reason"] == "protected_scene"
    assert observed["core"].endswith("！")
    assert [observed["core"] + "そのくらいでいいだろ。"] in observed["actual_variant_calls"]
    assert observed["reply"] == observed["core"] + "そのくらいでいいだろ。", observed
    assert observed["guard_repair"] == "none", observed
    assert observed["guard_initial_reasons"] == [], observed
    assert observed["episode_reply"] == observed["reply"]
    assert observed["episode_count"] == 1
    assert observed["calls"] == 1
