"""Zero-model D authority contracts; all fixtures are disjoint from frozen D."""

from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import uruha_current_decision_ack_authority_p4 as gate


DATE = "2064年8月17日"
SUBJECT = "陶芸作品を受け渡す場所"
PLACE = "白い工房の南窓"
SOURCE = f"私は{DATE}に{SUBJECT}を{PLACE}に決めた。"
CORRECTION = f"訂正、私は{DATE}に{SUBJECT}を青い劇場の東口に決めた。"
OTHER = "私は2066年11月5日に絵本を受け取る場所を赤い図書室の入口に決めた。"


class FakeRight:
    def __init__(self):
        self.history = []
        self.reply_variant_counts = Counter()
        self.intent_variant_counts = Counter()
        self.normalized_reply_counts = Counter()
        self.intent_normalized_counts = Counter()

    def _structured_surface_required(self):
        return False

    def _user_visible_language_rejection_reasons(self, *_args, **_kwargs):
        return []

    def _remember_turn(self, summary, reply, intent):
        self.history.extend((
            {"role": "user", "content": summary, "intent": intent},
            {"role": "assistant", "content": reply, "intent": intent},
        ))
        self.reply_variant_counts[reply] += 1
        self.intent_variant_counts[(intent, reply)] += 1
        self.normalized_reply_counts[reply] += 1
        self.intent_normalized_counts[(intent, reply)] += 1


def _fixture(raw=SOURCE, *, scene="casual", route="high_road",
             semantic="general_conversation"):
    runtime = SimpleNamespace(cycle_index=1, blackboard=[
        {"label": "bounded_slow_path_planner_m21", "payload": {"model_calls": 1}},
        {"label": "selected_plan", "payload": {"core_message_jp": "私は決めたんだね。"}},
    ])
    brain = SimpleNamespace(
        runtime=runtime, right_brain=FakeRight(), memory=SimpleNamespace(),
        _plan_trace_summary=lambda logic: {
            "core_message_jp": logic.get("core_message_jp"),
            "planner_path": logic.get("planner_path"),
        },
    )
    with patch.object(gate, "_ORIGINAL_INGEST", lambda _brain, text, input_context=None: {
        "user_input": text, "memory_data": {}, "input_context": input_context or {},
    }):
        event = gate.ingest_event_with_current_decision_ack_p4(brain, raw)
    tick = {"logic": {
        "intent": "chat", "scene": scene, "surface_act": "plain_reply",
        "core_message_jp": "私は決めたんだね。",
        "semantic_route_m22": {"selected_type": semantic},
        "bounded_slow_path_m21": {"status": "completed", "model_calls": 1},
    }, "route_info": {"route": route}}
    with patch.object(gate, "_ORIGINAL_TICK", lambda _brain, _event: tick):
        selected = gate.cognitive_tick_with_current_decision_ack_p4(brain, event)
    return brain, event, selected


def _fake_guard(_right, reply, logic, user_input="", memory_data=None):
    logic["visible_language_guard"] = {
        "original_reply": reply,
        "final_reply": "ん、もう少し聞かせて。",
        "repair_action": "unverified_user_actor_fail_closed",
    }
    return "ん、もう少し聞かせて。"


def _deliver(brain, event, tick, *, overlay=None, corrupt_trace=False,
             corrupt_episode=False, corrupt_trace_cycle=False, drop_cert_at=None):
    writes = []

    def base_emit(_brain, source_event, selected_tick):
        logic = selected_tick["logic"]
        brain.right_brain._remember_turn("モデル下書き", "私は決めたんだね。", "chat")
        if drop_cert_at == "before_guard":
            logic.pop(gate.LABEL)
        visible = gate.visible_guard_with_current_decision_ack_p4(
            brain.right_brain, "私は決めたんだね。", logic,
            source_event["user_input"], source_event["memory_data"],
        )
        final = overlay(visible) if overlay else visible
        if drop_cert_at == "before_post_check":
            logic.pop(gate.LABEL)
        gate.post_check_with_current_decision_ack_p4(
            brain, logic, source_event["user_input"], final,
            source_event["memory_data"],
        )
        # This stands in for save_episode.  A prewrite failure must not reach it.
        writes.append(final)
        gate.remember_profile_facts_with_current_decision_ack_p4(
            brain.memory, source_event["user_input"],
        )
        if drop_cert_at == "after_write":
            logic.pop(gate.LABEL)
        recorded = "別の返事。" if corrupt_episode else final
        episode = (
            f"Time: now | User: {source_event['user_input']} | Summary: 報告 | "
            f"Uruha: {recorded} | Mood: calm"
        )
        graph_reply = "別の返事。" if corrupt_trace else final
        return {
            "reply": final, "logic": logic, "episode_doc": episode,
            "runtime_trace": {"cycle_index": (
                brain.runtime.cycle_index + 998 if corrupt_trace_cycle
                else brain.runtime.cycle_index
            ),
                              "blackboard": [{"stage": "surface", "label": "utterance",
                                              "payload": {"reply": graph_reply}}]},
        }

    with patch.object(gate, "_ORIGINAL_EMIT", base_emit), patch.object(
        gate, "_ORIGINAL_GUARD", _fake_guard,
    ), patch.object(gate, "_ORIGINAL_POST_CHECK", lambda _b, logic, *_a: {"checked": True}):
        return gate.emit_response_with_current_decision_ack_p4(brain, event, tick), writes


