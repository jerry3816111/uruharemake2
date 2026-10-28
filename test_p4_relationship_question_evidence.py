"""Developer-authored, no-model question-evidence contracts (no Safari score)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

import uruha_leftbrain_rules as rules
import uruha_relationship_question_evidence_p4 as question


@pytest.mark.parametrize(
    "text, authorized",
    [
        ("好き？", True),
        ("好き?", True),
        ("ねえ、好き？", True),
        ("ねえ、好き?", True),
        ("私は紅茶が好き。", False),
        ("紅茶、好き？", False),
        ("「好き？」は作文の例文。", False),
        ("私は紅茶が好き。好き？", False),
        ("私は柚子豆乳が好き。好き?", False),
        ("好き？今日は何する？", False),
        ("ねえ。好き？", False),
    ],
)
def test_pure_whole_turn_authorization_does_not_expand_clauses(text, authorized):
    assert question.bare_question_authorized_p4(text) is authorized


@pytest.mark.parametrize(
    "text",
    [
        "私は紅茶が好き。",
        "紅茶、好き？",
        "「好き？」は作文の例文。",
        "私は紅茶が好き。好き？",
        "私は柚子豆乳が好き。好き?",
    ],
)
def test_pure_before_after_preserves_the_reproduced_false_route(text):
    assert rules.contains_any(text, ["好き？"]) is True  # inherited compact matcher
    assert question._ORIGINAL_DETECTOR(text) == "ask_like_me"
    token = question._FULL_TURN.set(text)
    try:
        assert question.relationship_intent_with_question_evidence_p4(text) != "ask_like_me"
    finally:
        question._FULL_TURN.reset(token)
    assert question._FULL_TURN.get() is None


def test_pure_scoped_clause_must_use_full_turn_evidence():
    assert question.relationship_intent_with_question_evidence_p4("好き？") == "ask_like_me"
    token = question._FULL_TURN.set("私は柚子豆乳が好き。好き?")
    try:
        assert question.relationship_intent_with_question_evidence_p4("好き?") != "ask_like_me"
    finally:
        question._FULL_TURN.reset(token)
    assert question._FULL_TURN.get() is None


def _isolated(program):
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(program)],
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    return json.loads(completed.stdout.splitlines()[-1])


def test_install_precondition_is_fail_closed_without_m42():
    report = _isolated(
        """
        import json
        import uruha_leftbrain_rules as rules
        from uruha_relationship_question_evidence_p4 import install_relationship_question_evidence_p4
        old = rules._detect_relationship_intent
        try:
            install_relationship_question_evidence_p4()
        except RuntimeError as exc:
            blocked = "requires installed M42" in str(exc)
        else:
            blocked = False
        print(json.dumps({"blocked": blocked, "detector_unchanged": rules._detect_relationship_intent is old}))
        """
    )
    assert report == {"blocked": True, "detector_unchanged": True}


def test_installed_extracted_inline_and_m42_clones_share_question_evidence():
    report = _isolated(
        """
        import json
        import uruha_leftbrain_rules as rules
        import uruha_cjk_relationship_evidence_m42 as m42
        from uruha_brain_mac import LeftBrain
        import uruha_relationship_question_evidence_p4 as question

        assert m42.install_m42_relationship_evidence() is True
        assert question.install_relationship_question_evidence_p4() is True
        assert question.install_relationship_question_evidence_p4() is False
        preflight = question.question_evidence_preflight_p4()
        assert all(preflight.values())
        assert rules.contains_any("私は紅茶が好き。", ["好き？"]) is True

        positives = ["好き？", "好き?", "ねえ、好き？", "ねえ、好き?",
                     "うちのこと好き？", "你喜歡我嗎？", "Do you like me?"]
        negatives = ["私は紅茶が好き。", "紅茶、好き？", "「好き？」は作文の例文。",
                     "私は紅茶が好き。好き？", "私は柚子豆乳が好き。好き?",
                     "好き？今日は何する？"]
        psyche = {"mood": 0, "trust": 50}
        left = LeftBrain.__new__(LeftBrain)
        def intent(plan):
            return (plan or {}).get("intent")
        def routes(text):
            before, after, trace, _ = m42.evaluate_relationship_route_m42(text, level="rule")
            return {
                "extracted": intent(rules.get_rule_based_plan(text, [], psyche)),
                "inline": intent(left._rule_based_plan(text, psyche, {})),
                "m42_before": intent(before),
                "m42_after": intent(after),
                "m42_changed": trace["changed"],
            }
        ordinary = {text: routes(text) for text in positives + negatives}
        for text in positives:
            assert ordinary[text]["extracted"] == "ask_like_me", (text, ordinary[text])
            assert ordinary[text]["inline"] == "ask_like_me", (text, ordinary[text])
        for text in negatives:
            assert ordinary[text]["extracted"] != "ask_like_me", (text, ordinary[text])
            assert ordinary[text]["inline"] != "ask_like_me", (text, ordinary[text])
        for text in positives + negatives:
            assert ordinary[text]["m42_before"] == ordinary[text]["m42_after"], (text, ordinary[text])
            assert ordinary[text]["m42_changed"] is False, (text, ordinary[text])

        old = rules.get_rule_based_plan
        try:
            rules.get_rule_based_plan = lambda *_args, **_kwargs: None
            fallback = {text: intent(left._rule_based_plan(text, psyche, {})) for text in positives + negatives}
        finally:
            rules.get_rule_based_plan = old
        for text in positives:
            assert fallback[text] == "ask_like_me", (text, fallback[text])
        for text in negatives:
            assert fallback[text] != "ask_like_me", (text, fallback[text])
        assert question._FULL_TURN.get() is None

        adjacent = {}
        for text, expected in [("你有想我嗎？", "ask_miss_me"),
                               ("我是不是很煩？", "annoying_check"),
                               ("死にたい", "crisis_support")]:
            adjacent[text] = routes(text)
            assert adjacent[text]["extracted"] == adjacent[text]["inline"] == expected
        old_m42, guarded_m42, audit, _ = m42.evaluate_relationship_route_m42("工夫したね。", level="rule")
        assert intent(old_m42) == "marriage_boundary"
        assert intent(guarded_m42) != "marriage_boundary" and audit["changed"] is True
        print(json.dumps({"preflight": preflight, "positive_count": len(positives),
                          "negative_count": len(negatives), "inline_fallback": fallback,
                          "m42_safety_preserved": True}, ensure_ascii=False))
        """
    )
    assert all(report["preflight"].values())
    assert report["positive_count"] == 7
    assert report["negative_count"] == 6
    assert report["inline_fallback"]["私は柚子豆乳が好き。好き?"] != "ask_like_me"
    assert report["m42_safety_preserved"] is True


def test_full_product_entry_rule_signal_and_m42_trace_in_temp_sandbox(tmp_path):
    """Import the complete product chain, but do not invoke a model or a turn."""
    import p4_b_safe_isolated_product_launcher as launcher
    import p4_b_safe_isolated_product_launcher_v2 as sandbox

    runtime_root = tmp_path / "question-product-runtime"
    runtime_root.mkdir(mode=0o700)
    layout = launcher.build_runtime_layout(runtime_root)
    env = launcher.child_environment(os.environ, layout, port=7892, prewarm=False)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["URUHA_PRODUCT_WRITE_SANDBOX"] = "1"
    profile = sandbox.write_sandbox_profile(runtime_root)
    program = r"""
        import json
        import uruha_web_ui_product_p4_question_evidence as entry
        import uruha_relationship_question_evidence_p4 as question
        from uruha_brain_mac import LeftBrain
        from uruha_cjk_relationship_evidence_m42 import LABEL_M42, SCHEMA_M42

        assert entry.RUNTIME is entry._prior.RUNTIME
        assert all(question.question_evidence_preflight_p4().values())
        left = LeftBrain.__new__(LeftBrain)
        psyche = {"mood": 0, "trust": 50}
        cases = [
            ("好き？", True),
            ("ねえ、好き?", True),
            ("うちのこと好き？", True),
            ("私は紅茶が好き。", False),
            ("紅茶、好き？", False),
            ("「好き？」は作文の例文。", False),
            ("私は柚子豆乳が好き。好き?", False),
        ]
        checks = []
        for text, should_ask in cases:
            plan = left._rule_based_plan(text, psyche, {})
            signal = left.classify_user_signal(text, psyche, {})
            trace = signal.get(LABEL_M42)
            plan_intent = (plan or {}).get("intent")
            signal_intent = signal.get("actual_intent")
            assert (plan_intent == "ask_like_me") is should_ask, (text, plan_intent)
            assert (signal_intent == "ask_like_me") is should_ask, (text, signal_intent)
            assert isinstance(trace, dict) and trace.get("schema") == SCHEMA_M42, (text, trace)
            assert trace.get("changed") is False, (text, trace)
            assert trace.get("candidate_plan") == trace.get("authorized_plan"), (text, trace)
            checks.append({"plan": plan_intent, "signal": signal_intent,
                           "m42_changed": trace["changed"]})
        print(json.dumps({"ok": True, "cases": len(checks), "checks": checks,
                          "selected_plan_checked": False}))
    """
    completed = subprocess.run(
        sandbox.sandbox_command(profile, [sys.executable, "-c", textwrap.dedent(program)]),
        cwd=Path(__file__).resolve().parent,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    report = json.loads(completed.stdout.splitlines()[-1])
    assert report["ok"] is True and report["cases"] == 7
    assert report["selected_plan_checked"] is False
    assert all(row["m42_changed"] is False for row in report["checks"])
