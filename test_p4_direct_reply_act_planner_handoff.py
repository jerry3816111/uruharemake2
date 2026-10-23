"""Zero-model evidence for the prospective same-carrier direct-act ablation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_p4_direct_reply_act_m29_priority import _isolated


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_direct_reply_act_planner_handoff_probe_2026-10-23.json").read_text()
)


@pytest.mark.parametrize("case", DATA["cases"], ids=lambda case: case["case_id"])
def test_frozen_case_classification_without_person_state_claim(case):
    from uruha_direct_reply_act_m29_priority_p4 import classify_direct_reply_act_p4

    got = classify_direct_reply_act_p4(case["user_input"])
    assert got["status"] == case["expected_admission"]
    assert got["requested_act"] == case["requested_act"]
    assert got["private_state_truth_claimed"] is False
    assert case["user_input"] not in repr(got)


def test_source_m29_m33_certificate_tampering_fails_closed(tmp_path):
    _isolated(tmp_path, """
        from copy import deepcopy
        import json
        import uruha_adaptive_person_model as adaptive
        import uruha_direct_reply_act_m29_priority_p4 as direct
        import uruha_direct_reply_act_planner_handoff_p4 as handoff
        import uruha_source_semantic_atoms_m33 as atoms

        source = "午後、銅色のカードを棚に戻した。今日はここまでやったから、今は一言だけ労って。"
        assert direct.install_direct_reply_act_m29_priority_p4()
        projection = adaptive.build_literal_topic_projection_candidate_m29(
            source, {}, {"pragmatic_label": "literal_intent_unresolved"}
        )
        source_atoms = atoms.extract_source_semantic_atoms_m33(source, projection)
        certificate = handoff.validate_handoff_p4(source, projection, source_atoms)
        assert certificate and certificate["requested_act"] == "brief_care"
        assert source not in repr(certificate)
        fragment = handoff.planner_constraint_p4(source, certificate)
        assert "requested_act=brief_care" in fragment
        assert source not in fragment
        assert "頑張ったね" not in fragment
        assert handoff.planner_constraint_p4(source + "別", certificate) == ""
        altered = deepcopy(projection)
        altered[direct.LABEL]["cue_sha256"] = "0" * 64
        assert handoff.validate_handoff_p4(source, altered, source_atoms) is None
        altered = deepcopy(projection)
        altered["input_digest"] = "0" * 16
        assert handoff.validate_handoff_p4(source, altered, source_atoms) is None
        altered = deepcopy(projection)
        altered["projection_required"] = True
        assert handoff.validate_handoff_p4(source, altered, source_atoms) is None
        altered = deepcopy(projection)
        altered["required_observable_act"] = "some_other_act"
        assert handoff.validate_handoff_p4(source, altered, source_atoms) is None
        assert handoff.validate_handoff_p4(source, projection, {"status": "source_atoms_extracted"}) is None
        print(json.dumps({"status": "ok"}))
    """)


def test_reported_speaker_cannot_become_current_user_planner_act(tmp_path):
    _isolated(tmp_path, """
        import uruha_adaptive_person_model as adaptive
        import uruha_direct_reply_act_m29_priority_p4 as direct
        import uruha_direct_reply_act_planner_handoff_p4 as handoff
        import uruha_source_semantic_atoms_m33 as atoms

        direct.install_direct_reply_act_m29_priority_p4()
        for source in (
            "母が言った。今日はここまでやったから、今は一言だけ労って。",
            "上司が言った。今は一言だけ労って。",
            "兄からの伝言。今は一言だけ労って。",
            "母はこう言った。今は一言だけ労って。",
            "上司から頼まれた。今は一言だけ労って。",
            "姉の依頼。今は一言だけ労って。",
            "母に言われた。今は一言だけ労って。",
            "母が言ってた。今は一言だけ労って。",
            "母から聞いた。今は一言だけ労って。",
            "母からのお願い。今は一言だけ労って。",
            "母に仕事の進捗を話した。今は一言だけ労って。",
        ):
            projection = adaptive.build_literal_topic_projection_candidate_m29(
                source, {}, {"pragmatic_label": "literal_intent_unresolved"}
            )
            source_atoms = atoms.extract_source_semantic_atoms_m33(source, projection)
            assert direct.classify_direct_reply_act_p4(source)["status"] == "ambiguous"
            assert direct.LABEL not in projection
            assert handoff.validate_handoff_p4(source, projection, source_atoms) is None
        near = "母と仕事を終えた。今は一言だけ労って。"
        assert direct.classify_direct_reply_act_p4(near)["status"] == "direct"
        print('{"status": "ok"}')
    """)


def test_control_and_treatment_same_compact_request_except_bound_act(tmp_path):
    observed = _isolated(tmp_path, """
        from copy import deepcopy
        import json
        import os
        from types import SimpleNamespace

        import uruha_adaptive_person_model as adaptive
        import uruha_compact_planner_p2 as compact
        import uruha_direct_reply_act_m29_priority_p4 as direct
        import uruha_direct_reply_act_planner_handoff_p4 as handoff
        import uruha_brain_mac as brain_runtime
        from uruha_brain_mac import LeftBrain
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        cases = json.load(open("datasets/p4_direct_reply_act_planner_handoff_probe_2026-10-23.json"))["cases"]
        brain_runtime.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = 20.0
        compact.install_compact_planner_p2()
        direct.install_direct_reply_act_m29_priority_p4()
        original_m31 = LeftBrain.authorize_literal_topic_m31
        def no_model_m31(self, source, projection):
            return ({
                "intent": "chat", "scene": "casual", "core_message_jp": "そうか。",
                "jp_summary": "確認", "response_mode": "direct_answer",
                "surface_act": "plain_reply", "constraints": {"max_chars": 96},
            }, {
                "schema": adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
                "status": "fixture_no_model", "surface_authority": True,
                "model_call_completed": False, "raw_dialogue_persisted": False,
            })
        LeftBrain.authorize_literal_topic_m31 = no_model_m31

        captured = []
        def make_brain():
            brain = _IsolatedContractBrain()
            def create(**kwargs):
                captured.append(deepcopy(kwargs))  # Underlying client, AFTER compact proxy.
                plans = [
                    {"scene": "casual", "core_message_jp": "うん、よくやった。", "response_mode": "direct_answer"},
                    {"scene": "casual", "core_message_jp": "そこまでやったの、えらいな。", "response_mode": "direct_answer"},
                    {"scene": "casual", "core_message_jp": "やるじゃん。", "response_mode": "direct_answer"},
                ]
                return SimpleNamespace(choices=[SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps({"plans": plans}, ensure_ascii=False)),
                    finish_reason="stop",
                )])
            brain.left_brain = LeftBrain(SimpleNamespace(
                chat=SimpleNamespace(completions=SimpleNamespace(create=create))
            ))
            return brain

        paired = []
        for case in cases[:2]:
            requests = {}
            for arm in ("control", "treatment"):
                os.environ[handoff.ARM_ENV] = arm
                before = len(captured)
                result = make_brain().run_turn_debug(case["user_input"])
                assert len(captured) == before + 1
                request = captured[-1]
                requests[arm] = request
                logic = result["logic"]
                receipt = logic[handoff.LABEL]
                assert logic["literal_topic_projection_m29"]["projection_required"] is False
                assert logic["bounded_slow_path_m21"]["route"] == "full_planner"
                assert logic["bounded_slow_path_m21"]["compact_general_plan_p2"]["completed"] is True
                assert logic["semantic_route_m22"]["performed_route"] == "full_planner"
                assert receipt["actual_route"] == "full_planner"
                assert receipt["status"] == ("control_no_handoff" if arm == "control" else "treatment_prompt_injected")
                assert receipt["planner_prompt_injected"] == (arm == "treatment")
                assert receipt["requested_act"] == case["requested_act"]
                assert case["user_input"] not in repr(receipt)
                node = next(row for row in result["runtime_trace"]["blackboard"] if row["label"] == handoff.LABEL)
                assert node["payload"] == receipt
                assert request["messages"][1] == {"role": "user", "content": "User Input: " + case["user_input"]}
                assert request["model"] == "qwen2.5:7b"
                assert request["temperature"] == 0.1
                assert request["max_tokens"] == 256
                assert request["response_format"] == {"type": "json_object"}
                assert request["timeout"] == 20.0
            control, treatment = requests["control"], requests["treatment"]
            c_system = control["messages"][0]["content"]
            t_system = treatment["messages"][0]["content"]
            assert "[Current User direct reply act — P4 opt-in]" not in c_system
            certificate = logic["literal_topic_projection_m29"][direct.LABEL]
            validated = handoff.validate_handoff_p4(
                case["user_input"], logic["literal_topic_projection_m29"],
                logic["source_semantic_atoms_m33"],
            )
            segment = handoff.planner_constraint_p4(case["user_input"], validated)
            assert t_system.count(segment) == 1
            assert t_system.replace(segment, "", 1) == c_system
            assert {k: v for k, v in treatment.items() if k != "messages"} == {
                k: v for k, v in control.items() if k != "messages"
            }
            assert treatment["messages"][1:] == control["messages"][1:]
            assert certificate["requested_act"] == case["requested_act"]
            paired.append({"case": case["case_id"], "route": "full_planner", "only_delta": "source_bound_constraint"})

        negative = []
        for case in cases[2:]:
            os.environ[handoff.ARM_ENV] = "treatment"
            before = len(captured)
            result = make_brain().run_turn_debug(case["user_input"])
            receipt = result["logic"][handoff.LABEL]
            assert receipt["requested_act"] is None
            assert receipt["planner_prompt_injected"] is False
            assert receipt["status"] == "not_admitted"
            for request in captured[before:]:
                assert "[Current User direct reply act — P4 opt-in]" not in request["messages"][0]["content"]
            negative.append({"case": case["case_id"], "route": receipt["actual_route"], "calls": len(captured) - before})

        # Reuse one brain across turns: an injected act cannot linger in a
        # later control turn or leak into an unrelated future narrative.
        shared = make_brain()
        os.environ[handoff.ARM_ENV] = "treatment"
        shared.run_turn_debug(cases[0]["user_input"])
        assert "[Current User direct reply act — P4 opt-in]" in captured[-1]["messages"][0]["content"]
        os.environ[handoff.ARM_ENV] = "control"
        before = len(captured)
        second = shared.run_turn_debug(cases[1]["user_input"])
        for request in captured[before:]:
            assert "[Current User direct reply act — P4 opt-in]" not in request["messages"][0]["content"]
        assert second["logic"][handoff.LABEL]["planner_prompt_injected"] is False
        os.environ[handoff.ARM_ENV] = "treatment"
        before = len(captured)
        third = shared.run_turn_debug(cases[2]["user_input"])
        for request in captured[before:]:
            assert "[Current User direct reply act — P4 opt-in]" not in request["messages"][0]["content"]
        assert third["logic"][handoff.LABEL]["requested_act"] is None

        # With no opt-in arm, neither prompt nor route receipt changes.
        os.environ.pop(handoff.ARM_ENV)
        off = make_brain().run_turn_debug(cases[0]["user_input"])
        assert handoff.LABEL not in off["logic"]
        assert "direct_reply_act_prompt_injected_p4" not in off["logic"]["bounded_slow_path_m21"]
        assert "[Current User direct reply act — P4 opt-in]" not in captured[-1]["messages"][0]["content"]
        LeftBrain.authorize_literal_topic_m31 = original_m31
        print(json.dumps({"paired": paired, "negative": negative, "captured": len(captured)}, ensure_ascii=False))
    """)
    assert len(observed["paired"]) == 2
    assert len(observed["negative"]) == 5


def test_detached_controller_arm_is_only_product_child_env(tmp_path, monkeypatch):
    import p4_direct_reply_act_m29_priority_detached_control as controller

    original_main = controller.prior.base_controller.main
    observed = []
    preflight_calls = []
    layout = {"runtime_root": tmp_path, "memory_db": tmp_path, "session_db": tmp_path,
              "web_logs": tmp_path, "jsonl_log": tmp_path / "a", "text_log": tmp_path / "b"}

    def fake_preflight(**kwargs):
        preflight_calls.append(kwargs)
        return kwargs

    monkeypatch.setattr(controller.product_launcher, "preflight_preference_fallback", fake_preflight)

    def fake_main(forwarded):
        observed.append((list(forwarded), controller.launchd._isolated_env(layout, port=None),
                         controller.launchd._isolated_env(layout, port=7894)))
        if forwarded[0] == "start" and "inert" not in forwarded:
            controller.product_launcher.preflight_preference_fallback(prewarm=False)
        return 0

    monkeypatch.setattr(controller.prior.base_controller, "main", fake_main)
    try:
        for argv in (
            ["prepare"],
            ["start", "--mode", "inert", "--seconds", "2"],
            ["status", "--runtime-root", str(tmp_path)],
            ["verify-ready", "--runtime-root", str(tmp_path)],
            ["stop", "--runtime-root", str(tmp_path)],
        ):
            assert controller.main(argv) == 0
            assert observed[-1][0] == argv
            assert "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM" not in observed[-1][1]
            assert "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM" not in observed[-1][2]
        assert controller.main(["start", "--prepared-runtime-root", str(tmp_path), "--python", "venv"]) == 0
        assert observed[-1][1]["URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"] == "control"
        assert observed[-1][2]["URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"] == "control"
        assert observed[-1][2]["URUHA_WEB_PREWARM_BRAIN"] == "1"
        assert observed[-1][2]["URUHA_WEB_ACTIVE_DB_RECEIPT_PATH"] == str(tmp_path / "active_db_receipt.json")
        assert preflight_calls[-1]["prewarm"] is True
        assert controller.main(["--direct-act-arm", "treatment", "start", "--mode", "product", "--python", "venv"]) == 0
        assert observed[-1][0] == ["start", "--mode", "product", "--python", "venv"]
        assert observed[-1][1]["URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"] == "treatment"
        assert observed[-1][2]["URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"] == "treatment"
        assert observed[-1][2]["URUHA_WEB_PREWARM_BRAIN"] == "1"
        assert observed[-1][2]["URUHA_WEB_ACTIVE_DB_RECEIPT_PATH"] == str(tmp_path / "active_db_receipt.json")
        assert preflight_calls[-1]["prewarm"] is True
        with pytest.raises(SystemExit):
            controller.main(["--direct-act-arm", "treatment", "prepare"])
    finally:
        monkeypatch.setattr(controller.prior.base_controller, "main", original_main)