class CurrentDecisionAckAuthorityTests(TestCase):
    def test_two_source_disjoint_events_and_correction_are_reported_not_facts(self):
        for raw, expected_kind in (
            (SOURCE, "ordinary_decision_reported"),
            (OTHER, "ordinary_decision_reported"),
            (CORRECTION, "correction_reported"),
        ):
            with self.subTest(raw=raw):
                parsed = gate.classify_current_decision_ack_p4(raw)
                self.assertIsNotNone(parsed)
                self.assertEqual(parsed["kind"], expected_kind)
                self.assertEqual(parsed["source_raw_sha256"], gate._sha(raw))
                self.assertIn(parsed["place"], parsed["authorized_reply"])
                self.assertIn("そっちが", parsed["authorized_reply"])
                self.assertNotIn("うちが", parsed["authorized_reply"])
                self.assertLessEqual(len(parsed["authorized_reply"]), gate.MAX_REPLY_CHARS)
                self.assertTrue(parsed["authorized_reply"].endswith("。"))
                brain, event, tick = _fixture(raw)
                cert = tick["logic"][gate.LABEL]
                self.assertEqual(cert["kind"], expected_kind)
                self.assertEqual(cert["profile_write_authority"], "none")
                self.assertFalse(cert["world_state_truth_claimed"])
                self.assertEqual(cert["model_calls_added"], 0)
                self.assertEqual(cert["event_id"], event["_p4_current_decision_event"]["event_id"])
                if expected_kind == "correction_reported":
                    self.assertEqual(cert["correction_supersession"], "unresolved")
                    self.assertTrue(cert["authorized_reply"].startswith("訂正ね。"))
                else:
                    self.assertEqual(cert["correction_supersession"], "not_claimed")
                self.assertEqual(brain.runtime.blackboard[1]["label"], gate.LABEL)
                self.assertEqual(brain.runtime.blackboard[0]["payload"]["post_gate_plan_status"],
                                 "shadowed_not_selected")

    def test_unquoted_single_statement_only_and_negative_controls(self):
        negatives = (
            f"友人が『{SOURCE}』と言ってた。",
            f"『{SOURCE}』を柔らかく言い換えて。",
            f"「{SOURCE}」",
            f"うるはは{DATE}に{SUBJECT}を{PLACE}に決めた。",
            f"私は{DATE}にうるはの{SUBJECT}を{PLACE}に決めた。",
            f"私は{DATE}に{SUBJECT}を{PLACE}に決めたかもしれない。",
            f"私は{DATE}に{SUBJECT}を{PLACE}に決めてない。",
            f"私は{DATE}に{SUBJECT}を{PLACE}に決めた。友人も決めた。",
            f"私は{DATE}に{SUBJECT}を白い工房に決めたけど赤い図書室に決めた。",
            f"私は{DATE}に{SUBJECT}を東口\u202eの北側に決めた。",
            f"私は{DATE}に{SUBJECT}を東口\u200bの北側に決めた。",
            f"私は{DATE}に{SUBJECT}を{PLACE}に決めた？",
            f"私は{DATE}に{SUBJECT}を{PLACE}に決めよう。",
            f"私は{DATE}に{SUBJECT}を{PLACE}に決めたと言ってた。",
            f"私は2064年2月30日に{SUBJECT}を{PLACE}に決めた。",
            f"私は{DATE}に{SUBJECT}を暗証番号の隠し棚に決めた。",
            f"私は{DATE}に鍵を隠す場所を{PLACE}に決めた。",
            f"私は{DATE}に{SUBJECT}を{PLACE}に置いた。",
            f"私は{DATE}に絵本の受け取りを{PLACE}に決めた。",
            f"私は{DATE}に{SUBJECT}を{PLACE}に決めた。\n続き",
            f"{DATE}に{SUBJECT}を決めたのは、うるは自身だった？",
            "うるはだよ。",
        )
        for raw in negatives:
            with self.subTest(raw=raw):
                self.assertIsNone(gate.classify_current_decision_ack_p4(raw))
                brain, event, tick = _fixture(raw)
                self.assertNotIn(gate.LABEL, tick["logic"])
                self.assertEqual(tick["logic"]["core_message_jp"], "私は決めたんだね。")

    def test_protected_route_does_not_take_over(self):
        for scene, route, semantic in (
            ("crisis", "high_road", "general_conversation"),
            ("casual", "low_road", "general_conversation"),
            ("casual", "high_road", "safety_sensitive"),
        ):
            with self.subTest(scene=scene, route=route, semantic=semantic):
                brain, event, tick = _fixture(
                    SOURCE, scene=scene, route=route, semantic=semantic,
                )
                self.assertNotIn(gate.LABEL, tick["logic"])

    def test_event_identity_owner_cycle_and_raw_replay_fail_closed(self):
        brain, event, tick = _fixture()
        cert = tick["logic"][gate.LABEL]
        self.assertEqual(cert["cycle_index"], 1)
        self.assertEqual(cert["source_raw_sha256"], gate._sha(SOURCE))
        self.assertEqual(cert["binding_sha256"], gate._fresh_certificate(brain, event)["binding_sha256"])

        other = deepcopy(event)
        self.assertIsNone(gate._fresh_certificate(brain, other))
        brain.runtime.cycle_index = 2
        self.assertIsNone(gate._fresh_certificate(brain, event))
        brain.runtime.cycle_index = 1
        event["user_input"] = SOURCE.replace(PLACE, "紫の部屋")
        self.assertIsNone(gate._fresh_certificate(brain, event))

    def test_tampered_typed_span_plan_and_certificate_rejected(self):
        for alteration in ("subject", "place", "event_id", "owner", "plan", "binding"):
            with self.subTest(alteration=alteration):
                brain, event, tick = _fixture()
                cert = tick["logic"][gate.LABEL]
                if alteration in {"subject", "place"}:
                    cert[alteration] = "別の内容"
                elif alteration == "event_id":
                    cert["event_id"] = "0" * 32
                elif alteration == "owner":
                    cert["brain_owner_id"] = "0" * 32
                elif alteration == "plan":
                    tick["logic"]["core_message_jp"] = "うちが決めた。"
                else:
                    cert["binding_sha256"] = "0" * 64
                # Span fields are included in binding, but a forged in-memory
                # field without a recomputed binding must also be rejected.
                with self.assertRaises(gate.CurrentDecisionAckDeliveryError):
                    _deliver(brain, event, tick)
                self.assertEqual(brain.right_brain.history, [])

    def test_actual_guard_history_prewrite_graph_and_episode_are_equal(self):
        for raw in (SOURCE, CORRECTION, OTHER):
            with self.subTest(raw=raw):
                brain, event, tick = _fixture(raw)
                result, writes = _deliver(brain, event, tick)
                final = result["reply"]
                self.assertEqual(writes, [final])
                self.assertEqual(final, tick["logic"][gate.LABEL]["authorized_reply"])
                self.assertEqual(brain.right_brain.history[-2]["content"], raw)
                self.assertEqual(brain.right_brain.history[-1]["content"], final)
                self.assertNotIn("モデル下書き", [row["content"] for row in brain.right_brain.history])
                self.assertNotIn("私は決めたんだね。", brain.right_brain.reply_variant_counts)
                receipt = result["logic"][gate.LABEL]
                self.assertEqual(receipt["pre_episode_status"], "verified_before_episode_write")
                self.assertEqual(receipt["terminal_status"], "trace_and_episode_reported_match")
                self.assertEqual(receipt["factive_profile_write_status"],
                                 "suppressed_for_current_report")
                self.assertEqual(result["logic"]["visible_language_guard"]["final_reply"], final)
                self.assertEqual(result["runtime_trace"][gate.LABEL], receipt)
                self.assertEqual(next(row["payload"] for row in result["runtime_trace"]["blackboard"]
                                      if row["label"] == gate.LABEL), receipt)

    def test_post_guard_overlay_cannot_reach_episode_and_restores_history(self):
        brain, event, tick = _fixture()
        brain.right_brain._remember_turn("先の話", "先の返事", "chat")
        before = deepcopy(brain.right_brain.history)
        with self.assertRaises(gate.CurrentDecisionAckDeliveryError):
            _deliver(brain, event, tick, overlay=lambda _reply: "うちが決めたよ。")
        self.assertEqual(brain.right_brain.history, before)
        self.assertEqual(tick["logic"][gate.LABEL]["pre_episode_status"],
                         "blocked_before_episode_write")

    def test_selected_certificate_removal_cannot_bypass_prewrite_guard(self):
        for phase in ("before_guard", "before_post_check"):
            with self.subTest(phase=phase):
                brain, event, tick = _fixture()
                brain.right_brain._remember_turn("先の話", "先の返事", "chat")
                before = deepcopy(brain.right_brain.history)
                with self.assertRaisesRegex(
                    gate.CurrentDecisionAckDeliveryError,
                    "selected_certificate_missing_before_episode_write",
                ):
                    _deliver(brain, event, tick, drop_cert_at=phase)
                self.assertEqual(brain.right_brain.history, before)

    def test_selected_marker_rejects_preemit_cert_loss_and_replay(self):
        brain, event, tick = _fixture()
        tick["logic"].pop(gate.LABEL)
        with self.assertRaisesRegex(
            gate.CurrentDecisionAckDeliveryError,
            "selected_event_or_certificate_mismatch_before_emit",
        ):
            _deliver(brain, event, tick)
        brain, event, tick = _fixture()
        _deliver(brain, event, tick)
        with self.assertRaisesRegex(
            gate.CurrentDecisionAckDeliveryError,
            "selected_event_or_certificate_mismatch_before_emit",
        ):
            _deliver(brain, event, tick)
        with self.assertRaisesRegex(
            gate.CurrentDecisionAckDeliveryError,
            "selected_event_replayed_at_cognitive_tick",
        ):
            gate.cognitive_tick_with_current_decision_ack_p4(brain, event)

    def test_new_actor_question_turn_resets_prior_selected_marker(self):
        brain, event, tick = _fixture()
        _deliver(brain, event, tick)
        query = f"{DATE}に{SUBJECT}を決めたのは、うるは自身だった？"
        brain.runtime.cycle_index += 1
        with patch.object(gate, "_ORIGINAL_INGEST", lambda _brain, text, input_context=None: {
            "user_input": text, "memory_data": {}, "input_context": input_context or {},
        }):
            new_event = gate.ingest_event_with_current_decision_ack_p4(brain, query)
        self.assertIsNone(brain._p4_current_decision_selected)
        actor_tick = {"logic": {"intent": "chat", "core_message_jp": "actor answer"},
                      "route_info": {"route": "high_road"}}
        with patch.object(gate, "_ORIGINAL_TICK", lambda _brain, _event: actor_tick):
            result = gate.cognitive_tick_with_current_decision_ack_p4(brain, new_event)
        self.assertNotIn(gate.LABEL, result["logic"])
        with patch.object(gate, "_ORIGINAL_EMIT", lambda *_args: {"reply": "前にそっちが決めたって話してたよ。"}):
            self.assertEqual(
                gate.emit_response_with_current_decision_ack_p4(brain, new_event, result)["reply"],
                "前にそっちが決めたって話してたよ。",
            )

    def test_precheck_exception_restores_draft_history(self):
        brain, event, tick = _fixture()
        brain.right_brain._remember_turn("先の話", "先の返事", "chat")
        before = deepcopy(brain.right_brain.history)

        def failed_emit(_brain, _event, _tick):
            brain.right_brain._remember_turn("モデル下書き", "私は決めたんだね。", "chat")
            raise RuntimeError("surface failed before post-check")

        with patch.object(gate, "_ORIGINAL_EMIT", failed_emit):
            with self.assertRaisesRegex(RuntimeError, "surface failed before post-check"):
                gate.emit_response_with_current_decision_ack_p4(brain, event, tick)
        self.assertEqual(brain.right_brain.history, before)

    def test_profile_extractor_false_positive_is_suppressed_only_for_selected_report(self):
        from uruha_brain_mac import MemoryManager

        raw = f"私は{DATE}に{SUBJECT}を海が好きな人の集会所に決めた。"
        memory = MemoryManager.__new__(MemoryManager)
        self.assertTrue(memory._extract_profile_facts(raw))
        brain, event, tick = _fixture(raw)
        brain.memory = memory
        ordinary_calls = []
        with patch.object(gate, "_ORIGINAL_PROFILE_REMEMBER",
                          lambda _memory, text: ordinary_calls.append(text)):
            gate.remember_profile_facts_with_current_decision_ack_p4(memory, "別の通常発話")
            token = gate._ACTIVE_TURN.set({
                "brain": brain, "event": event, "logic": tick["logic"],
            })
            try:
                self.assertIsNone(gate.remember_profile_facts_with_current_decision_ack_p4(
                    memory, raw,
                ))
            finally:
                gate._ACTIVE_TURN.reset(token)
        self.assertEqual(ordinary_calls, ["別の通常発話"])
        self.assertEqual(tick["logic"][gate.LABEL]["factive_profile_write_status"],
                         "suppressed_for_current_report")

    def test_language_rejection_stops_before_episode(self):
        brain, event, tick = _fixture()
        brain.right_brain._user_visible_language_rejection_reasons = lambda *_a, **_kw: ["forced_reject"]
        with self.assertRaises(gate.CurrentDecisionAckDeliveryError):
            _deliver(brain, event, tick)
        self.assertEqual(brain.right_brain.history, [])

    def test_postwrite_trace_or_episode_mismatch_detected_but_not_rolled_back(self):
        for kwargs in ({"corrupt_trace": True}, {"corrupt_episode": True},
                       {"corrupt_trace_cycle": True},
                       {"drop_cert_at": "after_write"}):
            with self.subTest(kwargs=kwargs):
                brain, event, tick = _fixture()
                with self.assertRaises(gate.CurrentDecisionAckDeliveryError):
                    _deliver(brain, event, tick, **kwargs)
                # The test intentionally does not claim a DB rollback after
                # the episode writer; the product run must be marked FAIL.
                self.assertEqual(len(brain.right_brain.history), 2)

    def test_prior_actor_question_stays_on_frozen_c_path(self):
        query = f"{DATE}に{SUBJECT}を決めたのは、うるは自身だった？"
        brain, event, tick = _fixture(query)
        self.assertNotIn(gate.LABEL, tick["logic"])
        with patch.object(gate, "_ORIGINAL_EMIT", lambda *_a: {"reply": "前にそっちが決めたって話してたよ。"}):
            result = gate.emit_response_with_current_decision_ack_p4(brain, event, tick)
        self.assertEqual(result["reply"], "前にそっちが決めたって話してたよ。")


