"""Zero-model contracts for retrospective decision-owner answer authority.

These synthetic events are disjoint from the frozen C0--C9 Safari probe.  The
tests establish source and delivery boundaries, not model or Safari quality.
"""

from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import uruha_local_fact_answer_authority_p4 as gate
import uruha_memory_runtime as memory_runtime


DATE = "2057年3月22日"
SUBJECT = "絵本を渡す場所"
PLACE = "紫のアトリエの北窓"
SECOND_PLACE = "銀の温室の南口"
SOURCE = f"私は{DATE}に{SUBJECT}を{PLACE}に決めた。"
FULL_QUERY = f"{DATE}に{SUBJECT}を決めたのは、うるは自身だった？"
DATE_QUERY = f"{DATE}の場所を決めたのは、うるは自身だった？"

OTHER_DATE = "2061年9月4日"
OTHER_SUBJECT = "木箱を受け取る場所"
OTHER_PLACE = "青い工房の裏庭"
OTHER_SOURCE = f"私は{OTHER_DATE}に{OTHER_SUBJECT}を{OTHER_PLACE}に決めた。"
OTHER_FULL_QUERY = f"{OTHER_DATE}に{OTHER_SUBJECT}を決めたのは、うるは自身だった？"
OTHER_DATE_QUERY = f"{OTHER_DATE}の場所を決めたのは、うるは自身だった？"


def _turn(user, *, reply="ん、聞いたよ。", episode_id="recent-one"):
    return {"user": user, "reply": reply, "episode_id": episode_id}


def _recent_memory(*turns):
    rows = []
    for turn in turns:
        candidate = memory_runtime.recent_turn_candidates([turn])[0]
        rows.append({
            "source": "recent_turn", "channel": "recent_turns",
            "trace_id": memory_runtime.memory_trace_id(candidate),
            "text": f"User:{turn['user']} -> Uruha:{turn['reply']}",
        })
    return _passed(*rows, recent_turns=turns)


def _episode(user, *, memory_id="3d51e1d1-4f08-4b89-9cc8-3485e424e5d1",
             summary="短い要約", assistant="ん、聞いたよ。", channel="direct_episode",
             kind="turn_episode", typed=True):
    row = {
        "source": "episode", "collection_name": "episode", "channel": channel,
        "memory_id": memory_id, "trace_id": f"stored:episode:{memory_id}",
        "text": (
            "Time: 2026-10-21 09:00 | Intent: chat | Scene: casual | "
            f"User: {user} | Summary: {summary} | Uruha: {assistant} | Mood: calm"
        ),
    }
    if typed:
        row.update(episode_record_kind=kind, episode_record_kind_origin="stored_metadata")
    return row


def _passed(*rows, recent_turns=()):
    return {
        "recent_turns": list(recent_turns),
        "memory_provenance": {
            "passed_to_leftbrain": list(rows),
            "passed_to_leftbrain_trace_ids": [row["trace_id"] for row in rows],
        },
    }


def _two_sources():
    memory = _recent_memory(
        _turn(SOURCE, episode_id="first"),
        _turn(SOURCE.replace(PLACE, SECOND_PLACE), episode_id="second"),
    )
    return memory


