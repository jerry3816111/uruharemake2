import unittest
import json

from memory_evidence_ledger import (
    LEDGER_SCHEMA,
    align_fact_to_source,
    align_quote_to_source,
    build_direct_answer_prompt,
    build_evidence_note_prompt,
    build_focused_evidence_note_prompt,
    build_ledger_answer_prompt,
    build_ledger_prompt,
    build_question_frame_prompt,
    chronological_sessions,
    augment_question_frame,
    audit_question_frame,
    evidence_quotes_are_grounded,
    filter_grounded_evidence,
    focused_user_utterances,
    ground_ledger_events,
    ledger_answer_view,
    ledger_derived_numeric_conflicts,
    ledger_events_are_grounded,
    parse_evidence_note,
    parse_ledger,
    parse_question_frame,
    reconcile_ledger_state,
    strict_answer_support,
)


FRAME = {
    "subject": "the user",
    "attribute": "bike count",
    "time_focus": "current",
    "operation": "count",
    "answer_type": "number",
    "evidence_requirements": ["explicit bike ownership count from past chats"],
}
FACT = {
    "source_role": "user",
    "quote": "I now own four bikes.",
    "attribute": "bike count",
}
NOTE = {
    "session_id": "s1",
    "timestamp": "2024-01-01",
    "evidence": {"relevant": True, "facts": [FACT]},
    "structured_parse_ok": True,
}


