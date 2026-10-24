"""Zero-model contracts for the opt-in mixed-request past-place source gate."""

from copy import deepcopy
from collections import Counter
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import uuid
import subprocess
import sys

import uruha_memory_runtime as memory_runtime
import uruha_mixed_past_place_source_authority_p4 as gate


DATA = json.loads((Path(__file__).resolve().parent / "datasets" /
                   "p4_mixed_past_place_source_authority_probe_2026-10-20.json").read_text())


def _memory(sources):
    recent_turns = []
    passed = []
    for index, source in enumerate(sources):
        user = source["user"]
        if source["channel"] in {"recent_turns", "recent_turns_unhanded"}:
            turn = {"user": user, "reply": "ん、分かった。", "episode_id": f"recent-{index}"}
            recent_turns.append(turn)
            candidate = memory_runtime.recent_turn_candidates([turn])[0]
            row = {
                "source": "recent_turn", "channel": "recent_turns",
                "trace_id": memory_runtime.memory_trace_id(candidate),
                "text": f"User:{user} -> Uruha:ん、分かった。",
            }
            if source["channel"] == "recent_turns":
                passed.append(row)
        elif source["channel"] == "direct_episode":
            memory_id = str(uuid.UUID(int=index + 1))
            passed.append({
                "source": "episode", "collection_name": "episode",
                "channel": "direct_episode", "memory_id": memory_id,
                "trace_id": f"stored:episode:{memory_id}",
                "episode_record_kind": "turn_episode",
                "episode_record_kind_origin": "stored_metadata",
                "text": (f"Time: 2026-10-20 14:00 | Intent: chat | Scene: casual | "
                         f"User: {user} | Summary: {source.get('summary', '普通の要約')} | "
                         f"Uruha: {source.get('assistant', 'ん。')} | Mood: calm"),
            })
        else:
            raise AssertionError(source["channel"])
    return {
        "recent_turns": recent_turns,
        "memory_provenance": {
            "passed_to_leftbrain": passed,
            "passed_to_leftbrain_trace_ids": [row["trace_id"] for row in passed],
        },
    }


def _case(case_id):
    return next(row for row in DATA["contract_cases"] if row["id"] == case_id)