def test_no_model_real_turn_preserves_current_report_and_profile_boundary(tmp_path):
    # The installed wrappers must work across the actual runtime and episode
    # writer, not only across the fake emit used by the contracts above.
    from test_p4_current_statement_source_authority import _isolated

    _isolated(tmp_path, """
        import uruha_current_decision_ack_authority_p4 as gate
        from test_personhood_loop_v2_13 import _IsolatedContractBrain
        from uruha_brain_mac import MemoryManager, RightBrain

        assert gate.install_current_decision_ack_authority_p4() is True
        brain = _IsolatedContractBrain()
        brain.memory = MemoryManager()
        brain.right_brain = RightBrain(load_model=False)
        brain.right_brain.speak = lambda _source, logic, _mem, _psyche: logic['core_message_jp']
        raw = '私は2069年6月14日に陶芸作品を受け渡す場所を海が好きな人の集会所に決めた。'
        before = set(brain.memory.profile_col.get()['ids'])
        result = brain.run_turn_debug(raw)
        cert = result['logic'][gate.LABEL]
        assert result['reply'] == cert['authorized_reply']
        assert cert['pre_episode_status'] == 'verified_before_episode_write'
        assert cert['terminal_status'] == 'trace_and_episode_reported_match'
        assert cert['factive_profile_write_status'] == 'suppressed_for_current_report'
        assert result['runtime_trace'][gate.LABEL] == cert
        assert result['episode_doc'].find(' | User: ' + raw + ' | ') > 0
        assert ' | Uruha: ' + result['reply'] + ' | Mood: ' in result['episode_doc']
        assert set(brain.memory.profile_col.get()['ids']) == before
        assert len(brain.memory.episode_col.get()['ids']) == 1
        print('ok')
    """, timeout=180)
