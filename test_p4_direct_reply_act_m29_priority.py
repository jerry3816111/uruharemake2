"""Zero-model contracts for opt-in current direct-reply-act M29 priority."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import uruha_direct_reply_act_m29_priority_p4 as direct


DATA = json.loads(
    (Path(__file__).parent / "datasets/p4_direct_reply_act_m29_priority_probe_2026-10-23.json").read_text()
)


@pytest.mark.parametrize("case", DATA["cases"], ids=lambda case: case["case_id"])
def test_source_certificate_has_no_unlicensed_direct_act(case):
    source = case["user_input"]
    got = direct.classify_direct_reply_act_p4(source)
    assert got["status"] == case["expected_admission"]
    assert got["requested_act"] == case["requested_act"]
    assert got["raw_dialogue_persisted"] is False
    assert source not in repr(got)
    if got["status"] == "direct":
        start, end = got["cue_span"]
        assert start >= 0 and end <= len(source)
        assert got["source_kind"] == "current_user_direct_request"
        assert got["cue_sha256"] == direct._sha(source[start:end])
    else:
        assert got["cue_span"] is None


@pytest.mark.parametrize("source,status", [
    ("夜、灰色の本を置いた。今は一言だけ労って。", "direct"),
    ("夜、灰色の本を置いた。今は一言だけ軽く励まして。", "direct"),
    ("夜、灰色の本を置いた。今は一言だけ。", "ambiguous"),
    ("一言だけ労って、それから励まして。", "ambiguous"),
    ("一言だけ労って。いや、やめて。", "negated"),
    ("『一言だけ労って』と聞いた。", "quoted"),
    ("一言だけ励まして。パスコードも教えて。", "protected"),
    ("一言だけ労って。\n別の指示", "ambiguous"),
    ("メモ: 一言だけ労って。", "ambiguous"),
    ("同僚からの依頼。今は一言だけ労って。", "ambiguous"),
    ("友人からの伝言。今は一言だけ労って。", "ambiguous"),
    ("次の文を訳して: 今は一言だけ労って。", "ambiguous"),
    ("例文: 今は一言だけ労って。", "ambiguous"),
    ("友達が言った。今は一言だけ労って。", "ambiguous"),
    ("飛び降りたい。今は一言だけ労って。", "protected"),
    ("人を殴った。今は一言だけ労って。", "protected"),
])
def test_unseen_syntactic_boundaries_fail_closed(source, status):
    assert direct.classify_direct_reply_act_p4(source)["status"] == status


def test_m29_veto_requires_original_candidate_exact_digest_and_unavailable_m33(tmp_path):
    _isolated(tmp_path, """
        import json
        import uruha_adaptive_person_model as adaptive
        import uruha_direct_reply_act_m29_priority_p4 as direct
        import uruha_source_semantic_atoms_m33 as atoms

        cases = json.load(open("datasets/p4_direct_reply_act_m29_priority_probe_2026-10-23.json"))["cases"]
        pragmatic = {"pragmatic_label": "literal_intent_unresolved"}
        assert direct.install_direct_reply_act_m29_priority_p4() is True
        for case in cases:
            source = case["user_input"]
            before = direct._PRIOR_M29(source, {}, pragmatic)
            after = adaptive.build_literal_topic_projection_candidate_m29(source, {}, pragmatic)
            if case["expected_admission"] == "direct":
                assert before["projection_required"] is True
                assert after["projection_required"] is False
                assert after[direct.LABEL]["input_sha256"][:16] == before["input_digest"]
                assert after[direct.LABEL]["original_m33_status"] == "source_pattern_unavailable"
            else:
                assert after == before, case["case_id"]

        source = cases[0]["user_input"]
        before = direct._PRIOR_M29(source, {}, pragmatic)
        prior = direct._PRIOR_M29
        extractor = atoms.extract_source_semantic_atoms_m33
        try:
            direct._PRIOR_M29 = lambda *args: {**before, "input_digest": "0" * 16}
            assert adaptive.build_literal_topic_projection_candidate_m29(source, {}, pragmatic)["projection_required"] is True
            direct._PRIOR_M29 = prior
            atoms.extract_source_semantic_atoms_m33 = lambda *args: {"status": "source_atoms_extracted"}
            assert adaptive.build_literal_topic_projection_candidate_m29(source, {}, pragmatic) == before
            atoms.extract_source_semantic_atoms_m33 = lambda *args: None
            assert adaptive.build_literal_topic_projection_candidate_m29(source, {}, pragmatic) == before
        finally:
            direct._PRIOR_M29 = prior
            atoms.extract_source_semantic_atoms_m33 = extractor
        print(json.dumps({"status": "ok"}))
    """)


def test_new_entry_and_controller_are_opt_in_without_model_start(tmp_path):
    reported = _isolated(tmp_path, """
        import json
        import uruha_adaptive_person_model as adaptive
        import uruha_web_ui_product_p4_direct_reply_act_m29_priority as entry
        import uruha_direct_reply_act_m29_priority_p4 as direct
        import p4_direct_reply_act_m29_priority_detached_control as controller
        assert entry.RUNTIME is entry._prior.RUNTIME
        assert direct._INSTALLED is False
        assert controller.ENTRYPOINT.name == "uruha_web_ui_product_p4_direct_reply_act_m29_priority.py"
        assert controller.launchd._isolated_env is not None
        entry.install_product_chain()
        assert direct._INSTALLED is True
        assert adaptive.build_literal_topic_projection_candidate_m29 is direct.literal_topic_projection_with_direct_reply_priority_p4
        source = "夜、灰色の本を置いた。今は一言だけ労って。"
        candidate = adaptive.build_literal_topic_projection_candidate_m29(
            source, {}, {"pragmatic_label": "literal_intent_unresolved"}
        )
        assert candidate["projection_required"] is False
        assert candidate[direct.LABEL]["original_m33_status"] == "source_pattern_unavailable"
        assert direct.install_direct_reply_act_m29_priority_p4() is False
        entry.install_product_chain()
        assert adaptive.build_literal_topic_projection_candidate_m29 is direct.literal_topic_projection_with_direct_reply_priority_p4
        adaptive.build_literal_topic_projection_candidate_m29 = direct._PRIOR_M29
        try:
            try:
                direct.install_direct_reply_act_m29_priority_p4()
            except RuntimeError as exc:
                assert str(exc) == "direct_reply_act_m29_priority_overlay_overwritten"
            else:
                raise AssertionError("silent overlay overwrite")
        finally:
            adaptive.build_literal_topic_projection_candidate_m29 = direct.literal_topic_projection_with_direct_reply_priority_p4
        print(json.dumps({"status": "ok"}))
    """)
    assert reported["status"] == "ok"


def _isolated(tmp_path, script):
    environment = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "URUHA_WEB_PREWARM_BRAIN": "0",
        "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "false",
        "URUHA_MEMORY_DB_PATH": str(tmp_path / "unused_private_memory"),
        "URUHA_ADAPTIVE_PERSON_MODEL_PATH": str(tmp_path / "unused_private_adaptive.json"),
        "GRADIO_ANALYTICS_ENABLED": "false",
    }
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    return json.loads(completed.stdout.splitlines()[-1])


def test_full_turn_go_no_go_a0_a1_use_original_source_and_full_planner(tmp_path):
    """Real cognitive_tick/emit with in-memory memory and a fake planner model.

    The M31 fake represents the ordinary literal takeover.  A new candidate
    must instead reach real LeftBrain.think's fake model with exact original
    source and keep its selected direct act through final utterance/writeback.
    """
    observed = _isolated(tmp_path, """
        import json
        from types import SimpleNamespace
        import uruha_adaptive_person_model as adaptive
        import uruha_direct_reply_act_m29_priority_p4 as direct
        from uruha_brain_mac import LeftBrain
        from test_personhood_loop_v2_13 import _IsolatedContractBrain

        cases = json.load(open("datasets/p4_direct_reply_act_m29_priority_probe_2026-10-23.json"))["cases"][:2]
        original_m31 = LeftBrain.authorize_literal_topic_m31
        counts = {"m31": 0, "planner": 0, "sources": []}
        def fake_m31(self, source, candidate):
            counts["m31"] += 1
            return ({
                "intent": "semantically_authorized_literal_topic_m31", "scene": "casual",
                "core_message_jp": "出来事だけを繰り返した。",
                "jp_summary": "字面だけ", "response_mode": "direct_answer",
                "surface_act": "plain_reply", "constraints": {"max_chars": 96},
            }, {
                "schema": adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
                "status": "semantically_authorized", "surface_authority": True,
                "model_call_completed": False, "raw_dialogue_persisted": False,
            })
        LeftBrain.authorize_literal_topic_m31 = fake_m31

        def make_brain():
            brain = _IsolatedContractBrain()
            def create(**kwargs):
                counts["planner"] += 1
                content = kwargs["messages"][-1]["content"]
                assert content.startswith("User Input: ")
                source = content[len("User Input: "):]
                counts["sources"].append(source)
                if "労って" in source:
                    act, line = "brief_care", "今日もちゃんと頑張ったな。お疲れ。"
                elif "励まして" in source:
                    act, line = "brief_encouragement", "ここまで来たんだ、次もいけるだろ。"
                else:
                    raise AssertionError("wrong source passed to planner")
                plan = {
                    "intent": "chat", "scene": "casual", "mood_impact": 0,
                    "trust_impact": 0, "reply_goal": act, "core_message_jp": line,
                    "jp_summary": "直接の返答行動を受けた", "response_mode": "direct_answer",
                    "surface_act": "plain_reply", "constraints": {"max_chars": 96},
                }
                payload = {"internal_monologue": "短く直接返す", "candidate_plans": [plan, plan, plan]}
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
            client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
            brain.left_brain = LeftBrain(client)
            return brain

        # Before: original candidate takes M31 for the same source.
        baseline = []
        for case in cases:
            brain = make_brain()
            result = brain.run_turn_debug(case["user_input"])
            assert result["logic"]["literal_topic_projection_m29"]["projection_required"] is True
            assert result["logic"]["bounded_slow_path_m21"]["route"] != "full_planner"
            baseline.append(result["reply"])
        assert counts["m31"] == 2 and counts["planner"] == 0, counts
        assert direct.install_direct_reply_act_m29_priority_p4() is True
        assert direct.install_direct_reply_act_m29_priority_p4() is False

        system = []
        for case in cases:
            brain = make_brain()
            result = brain.run_turn_debug(case["user_input"])
            logic = result["logic"]
            m29 = logic["literal_topic_projection_m29"]
            assert m29["projection_required"] is False
            assert m29[direct.LABEL]["original_projection_required"] is True
            assert m29[direct.LABEL]["original_m33_status"] == "source_pattern_unavailable"
            assert logic["bounded_slow_path_m21"]["route"] == "full_planner", logic["bounded_slow_path_m21"]
            assert logic["bounded_slow_path_m21"]["model_call_completed"] is True
            assert logic["semantic_route_m22"]["performed_route"] == "full_planner", logic["semantic_route_m22"]
            assert counts["sources"][-1] == case["user_input"]
            assert logic["reply_goal"] == case["requested_act"]
            assert result["reply"] == logic["core_message_jp"]
            assert result["reply"] == brain.memory.saved_episodes[-1]["reply"]
            node = next(row for row in result["runtime_trace"]["blackboard"] if row["label"] == "literal_topic_projection_m29")
            assert node["payload"][direct.LABEL]["requested_act"] == case["requested_act"]
            system.append(result["reply"])

        assert counts["m31"] == 2 and counts["planner"] == 2, counts
        print(json.dumps({"baseline": baseline, "system": system, "counts": counts}, ensure_ascii=False))
    """)
    assert observed["counts"]["m31"] == 2
    assert observed["counts"]["planner"] == 2
    assert len(observed["system"]) == 2