class MixedPastPlaceSourceAuthorityTests(TestCase):
    def test_opt_in_web_entry_controller_and_install_order_resolve(self):
        script = """
import ast
from pathlib import Path
import uruha_web_ui_product_p4_mixed_past_place_source_authority as entry
import p4_mixed_past_place_source_authority_detached_control as controller
assert controller.ENTRYPOINT.name == 'uruha_web_ui_product_p4_mixed_past_place_source_authority.py'
tree = ast.parse(Path(entry.__file__).read_text(encoding='utf-8'))
def resolve(node):
    if isinstance(node, ast.Name): return vars(entry)[node.id]
    if isinstance(node, ast.Attribute): return getattr(resolve(node.value), node.attr)
    raise AssertionError(type(node).__name__)
targets = [node.func for node in ast.walk(tree) if isinstance(node, ast.Call)
           and isinstance(node.func, ast.Attribute)
           and (node.func.attr.startswith('install_') or node.func.attr == 'build_demo')]
assert all(callable(resolve(target)) for target in targets)
assert len(targets) == 20, len(targets)
assert [node.value.func.id for node in tree.body[-1].body if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
        and node.value.func.id.startswith('install_')][-2:] == [
    'install_explicit_rewrite_action_p4', 'install_mixed_past_place_source_authority_p4']
"""
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True,
                              text=True, timeout=45, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_frozen_contract_cases_have_bounded_results(self):
        for case in DATA["contract_cases"]:
            with self.subTest(case=case["id"]):
                cert = gate.build_mixed_past_place_certificate_p4(
                    case["query"], _memory(case["sources"]),
                )
                self.assertEqual(cert["status"], case["expected_status"])
                if cert["eligible"]:
                    self.assertEqual(cert["admitted_value"], case["expected_value"])
                    self.assertLessEqual(len(cert["authorized_reply"]), gate.MAX_CORE_CHARS)
                    self.assertFalse(cert["raw_dialogue_persisted"])
                    self.assertFalse(cert["private_state_truth_claimed"])
                    self.assertEqual(cert["model_calls_added"], 0)
                    self.assertFalse(cert["rewrite_subtask_fulfilled"])
                    if case["expected_value"] is None:
                        self.assertIn("分からない", cert["authorized_reply"])
                    else:
                        self.assertIn(case["expected_value"], cert["authorized_reply"])
                        self.assertTrue(cert["source_trace_id"])

    def test_user_transport_and_date_must_match_exactly(self):
        case = _case("D1_recent_direct")
        memory = _memory(case["sources"])
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            case["query"], memory)["status"], "source_backed")
        self.assertIsNone(gate.build_mixed_past_place_certificate_p4(
            case["query"], memory)["source_memory_id"])
        tampered = deepcopy(memory)
        tampered["memory_provenance"]["passed_to_leftbrain"][0]["text"] += "別文"
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            case["query"], tampered)["status"], "no_admitted_user_source")
        wrong_day = deepcopy(memory)
        wrong_day["recent_turns"][0]["user"] = wrong_day["recent_turns"][0]["user"].replace("10月11日", "10月10日")
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            case["query"], wrong_day)["status"], "no_admitted_user_source")
        invalid = case["query"].replace("2026年10月11日", "2026年2月31日")
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            invalid, memory)["status"], "ineligible")

    def test_malformed_or_duplicate_transport_abstains_without_crashing(self):
        case = _case("D1_recent_direct")
        malformed = {"memory_provenance": {"passed_to_leftbrain_trace_ids": [{}]}}
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            case["query"], malformed)["status"], "source_transport_ambiguous")
        memory = _memory(case["sources"])
        duplicate = deepcopy(memory)
        forged = deepcopy(duplicate["memory_provenance"]["passed_to_leftbrain"][0])
        forged["text"] = forged["text"].replace("藍色の階段前", "赤い門前")
        duplicate["memory_provenance"]["passed_to_leftbrain"].append(forged)
        cert = gate.build_mixed_past_place_certificate_p4(case["query"], duplicate)
        self.assertEqual(cert["status"], "source_transport_ambiguous")
        self.assertIsNone(cert["admitted_value"])
        restart = _case("D2_typed_episode_after_restart")
        episode_memory = _memory(restart["sources"])
        selected_copy = deepcopy(episode_memory["memory_provenance"]["passed_to_leftbrain"][0])
        selected_copy["channel"] = "selected_working_memory"
        episode_memory["memory_provenance"]["passed_to_leftbrain"].append(selected_copy)
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            restart["query"], episode_memory)["status"], "source_backed")
        conflicting_type = deepcopy(episode_memory)
        conflicting_type["memory_provenance"]["passed_to_leftbrain"][-1]["episode_record_kind"] = "episodic_consolidation"
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            restart["query"], conflicting_type)["status"], "source_transport_ambiguous")

    def test_compound_choice_and_unqualified_change_cannot_authorize_old_place(self):
        case = _case("D1_recent_direct")
        compound = _memory([{**case["sources"][0], "user": (
            "私は2026年10月11日の集合場所を青い門に決めたけど赤い門に決めた。"
        )}])
        cert = gate.build_mixed_past_place_certificate_p4(case["query"], compound)
        self.assertEqual(cert["status"], "source_retracted_or_ambiguous")
        self.assertIsNone(cert["admitted_value"])

        changed = _memory([
            case["sources"][0],
            {"channel": "recent_turns", "user": "2026年10月11日の集合場所は藍色の階段前から赤い門に変更した。"},
        ])
        cert = gate.build_mixed_past_place_certificate_p4(case["query"], changed)
        self.assertEqual(cert["status"], "source_retracted_or_ambiguous")
        self.assertIsNone(cert["admitted_value"])
        self.assertNotIn("藍色の階段前", cert["authorized_reply"])

        anaphoric = _memory([
            case["sources"][0],
            {"channel": "recent_turns", "user": "さっきの集合場所、赤い門に変えた。"},
        ])
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            case["query"], anaphoric)["status"], "source_retracted_or_ambiguous")

        alternate_name = _memory([
            case["sources"][0],
            {"channel": "recent_turns", "user": "2026年10月11日の集合先は藍色の階段前から赤い門に変更した。"},
        ])
        self.assertEqual(gate.build_mixed_past_place_certificate_p4(
            case["query"], alternate_name)["status"], "source_retracted_or_ambiguous")

        current_correction = (
            "「集合場所は保留」を友達向けに柔らかく言い換えて、"
            "2026年10月11日に私が選んだ場所も教えて。"
            "集合場所は藍色の階段前から赤い門に変更したから、新しい方ね。"
        )
        cert = gate.build_mixed_past_place_certificate_p4(current_correction, _memory(case["sources"]))
        self.assertEqual(cert["status"], "current_turn_change_ambiguous")
        self.assertIsNone(cert["admitted_value"])
        self.assertNotIn("藍色の階段前", cert["authorized_reply"])

    def test_visible_guard_rechecks_source_binding_and_fails_closed_on_loss(self):
        case = _case("D2_typed_episode_after_restart")
        memory = _memory(case["sources"])
        cert = gate.build_mixed_past_place_certificate_p4(case["query"], memory)
        self.assertEqual(cert["status"], "source_backed")

        class Right:
            def _structured_surface_required(self):
                return False

            def _user_visible_language_rejection_reasons(self, *_args, **_kwargs):
                return []

        logic = {
            "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
            "planner_path": gate.PLANNER_PATH, "core_message_jp": cert["authorized_reply"],
            gate.LABEL: {**cert, "selected_status": "source_authorized_plan_selected"},
        }
        with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "別の場所にしたよね。"):
            visible = gate.visible_guard_with_mixed_past_place_source_authority_p4(
                Right(), "別の場所にしたよね。", logic, case["query"], memory,
            )
        self.assertEqual(visible, cert["authorized_reply"])
        self.assertEqual(logic[gate.LABEL]["visible_surface_status"], "matched")

        changed = deepcopy(logic)
        changed[gate.LABEL] = {**cert, "selected_status": "source_authorized_plan_selected"}
        with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "別の場所にしたよね。"):
            visible = gate.visible_guard_with_mixed_past_place_source_authority_p4(
                Right(), "別の場所にしたよね。", changed, case["query"], _memory([]),
            )
        self.assertEqual(visible, "ん、今は確かめられないな。")
        self.assertNotIn(case["expected_value"], visible)
        self.assertEqual(changed[gate.LABEL]["visible_surface_status"], "failed_closed")

    def test_emit_transaction_drops_all_pre_guard_speech_history_and_counters(self):
        case = _case("D3_relative_unknown")
        memory = _memory([])
        cert = gate.build_mixed_past_place_certificate_p4(case["query"], memory)
        logic = {
            "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
            "planner_path": gate.PLANNER_PATH, "jp_summary": cert["authorized_reply"],
            "core_message_jp": cert["authorized_reply"],
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
                self.history += [
                    {"role": "user", "content": summary, "intent": intent},
                    {"role": "assistant", "content": reply, "intent": intent},
                ]
                self.reply_variant_counts[reply] += 1
                self.intent_variant_counts[(intent, reply)] += 1
                self.normalized_reply_counts[reply] += 1
                self.intent_normalized_counts[(intent, reply)] += 1

            def _user_visible_language_rejection_reasons(self, *_args, **_kwargs):
                return []

            def _structured_surface_required(self):
                return False

        right = Right()
        right._remember_turn("前の会話", "前の安全な返事", "chat")
        brain = SimpleNamespace(right_brain=right)
        saved = []

        def base_emit(_brain, event, tick):
            right._remember_turn("一度目", "根拠のない港の返事", "chat")
            right._remember_turn("二度目", "根拠のない橋の返事", "chat")
            visible = gate.visible_guard_with_mixed_past_place_source_authority_p4(
                right, "根拠のない橋の返事", tick["logic"], event["user_input"], event["memory_data"],
            )
            saved.append(visible)
            return {"reply": visible, "logic": tick["logic"]}

        with patch.object(gate, "_ORIGINAL_EMIT", base_emit), patch.object(
            gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "根拠のない橋の返事",
        ):
            result = gate.emit_response_with_mixed_past_place_source_authority_p4(
                brain, {"user_input": case["query"], "memory_data": memory}, {"logic": logic},
            )
        self.assertEqual(result["reply"], cert["authorized_reply"])
        self.assertEqual(saved, [cert["authorized_reply"]])
        self.assertEqual([row["content"] for row in right.history if row["role"] == "assistant"],
                         ["前の安全な返事", cert["authorized_reply"]])
        self.assertNotIn("根拠のない港の返事", right.reply_variant_counts)
        self.assertNotIn("根拠のない橋の返事", right.reply_variant_counts)
        self.assertEqual(right.reply_variant_counts[cert["authorized_reply"]], 1)
        self.assertEqual(logic[gate.LABEL]["right_brain_history_surface_status"],
                         "pre_guard_speech_rolled_back_final_visible_committed")

    def test_unknown_guard_replaces_fabricated_selected_core_before_episode_write(self):
        case = _case("D3_relative_unknown")
        logic = {
            "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
            "core_message_jp": "一昨日は港の階段にしたよね。",
            "semantic_route_m22": {"selected_type": "general_conversation"},
            "bounded_slow_path_m21": {"stage_seconds": {"total": 1.2}},
        }
        tick = {"logic": logic, "route_info": {"route": "high_road", "performed_route": "full_planner"}}
        runtime = SimpleNamespace(
            blackboard=[
                {"label": "bounded_slow_path_planner_m21", "payload": {"stage_seconds": {"total": 1.2}}},
                {"label": "selected_plan", "payload": {"core_message_jp": logic["core_message_jp"]}},
            ], last_selected_plan={}, active_goal="", last_internal_monologue="old",
            last_candidates=[1], planner_tick_trace=[1], planner_tick_count=1,
            self_correction_applied=True, last_personhood_loop={"action_choice": {}},
            open_loops=[], latent_goal_stack=[], set_prediction=lambda *_a, **_kw: None,
        )
        brain = SimpleNamespace(
            runtime=runtime,
            right_brain=SimpleNamespace(_structured_surface_required=lambda: False),
            left_brain=SimpleNamespace(predict_next_user_signal=lambda *_a, **_kw: {
                "expected_intent": "chat", "expected_valence": 0.0, "source_plan_intent": "chat",
            }),
            _derive_open_loops=lambda _logic: [],
            _infer_focus_label=lambda *_a: "chat",
            _plan_trace_summary=lambda current: {"core_message_jp": current["core_message_jp"]},
        )
        event = {"user_input": case["query"], "memory_data": _memory([])}
        with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
            selected = gate.cognitive_tick_with_mixed_past_place_source_authority_p4(brain, event)
        self.assertNotIn("港の階段", selected["logic"]["core_message_jp"])
        self.assertEqual(selected["logic"][gate.LABEL]["status"], "relative_time_unverifiable")
        self.assertEqual(runtime.blackboard[1]["label"], gate.LABEL)
        self.assertEqual(runtime.blackboard[2]["payload"]["core_message_jp"], selected["logic"]["core_message_jp"])

        class Right:
            def _structured_surface_required(self):
                return False

            def _user_visible_language_rejection_reasons(self, *_args, **_kwargs):
                return []

        with patch.object(gate, "_ORIGINAL_VISIBLE_GUARD", lambda *_a, **_kw: "一昨日は港の階段にしたよね。"):
            visible = gate.visible_guard_with_mixed_past_place_source_authority_p4(
                Right(), "一昨日は港の階段にしたよね。", selected["logic"], case["query"], event["memory_data"],
            )
        self.assertNotIn("港の階段", visible)
        self.assertEqual(selected["logic"]["visible_language_guard"]["final_reply"], visible)
        self.assertEqual(selected["logic"][gate.LABEL]["visible_surface_status"], "matched")
        result = {"reply": visible, "logic": selected["logic"],
                  "runtime_trace": {"blackboard": deepcopy(runtime.blackboard)}}
        gate.materialize_mixed_past_place_source_authority_p4(result)
        self.assertTrue(result["runtime_trace"][gate.LABEL]["final_visible_surface_matches_contract"])
        self.assertEqual([row["label"] for row in result["runtime_trace"]["blackboard"]].count(gate.LABEL), 1)

    def test_competing_m31_m32_and_protected_routes_keep_existing_authority(self):
        case = _case("D1_recent_direct")
        event = {"user_input": case["query"], "memory_data": _memory(case["sources"])}
        for extra in (
            {"semantic_authorization_m31": {"surface_authority": True}},
            {"semantic_commit_repair_m32": {"surface_authority": True}},
            {"intent": "sexual_boundary"},
        ):
            with self.subTest(extra=extra):
                logic = {"intent": "chat", "scene": "casual", "core_message_jp": "既存権限。", **extra}
                tick = {"logic": logic, "route_info": {"route": "high_road"}}
                brain = SimpleNamespace(right_brain=SimpleNamespace(_structured_surface_required=lambda: False))
                with patch.object(gate, "_ORIGINAL_TICK", lambda _self, _event: tick):
                    selected = gate.cognitive_tick_with_mixed_past_place_source_authority_p4(brain, event)
                self.assertEqual(selected["logic"]["core_message_jp"], "既存権限。")
                self.assertNotIn(gate.LABEL, selected["logic"])
