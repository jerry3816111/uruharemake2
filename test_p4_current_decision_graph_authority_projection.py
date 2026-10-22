"""Source-disjoint, zero-model contracts for D's verified graph signals."""

from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase

import uruha_current_decision_ack_authority_p4 as gate
import uruha_memory_observatory as graph


CASES = json.loads((Path(__file__).resolve().parent / "datasets"
                    / "p4_current_decision_graph_authority_projection_probe_2026-10-23.json")
                   .read_text(encoding="utf-8"))


def _turn(source, cycle=17):
    stamp = {
        "schema": gate.SCHEMA, "owner_id": "a" * 32,
        "event_id": "b" * 32, "cycle_index": cycle,
        "source_raw_sha256": gate._sha(source),
    }
    cert = gate.build_current_decision_ack_certificate_p4(source, stamp)
    assert cert is not None
    reply = cert["authorized_reply"]
    cert.update({
        "selected_status": "source_authorized_plan_selected",
        "pre_episode_status": "verified_before_episode_write",
        "pre_episode_reply_sha256": gate._sha(reply),
        "factive_profile_write_status": "suppressed_for_current_report",
        "visible_surface_status": "matched",
        "visible_failure_reasons": [],
        "final_visible_surface_matches_contract": True,
        "final_visible_surface_sha256": gate._sha(reply),
        "right_brain_history_surface_status": "raw_user_and_final_visible_reply_committed",
        "terminal_status": "trace_and_episode_reported_match",
        "terminal_reply_sha256": gate._sha(reply),
    })
    selected = {
        "intent": "deterministic_semantic_commit_m32",
        "core_message_jp": reply,
        "post_gate_selected_plan_authority": gate.LABEL,
    }
    return {
        "user_text": source, "reply": reply,
        "logic": {
            gate.LABEL: deepcopy(cert), "planner_path": gate.PLANNER_PATH,
            "core_message_jp": reply, "surface_act": "plain_reply",
            "visible_language_guard": {
                "final_reply": reply, "final_reply_sha256": gate._sha(reply),
                "final_rejection_reasons": [],
                "repair_action": "current_user_decision_ack_matched",
            },
        },
        "runtime_trace": {
            "cycle_index": cycle, gate.LABEL: deepcopy(cert),
            "route_info": {"route": "high_road", "reason": "deliberative"},
            "selected_plan": {"intent": selected["intent"], "core_message_jp": reply},
            "blackboard": [
                {"stage": "evidence", "label": gate.LABEL, "payload": deepcopy(cert)},
                {"stage": "select", "label": "selected_plan", "payload": selected},
                {"stage": "surface", "label": "utterance", "payload": {"reply": reply}},
            ],
        },
    }


def _node_for(result_graph, label):
    rows = [node for node in result_graph["nodes"] if node.get("label") == label]
    assert len(rows) == 1
    return rows[0]


def _without_d_presentation(result):
    baseline = deepcopy(result)
    baseline["logic"].pop(gate.LABEL, None)
    return graph.collect_cognitive_graph(baseline)


def _sync_cert(result):
    cert = result["logic"][gate.LABEL]
    result["runtime_trace"][gate.LABEL] = deepcopy(cert)
    for row in result["runtime_trace"]["blackboard"]:
        if row["label"] == gate.LABEL:
            row["payload"] = deepcopy(cert)


def _negative_mutation(case_id, result):
    trace = result["runtime_trace"]
    rows = trace["blackboard"]
    if case_id == "certificate_missing":
        result["logic"].pop(gate.LABEL)
    elif case_id == "terminal_status_missing":
        result["logic"][gate.LABEL].pop("terminal_status")
        _sync_cert(result)
    elif case_id == "stale_cycle":
        trace["cycle_index"] += 1
    elif case_id == "raw_sha_mismatch":
        result["user_text"] += "追記"
    elif case_id == "reply_sha_mismatch":
        result["reply"] = "違う返事。"
    elif case_id == "blackboard_certificate_mismatch":
        rows[0]["payload"]["terminal_status"] = "not_verified"
    elif case_id == "foreign_route_marker":
        result["logic"]["planner_path"] = "another_route"
    elif case_id == "other_gate_marker_unchanged":
        rows[1]["payload"]["post_gate_selected_plan_authority"] = "local_fact_answer_authority_p4"
    elif case_id == "duplicate_d_row":
        rows.insert(1, deepcopy(rows[0]))
    elif case_id == "duplicate_selected_plan_row":
        rows.insert(2, deepcopy(rows[1]))
    elif case_id == "utterance_reply_mismatch":
        rows[-1]["payload"]["reply"] = "違う返事。"
    elif case_id == "guard_final_mismatch":
        result["logic"]["visible_language_guard"]["final_reply_sha256"] = "0" * 64
    elif case_id == "binding_sha_mismatch":
        result["logic"][gate.LABEL]["binding_sha256"] = "0" * 64
        _sync_cert(result)
    else:
        raise AssertionError(f"unknown frozen negative: {case_id}")


