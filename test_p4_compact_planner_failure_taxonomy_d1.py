"""Zero-model route go/no-go for the source-disjoint d1 diagnostic probe."""

from __future__ import annotations

import json
from pathlib import Path

from test_p4_direct_reply_act_m29_priority import _isolated


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_compact_planner_failure_taxonomy_d1_probe_2026-10-23.json").read_text()
)


def test_d1_reaches_real_compact_proxy_and_full_planner_without_model(tmp_path):
    observed = _isolated(tmp_path, """
        import json
        import os
        from types import SimpleNamespace

        import uruha_brain_mac as brain_runtime
        import uruha_compact_planner_p2 as compact
        import uruha_direct_reply_act_m29_priority_p4 as direct
        import uruha_direct_reply_act_planner_handoff_p4 as handoff
        from uruha_brain_mac import LeftBrain
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        source = json.load(open(
            "datasets/p4_compact_planner_failure_taxonomy_d1_probe_2026-10-23.json"
        ))["user_input"]
        brain_runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
        compact.install_compact_planner_p2()
        direct.install_direct_reply_act_m29_priority_p4()
        os.environ[handoff.ARM_ENV] = "control"
        captured = []

        def create(**kwargs):
            captured.append(kwargs)
            plans = [
                {"scene": "casual", "core_message_jp": "うん、よくやった。", "response_mode": "direct_answer"},
                {"scene": "casual", "core_message_jp": "そこまで進んだんだな。", "response_mode": "direct_answer"},
                {"scene": "casual", "core_message_jp": "やるじゃん。", "response_mode": "direct_answer"},
            ]
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
                finish_reason="stop",
            )])

        brain = _IsolatedContractBrain()
        brain.left_brain = LeftBrain(SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        ))
        result = brain.run_turn_debug(source)
        logic = result["logic"]
        m29 = logic["literal_topic_projection_m29"]
        assert direct.classify_direct_reply_act_p4(source)["requested_act"] == "brief_encouragement"
        assert m29[direct.LABEL]["requested_act"] == "brief_encouragement"
        assert m29["projection_required"] is False
        assert logic["source_semantic_atoms_m33"]["status"] == "not_applicable"
        assert (logic.get("adaptive_planner_fast_path_m18") or {}).get("applied") is not True
        assert logic["bounded_slow_path_m21"]["route"] == "full_planner"
        assert logic["bounded_slow_path_m21"]["compact_general_plan_p2"]["completed"] is True
        assert logic["semantic_route_m22"]["performed_route"] == "full_planner"
        receipt = logic[handoff.LABEL]
        assert receipt["status"] == "control_no_handoff"
        assert receipt["requested_act"] == "brief_encouragement"
        assert receipt["actual_route"] == "full_planner"
        assert len(captured) == 1
        request = captured[0]
        assert request["model"] == "qwen2.5:7b"
        assert request["temperature"] == 0.1
        assert request["max_tokens"] == 256
        assert request["response_format"] == {"type": "json_object"}
        assert request["timeout"] == 20.0
        assert request["messages"][1] == {"role": "user", "content": "User Input: " + source}
        print(json.dumps({"route": receipt["actual_route"], "calls": len(captured)}))
    """)
    assert observed == {"route": "full_planner", "calls": 1}


def test_d1_dataset_is_source_only_and_not_scored_holdout():
    assert DATA["status"] == "source_only_developer_authored_not_holdout"
    assert DATA["expected_direct_reply_act"] == "brief_encouragement"
    assert DATA["expected_product_route"] == "full_planner"
