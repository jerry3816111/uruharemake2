"""Zero-model contracts for the verified D main-chain focus renderer.

The f0/f1/f2 sources and the thirteen named negative controls are frozen before
the renderer change.  These tests inspect only existing graph/trace structures;
they do not run a model, a browser, or a database.
"""

from copy import deepcopy
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import uruha_current_decision_ack_authority_p4 as gate
import uruha_memory_observatory as observatory
from test_p4_current_decision_graph_authority_projection import _turn


CASES = json.loads(
    (Path(__file__).resolve().parent / "datasets"
     / "p4_verified_main_chain_focus_probe_2026-10-23.json")
    .read_text(encoding="utf-8")
)
BY_ID = {case["id"]: case for case in CASES["cases"]}


def _d_turn(case_id, *, with_write=False):
    """A real D receipt with intervening, source-neutral blackboard records."""
    result = _turn(BY_ID[case_id]["source"])
    rows = result["runtime_trace"]["blackboard"]
    prefix = {"stage": "observe", "label": "focus_fixture_prefix", "payload": {"step": 0}}
    middle_a = {"stage": "observe", "label": "focus_fixture_middle_a", "payload": {"step": 1}}
    middle_b = {"stage": "observe", "label": "focus_fixture_middle_b", "payload": {"step": 2}}
    middle_c = {"stage": "observe", "label": "focus_fixture_middle_c", "payload": {"step": 3}}
    suffix = {"stage": "observe", "label": "focus_fixture_suffix", "payload": {"step": 4}}
    rows[:] = [prefix, rows[0], middle_a, middle_b, rows[1], middle_c, rows[2], suffix]
    if with_write:
        result["runtime_trace"]["memory_writes"] = [{
            "layer": "episodic_memory",
            "kind": "turn_episode",
            "summary": "trace-reported turn episode",
        }]
    return result


def _anchor(graph, label):
    found = [node for node in graph["nodes"] if node["label"] == label]
    assert len(found) == 1, (label, found)
    return found[0]


def _main_ids(graph):
    """Reconstruct the fixture's original is-main order, not a new inferred edge."""
    next_by_source = {}
    for edge in graph["edges"]:
        if edge["class"] == "is-main":
            assert edge["source"] not in next_by_source
            next_by_source[edge["source"]] = edge["target"]
    ids = ["turn-input"]
    while ids[-1] != "turn-output":
        assert ids[-1] in next_by_source
        ids.append(next_by_source[ids[-1]])
        assert len(ids) <= len(graph["nodes"])
    return ids


def _expected_segments(graph, anchor_ids, *, with_write):
    main_ids = _main_ids(graph)
    segments = []
    for source, target in zip(anchor_ids, anchor_ids[1:]):
        start, end = main_ids.index(source), main_ids.index(target)
        assert start < end
        segments.append({
            "source": source, "target": target,
            "edge_class": "is-main", "omitted": end - start - 1,
        })
    if with_write:
        segments.append({
            "source": "turn-output", "target": "write-0",
            "edge_class": "is-active", "omitted": 0,
        })
    return segments


