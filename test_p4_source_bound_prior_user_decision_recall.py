"""Zero-model contracts for source-bound recall of a prior User place decision.

Fixtures deliberately differ from the frozen B0–B6 Safari conversation. These
contracts test an authority boundary, not open-domain recall or human ratings.
"""

from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import uruha_local_fact_answer_authority_p4 as gate
import uruha_memory_runtime as memory_runtime


DATE = "2048年7月26日"
SUBJECT = "研究ノートを渡す場所"
PLACE = "群青の渡り廊下の西端"
QUERY = f"{DATE}に{SUBJECT}、さっき私が決めたのはどこだっけ？"
SOURCE = f"私は{DATE}に{SUBJECT}を{PLACE}に決めた。"
OTHER_DATE = "2052年11月8日"
OTHER_SUBJECT = "備品を返す場所"
OTHER_PLACE = "薄緑の観測塔の裏手"
OTHER_QUERY = f"{OTHER_DATE}に{OTHER_SUBJECT}、私が決めたのはどこだった？"
OTHER_SOURCE = f"私は{OTHER_DATE}に{OTHER_SUBJECT}を{OTHER_PLACE}に決めた。"


def _recent_turn(user, reply="ん、聞いた。", episode_id="recent-one"):
    return {"user": user, "reply": reply, "episode_id": episode_id}


def _recent_memory(*turns):
    rows = []
    for turn in turns:
        candidate = memory_runtime.recent_turn_candidates([turn])[0]
        rows.append({
            "source": "recent_turn",
            "channel": "recent_turns",
            "trace_id": memory_runtime.memory_trace_id(candidate),
            "text": f"User:{turn['user']} -> Uruha:{turn['reply']}",
        })
    return {
        "recent_turns": list(turns),
        "memory_provenance": {
            "passed_to_leftbrain": rows,
            "passed_to_leftbrain_trace_ids": [row["trace_id"] for row in rows],
        },
    }


def _episode(user, *, memory_id="85c668c4-4c8e-4d35-9370-2eac35fbe62e",
             summary="短い要約", assistant="ん、聞いた。", channel="direct_episode",
             kind="turn_episode", typed=True):
    row = {
        "source": "episode",
        "collection_name": "episode",
        "channel": channel,
        "memory_id": memory_id,
        "trace_id": f"stored:episode:{memory_id}",
        "text": (
            "Time: 2026-10-21 09:00 | Intent: chat | Scene: casual | "
            f"User: {user} | Summary: {summary} | Uruha: {assistant} | Mood: calm"
        ),
    }
    if typed:
        row.update(episode_record_kind=kind, episode_record_kind_origin="stored_metadata")
    return row


def _with_passed(*rows, recent_turns=()):
    return {
        "recent_turns": list(recent_turns),
        "memory_provenance": {
            "passed_to_leftbrain": list(rows),
            "passed_to_leftbrain_trace_ids": [row["trace_id"] for row in rows],
        },
    }


