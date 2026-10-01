from copy import deepcopy

import pytest

import uruha_contextual_expression_commit_p2 as expression
from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac


@pytest.fixture(autouse=True)
def isolated_expression_overlay():
    """Exercise the product overlay without leaking class patches to other suites."""
    methods = {
        "speak": RightBrain.speak,
        "variants": RightBrain._speech_plan_variants,
        "finalize": RightBrain._finalize_surface_reply,
        "refine": RightBrain._refine_conversational_reply,
        "emit": UruhaBrainV4_Mac.emit_response_if_ready,
        "run": UruhaBrainV4_Mac.run_turn_debug,
    }
    assert expression.install_contextual_expression_commit_p2()
    try:
        yield
    finally:
        RightBrain.speak = methods["speak"]
        RightBrain._speech_plan_variants = methods["variants"]
        RightBrain._finalize_surface_reply = methods["finalize"]
        RightBrain._refine_conversational_reply = methods["refine"]
        UruhaBrainV4_Mac.emit_response_if_ready = methods["emit"]
        UruhaBrainV4_Mac.run_turn_debug = methods["run"]
        expression._INSTALLED = False
        expression._ORIGINAL_FINALIZE = None
        expression._ORIGINAL_SPEECH_VARIANTS = None
        expression._ORIGINAL_REFINE = None


def compact_logic(core="うん、そのとおりだ。", **updates):
    logic = {
        "intent": "chat",
        "scene": "casual",
        # The preserved P2 runtime cases reach the compact planner through the
        # pragmatic-attunement surface; use that real route instead of letting
        # the unrelated dynamic-context fallback become the test subject.
        "surface_act": "pragmatic_attunement",
        "response_mode": "direct_answer",
        "core_message_jp": core,
        "constraints": {"max_chars": 64},
        "bounded_slow_path_m21": {
            "compact_general_plan_p2": {
                "schema": "uruha_compact_general_plan_p2",
                "completed": True,
                "candidate_count": 3,
            }
        },
    }
    logic.update(updates)
    return logic


def test_completed_compact_direct_chat_keeps_selected_core_without_fixed_decorators():
    rb = RightBrain(load_model=False)
    for user_input, core in (
        ("そう、それでいい。", "うん、そのとおりだ。"),
        ("うん、聞いてくれてありがとう。", "ありがとう。そのくらいでいいよ。"),
    ):
        logic = compact_logic(core)
        speech_plan = rb.build_human_speech_plan(logic, user_input, {}, {"mood": 0, "trust": 50})
        logic = rb._apply_human_speech_plan_to_logic(logic, speech_plan)
        audit = expression._new_trace(logic, "direct_chat_answer")
        token = expression._TRACE.set(audit)
        try:
            variants = rb._speech_plan_variants("", logic, user_input)
            reply = rb._finalize_surface_reply(variants[0], logic, user_input, 64)
        finally:
            expression._TRACE.reset(token)
        assert variants == [core]
        assert reply == core
        assert audit["selected_core_message_jp"] == core
        assert set(audit["suppressed_decorators"]) == {
            "fixed_direct_chat_suffix",
            "hash_selected_discourse_prefix",
        }
        assert audit["model_call_added"] is False
        assert audit["long_term_memory_write"] is False


def test_two_sentence_core_is_not_truncated_to_first_sentence_or_phrase_matched():
    rb = RightBrain(load_model=False)
    core = "そこは読み違えた。今はそのまま聞く。"
    logic = compact_logic(core)
    audit = expression._new_trace(logic, "direct_chat_answer")
    token = expression._TRACE.set(audit)
    try:
        reply = rb._finalize_surface_reply(core, logic, "違う、今は聞いて。", 64)
    finally:
        expression._TRACE.reset(token)
    assert reply == core


def test_density_only_repair_cannot_redecorate_the_same_selected_core():
    rb = RightBrain(load_model=False)
    core = "うん、そのとおりだ。"
    logic = compact_logic(core)
    assert rb._refine_conversational_reply(core, logic, "そう、それでいい。", {}) == core


def test_noncompact_and_protected_surfaces_are_byte_identical_to_legacy_path():
    assert expression._ORIGINAL_FINALIZE is not None
    rb = RightBrain(load_model=False)
    cases = [
        ("普通の話。", {**compact_logic("普通に返す。"), "bounded_slow_path_m21": {}}),
        ("名前覚えてる？", compact_logic("Jerryだろ。", intent="recall_name", memory_use_expected=True)),
        ("消えたい。", compact_logic("今は一人になるな。", intent="crisis_support", scene="support", surface_act="protective_brake")),
        ("どこの話？", compact_logic("どの部分か一個だけ言って。", response_mode="clarify_light")),
        ("その言い方はやめて。", compact_logic("その言い方はやめろ。", scene="boundary")),
    ]
    for user_input, logic in cases:
        current = rb._finalize_surface_reply(logic["core_message_jp"], deepcopy(logic), user_input, 64)
        legacy = expression._ORIGINAL_FINALIZE(rb, logic["core_message_jp"], deepcopy(logic), user_input, 64)
        assert current == legacy


def test_invalid_language_still_goes_through_existing_visible_language_firewall():
    rb = RightBrain(load_model=False)
    logic = compact_logic("English only")
    audit = expression._new_trace(logic, "direct_chat_answer")
    token = expression._TRACE.set(audit)
    try:
        reply = rb._finalize_surface_reply("English only", logic, "okay", 64)
    finally:
        expression._TRACE.reset(token)
    visible = rb.enforce_user_visible_japanese(reply, logic, user_input="okay", memory_data={})
    assert visible
    assert not any("a" <= char.lower() <= "z" for char in visible)
    assert logic["visible_language_guard"]["final_rejection_reasons"] == []


def test_graph_node_is_connected_idempotent_and_records_post_guard_surface():
    from uruha_memory_observatory import collect_cognitive_graph

    logic = compact_logic()
    logic["contextual_expression_commit_p2"] = {
        "schema": expression.SCHEMA,
        "pre_language_guard_surface": "うん、そのとおりだ。",
        "suppressed_decorators": ["fixed_direct_chat_suffix", "hash_selected_discourse_prefix"],
    }
    logic["visible_language_guard"] = {
        "final_reply": "うん、そのとおりだ。",
        "repair_action": "none",
    }
    result = {
        "reply": "うん、そのとおりだ。",
        "logic": logic,
        "runtime_trace": {
            "blackboard": [
                {"stage": "plan", "label": "compact_general_plan_p2", "payload": {}},
                {"stage": "speak", "label": "utterance", "payload": {}},
            ]
        },
    }
    expression.materialize_expression_commit_trace(result)
    expression.materialize_expression_commit_trace(result)
    graph = collect_cognitive_graph(result)
    nodes = [node for node in graph["nodes"] if node["label"] == "contextual_expression_commit_p2"]
    assert len(nodes) == 1
    assert any(edge["source"] == nodes[0]["id"] or edge["target"] == nodes[0]["id"] for edge in graph["edges"])
    audit = result["logic"]["contextual_expression_commit_p2"]
    assert audit["final_visible_surface_matched"] is True
    assert audit["visible_language_guard_applied"] is True