class _GraphDOM(HTMLParser):
    """Check disclosure ancestry and collect only the marked focus text."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.focus_text = []
        self.graph_scroll_in_disclosure = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if "brain-graph-scroll" in classes:
            self.graph_scroll_in_disclosure.append(
                any(name == "details" for name, _ in self.stack)
            )
        if tag not in self.VOID:
            self.stack.append((tag, attributes))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if any(attrs.get("data-p4-d-focus") == "verified" for _, attrs in self.stack):
            self.focus_text.append(data)


def _dom(html):
    parser = _GraphDOM()
    parser.feed(html)
    parser.close()
    return parser


class VerifiedMainChainFocusP4Tests(TestCase):
    def test_frozen_case_inventory_is_source_disjoint_and_zero_model(self):
        self.assertEqual([case["id"] for case in CASES["cases"]], ["f0", "f1", "f2"])
        self.assertEqual([case["expected_focus"] for case in CASES["cases"]], [True, True, False])
        self.assertEqual(CASES["model_calls_for_contract"], 0)
        self.assertEqual(len(CASES["negative_mutations"]), 13)
        self.assertEqual(len({case["source"] for case in CASES["cases"]}), 3)

    def test_f0_f1_use_original_nodes_and_exact_directed_main_path(self):
        for case_id in ("f0", "f1"):
            for with_write in (False, True):
                with self.subTest(case=case_id, write=with_write):
                    result = _d_turn(case_id, with_write=with_write)
                    before_result = deepcopy(result)
                    original = observatory.collect_cognitive_graph(result)
                    before_graph = deepcopy(original)
                    focus = observatory._verified_d_main_chain_focus_p4(result, original)
                    self.assertIsNotNone(focus)
                    expected_ids = [
                        "turn-input", _anchor(original, gate.LABEL)["id"],
                        _anchor(original, "selected_plan")["id"],
                        _anchor(original, "utterance")["id"], "turn-output",
                    ]
                    if with_write:
                        expected_ids.append("write-0")
                    self.assertEqual([node["id"] for node in focus["anchors"]], expected_ids)
                    original_by_id = {node["id"]: node for node in original["nodes"]}
                    for node in focus["anchors"]:
                        self.assertIs(node, original_by_id[node["id"]])
                    self.assertEqual(
                        focus["segments"],
                        _expected_segments(original, expected_ids[:5], with_write=with_write),
                    )
                    self.assertEqual(
                        [part["omitted"] for part in focus["segments"][:4]],
                        [1, 2, 1, 1],
                    )
                    self.assertEqual(
                        focus["write_status"],
                        "trace_reported" if with_write else "not_in_focus",
                    )
                    self.assertEqual(original, before_graph)
                    self.assertEqual(result, before_result)

    def test_verified_html_preserves_full_graph_and_untruncated_details(self):
        for case_id in ("f0", "f1"):
            with self.subTest(case=case_id):
                result = _d_turn(case_id, with_write=True)
                before_result = deepcopy(result)
                original = observatory.collect_cognitive_graph(result)
                before_graph = deepcopy(original)
                html = observatory.render_memory_observatory(result)
                parsed = _dom(html)
                self.assertIn('data-p4-d-focus="verified"', html)
                self.assertEqual(parsed.graph_scroll_in_disclosure, [True])
                focus_text = "".join(parsed.focus_text)
                self.assertIn(result["user_text"], focus_text)
                self.assertIn(result["reply"], focus_text)
                self.assertIn(_anchor(original, gate.LABEL)["signal"], focus_text)
                self.assertIn(_anchor(original, "selected_plan")["signal"], focus_text)
                self.assertEqual(html.count('<details class="brain-node '), len(original["nodes"]))
                self.assertEqual(html.count('<path class="brain-edge '), len(original["edges"]))
                self.assertEqual(observatory.collect_cognitive_graph(result), before_graph)
                self.assertEqual(result, before_result)

    def test_full_input_output_are_html_escaped_inside_focus(self):
        source = "私は2089年4月19日に陶器&<の羅針盤を受け取る場所を紫<&の工房の南扉に決めた。"
        result = _turn(source)
        self.assertGreater(len(source), 42)
        self.assertGreater(len(result["reply"]), 42)
        html = observatory.render_memory_observatory(result)
        focus_text = "".join(_dom(html).focus_text)
        self.assertIn(source, focus_text)
        self.assertIn(result["reply"], focus_text)
        self.assertIn(escape(source), html)
        self.assertIn(escape(result["reply"]), html)
        self.assertNotIn(source, html)
        self.assertNotIn(result["reply"], html)

    def test_f2_and_non_d_graph_remain_unfocused_and_open(self):
        result = {
            "user_text": BY_ID["f2"]["source"],
            "reply": "友人の話だね。",
            "runtime_trace": {"blackboard": [
                {"stage": "select", "label": "selected_plan", "payload": {"intent": "chat"}},
                {"stage": "surface", "label": "utterance", "payload": {"reply": "友人の話だね。"}},
            ]},
        }
        original = observatory.collect_cognitive_graph(result)
        self.assertIsNone(observatory._verified_d_main_chain_focus_p4(result, original))
        html = observatory.render_memory_observatory(result)
        self.assertNotIn('data-p4-d-focus="verified"', html)
        self.assertEqual(_dom(html).graph_scroll_in_disclosure, [False])

    def test_thirteen_frozen_mutations_cannot_invent_focus_or_writeback(self):
        main_failures = {
            "certificate_missing", "stale_cycle", "foreign_route",
            "duplicate_d_node", "duplicate_selected_node", "missing_utterance_node",
            "missing_output_node", "broken_input_to_d_main_path",
            "broken_d_to_selected_main_edge", "broken_selected_to_utterance_main_path",
            "broken_utterance_to_output_main_path",
        }
        self.assertEqual(
            set(CASES["negative_mutations"]),
            main_failures | {"fake_write_edge", "wrong_kind_write_node"},
        )
        for mutation in CASES["negative_mutations"]:
            with self.subTest(mutation=mutation):
                result = _d_turn("f0", with_write=mutation == "wrong_kind_write_node")
                original = observatory.collect_cognitive_graph(result)
                mutated = deepcopy(original)
                if mutation == "certificate_missing":
                    result["logic"].pop(gate.LABEL)
                elif mutation == "stale_cycle":
                    result["runtime_trace"]["cycle_index"] += 1
                elif mutation == "foreign_route":
                    result["logic"]["planner_path"] = "another_route"
                elif mutation in {"duplicate_d_node", "duplicate_selected_node"}:
                    label = gate.LABEL if mutation == "duplicate_d_node" else "selected_plan"
                    duplicate = deepcopy(_anchor(mutated, label))
                    duplicate["id"] = "duplicate-" + duplicate["id"]
                    mutated["nodes"].append(duplicate)
                elif mutation in {"missing_utterance_node", "missing_output_node"}:
                    missing_id = (
                        _anchor(mutated, "utterance")["id"]
                        if mutation == "missing_utterance_node" else "turn-output"
                    )
                    mutated["nodes"] = [node for node in mutated["nodes"] if node["id"] != missing_id]
                elif mutation.startswith("broken_"):
                    rows = result["runtime_trace"]["blackboard"]
                    if mutation == "broken_input_to_d_main_path":
                        source, target = "turn-input", "runtime-0"
                    elif mutation == "broken_d_to_selected_main_edge":
                        source, target = "runtime-1", "runtime-2"
                    elif mutation == "broken_selected_to_utterance_main_path":
                        source, target = "runtime-4", "runtime-5"
                    else:
                        source, target = "runtime-6", "runtime-7"
                    self.assertEqual(len(rows), 8)
                    edge = next(edge for edge in mutated["edges"]
                                if edge["source"] == source and edge["target"] == target
                                and edge["class"] == "is-main")
                    edge["class"] = "not-main"
                elif mutation == "fake_write_edge":
                    fake = deepcopy(mutated["nodes"][-1])
                    fake.update({
                        "id": "write-0", "kind": "write", "label": "episodic_memory",
                        "trace_id": "write:0:episodic_memory", "write": True,
                    })
                    mutated["nodes"].append(fake)
                    mutated["edges"].append({
                        "source": "turn-output", "target": "write-0", "class": "is-active",
                    })
                elif mutation == "wrong_kind_write_node":
                    _anchor(mutated, "episodic_memory")["kind"] = "memory"
                else:
                    self.fail(f"Unhandled frozen mutation: {mutation}")
                before_result, before_graph = deepcopy(result), deepcopy(mutated)
                focus = observatory._verified_d_main_chain_focus_p4(result, mutated)
                if mutation in main_failures:
                    self.assertIsNone(focus)
                else:
                    self.assertIsNotNone(focus)
                    self.assertEqual(focus["write_status"], "not_in_focus")
                    self.assertEqual(len(focus["anchors"]), 5)
                    self.assertEqual(len(focus["segments"]), 4)
                    self.assertFalse(any(segment["edge_class"] == "is-active"
                                         for segment in focus["segments"]))
                self.assertEqual(result, before_result)
                self.assertEqual(mutated, before_graph)

    def test_missing_or_duplicate_trace_write_does_not_make_a_focus_arrow(self):
        for mutation in ("missing_edge", "duplicate_report", "duplicate_other_kind"):
            with self.subTest(mutation=mutation):
                result = _d_turn("f1", with_write=True)
                original = observatory.collect_cognitive_graph(result)
                if mutation == "missing_edge":
                    original["edges"] = [edge for edge in original["edges"]
                                         if not (edge["source"] == "turn-output"
                                                 and edge["target"] == "write-0"
                                                 and edge["class"] == "is-active")]
                else:
                    duplicate = deepcopy(result["runtime_trace"]["memory_writes"][0])
                    if mutation == "duplicate_other_kind":
                        duplicate["kind"] = "other_episodic_write"
                    result["runtime_trace"]["memory_writes"].append(duplicate)
                focus = observatory._verified_d_main_chain_focus_p4(result, original)
                self.assertIsNotNone(focus)
                self.assertEqual(focus["write_status"], "not_in_focus")
                self.assertEqual(len(focus["anchors"]), 5)

    def test_added_focus_markup_stays_within_frozen_html_delta_target(self):
        result = _d_turn("f0", with_write=True)
        with patch.object(observatory, "_verified_d_main_chain_focus_p4", return_value=None):
            without_focus = observatory.render_memory_observatory(result)
        with_focus = observatory.render_memory_observatory(result)
        delta = len(with_focus.encode("utf-8")) - len(without_focus.encode("utf-8"))
        self.assertGreater(delta, 0)
        self.assertLessEqual(delta, 15_000)