class PriorUserDecisionRecallTests(TestCase):
    def test_distinct_dates_subjects_and_places_use_one_bounded_query_slot(self):
        for query, subject, source, place in (
            (QUERY, f"{DATE}に{SUBJECT}", SOURCE, PLACE),
            (OTHER_QUERY, f"{OTHER_DATE}に{OTHER_SUBJECT}", OTHER_SOURCE, OTHER_PLACE),
        ):
            with self.subTest(query=query):
                classified = gate.classify_local_fact_query_p4(query)
                self.assertTrue(classified["eligible"])
                self.assertEqual(classified["slot"], "prior_user_decided_place")
                self.assertEqual(classified["subject"], subject)
                cert = gate.build_local_fact_certificate_p4(
                    query, _recent_memory(_recent_turn(source))
                )
                self.assertEqual(cert["status"], "source_backed")
                self.assertEqual(cert["admitted_value"], place)
                self.assertIn(place, cert["authorized_reply"])
                self.assertIn("そっち", cert["authorized_reply"])
                self.assertNotIn("うちが決め", cert["authorized_reply"])
                self.assertEqual(cert["model_calls_added"], 0)

    def test_typed_episode_is_an_independent_source_channel(self):
        row = _episode(SOURCE)
        cert = gate.build_local_fact_certificate_p4(QUERY, _with_passed(row))
        self.assertEqual(cert["status"], "source_backed")
        self.assertEqual(cert["source_channel"], "direct_episode")
        self.assertEqual(cert["source_trace_id"], row["trace_id"])
        self.assertEqual(cert["source_memory_id"], row["memory_id"])
        self.assertEqual(cert["source_user_sha256"], gate._sha(SOURCE))
        self.assertIn(PLACE, cert["authorized_reply"])

    def test_summary_assistant_short_term_and_untyped_episode_are_not_user_proof(self):
        wrong_user = "今日の準備はあとで確認する。"
        cases = (
            _with_passed(_episode(wrong_user, summary=SOURCE, assistant=SOURCE)),
            _with_passed({
                "source": "short_term", "channel": "short_term_summary",
                "trace_id": "derived:short_term:only-summary", "text": f"User:{SOURCE} -> Uruha:ん。",
            }),
            _with_passed(_episode(SOURCE, typed=False)),
            _with_passed(_episode(SOURCE, kind="episodic_consolidation")),
            _with_passed(_episode(SOURCE, channel="selected_working_memory")),
        )
        for memory in cases:
            with self.subTest(memory=memory):
                cert = gate.build_local_fact_certificate_p4(QUERY, memory)
                self.assertEqual(cert["status"], "no_admitted_user_source")
                self.assertIsNone(cert["admitted_value"])
                self.assertNotIn(PLACE, cert["authorized_reply"])

    def test_stale_recent_trace_and_changed_date_or_subject_cannot_authorize(self):
        stale = _recent_memory(_recent_turn(SOURCE))
        stale["memory_provenance"]["passed_to_leftbrain"][0]["trace_id"] = "derived:recent_turn:stale"
        stale["memory_provenance"]["passed_to_leftbrain_trace_ids"] = ["derived:recent_turn:stale"]
        variants = (
            (QUERY, stale),
            (QUERY, _recent_memory(_recent_turn(SOURCE.replace(DATE, OTHER_DATE)))),
            (QUERY, _recent_memory(_recent_turn(SOURCE.replace(SUBJECT, OTHER_SUBJECT)))),
            (OTHER_QUERY, _recent_memory(_recent_turn(SOURCE))),
        )
        for query, memory in variants:
            with self.subTest(query=query, memory=memory):
                cert = gate.build_local_fact_certificate_p4(query, memory)
                self.assertEqual(cert["status"], "no_admitted_user_source")
                self.assertIsNone(cert["admitted_value"])

    def test_reported_friend_and_uruha_text_do_not_become_user_decision(self):
        friend = f"友人が「{SOURCE.rstrip('。')}」と言ってた。"
        cases = (
            _recent_memory(_recent_turn(friend)),
            _with_passed(_episode("友人から聞いた話。", summary=SOURCE, assistant=SOURCE)),
            _recent_memory(_recent_turn("友人から聞いた話。", reply=SOURCE)),
        )
        for memory in cases:
            with self.subTest(memory=memory):
                cert = gate.build_local_fact_certificate_p4(QUERY, memory)
                self.assertEqual(cert["status"], "no_admitted_user_source")
                self.assertNotIn(PLACE, cert["authorized_reply"])

    def test_one_raw_user_assertion_on_two_channels_is_one_observation(self):
        turn = _recent_turn(SOURCE)
        memory = _recent_memory(turn)
        row = _episode(SOURCE)
        memory["memory_provenance"]["passed_to_leftbrain"].append(row)
        memory["memory_provenance"]["passed_to_leftbrain_trace_ids"].append(row["trace_id"])
        cert = gate.build_local_fact_certificate_p4(QUERY, memory)
        self.assertEqual(cert["status"], "source_backed")
        self.assertEqual(cert["admitted_source_count"], 1)
        self.assertEqual(cert["distinct_value_count"], 1)
        self.assertEqual(cert["source_user_sha256"], gate._sha(SOURCE))

    def test_two_distinct_direct_user_values_require_clarification(self):
        newer_place = "灰青の連絡橋の中央"
        newer = _recent_turn(SOURCE.replace(PLACE, newer_place), episode_id="recent-newer")
        memory = _recent_memory(newer)
        older = _episode(SOURCE)
        memory["memory_provenance"]["passed_to_leftbrain"].append(older)
        memory["memory_provenance"]["passed_to_leftbrain_trace_ids"].append(older["trace_id"])
        cert = gate.build_local_fact_certificate_p4(QUERY, memory)
        self.assertEqual(cert["status"], "conflicting_user_sources")
        self.assertEqual(cert["admitted_source_count"], 2)
        self.assertEqual(cert["distinct_value_count"], 2)
        self.assertIsNone(cert["admitted_value"])
        self.assertIn(PLACE, cert["authorized_reply"])
        self.assertIn(newer_place, cert["authorized_reply"])
        self.assertRegex(cert["authorized_reply"], r"どっち|どちら")
        self.assertLessEqual(len(cert["authorized_reply"]), gate.MAX_AUTHORIZED_CORE_CHARS)

    def test_explicit_user_correction_does_not_leave_old_place_as_answer(self):
        correction = (
            f"さっきのは違う、私は{DATE}に{SUBJECT}を"
            "灰青の連絡橋の中央に決めた。"
        )
        memory = _recent_memory(
            _recent_turn(SOURCE, episode_id="first"),
            _recent_turn(correction, episode_id="correction"),
        )
        cert = gate.build_local_fact_certificate_p4(QUERY, memory)
        self.assertEqual(cert["status"], "unresolved_user_correction")
        self.assertIsNone(cert["admitted_value"])
        self.assertNotIn(PLACE, cert["authorized_reply"])
        self.assertIn("確認", cert["authorized_reply"])

    def test_sensitive_placement_is_not_promoted(self):
        subject = "暗証番号を書いた紙を渡す場所"
        query = f"{DATE}に{subject}、さっき私が決めたのはどこだっけ？"
        source = f"私は{DATE}に{subject}を北棟の施錠箱に決めた。"
        classified = gate.classify_local_fact_query_p4(query)
        self.assertFalse(classified["eligible"])
        cert = gate.build_local_fact_certificate_p4(query, _recent_memory(_recent_turn(source)))
        self.assertFalse(cert["eligible"])
        self.assertNotIn("北棟の施錠箱", str(cert.get("authorized_reply") or ""))

        # The question can look ordinary while the remembered place itself
        # reveals a sensitive placement.  Neither side may authorize it.
        ordinary_query = QUERY
        hidden_sensitive_place = "認証コード保管箱の裏"
        hidden_source = SOURCE.replace(PLACE, hidden_sensitive_place)
        hidden_cert = gate.build_local_fact_certificate_p4(
            ordinary_query, _recent_memory(_recent_turn(hidden_source))
        )
        self.assertEqual(hidden_cert["status"], "no_admitted_user_source")
        self.assertNotIn(hidden_sensitive_place, hidden_cert["authorized_reply"])

        spare_key_place = "スペアキーの隠し棚の裏"
        spare_key_cert = gate.build_local_fact_certificate_p4(
            ordinary_query,
            _recent_memory(_recent_turn(SOURCE.replace(PLACE, spare_key_place))),
        )
        self.assertEqual(spare_key_cert["status"], "no_admitted_user_source")
        self.assertNotIn(spare_key_place, spare_key_cert["authorized_reply"])

        physical_query = f"{DATE}に家の鍵を隠す場所、さっき私が決めたのはどこだっけ？"
        physical_source = f"私は{DATE}に家の鍵を隠す場所を玄関の鉢の裏に決めた。"
        physical_cert = gate.build_local_fact_certificate_p4(
            physical_query, _recent_memory(_recent_turn(physical_source))
        )
        self.assertFalse(physical_cert["eligible"])
        self.assertNotIn("玄関の鉢の裏", str(physical_cert.get("authorized_reply") or ""))

    def test_over_budget_value_is_never_clipped_into_an_answer(self):
        long_value = "東の細い回廊" * 5
        memory = _recent_memory(_recent_turn(SOURCE.replace(PLACE, long_value)))
        cert = gate.build_local_fact_certificate_p4(QUERY, memory)
        self.assertNotEqual(cert["status"], "source_backed")
        self.assertIsNone(cert.get("admitted_value"))
        self.assertIsNone(cert.get("source_trace_id"))
        self.assertLessEqual(len(cert["authorized_reply"]), gate.MAX_AUTHORIZED_CORE_CHARS)
        self.assertNotIn(long_value[:16], cert["authorized_reply"])

    def test_selected_plan_guard_final_hash_and_stale_memory_failure(self):
        memory = _recent_memory(_recent_turn(SOURCE))
        tick = {
            "logic": {
                "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
                "core_message_jp": "未確認の東端だと思う。",
                "semantic_route_m22": {"selected_type": "general_conversation"},
            },
            "route_info": {"route": "high_road", "performed_route": "full_planner"},
        }
        fake = SimpleNamespace(
            right_brain=SimpleNamespace(_structured_surface_required=lambda: False)
        )
        with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
            selected = gate.cognitive_tick_with_local_fact_answer_authority_p4(
                fake, {"user_input": QUERY, "memory_data": memory}
            )
        logic = selected["logic"]
        cert = logic[gate.LABEL]
        self.assertEqual(cert["selected_status"], "source_authorized_plan_selected")
        self.assertEqual(logic["core_message_jp"], cert["authorized_reply"])
        self.assertIn(PLACE, logic["core_message_jp"])
        self.assertNotIn("未確認の東端", logic["core_message_jp"])
        self.assertEqual(cert["authorized_reply_sha256"], gate._sha(logic["core_message_jp"]))

        right = SimpleNamespace(
            _structured_surface_required=lambda: False,
            _user_visible_language_rejection_reasons=lambda *_a, **_kw: [],
        )
        with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "東端だよ。"):
            visible = gate.visible_guard_with_local_fact_answer_authority_p4(
                right, "東端だよ。", logic, QUERY, memory
            )
        self.assertEqual(visible, cert["authorized_reply"])
        self.assertEqual(logic["visible_language_guard"]["final_reply_sha256"], gate._sha(visible))
        result = {"reply": visible, "logic": logic, "runtime_trace": {"blackboard": []}}
        gate.materialize_local_fact_answer_authority_p4(result)
        receipt = result["logic"][gate.LABEL]
        self.assertTrue(receipt["final_visible_surface_matches_contract"])
        self.assertEqual(receipt["final_visible_surface_sha256"], gate._sha(visible))
        self.assertEqual(result["runtime_trace"][gate.LABEL], receipt)

        changed = _recent_memory(_recent_turn(SOURCE.replace(PLACE, OTHER_PLACE)))
        stale_logic = deepcopy(logic)
        with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "東端だよ。"):
            withheld = gate.visible_guard_with_local_fact_answer_authority_p4(
                right, "東端だよ。", stale_logic, QUERY, changed
            )
        self.assertNotIn(PLACE, withheld)
        self.assertEqual(stale_logic[gate.LABEL]["visible_surface_status"], "failed_closed")
        result["reply"] = "別の場所だよ。"
        gate.materialize_local_fact_answer_authority_p4(result)
        self.assertEqual(result["logic"][gate.LABEL]["visible_surface_status"], "post_guard_surface_mismatch")

    def test_new_slot_history_records_visible_answer_not_pre_guard_candidates(self):
        memory = _recent_memory(_recent_turn(SOURCE))
        cert = gate.build_local_fact_certificate_p4(QUERY, memory)
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
        right._remember_turn("前の会話", "前の安全な返事", "chat")
        brain = SimpleNamespace(right_brain=right)

        def base_emit(_brain, event, tick):
            right._remember_turn("一度目", "根拠のない港の返事", "chat")
            right._remember_turn("二度目", "根拠のない橋の返事", "chat")
            visible = gate.visible_guard_with_local_fact_answer_authority_p4(
                right, "根拠のない橋の返事", tick["logic"],
                event["user_input"], event["memory_data"],
            )
            return {"reply": visible, "logic": tick["logic"]}

        with patch.object(gate, "_ORIGINAL_EMIT", base_emit), patch.object(
            gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "根拠のない橋の返事",
        ):
            result = gate.emit_response_with_local_fact_answer_authority_p4(
                brain, {"user_input": QUERY, "memory_data": memory}, {"logic": logic},
            )
        self.assertEqual(result["reply"], cert["authorized_reply"])
        self.assertEqual(
            [row["content"] for row in right.history if row["role"] == "assistant"],
            ["前の安全な返事", cert["authorized_reply"]],
        )
        self.assertEqual(right.history[-2]["role"], "user")
        self.assertEqual(right.history[-2]["content"], QUERY)
        self.assertNotEqual(right.history[-2]["content"], cert["authorized_reply"])
        self.assertNotIn("根拠のない港の返事", right.reply_variant_counts)
        self.assertNotIn("根拠のない橋の返事", right.reply_variant_counts)
        self.assertEqual(right.reply_variant_counts[cert["authorized_reply"]], 1)
        self.assertEqual(
            logic[gate.LABEL]["right_brain_history_surface_status"],
            "pre_guard_speech_rolled_back_final_visible_committed",
        )

    def test_protected_route_is_unchanged_and_older_local_fact_still_works(self):
        memory = _recent_memory(_recent_turn(SOURCE))
        for scene, route, route_type in (
            ("crisis", "high_road", "general_conversation"),
            ("casual", "low_road", "general_conversation"),
            ("casual", "high_road", "safety_sensitive"),
        ):
            with self.subTest(scene=scene, route=route, route_type=route_type):
                tick = {
                    "logic": {
                        "intent": "chat", "scene": scene, "surface_act": "plain_reply",
                        "core_message_jp": "元のまま。",
                        "semantic_route_m22": {"selected_type": route_type},
                    },
                    "route_info": {"route": route},
                }
                fake = SimpleNamespace(
                    right_brain=SimpleNamespace(_structured_surface_required=lambda: False)
                )
                with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
                    selected = gate.cognitive_tick_with_local_fact_answer_authority_p4(
                        fake, {"user_input": QUERY, "memory_data": memory}
                    )
                self.assertEqual(selected["logic"]["core_message_jp"], "元のまま。")
                self.assertNotIn(gate.LABEL, selected["logic"])

        old_user = "音響確認は16時から始まる。"
        old_cert = gate.build_local_fact_certificate_p4(
            "音響確認は何時から始まる？", _recent_memory(_recent_turn(old_user))
        )
        self.assertEqual(old_cert["status"], "source_backed")
        self.assertEqual(old_cert["admitted_value"], "16時")
        self.assertEqual(old_cert["slot"], "local_start_time")