class MemoryEvidenceLedgerTest(unittest.TestCase):
    def test_sessions_are_chronological_without_mutating_input(self):
        sessions = [
            {"timestamp": "2024-02-01", "text": "new"},
            {"timestamp": "2024-01-01", "text": "old"},
        ]

        ordered = chronological_sessions(sessions)

        self.assertEqual([row["text"] for row in ordered], ["old", "new"])
        self.assertEqual(sessions[0]["text"], "new")

    def test_generation_prompts_never_require_or_accept_a_gold_answer(self):
        session = {"timestamp": "2024-01-01", "text": "User: I now own four bikes."}
        evidence_prompt = build_evidence_note_prompt(
            "How many bikes?", "2024-02-01", FRAME, session
        )
        prompts = [
            build_direct_answer_prompt("How many bikes?", "2024-02-01", [session]),
            build_question_frame_prompt("How many bikes?", "2024-02-01"),
            evidence_prompt,
            build_ledger_prompt(
                "How many bikes?",
                "2024-02-01",
                FRAME,
                [NOTE],
            ),
        ]

        for prompt in prompts:
            self.assertNotIn("Correct Answer", prompt)
            self.assertNotIn("gold", prompt.lower())
        self.assertLess(
            evidence_prompt.index("User-Utterance Index"),
            evidence_prompt.index("Session Content"),
        )

    def test_ledger_prompt_distinguishes_updates_from_cumulative_events(self):
        prompt = build_ledger_prompt(
            "How many bikes?",
            "2024-02-01",
            FRAME,
            [NOTE],
        )

        self.assertIn("cumulative_total", prompt)
        self.assertIn("incremental events", prompt)
        self.assertIn("updates an earlier value", prompt)
        self.assertIn("user correction", prompt)

    def test_structured_question_frame_and_note_are_validated(self):
        self.assertEqual(parse_question_frame(json.dumps(FRAME)), FRAME)
        evidence = {"relevant": True, "facts": [FACT]}
        self.assertEqual(parse_evidence_note(json.dumps(evidence)), evidence)
        self.assertIsNone(parse_evidence_note('{"relevant":false,"facts":[{}]}'))

    def test_previous_frame_requires_both_dated_states(self):
        frame = {**FRAME, "time_focus": "previous", "evidence_requirements": []}

        augmented = augment_question_frame(frame)

        self.assertIn("later/current", augmented["evidence_requirements"][0])
        self.assertEqual(frame["evidence_requirements"], [])

    def test_temporal_audit_separates_previous_state_from_past_window_total(self):
        crash = audit_question_frame(
            "How many videos have I watched in the past few weeks?",
            {**FRAME, "time_focus": "previous"},
        )
        united = audit_question_frame(
            "What was my previous status before I got the current status?",
            {**FRAME, "time_focus": "current", "operation": "lookup"},
        )
        possession = audit_question_frame(
            "Do I have a spare screwdriver?",
            {**FRAME, "time_focus": "unspecified", "operation": "yes_no"},
        )
        bounded_possession = audit_question_frame(
            "Before I purchased the gravel bike, do I have another road bike?",
            {**FRAME, "time_focus": "current", "operation": "yes_no"},
        )
        before_and_now = audit_question_frame(
            "How often did I play previously? How often do I play now?",
            {**FRAME, "time_focus": "previous", "operation": "lookup"},
        )
        direction = audit_question_frame(
            "Did I most recently increase or decrease my coffee limit?",
            {**FRAME, "time_focus": "current", "operation": "lookup"},
        )
        completion = audit_question_frame(
            "Did I finish reading the book?",
            {**FRAME, "time_focus": "specific_time", "operation": "lookup"},
        )

        self.assertEqual(crash["time_focus"], "historical_total")
        self.assertEqual(united["time_focus"], "previous")
        self.assertEqual(possession["time_focus"], "current")
        self.assertEqual(bounded_possession["time_focus"], "specific_time")
        self.assertEqual(bounded_possession["operation"], "yes_no")
        self.assertEqual(before_and_now["time_focus"], "change_direction")
        self.assertEqual(before_and_now["operation"], "compare")
        self.assertEqual(direction["time_focus"], "change_direction")
        self.assertEqual(direction["operation"], "compare")
        self.assertEqual(direction["attribute"], "my coffee limit")
        self.assertEqual(completion["time_focus"], "current")
        self.assertEqual(completion["operation"], "yes_no")

    def test_parse_ledger_accepts_fenced_json_and_rejects_wrong_schema(self):
        valid = (
            "```json\n"
            f'{{"schema":"{LEDGER_SCHEMA}","events":[],"current_event_indices":[],"superseded_event_indices":[],"historical_event_indices":[],"uncertainties":[]}}'
            "\n```"
        )

        self.assertEqual(parse_ledger(valid)["schema"], LEDGER_SCHEMA)
        self.assertIsNone(parse_ledger(valid.replace(LEDGER_SCHEMA, "wrong")))

    def test_parse_ledger_rejects_non_scalar_event_fields_without_crashing(self):
        malformed = (
            f'{{"schema":"{LEDGER_SCHEMA}",'
            '"events":[{"date":["2024-01-01"],"session_id":"s1",'
            '"source_role":"user","source_quote":"I own four bikes.",'
            '"attribute":"bike count","claim":"four bikes","value":"four","value_role":"state",'
            '"relation":"updates"}],"current_event_indices":[0],"superseded_event_indices":[],'
            '"historical_event_indices":[],"uncertainties":[]}'
        )

        self.assertIsNone(parse_ledger(malformed))

    def test_parse_ledger_rejects_speaker_as_value_role(self):
        invalid = (
            f'{{"schema":"{LEDGER_SCHEMA}","events":['
            '{"date":"2024-01-01","session_id":"s1","attribute":"status",'
            '"source_role":"user","source_quote":"I reached Silver.",'
            '"claim":"Reached Silver","value":"Silver","value_role":"user",'
            '"relation":"adds"}],"current_event_indices":[0],"superseded_event_indices":[],'
            '"historical_event_indices":[],"uncertainties":[]}'
        )

        self.assertIsNone(parse_ledger(invalid))

    def test_parse_ledger_requires_coverage_and_current_superseded_exclusivity(self):
        ledger = {
            "schema": LEDGER_SCHEMA,
            "events": [
                {
                    "date": "2024-01-01",
                    "session_id": "s1",
                    "source_role": "user",
                    "source_quote": "I now own four bikes.",
                    "attribute": "bike count",
                    "claim": "owns four bikes",
                    "value": "four",
                    "value_role": "cumulative_total",
                    "relation": "adds",
                }
            ],
            "current_event_indices": [0],
            "superseded_event_indices": [],
            "historical_event_indices": [],
            "uncertainties": [],
        }

        self.assertIsNotNone(parse_ledger(json.dumps(ledger)))
        ledger["historical_event_indices"] = [0]
        self.assertIsNotNone(parse_ledger(json.dumps(ledger)))
        ledger["current_event_indices"] = []
        ledger["historical_event_indices"] = []
        self.assertIsNone(parse_ledger(json.dumps(ledger)))
        ledger["current_event_indices"] = [0]
        ledger["superseded_event_indices"] = [0]
        self.assertIsNone(parse_ledger(json.dumps(ledger)))

    def test_answer_view_excludes_superseded_state_from_current_questions(self):
        ledger = {
            "schema": LEDGER_SCHEMA,
            "events": [
                {
                    "date": "2024-02-01",
                    "source_role": "user",
                    "source_quote": "I now own four bikes.",
                    "value_role": "cumulative_total",
                },
                {
                    "date": "2024-01-01",
                    "source_role": "user",
                    "source_quote": "I owned three bikes.",
                    "value_role": "cumulative_total",
                },
            ],
            "current_event_indices": [0],
            "superseded_event_indices": [1],
            "historical_event_indices": [0, 1],
            "uncertainties": [],
        }

        prompt = build_ledger_answer_prompt(
            "How many bikes?", "2024-02-01", ledger, FRAME
        )
        previous_frame = {**FRAME, "time_focus": "previous"}
        previous_view = ledger_answer_view(ledger, previous_frame)

        self.assertIn("I now own four bikes.", prompt)
        self.assertNotIn("I owned three bikes.", prompt)
        self.assertEqual(
            previous_view["target_events"][0]["source_quote"],
            "I owned three bikes.",
        )

    def test_quote_and_ledger_provenance_must_match_source(self):
        evidence = {"relevant": True, "facts": [FACT]}
        self.assertTrue(
            evidence_quotes_are_grounded(evidence, "User: I now own four bikes.")
        )
        self.assertFalse(
            evidence_quotes_are_grounded(evidence, "User: I own three bikes.")
        )
        self.assertEqual(
            filter_grounded_evidence(evidence, "User: I own three bikes."),
            {"relevant": False, "facts": []},
        )
        ledger = {
            "events": [
                {
                    "date": "2024-01-01T00:00:00Z",
                    "session_id": NOTE["session_id"],
                    "source_role": FACT["source_role"],
                    "source_quote": FACT["quote"],
                    "attribute": FACT["attribute"],
                }
            ],
            "current_event_indices": [0],
            "superseded_event_indices": [],
            "historical_event_indices": [],
        }
        self.assertTrue(ledger_events_are_grounded(ledger, [NOTE]))
        grounded = ground_ledger_events(ledger, [NOTE])
        self.assertEqual(grounded["events"][0]["date"], NOTE["timestamp"])
        ledger["events"][0]["source_quote"] = "I own five bikes."
        self.assertFalse(ledger_events_are_grounded(ledger, [NOTE]))

    def test_quote_alignment_only_normalizes_quote_punctuation(self):
        source = 'User: I recently finished "The Nightingale" by Kristin Hannah.'
        extracted = "I recently finished 'The Nightingale' by Kristin Hannah."
        wrapped = '"I recently finished \'The Nightingale\' by Kristin Hannah."'

        self.assertEqual(
            align_quote_to_source(extracted, source),
            'I recently finished "The Nightingale" by Kristin Hannah.',
        )
        self.assertEqual(
            align_quote_to_source(wrapped, source),
            'I recently finished "The Nightingale" by Kristin Hannah.',
        )
        self.assertIsNone(
            align_quote_to_source("I finished a different novel.", source)
        )

    def test_fact_alignment_repairs_role_from_source_turn(self):
        source = "User: I reduced my coffee limit to one cup.\nAssistant: Good plan."

        alignment = align_fact_to_source(
            "I reduced my coffee limit to one cup.", source, "assistant"
        )
        grounded = filter_grounded_evidence(
            {
                "relevant": True,
                "facts": [
                    {
                        "source_role": "assistant",
                        "quote": "I reduced my coffee limit to one cup.",
                        "attribute": "coffee limit",
                    }
                ],
            },
            source,
        )

        self.assertTrue(alignment["role_repaired"])
        self.assertEqual(grounded["facts"][0]["source_role"], "user")

    def test_focused_user_turns_require_multiple_query_terms(self):
        session = (
            "User: I need new socks.\n"
            "Assistant: Try wool.\n"
            "User: My weekly tennis sessions with friends are at the local park."
        )
        frame = {**FRAME, "subject": "tennis", "attribute": "playing frequency"}

        focused = focused_user_utterances(
            "How often do I play tennis with friends at the local park?",
            frame,
            session,
        )

        self.assertIn("weekly tennis sessions", focused)
        self.assertNotIn("new socks", focused)
        prompt = build_focused_evidence_note_prompt(frame, focused)
        self.assertIn("incidental comparison, reminder", prompt)
        self.assertIn("recurring interval or cadence", prompt)
        self.assertNotIn("every other week", prompt)
        self.assertNotIn("How often", prompt)

    def test_focused_prompt_routes_scan_rule_by_attribute(self):
        location_prompt = build_focused_evidence_note_prompt(
            {"subject": "a painting", "attribute": "location"},
            "User: I left it above the sofa.",
        )
        count_prompt = build_focused_evidence_note_prompt(
            {"subject": "owned bikes", "attribute": "number_owned"},
            "User: I have three bikes.",
        )

        self.assertIn("physical placement or location", location_prompt)
        self.assertIn("explicit number or quantity", count_prompt)

    def test_ledger_grounding_repairs_quote_style_and_role_only(self):
        note = {
            "session_id": "s1",
            "timestamp": "2024-01-01",
            "evidence": {
                "relevant": True,
                "facts": [
                    {
                        "source_role": "user",
                        "quote": 'I finished "The Nightingale".',
                        "attribute": "completion",
                    }
                ],
            },
            "fact_source_offsets": [0],
        }
        ledger = {
            "events": [
                {
                    "date": "wrong",
                    "session_id": "s1",
                    "source_role": "assistant",
                    "source_quote": "I finished 'The Nightingale'.",
                    "attribute": "completion",
                }
            ],
            "current_event_indices": [0],
            "superseded_event_indices": [],
            "historical_event_indices": [0],
        }

        grounded = ground_ledger_events(ledger, [note])

        self.assertEqual(grounded["events"][0]["source_role"], "user")
        self.assertEqual(
            grounded["events"][0]["source_quote"],
            'I finished "The Nightingale".',
        )
        self.assertEqual(grounded["ledger_quote_alignment_repairs"], [0])
        self.assertEqual(grounded["ledger_role_alignment_repairs"], [0])

    def test_ledger_grounding_allows_reported_fact_omission(self):
        note = {
            "session_id": "s1",
            "timestamp": "2024-01-01",
            "evidence": {
                "relevant": True,
                "facts": [
                    {
                        "source_role": "user",
                        "quote": "I finished the book.",
                        "attribute": "completion",
                    },
                    {
                        "source_role": "user",
                        "quote": "It was emotional.",
                        "attribute": "completion",
                    },
                ],
            },
            "fact_source_offsets": [0, 30],
        }
        ledger = {
            "events": [
                {
                    "date": "wrong",
                    "session_id": "s1",
                    "source_role": "user",
                    "source_quote": "I finished the book.",
                    "attribute": "completion",
                }
            ],
            "current_event_indices": [0],
            "superseded_event_indices": [],
            "historical_event_indices": [0],
        }

        grounded = ground_ledger_events(ledger, [note])

        self.assertEqual(grounded["ledger_fact_coverage"], 0.5)
        self.assertEqual(len(grounded["omitted_grounded_facts"]), 1)
        self.assertEqual(
            grounded["omitted_grounded_facts"][0]["source_quote"],
            "It was emotional.",
        )

    def test_reconciliation_prefers_latest_user_state_over_assistant_claim(self):
        def event(date, role, value):
            return {
                "date": date,
                "source_role": role,
                "attribute": "gold threshold",
                "value_role": "threshold",
                "value": value,
            }

        ledger = {
            "events": [
                event("2023-07-11 00:07:00", "user", "125"),
                event("2023-07-30 02:08:00", "assistant", "300"),
                event("2023-07-30 02:08:00", "user", "120"),
            ],
            "current_event_indices": [1],
            "superseded_event_indices": [],
            "historical_event_indices": [0, 2],
        }

        reconciled = reconcile_ledger_state(ledger)

        self.assertEqual(reconciled["current_event_indices"], [2])
        self.assertEqual(reconciled["superseded_event_indices"], [0, 1])
        self.assertEqual(reconciled["historical_event_indices"], [0, 1, 2])

    def test_reconciliation_repairs_non_additive_increment_label(self):
        ledger = {
            "events": [
                {
                    "date": "2024-01-01",
                    "source_role": "user",
                    "attribute": "attempt count",
                    "value_role": "incremental_event",
                    "relation": "updates",
                }
            ],
            "current_event_indices": [0],
            "superseded_event_indices": [],
            "historical_event_indices": [0],
        }

        reconciled = reconcile_ledger_state(ledger)

        self.assertEqual(reconciled["events"][0]["value_role"], "cumulative_total")
        self.assertEqual(
            reconciled["semantic_repairs"][0]["reason"],
            "updates_relation_is_non_additive",
        )

    def test_historical_total_sums_only_explicit_additions(self):
        ledger = {
            "events": [
                {
                    "date": "2024-01-01",
                    "source_role": "user",
                    "source_quote": "I attended one meetup.",
                    "value_role": "incremental_event",
                    "relation": "adds",
                },
                {
                    "date": "2024-02-01",
                    "source_role": "user",
                    "source_quote": "I mentioned that same meetup again.",
                    "value_role": "incremental_event",
                    "relation": "confirms",
                },
            ],
            "current_event_indices": [],
            "superseded_event_indices": [],
            "historical_event_indices": [0, 1],
            "uncertainties": [],
        }
        frame = {**FRAME, "time_focus": "historical_total", "operation": "aggregate"}

        view = ledger_answer_view(ledger, frame)

        self.assertEqual(
            [event["source_quote"] for event in view["target_events"]],
            ["I attended one meetup."],
        )
        self.assertEqual(view["target_events"][0]["evidence_role"], "distinct_increment")

    def test_change_view_labels_before_and_current_evidence(self):
        ledger = {
            "events": [
                {
                    "date": "2024-01-01",
                    "source_role": "user",
                    "source_quote": "I play weekly.",
                    "attribute": "tennis frequency",
                    "value_role": "frequency",
                },
                {
                    "date": "2024-02-01",
                    "source_role": "user",
                    "source_quote": "I now play every other week.",
                    "attribute": "tennis frequency",
                    "value_role": "frequency",
                },
            ],
            "current_event_indices": [1],
            "superseded_event_indices": [0],
            "historical_event_indices": [0, 1],
            "uncertainties": [],
        }
        frame = {**FRAME, "time_focus": "change_direction", "operation": "compare"}

        view = ledger_answer_view(ledger, frame)

        self.assertEqual(
            [event["evidence_role"] for event in view["target_events"]],
            ["before", "current"],
        )

    def test_change_view_prefers_numeric_endpoints_over_irrelevant_state(self):
        ledger = {
            "events": [
                {
                    "date": "2024-01-01",
                    "source_role": "user",
                    "source_quote": "I used a French press.",
                    "attribute": "coffee limit",
                },
                {
                    "date": "2024-01-01",
                    "source_role": "user",
                    "source_quote": "I limited myself to one cup.",
                    "attribute": "coffee limit",
                },
                {
                    "date": "2024-02-01",
                    "source_role": "user",
                    "source_quote": "I increased the limit to two cups.",
                    "attribute": "coffee limit",
                },
            ],
            "current_event_indices": [2],
            "superseded_event_indices": [0, 1],
            "historical_event_indices": [0, 1, 2],
            "uncertainties": [],
        }
        frame = {**FRAME, "time_focus": "change_direction", "operation": "compare"}

        view = ledger_answer_view(ledger, frame)

        self.assertEqual(
            [event["source_quote"] for event in view["target_events"]],
            ["I limited myself to one cup.", "I increased the limit to two cups."],
        )

    def test_answer_view_quarantines_unsupported_derived_numbers(self):
        ledger = {
            "events": [
                {
                    "date": "2024-01-01",
                    "session_id": "s1",
                    "source_role": "user",
                    "source_quote": "I currently own four bikes.",
                    "attribute": "bike quantity",
                    "claim": "six bikes",
                    "value": "six",
                    "value_role": "cumulative_total",
                    "relation": "updates",
                }
            ],
            "current_event_indices": [0],
            "superseded_event_indices": [],
            "historical_event_indices": [0],
            "uncertainties": [],
        }

        conflicts = ledger_derived_numeric_conflicts(ledger)
        view = ledger_answer_view(ledger, FRAME)
        prompt = build_ledger_answer_prompt(
            "How many bikes do I own?", "2024-02-01", ledger, FRAME
        )

        self.assertEqual(conflicts[0]["unsupported_derived_numbers"], ["6"])
        self.assertNotIn("claim", view["target_events"][0])
        self.assertNotIn("value", view["target_events"][0])
        self.assertIn("four bikes", prompt)
        self.assertNotIn("six bikes", prompt)

    def test_answer_view_exposes_only_verbatim_source_anchored_claims(self):
        ledger = {
            "events": [
                {
                    "date": "2024-01-01",
                    "session_id": "s1",
                    "source_role": "user",
                    "source_quote": "I used to play weekly with friends.",
                    "attribute": "frequency",
                    "claim": "weekly",
                },
                {
                    "date": "2024-02-01",
                    "session_id": "s2",
                    "source_role": "user",
                    "source_quote": "Now we play every other week.",
                    "attribute": "frequency",
                    "claim": "every week",
                },
            ],
            "current_event_indices": [1],
            "superseded_event_indices": [0],
            "historical_event_indices": [0, 1],
            "uncertainties": [],
        }
        frame = {**FRAME, "time_focus": "change_direction", "operation": "compare"}

        view = ledger_answer_view(ledger, frame)
        prompt = build_ledger_answer_prompt("How often before and now?", "2024-03-01", ledger, frame)

        self.assertEqual(view["target_events"][0]["source_anchored_claim"], "weekly")
        self.assertNotIn("source_anchored_claim", view["target_events"][1])
        self.assertIn("preserve it exactly", prompt)
        self.assertIn("explicitly state the before value", prompt)

    def test_strict_answer_support_normalizes_numbers_and_pronouns(self):
        self.assertTrue(strict_answer_support("four", "You currently own 4 bikes."))
        self.assertTrue(strict_answer_support("in my bedroom", "It is in your bedroom."))
        self.assertTrue(strict_answer_support("in my bedroom", "It is in the bedroom."))
        self.assertFalse(strict_answer_support("five", "You currently own four bikes."))
        self.assertTrue(strict_answer_support("We've met up twice.", "2", "How many times?"))
        self.assertTrue(
            strict_answer_support(
                "We've met up twice.",
                "You have met up with Alex from Germany twice.",
                "How many times have I met up with Alex?",
            )
        )
        self.assertTrue(
            strict_answer_support(
                "We've met up twice.",
                "The current cumulative total of meetings with Alex is 2 times.",
                "How many times have I met up with Alex?",
            )
        )
        self.assertFalse(
            strict_answer_support(
                "Premier Silver",
                "The previous status is not specified; current status is Premier Silver.",
            )
        )

    def test_strict_answer_support_requires_every_frequency_endpoint(self):
        gold = (
            "Previously, you played tennis with friends at the local park every week on Sunday. "
            "Currently, you play tennis every other week on Sunday."
        )
        question = "How often previously, and how often now?"

        self.assertTrue(
            strict_answer_support(
                gold,
                "Previously weekly; now every other week.",
                question,
            )
        )
        self.assertFalse(
            strict_answer_support(
                gold,
                "The schedule remains weekly.",
                question,
            )
        )


if __name__ == "__main__":
    unittest.main()