class CurrentDecisionGraphAuthorityProjectionTests(TestCase):
    def test_frozen_case_count_and_no_model_contract(self):
        self.assertEqual(len(CASES["positives"]), 2)
        self.assertEqual(len(CASES["negative_mutations"]), 13)
        self.assertEqual(CASES["model_calls_for_contract"], 0)

    def test_two_verified_signals_only_and_html(self):
        for case in CASES["positives"]:
            with self.subTest(case=case["id"]):
                result = _turn(case["source"])
                self.assertEqual(result["logic"][gate.LABEL]["kind"], case["expected_kind"])
                before = deepcopy(result)
                actual = graph.collect_cognitive_graph(result)
                baseline = _without_d_presentation(result)
                self.assertEqual(result, before)
                self.assertEqual(actual["edges"], baseline["edges"])
                self.assertEqual(actual.get("payload_budget_m24"), baseline.get("payload_budget_m24"))
                self.assertEqual(len(actual["nodes"]), len(baseline["nodes"]))
                changed = []
                for node, old in zip(actual["nodes"], baseline["nodes"]):
                    self.assertEqual({k: v for k, v in node.items() if k != "signal"},
                                     {k: v for k, v in old.items() if k != "signal"})
                    if node["signal"] != old["signal"]:
                        changed.append(node["label"])
                self.assertEqual(changed, [gate.LABEL, "selected_plan"])
                self.assertIn("來源與回覆核對", _node_for(actual, gate.LABEL)["signal"])
                self.assertIn("已選：", _node_for(actual, "selected_plan")["signal"])
                self.assertNotIn("deterministic_semantic_commit_m32",
                                 _node_for(actual, "selected_plan")["signal"])
                html = graph.render_memory_observatory(result)
                self.assertIn("來源與回覆核對", html)
                self.assertIn("已選：", html)

    def test_all_frozen_negative_mutations_fail_closed(self):
        source = CASES["positives"][0]["source"]
        for case_id in CASES["negative_mutations"]:
            with self.subTest(case=case_id):
                result = _turn(source)
                _negative_mutation(case_id, result)
                before = deepcopy(result)
                actual = graph.collect_cognitive_graph(result)
                baseline = _without_d_presentation(result)
                self.assertEqual(result, before)
                self.assertEqual(actual, baseline)
                for node in actual["nodes"]:
                    self.assertNotIn("已選：當輪", node["signal"])

    def test_unrelated_gate_graph_is_byte_for_byte_unchanged(self):
        result = _turn(CASES["positives"][0]["source"])
        result["logic"].pop(gate.LABEL)
        result["runtime_trace"]["blackboard"][1]["payload"][
            "post_gate_selected_plan_authority"] = "local_fact_answer_authority_p4"
        baseline = deepcopy(result)
        actual = graph.collect_cognitive_graph(result)
        self.assertEqual(actual, graph.collect_cognitive_graph(baseline))
        self.assertEqual(result, baseline)

    def test_additional_terminal_consistency_controls(self):
        source = CASES["positives"][1]["source"]
        for field in ("visible_failure_reasons", "right_brain_history_surface_status",
                      "guard_rejections", "trace_selected_core", "low_road", "boolean_cycle"):
            with self.subTest(field=field):
                result = _turn(source)
                if field == "visible_failure_reasons":
                    result["logic"][gate.LABEL][field] = ["unexpected"]
                    _sync_cert(result)
                elif field == "right_brain_history_surface_status":
                    result["logic"][gate.LABEL][field] = "unverified"
                    _sync_cert(result)
                elif field == "guard_rejections":
                    result["logic"]["visible_language_guard"]["final_rejection_reasons"] = ["unexpected"]
                elif field == "trace_selected_core":
                    result["runtime_trace"]["selected_plan"]["core_message_jp"] = "別の草稿。"
                elif field == "low_road":
                    result["runtime_trace"]["route_info"]["route"] = "low_road"
                else:
                    result["runtime_trace"]["cycle_index"] = True
                self.assertEqual(graph.collect_cognitive_graph(result),
                                 _without_d_presentation(result))