class RetrospectiveDecisionActorAuthorityTests(TestCase):
    def assert_reported_user_ownership(self, cert):
        self.assertEqual(cert["status"], "source_backed_user_actor")
        reply = cert["authorized_reply"]
        self.assertRegex(reply, r"そっち|あなた")
        self.assertRegex(reply, r"言って|話して|伝えて|教えて")
        self.assertIn("決め", reply)
        self.assertNotRegex(reply, r"うるは(?:自身)?が決めた(?:んだ)?[。！!]?$")
        self.assertNotRegex(reply, r"うるは(?:自身)?は決めてない|うるは(?:自身)?は決めなかった")
        self.assertLessEqual(len(reply), gate.MAX_AUTHORIZED_CORE_CHARS)
        self.assertEqual(cert["authorized_reply_sha256"], gate._sha(reply))
        self.assertEqual(cert["model_calls_added"], 0)

    def test_full_and_date_only_queries_classify_two_unrelated_events(self):
        for query, date, mode in (
            (FULL_QUERY, DATE, "full"), (DATE_QUERY, DATE, "date_only"),
            (OTHER_FULL_QUERY, OTHER_DATE, "full"),
            (OTHER_DATE_QUERY, OTHER_DATE, "date_only"),
        ):
            with self.subTest(query=query):
                classified = gate.classify_local_fact_query_p4(query)
                self.assertTrue(classified["eligible"])
                self.assertEqual(classified["slot"], "prior_user_decision_actor")
                self.assertEqual(classified["date_anchor"], date)
                self.assertEqual(classified["subject_mode"], mode)

        for query in (
            f"「{FULL_QUERY}」", f"{FULL_QUERY}「",
            f"友人が『{FULL_QUERY}』と聞いた。", f"{DATE}に{SUBJECT}を決めたのは誰？",
        ):
            with self.subTest(malformed=query):
                self.assertFalse(gate.classify_local_fact_query_p4(query)["eligible"])

    def test_full_and_unique_date_only_use_direct_user_report_not_private_world_fact(self):
        for source, full_query, date_query in (
            (SOURCE, FULL_QUERY, DATE_QUERY),
            (OTHER_SOURCE, OTHER_FULL_QUERY, OTHER_DATE_QUERY),
        ):
            memory = _recent_memory(_turn(source))
            for query in (full_query, date_query):
                with self.subTest(query=query):
                    cert = gate.build_local_fact_certificate_p4(query, memory)
                    self.assert_reported_user_ownership(cert)
                    self.assertEqual(cert["admitted_source_count"], 1)
                    self.assertEqual(len(cert["admitted_subjects"]), 1)
                    self.assertEqual(cert["source_channel"], "recent_turns")
                    self.assertEqual(cert["source_user_sha256"], gate._sha(source))
                    self.assertEqual(len(cert["admitted_source_trace_ids"]), 1)
                    self.assertEqual(cert["admitted_source_user_sha256s"], [gate._sha(source)])
                    self.assertTrue(cert["binding_sha256"])

    def test_typed_episode_is_independent_and_same_raw_turn_is_deduplicated(self):
        episode = _episode(SOURCE)
        cert = gate.build_local_fact_certificate_p4(FULL_QUERY, _passed(episode))
        self.assert_reported_user_ownership(cert)
        self.assertEqual(cert["source_channel"], "direct_episode")
        self.assertEqual(cert["source_trace_id"], episode["trace_id"])
        self.assertEqual(cert["source_memory_id"], episode["memory_id"])

        turn = _turn(SOURCE)
        memory = _recent_memory(turn)
        memory["memory_provenance"]["passed_to_leftbrain"].append(episode)
        memory["memory_provenance"]["passed_to_leftbrain_trace_ids"].append(episode["trace_id"])
        deduped = gate.build_local_fact_certificate_p4(DATE_QUERY, memory)
        self.assert_reported_user_ownership(deduped)
        self.assertEqual(deduped["admitted_source_count"], 1)
        self.assertEqual(deduped["distinct_value_count"], 1)
        self.assertEqual(deduped["admitted_source_user_sha256s"], [gate._sha(SOURCE)])

    def test_two_agreeing_raw_user_statements_remain_source_backed(self):
        equivalent = SOURCE.rstrip("。")
        memory = _recent_memory(_turn(SOURCE, episode_id="first"),
                                _turn(equivalent, episode_id="second"))
        cert = gate.build_local_fact_certificate_p4(DATE_QUERY, memory)
        self.assert_reported_user_ownership(cert)
        self.assertEqual(cert["admitted_source_count"], 2)
        self.assertEqual(cert["distinct_value_count"], 1)
        self.assertEqual(len(cert["admitted_subjects"]), 1)
        self.assertEqual(len(cert["admitted_source_trace_ids"]), 2)

    def test_full_subject_does_not_borrow_another_event_and_date_only_is_ambiguous(self):
        same_date_other_subject = "陶器の札を返す場所"
        same_date_source = f"私は{DATE}に{same_date_other_subject}を白い廊下の角に決めた。"
        memory = _recent_memory(_turn(SOURCE, episode_id="a"),
                                _turn(same_date_source, episode_id="b"))
        full = gate.build_local_fact_certificate_p4(FULL_QUERY, memory)
        self.assert_reported_user_ownership(full)
        self.assertEqual(full["admitted_source_count"], 1)
        self.assertEqual(len(full["admitted_subjects"]), 1)

        ambiguous = gate.build_local_fact_certificate_p4(DATE_QUERY, memory)
        self.assertEqual(ambiguous["status"], "ambiguous_user_event")
        self.assertEqual(len(ambiguous["admitted_subjects"]), 2)
        self.assertIsNone(ambiguous.get("admitted_value"))
        self.assertIsNone(ambiguous.get("source_trace_id"))
        self.assertNotIn(PLACE, ambiguous["authorized_reply"])
        self.assertNotIn("白い廊下の角", ambiguous["authorized_reply"])

        # Subject ambiguity takes precedence even when one of those subjects
        # also has two incompatible place values.
        mixed = _recent_memory(
            _turn(SOURCE, episode_id="a"),
            _turn(SOURCE.replace(PLACE, SECOND_PLACE), episode_id="c"),
            _turn(same_date_source, episode_id="b"),
        )
        mixed_cert = gate.build_local_fact_certificate_p4(DATE_QUERY, mixed)
        self.assertEqual(mixed_cert["status"], "ambiguous_user_event")
        self.assertEqual(len(mixed_cert["admitted_subjects"]), 2)

        other_event_only = gate.build_local_fact_certificate_p4(
            FULL_QUERY, _recent_memory(_turn(same_date_source))
        )
        self.assertEqual(other_event_only["status"], "no_admitted_user_actor_source")
        wrong_date = gate.build_local_fact_certificate_p4(
            OTHER_FULL_QUERY, _recent_memory(_turn(SOURCE))
        )
        self.assertEqual(wrong_date["status"], "no_admitted_user_actor_source")

    def test_assistant_summary_untyped_stale_and_unhanded_are_not_user_proof(self):
        other_user = "今日は机を片づけた。"
        stale = _recent_memory(_turn(SOURCE))
        stale["memory_provenance"]["passed_to_leftbrain"][0]["trace_id"] = "derived:recent_turn:stale"
        stale["memory_provenance"]["passed_to_leftbrain_trace_ids"] = ["derived:recent_turn:stale"]
        unhanded = _recent_memory(_turn(SOURCE))
        unhanded["memory_provenance"]["passed_to_leftbrain"] = []
        unhanded["memory_provenance"]["passed_to_leftbrain_trace_ids"] = []
        cases = (
            _passed(), unhanded, stale,
            _recent_memory(_turn(other_user, reply=SOURCE)),
            _passed(_episode(other_user, summary=SOURCE, assistant=SOURCE)),
            _passed({"source": "short_term", "channel": "short_term_summary",
                     "trace_id": "derived:short_term:summary", "text": f"User:{SOURCE} -> Uruha:ん。"}),
            _passed(_episode(SOURCE, typed=False)),
            _passed(_episode(SOURCE, kind="episodic_consolidation")),
            _passed(_episode(SOURCE, channel="selected_working_memory")),
        )
        for memory in cases:
            with self.subTest(memory=memory):
                cert = gate.build_local_fact_certificate_p4(FULL_QUERY, memory)
                self.assertEqual(cert["status"], "no_admitted_user_actor_source")
                self.assertIsNone(cert.get("source_trace_id"))
                self.assertNotIn(PLACE, cert["authorized_reply"])

    def test_conflicting_handed_episode_identity_fails_closed(self):
        first = _episode(SOURCE)
        second = _episode(SOURCE.replace(PLACE, SECOND_PLACE))
        self.assertEqual(first["memory_id"], second["memory_id"])
        self.assertNotEqual(first["text"], second["text"])
        cert = gate.build_local_fact_certificate_p4(FULL_QUERY, _passed(first, second))
        self.assertEqual(cert["status"], "source_identity_conflict")
        self.assertEqual(cert["duplicate_episode_conflict_count"], 1)
        self.assertEqual(cert["duplicate_episode_trace_ids"], [first["trace_id"]])
        self.assertIsNone(cert["source_trace_id"])
        self.assertNotIn(PLACE, cert["authorized_reply"])
        changed = _episode(SOURCE.replace(PLACE, "赤い庭の門"))
        altered = gate.build_local_fact_certificate_p4(FULL_QUERY, _passed(first, changed))
        self.assertEqual(altered["status"], "source_identity_conflict")
        self.assertNotEqual(altered["binding_sha256"], cert["binding_sha256"])

    def test_quoted_friend_anonymous_quote_and_uruha_speech_are_not_user_ownership(self):
        quoted = SOURCE.rstrip("。")
        for user in (
            f"友人が「{quoted}」と言ってた。",
            f"「{quoted}」",
            f"『{quoted}』というメモを見た。",
            f"うるはが{DATE}に{SUBJECT}を{PLACE}に決めた。",
        ):
            with self.subTest(user=user):
                cert = gate.build_local_fact_certificate_p4(FULL_QUERY, _recent_memory(_turn(user)))
                self.assertEqual(cert["status"], "no_admitted_user_actor_source")
                self.assertNotIn(PLACE, cert["authorized_reply"])

    def test_conflicting_user_values_keep_owner_bounded_without_choosing_place(self):
        memory = _two_sources()
        for query in (FULL_QUERY, DATE_QUERY):
            with self.subTest(query=query):
                cert = gate.build_local_fact_certificate_p4(query, memory)
                self.assertEqual(cert["status"], "conflicting_user_values")
                self.assertEqual(cert["admitted_source_count"], 2)
                self.assertEqual(cert["distinct_value_count"], 2)
                self.assertEqual(len(cert["admitted_subjects"]), 1)
                self.assertIsNone(cert.get("admitted_value"))
                self.assertIsNone(cert.get("source_trace_id"))
                self.assertEqual(set(cert["admitted_source_user_sha256s"]), {
                    gate._sha(SOURCE), gate._sha(SOURCE.replace(PLACE, SECOND_PLACE)),
                })
                self.assertNotRegex(cert["authorized_reply"], r"うるは(?:自身)?が決めた")
                self.assertLessEqual(len(cert["authorized_reply"]), gate.MAX_AUTHORIZED_CORE_CHARS)

    def test_explicit_correction_is_not_unqualified_new_current_place(self):
        correction = f"訂正、私は{DATE}に{SUBJECT}を銀の温室の南口に決めた。"
        memory = _recent_memory(_turn(SOURCE, episode_id="before"),
                                _turn(correction, episode_id="correction"))
        for query in (FULL_QUERY, DATE_QUERY):
            with self.subTest(query=query):
                cert = gate.build_local_fact_certificate_p4(query, memory)
                self.assertEqual(cert["status"], "unresolved_user_correction")
                self.assertIsNone(cert.get("admitted_value"))
                self.assertIsNone(cert.get("source_trace_id"))
                self.assertNotIn(PLACE, cert["authorized_reply"])
                self.assertNotIn(SECOND_PLACE, cert["authorized_reply"])
                self.assertNotRegex(cert["authorized_reply"], r"うるは(?:自身)?が決めた")
                self.assertEqual(cert["correction_source_count"], 1)
                self.assertEqual(cert["correction_source_user_sha256s"], [gate._sha(correction)])
                self.assertEqual(len(cert["correction_source_trace_ids"]), 1)

    def test_correction_receipt_rejects_raw_or_trace_swap_after_plan(self):
        correction = f"訂正、私は{DATE}に{SUBJECT}を{SECOND_PLACE}に決めた。"
        original = _recent_memory(_turn(SOURCE, episode_id="before"),
                                  _turn(correction, episode_id="correction"))
        cert = gate.build_local_fact_certificate_p4(FULL_QUERY, original)
        self.assertEqual(cert["status"], "unresolved_user_correction")
        self.assertEqual(cert["correction_source_count"], 1)
        right = SimpleNamespace(
            _structured_surface_required=lambda: False,
            _user_visible_language_rejection_reasons=lambda *_a, **_kw: [],
        )
        for changed in (
            _recent_memory(
                _turn(SOURCE, episode_id="before"),
                _turn(correction.replace(SECOND_PLACE, "新しい中庭"), episode_id="correction"),
            ),
            _recent_memory(
                _turn(SOURCE, episode_id="before"),
                _turn(correction, reply="了解、訂正を聞いた。", episode_id="correction"),
            ),
        ):
            with self.subTest(changed=changed):
                fresh = gate.build_local_fact_certificate_p4(FULL_QUERY, changed)
                self.assertEqual(fresh["status"], "unresolved_user_correction")
                self.assertNotEqual(fresh["binding_sha256"], cert["binding_sha256"])
                logic = {
                    "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
                    "core_message_jp": cert["authorized_reply"],
                    "planner_path": gate.PLANNER_PATH,
                    gate.LABEL: {**cert, "selected_status": "source_authorized_plan_selected"},
                }
                with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "元の返事。"):
                    visible = gate.visible_guard_with_local_fact_answer_authority_p4(
                        right, "元の返事。", logic, FULL_QUERY, changed,
                    )
                self.assertEqual(logic[gate.LABEL]["visible_surface_status"], "failed_closed")
                self.assertEqual(logic[gate.LABEL]["visible_failure_reason"],
                                 "source_or_plan_integrity_mismatch")
                self.assertNotIn(SECOND_PLACE, visible)

    def test_source_overflow_fails_closed_instead_of_truncating_evidence(self):
        turns = [
            _turn(f"私は{DATE}に{SUBJECT}を第{index}工房の入口に決めた。",
                  episode_id=f"overflow-{index}")
            for index in range(9)
        ]
        cert = gate.build_local_fact_certificate_p4(DATE_QUERY, _recent_memory(*turns))
        self.assertEqual(cert["status"], "actor_source_overflow")
        self.assertIsNone(cert.get("source_trace_id"))
        self.assertIsNone(cert.get("admitted_value"))
        self.assertLessEqual(len(cert["authorized_reply"]), gate.MAX_AUTHORIZED_CORE_CHARS)

    def test_sensitive_subject_and_value_never_become_actor_certificate(self):
        sensitive_subject = "暗証番号を書いた紙を隠す場所"
        sensitive_query = f"{DATE}に{sensitive_subject}を決めたのは、うるは自身だった？"
        sensitive_source = f"私は{DATE}に{sensitive_subject}を古い棚の裏に決めた。"
        classified = gate.classify_local_fact_query_p4(sensitive_query)
        self.assertFalse(classified["eligible"])
        self.assertFalse(gate.build_local_fact_certificate_p4(
            sensitive_query, _recent_memory(_turn(sensitive_source))
        )["eligible"])

        for unsafe_place in ("認証コード保管箱の裏", "スペアキーの隠し棚"):
            with self.subTest(unsafe_place=unsafe_place):
                source = SOURCE.replace(PLACE, unsafe_place)
                cert = gate.build_local_fact_certificate_p4(
                    FULL_QUERY, _recent_memory(_turn(source))
                )
                self.assertEqual(cert["status"], "unadmitted_user_actor_source")
                self.assertNotIn(unsafe_place, cert["authorized_reply"])

        safe = _turn(SOURCE, episode_id="safe")
        sensitive_subject_turn = _turn(sensitive_source, episode_id="sensitive-subject")
        sensitive_value_turn = _turn(
            f"私は{DATE}に陶器の札を返す場所を認証コード保管箱の裏に決めた。",
            episode_id="sensitive-value",
        )
        for hidden in (sensitive_subject_turn, sensitive_value_turn):
            with self.subTest(hidden=hidden):
                date_only = gate.build_local_fact_certificate_p4(
                    DATE_QUERY, _recent_memory(safe, hidden)
                )
                self.assertEqual(date_only["status"], "unadmitted_user_actor_source")
                self.assertEqual(date_only["admitted_source_count"], 1)
                self.assertEqual(date_only["unadmitted_source_count"], 1)
                self.assertEqual(len(date_only["unadmitted_source_trace_ids"]), 1)
                self.assertNotIn("暗証番号", date_only["authorized_reply"])
                self.assertNotIn("認証コード", date_only["authorized_reply"])
                full = gate.build_local_fact_certificate_p4(
                    FULL_QUERY, _recent_memory(safe, hidden)
                )
                self.assert_reported_user_ownership(full)
                self.assertEqual(full["unadmitted_source_count"], 0)

    def test_selected_plan_visible_guard_graph_and_overlay_share_one_receipt(self):
        memory = _recent_memory(_turn(SOURCE))
        tick = {
            "logic": {
                "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
                "core_message_jp": "うるはが決めたんだ。",
                "semantic_route_m22": {"selected_type": "general_conversation"},
            },
            "route_info": {"route": "high_road", "performed_route": "full_planner"},
        }
        brain = SimpleNamespace(
            right_brain=SimpleNamespace(_structured_surface_required=lambda: False)
        )
        with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
            selected = gate.cognitive_tick_with_local_fact_answer_authority_p4(
                brain, {"user_input": FULL_QUERY, "memory_data": memory}
            )
        logic = selected["logic"]
        cert = logic[gate.LABEL]
        self.assertEqual(cert["selected_status"], "source_authorized_plan_selected")
        self.assertEqual(cert["slot"], "prior_user_decision_actor")
        self.assertEqual(logic["core_message_jp"], cert["authorized_reply"])
        self.assertNotEqual(logic["core_message_jp"], "うるはが決めたんだ。")
        self.assertEqual(cert["authorized_reply_sha256"], gate._sha(logic["core_message_jp"]))
        self.assertTrue(cert["binding_sha256"])

        right = SimpleNamespace(
            _structured_surface_required=lambda: False,
            _user_visible_language_rejection_reasons=lambda *_a, **_kw: [],
        )
        with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "うちは決めたよ。"):
            visible = gate.visible_guard_with_local_fact_answer_authority_p4(
                right, "うちは決めたよ。", logic, FULL_QUERY, memory
            )
        self.assertEqual(visible, cert["authorized_reply"])
        self.assertEqual(logic["visible_language_guard"]["final_reply_sha256"], gate._sha(visible))
        self.assertEqual(logic[gate.LABEL]["visible_surface_status"], "matched")

        result = {"reply": visible, "logic": logic,
                  "runtime_trace": {"blackboard": [{"label": "selected_plan", "payload": {}}]}}
        gate.materialize_local_fact_answer_authority_p4(result)
        receipt = result["logic"][gate.LABEL]
        graph_node = next(row for row in result["runtime_trace"]["blackboard"]
                          if row["label"] == gate.LABEL)
        self.assertTrue(receipt["final_visible_surface_matches_contract"])
        self.assertEqual(receipt["final_visible_surface_sha256"], gate._sha(visible))
        self.assertEqual(result["runtime_trace"][gate.LABEL], receipt)
        self.assertEqual(graph_node["payload"], receipt)

        changed = _recent_memory(_turn(SOURCE.replace(PLACE, SECOND_PLACE)))
        stale_logic = deepcopy(logic)
        with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "うちは決めたよ。"):
            withheld = gate.visible_guard_with_local_fact_answer_authority_p4(
                right, "うちは決めたよ。", stale_logic, FULL_QUERY, changed
            )
        self.assertEqual(stale_logic[gate.LABEL]["visible_surface_status"], "failed_closed")
        self.assertNotIn(PLACE, withheld)

        result["reply"] = "うちは決めたよ。"
        gate.materialize_local_fact_answer_authority_p4(result)
        mismatch = result["logic"][gate.LABEL]
        self.assertEqual(mismatch["visible_surface_status"], "post_guard_surface_mismatch")
        self.assertFalse(mismatch["final_visible_surface_matches_contract"])
        self.assertEqual(result["runtime_trace"][gate.LABEL], mismatch)

    def test_authorized_actor_reply_satisfies_existing_monitor_and_memory_post_check(self):
        from uruha_brain_mac import UruhaBrainV4_Mac

        for memory, expected_status in (
            (_recent_memory(_turn(SOURCE)), "source_backed_user_actor"),
            (_two_sources(), "conflicting_user_values"),
        ):
            with self.subTest(expected_status=expected_status):
                cert = gate.build_local_fact_certificate_p4(FULL_QUERY, memory)
                self.assertEqual(cert["status"], expected_status)
                tick = {
                    "logic": {
                        "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
                        "core_message_jp": "うるはが決めたんだ。",
                    },
                    "route_info": {"route": "high_road", "performed_route": "full_planner"},
                }
                brain = SimpleNamespace(
                    right_brain=SimpleNamespace(_structured_surface_required=lambda: False)
                )
                with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
                    selected = gate.cognitive_tick_with_local_fact_answer_authority_p4(
                        brain, {"user_input": FULL_QUERY, "memory_data": memory}
                    )
                logic = selected["logic"]
                logic["human_speech_plan"] = {
                    "dialogue_act": "direct_chat_answer",
                    "content_units": ["使用者の発話範囲で答える"],
                    "content_density_target": "low",
                    "turn_opening_potential": False,
                }
                reply = cert["authorized_reply"]

                class MonitorHarness:
                    memory = SimpleNamespace(session_turns=[])
                    runtime = SimpleNamespace(last_self_monitor=None)
                    right_brain = None

                    def _focus_terms(self, *_args):
                        return []

                    def _jp_memory_value(self, *_args):
                        return None

                    def _reply_uses_memory_anchor(self, text, anchor):
                        return UruhaBrainV4_Mac._reply_uses_memory_anchor(self, text, anchor)

                harness = MonitorHarness()
                monitored = UruhaBrainV4_Mac._self_monitor_reply(
                    harness, FULL_QUERY, reply, logic, memory
                )
                checked = UruhaBrainV4_Mac._attach_reply_post_check(
                    harness, logic, FULL_QUERY, reply, memory
                )
                self.assertNotIn("missed_memory_anchor", monitored["issues"])
                self.assertFalse(monitored["needs_repair"])
                self.assertTrue(checked["memory_use_expected"])
                self.assertTrue(checked["did_reply_use_memory_explicitly"])
                self.assertEqual(logic["memory_anchor"]["source_subjects"],
                                 cert["admitted_subjects"])

    def test_zero_model_final_graph_and_episode_serializer_keep_same_reply(self):
        from uruha_brain_mac import MemoryManager

        memory = _recent_memory(_turn(SOURCE))
        cert = gate.build_local_fact_certificate_p4(FULL_QUERY, memory)
        logic = {
            "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
            "jp_summary": cert["authorized_reply"],
            "core_message_jp": cert["authorized_reply"],
            "planner_path": gate.PLANNER_PATH,
            gate.LABEL: {**cert, "selected_status": "source_authorized_plan_selected"},
        }
        right = SimpleNamespace(
            _structured_surface_required=lambda: False,
            _user_visible_language_rejection_reasons=lambda *_a, **_kw: [],
        )
        with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "うるはが決めた。"):
            visible = gate.visible_guard_with_local_fact_answer_authority_p4(
                right, "うるはが決めた。", logic, FULL_QUERY, memory
            )
        recorded = {}
        writer = SimpleNamespace(
            episode_col=SimpleNamespace(add=lambda **kwargs: recorded.update(kwargs)),
            session_turns=[],
            _append_short_term_buffer=lambda *_args: None,
            _remember_profile_facts=lambda *_args: None,
        )
        episode_doc = MemoryManager.save_episode(writer, FULL_QUERY, visible, {}, logic)
        result = {
            "reply": visible, "logic": logic,
            "runtime_trace": {"blackboard": [
                {"stage": "surface", "label": "utterance", "payload": {"reply": visible}},
            ]},
        }
        gate.materialize_local_fact_answer_authority_p4(result)
        utterance = next(row["payload"]["reply"] for row in result["runtime_trace"]["blackboard"]
                         if row["label"] == "utterance")
        self.assertEqual(visible, utterance)
        self.assertEqual(writer.session_turns[-1]["reply"], visible)
        self.assertEqual(recorded["documents"], [episode_doc])
        self.assertIn(f"| Uruha: {visible} | Mood:", episode_doc)
        self.assertEqual(logic[gate.LABEL]["final_visible_surface_sha256"], gate._sha(visible))

    def test_history_keeps_raw_user_question_and_only_final_assistant_answer(self):
        memory = _recent_memory(_turn(SOURCE))
        cert = gate.build_local_fact_certificate_p4(FULL_QUERY, memory)
        logic = {
            "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
            "jp_summary": cert["authorized_reply"],
            "core_message_jp": cert["authorized_reply"],
            "planner_path": gate.PLANNER_PATH,
            gate.LABEL: {**cert, "selected_status": "source_authorized_plan_selected"},
        }

        class Right:
            def __init__(self):
                self.history = []
                self.reply_variant_counts = Counter()
                self.intent_variant_counts = Counter()
                self.normalized_reply_counts = Counter()
                self.intent_normalized_counts = Counter()

            def _remember_turn(self, summary, reply, intent):
                self.history.extend((
                    {"role": "user", "content": summary, "intent": intent},
                    {"role": "assistant", "content": reply, "intent": intent},
                ))
                self.reply_variant_counts[reply] += 1
                self.intent_variant_counts[(intent, reply)] += 1
                self.normalized_reply_counts[reply] += 1
                self.intent_normalized_counts[(intent, reply)] += 1

            def _structured_surface_required(self):
                return False

            def _user_visible_language_rejection_reasons(self, *_args, **_kwargs):
                return []

        right = Right()
        right._remember_turn("前の会話", "前の返事", "chat")

        def base_emit(_brain, event, tick):
            right._remember_turn("下書き一", "うるはが決めたんだ。", "chat")
            right._remember_turn("下書き二", "うちは決めたよ。", "chat")
            visible = gate.visible_guard_with_local_fact_answer_authority_p4(
                right, "うちは決めたよ。", tick["logic"],
                event["user_input"], event["memory_data"],
            )
            return {"reply": visible, "logic": tick["logic"]}

        with patch.object(gate, "_ORIGINAL_EMIT", base_emit), patch.object(
            gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "うちは決めたよ。",
        ):
            result = gate.emit_response_with_local_fact_answer_authority_p4(
                SimpleNamespace(right_brain=right),
                {"user_input": FULL_QUERY, "memory_data": memory}, {"logic": logic},
            )
        self.assertEqual(result["reply"], cert["authorized_reply"])
        self.assertEqual([row["content"] for row in right.history if row["role"] == "assistant"],
                         ["前の返事", cert["authorized_reply"]])
        self.assertEqual(right.history[-2],
                         {"role": "user", "content": FULL_QUERY, "intent": "chat"})
        self.assertNotIn("うるはが決めたんだ。", right.reply_variant_counts)
        self.assertNotIn("うちは決めたよ。", right.reply_variant_counts)
        self.assertEqual(right.reply_variant_counts[cert["authorized_reply"]], 1)
        self.assertEqual(logic[gate.LABEL]["right_brain_history_surface_status"],
                         "pre_guard_speech_rolled_back_final_visible_committed")

    def test_protected_routes_self_speech_and_place_value_slot_stay_outside_actor_gate(self):
        memory = _recent_memory(_turn(SOURCE))
        for scene, route, route_type in (
            ("crisis", "high_road", "general_conversation"),
            ("casual", "low_road", "general_conversation"),
            ("casual", "high_road", "safety_sensitive"),
        ):
            with self.subTest(scene=scene, route=route, route_type=route_type):
                tick = {
                    "logic": {
                        "intent": "chat", "scene": scene, "surface_act": "plain_reply",
                        "core_message_jp": "元の返事。",
                        "semantic_route_m22": {"selected_type": route_type},
                    },
                    "route_info": {"route": route},
                }
                brain = SimpleNamespace(
                    right_brain=SimpleNamespace(_structured_surface_required=lambda: False)
                )
                with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
                    selected = gate.cognitive_tick_with_local_fact_answer_authority_p4(
                        brain, {"user_input": FULL_QUERY, "memory_data": memory}
                    )
                self.assertEqual(selected["logic"]["core_message_jp"], "元の返事。")
                self.assertNotIn(gate.LABEL, selected["logic"])

        self_speech = "今日はうるは自身が決めたんだ。"
        self.assertFalse(gate.classify_local_fact_query_p4(self_speech)["eligible"])
        self.assertEqual(gate.build_local_fact_certificate_p4(
            self_speech, memory
        )["reason"], "outside_bounded_fact_query")
        ordinary_tick = {
            "logic": {"intent": "chat", "scene": "casual", "surface_act": "plain_reply",
                      "core_message_jp": "うちは自分で決めたよ。"},
            "route_info": {"route": "high_road"},
        }
        with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: ordinary_tick):
            unchanged = gate.cognitive_tick_with_local_fact_answer_authority_p4(
                SimpleNamespace(), {"user_input": self_speech, "memory_data": memory}
            )
        self.assertEqual(unchanged["logic"]["core_message_jp"], "うちは自分で決めたよ。")
        self.assertNotIn(gate.LABEL, unchanged["logic"])
        old_place_query = f"{DATE}に{SUBJECT}、さっき私が決めたのはどこだっけ？"
        old_place = gate.build_local_fact_certificate_p4(old_place_query, memory)
        self.assertEqual(old_place["slot"], "prior_user_decided_place")
        self.assertEqual(old_place["status"], "source_backed")
        self.assertEqual(old_place["admitted_value"], PLACE)
