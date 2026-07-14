import json
import unittest

from memory_highlight_span_contract import (
    annotate_highlights,
    build_controller_contract,
    build_span_binding_json_schema,
    build_span_binding_prompt,
    parse_span_binding,
    render_span_contract,
    required_slots,
    source_records_from_ledger,
    strip_highlight_tags,
    validate_span_binding,
)


class MemoryHighlightSpanContractTest(unittest.TestCase):
    def test_highlights_are_reversible_and_do_not_remove_context(self):
        source = (
            "User: First line\ncontinued detail\n"
            "Assistant: Reply\n"
            "User: Last line"
        )
        selected = [
            {"turn_index": 0, "attention_rank": 1},
            {"turn_index": 2, "attention_rank": 2},
        ]

        highlighted = annotate_highlights(source, selected)

        self.assertIn(
            'User: <memory-highlight rank="1">First line\ncontinued detail</memory-highlight>',
            highlighted,
        )
        self.assertIn(
            'User: <memory-highlight rank="2">Last line</memory-highlight>',
            highlighted,
        )
        self.assertIn("Assistant: Reply", highlighted)
        self.assertEqual(strip_highlight_tags(highlighted), source)

    def test_highlighter_rejects_assistant_and_duplicate_turns(self):
        source = "User: One\nAssistant: Two"
        with self.assertRaisesRegex(ValueError, "only user turns"):
            annotate_highlights(source, [{"turn_index": 1, "attention_rank": 1}])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            annotate_highlights(
                source,
                [
                    {"turn_index": 0, "attention_rank": 1},
                    {"turn_index": 0, "attention_rank": 2},
                ],
            )

    def test_empty_user_turn_keeps_valid_tag_order_and_exact_restoration(self):
        source = "User: \nAssistant: Reply"
        highlighted = annotate_highlights(
            source, [{"turn_index": 0, "attention_rank": 1}]
        )

        self.assertIn('<memory-highlight rank="1"></memory-highlight>', highlighted)
        self.assertEqual(strip_highlight_tags(highlighted), source)

    def test_controller_derives_slots_without_model_choice(self):
        self.assertEqual(required_slots({"time_focus": "current"}), ("current",))
        self.assertEqual(required_slots({"time_focus": "previous"}), ("previous",))
        self.assertEqual(
            required_slots({"time_focus": "change_direction", "operation": "compare"}),
            ("before", "current"),
        )
        self.assertEqual(
            required_slots({"time_focus": "specific_time", "operation": "yes_no"}),
            ("support",),
        )
        contract = build_controller_contract(
            {
                "time_focus": "change_direction",
                "operation": "compare",
                "answer_type": "direction with before and after values",
            }
        )
        self.assertEqual(contract["answer_type"], "compare")
        self.assertEqual(contract["required_slots"], ["before", "current"])
        self.assertEqual(contract["relation_mode"], "controller_derives_from_numeric_spans")

    def test_dynamic_schema_requires_exact_controller_slot_count(self):
        frame = {
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
        }
        schema = build_span_binding_json_schema(frame)
        bindings = schema["properties"]["bindings"]
        self.assertEqual((bindings["minItems"], bindings["maxItems"]), (2, 2))
        self.assertEqual(bindings["items"]["properties"]["slot"]["enum"], ["before", "current"])
        self.assertEqual(schema["properties"]["polarity"]["enum"], ["none"])

    def test_source_records_keep_grounded_provenance_and_deduplicate(self):
        event = {
            "date": "2026-07-13",
            "session_id": "s1",
            "source_role": "user",
            "source_quote": "There were four before, and there are seven now.",
            "attribute": "weekly study duration",
        }
        records = source_records_from_ledger({"events": [event, event]})

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_index"], 0)
        self.assertEqual(records[0]["source_quote"], event["source_quote"])

    def test_compare_can_bind_two_slots_to_one_quote_and_derives_relation(self):
        frame = {
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
        }
        records = [
            {
                "source_index": 0,
                "date": "2026-07-13",
                "session_id": "s1",
                "source_role": "user",
                "source_quote": (
                    "I used to study four hours per week; now I study seven hours per week."
                ),
                "attribute": "weekly study duration",
            }
        ]
        parsed = parse_span_binding(
            json.dumps(
                {
                    "bindings": [
                        {
                            "slot": "before",
                            "source_index": 0,
                            "answer_span": "four hours per week",
                        },
                        {
                            "slot": "current",
                            "source_index": 0,
                            "answer_span": "seven hours per week",
                        },
                    ],
                    "polarity": "none",
                }
            )
        )
        validation = validate_span_binding(parsed, records, frame)

        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(validation["contract"]["relation"], "increase")
        self.assertTrue(validation["audits"]["slot_complete"])
        self.assertTrue(validation["audits"]["all_spans_grounded"])
        self.assertEqual(
            render_span_contract(validation),
            "four hours per week -> seven hours per week; increase.",
        )

    def test_no_answer_requires_explicit_grounded_negation(self):
        frame = {
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with a concise supporting fact",
        }
        records = [
            {
                "source_index": 0,
                "date": "2026-07-13",
                "session_id": "s1",
                "source_role": "user",
                "source_quote": "I definitely did not own a bird.",
                "attribute": "pet ownership",
            }
        ]
        payload = {
            "bindings": [
                {"slot": "support", "source_index": 0, "answer_span": "did not own a bird"}
            ],
            "polarity": "no",
        }
        validation = validate_span_binding(payload, records, frame)

        self.assertTrue(validation["valid"], validation["errors"])
        self.assertEqual(render_span_contract(validation), "No - did not own a bird.")

        payload["bindings"][0]["answer_span"] = "bird"
        invalid = validate_span_binding(payload, records, frame)
        self.assertFalse(invalid["valid"])
        self.assertIn("no_polarity_without_grounded_negation", invalid["errors"])

        false_yes = validate_span_binding(
            {
                "bindings": [
                    {"slot": "support", "source_index": 0, "answer_span": "bird"}
                ],
                "polarity": "yes",
            },
            records,
            frame,
        )
        self.assertFalse(false_yes["valid"])
        self.assertIn(
            "yes_polarity_conflicts_with_grounded_negation", false_yes["errors"]
        )

    def test_validation_rejects_missing_slot_unknown_source_and_ungrounded_span(self):
        frame = {
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
        }
        records = [
            {
                "source_index": 0,
                "source_quote": "It changed from six hours to two hours.",
            }
        ]
        missing = validate_span_binding(
            {
                "bindings": [
                    {"slot": "current", "source_index": 0, "answer_span": "two hours"}
                ],
                "polarity": "none",
            },
            records,
            frame,
        )
        self.assertFalse(missing["valid"])
        self.assertIn("missing_slots:before", missing["errors"])

        invalid = validate_span_binding(
            {
                "bindings": [
                    {"slot": "before", "source_index": 4, "answer_span": "six hours"},
                    {"slot": "current", "source_index": 0, "answer_span": "nine hours"},
                ],
                "polarity": "none",
            },
            records,
            frame,
        )
        self.assertFalse(invalid["valid"])
        self.assertIn("source_index_out_of_range", invalid["errors"])
        self.assertIn("answer_span_not_grounded", invalid["errors"])

    def test_binding_prompt_contains_sources_but_no_gold_channel(self):
        frame = {
            "subject": "reusable water bottles",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
        }
        records = [
            {
                "source_index": 0,
                "source_quote": "There used to be five, but I have nine now.",
            }
        ]
        prompt = build_span_binding_prompt(
            "How many reusable water bottles do I have now?",
            "2026-07-14",
            records,
            frame,
        )

        self.assertIn('"required_slots": ["current"]', prompt)
        self.assertIn("There used to be five, but I have nine now.", prompt)
        self.assertNotIn("correct answer", prompt.lower())
        self.assertNotIn("expected relation", prompt.lower())


if __name__ == "__main__":
    unittest.main()
