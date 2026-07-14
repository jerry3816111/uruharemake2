import json
import unittest
from pathlib import Path

from memory_evidence_ledger import focused_user_utterances
from memory_utterance_attention import (
    PROPOSITION_SCHEMA,
    build_answer_proposition_prompt,
    parse_answer_proposition,
    parse_dialogue_turns,
    rank_user_utterances,
    render_answer_proposition,
    render_attention_context,
    validate_answer_proposition,
)


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "memory_utterance_attention_v1.json"


class MemoryUtteranceAttentionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_dialogue_parser_preserves_roles_order_and_continuations(self):
        turns = parse_dialogue_turns(
            "User: First line\ncontinued detail\nAssistant: Reply\nUser: Last line"
        )
        self.assertEqual(
            turns,
            [
                {"turn_index": 0, "role": "user", "text": "First line\ncontinued detail"},
                {"turn_index": 1, "role": "assistant", "text": "Reply"},
                {"turn_index": 2, "role": "user", "text": "Last line"},
            ],
        )

    def test_query_attention_recalls_all_frozen_evidence_without_gold_input(self):
        old_hits = 0
        new_hits = 0
        total = 0
        for case in self.payload["cases"]:
            baseline = focused_user_utterances(
                case["question"],
                case["question_frame"],
                case["session"]["text"],
                limit=4,
            )
            selected = rank_user_utterances(
                case["question"],
                case["question_frame"],
                case["session"]["text"],
                limit=4,
            )
            focused = render_attention_context(selected)
            gold_quotes = case["gold"]["attention_quotes"]
            old_hits += sum(quote in baseline for quote in gold_quotes)
            new_hits += sum(quote in focused for quote in gold_quotes)
            total += len(gold_quotes)
            self.assertTrue(
                all(row["text"] in gold_quotes for row in selected), case["case_id"]
            )

        self.assertEqual((new_hits, total), (72, 72))
        self.assertLess(old_hits, new_hits)

    def test_attention_is_position_invariant_on_matched_scenarios(self):
        selected_by_scenario = {}
        for case in self.payload["cases"]:
            selected = rank_user_utterances(
                case["question"],
                case["question_frame"],
                case["session"]["text"],
                limit=4,
            )
            selected_by_scenario.setdefault(case["scenario_id"], set()).add(
                tuple(row["text"] for row in selected)
            )
        for scenario_id, variants in selected_by_scenario.items():
            self.assertEqual(len(variants), 1, scenario_id)

    def test_valid_proposition_is_grounded_and_rendered_without_answer_loss(self):
        quote = "I had a road bike in addition to my commuter bike."
        view = {
            "target_events": [
                {
                    "evidence_role": "earlier_state",
                    "source_quote": quote,
                }
            ]
        }
        frame = {
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with a concise supporting fact",
        }
        proposition = {
            "schema": PROPOSITION_SCHEMA,
            "answer_type": "yes_no",
            "relation": "yes",
            "claims": [
                {
                    "target_index": 0,
                    "answer_span": "road bike",
                }
            ],
        }
        parsed = parse_answer_proposition(json.dumps(proposition))
        validated = validate_answer_proposition(parsed, view, frame)

        self.assertTrue(validated["valid"])
        self.assertEqual(render_answer_proposition(validated), "Yes — road bike.")

    def test_proposition_rejects_ungrounded_span(self):
        view = {
            "target_events": [
                {"evidence_role": "current", "source_quote": "It is in the cedar drawer."}
            ]
        }
        frame = {"time_focus": "current", "operation": "locate", "answer_type": "location"}
        proposition = {
            "schema": PROPOSITION_SCHEMA,
            "answer_type": "location",
            "relation": "none",
            "claims": [
                {
                    "target_index": 0,
                    "answer_span": "metal cabinet",
                }
            ],
        }
        validated = validate_answer_proposition(proposition, view, frame)

        self.assertFalse(validated["valid"])
        self.assertIn("answer_span_not_grounded", validated["errors"])
        self.assertEqual(render_answer_proposition(validated), "")

    def test_comparison_requires_before_and_current_roles(self):
        view = {
            "target_events": [
                {"evidence_role": "before", "source_quote": "It took fifty minutes."},
                {"evidence_role": "current", "source_quote": "It takes thirty-five minutes."},
            ]
        }
        frame = {
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
        }
        proposition = {
            "schema": PROPOSITION_SCHEMA,
            "answer_type": "compare",
            "relation": "decrease",
            "claims": [
                {
                    "target_index": 1,
                    "answer_span": "thirty-five minutes",
                }
            ],
        }

        validated = validate_answer_proposition(proposition, view, frame)
        self.assertFalse(validated["valid"])
        self.assertIn("missing_roles:before", validated["errors"])

    def test_proposition_rejects_unknown_target_index(self):
        view = {
            "target_events": [
                {"evidence_role": "current", "source_quote": "There are eleven now."}
            ]
        }
        frame = {"time_focus": "current", "operation": "count", "answer_type": "number"}
        proposition = {
            "schema": PROPOSITION_SCHEMA,
            "answer_type": "count",
            "relation": "none",
            "claims": [{"target_index": 4, "answer_span": "eleven"}],
        }

        validated = validate_answer_proposition(proposition, view, frame)
        self.assertFalse(validated["valid"])
        self.assertIn("target_index_out_of_range", validated["errors"])

    def test_proposition_prompt_contains_evidence_but_has_no_gold_channel(self):
        view = {
            "target_events": [
                {"evidence_role": "current", "source_quote": "There are eleven now."}
            ]
        }
        frame = {"time_focus": "current", "operation": "count", "answer_type": "number"}
        prompt = build_answer_proposition_prompt(
            "How many plants do I have?", "2026-07-14", view, frame
        )

        self.assertIn("There are eleven now.", prompt)
        self.assertIn("Required answer_type: count", prompt)
        self.assertNotIn("correct answer", prompt.lower())


if __name__ == "__main__":
    unittest.main()
