import unittest

from memory_evidence_ledger import LEDGER_SCHEMA
from memory_provenance_reread import (
    evaluate_evidence_sufficiency,
    explicit_abstention_detected,
    filter_ledger_to_authoritative_user,
    filter_note_to_authoritative_user,
    ledger_source_audit,
    merge_authoritative_ledgers,
    sanitize_extracted_evidence,
)


def event(quote, role="user", attribute="memory", value_role="other"):
    return {
        "date": "2026-07-13 18:00:00",
        "session_id": "s1",
        "source_role": role,
        "source_quote": quote,
        "attribute": attribute,
        "claim": quote,
        "value": quote,
        "value_role": value_role,
        "relation": "adds",
    }


def ledger(*events):
    return {
        "schema": LEDGER_SCHEMA,
        "events": list(events),
        "current_event_indices": list(range(len(events))),
        "superseded_event_indices": [],
        "historical_event_indices": list(range(len(events))),
        "uncertainties": [],
    }


class MemoryProvenanceRereadTest(unittest.TestCase):
    def test_controller_markup_is_repaired_only_when_exactly_source_grounded(self):
        source = (
            "User: I keep them in the bottom pantry drawer now.\n"
            "Assistant: Thanks for correcting me."
        )
        evidence = {
            "relevant": True,
            "facts": [
                {
                    "source_role": "user",
                    "quote": (
                        '<memory-highlight rank="1">I keep them in the bottom pantry '
                        "drawer now.</memory-highlight>"
                    ),
                    "attribute": "storage location",
                },
                {
                    "source_role": "user",
                    "quote": '<memory-highlight rank="x">invented location</memory-highlight>',
                    "attribute": "storage location",
                },
            ],
        }
        result = sanitize_extracted_evidence(evidence, source)
        self.assertEqual(
            result["evidence"]["facts"][0]["quote"],
            "I keep them in the bottom pantry drawer now.",
        )
        self.assertEqual(result["audit"]["markup_repair_attempt_count"], 2)
        self.assertEqual(result["audit"]["markup_repair_success_count"], 1)
        self.assertFalse(result["audit"]["all_markup_repairs_grounded"])
        self.assertEqual(result["audit"]["dropped_fact_count"], 1)

    def test_role_alignment_prevents_assistant_guess_from_becoming_user_memory(self):
        source = (
            "User: I have not decided where to keep them.\n"
            "Assistant: The bedroom drawer would make sense."
        )
        extracted = sanitize_extracted_evidence(
            {
                "relevant": True,
                "facts": [
                    {
                        "source_role": "user",
                        "quote": "The bedroom drawer would make sense.",
                        "attribute": "storage location",
                    }
                ],
            },
            source,
        )
        self.assertEqual(extracted["evidence"]["facts"][0]["source_role"], "assistant")
        note = filter_note_to_authoritative_user(
            {"schema_parse_ok": True, "evidence": extracted["evidence"]}
        )
        self.assertEqual(note["evidence"], {"relevant": False, "facts": []})

    def test_user_ledger_projection_remaps_indices_and_excludes_assistant(self):
        mixed = ledger(
            event("Assistant guess.", role="assistant", value_role="location"),
            event("I keep it in the blue case.", value_role="location"),
        )
        mixed["current_event_indices"] = [1]
        mixed["superseded_event_indices"] = [0]
        projected = filter_ledger_to_authoritative_user(mixed)
        self.assertEqual(len(projected["events"]), 1)
        self.assertEqual(projected["events"][0]["source_role"], "user")
        self.assertEqual(projected["current_event_indices"], [0])
        self.assertEqual(projected["historical_event_indices"], [0])
        self.assertEqual(ledger_source_audit(projected)["assistant_event_count"], 0)

    def test_merge_deduplicates_user_provenance(self):
        first = ledger(event("I own seven notebooks.", attribute="count"))
        second = ledger(
            event("I own seven notebooks.", attribute="count"),
            event("I keep them in a cabinet.", attribute="location"),
        )
        merged = merge_authoritative_ledgers(first, second)
        self.assertEqual(len(merged["events"]), 2)
        self.assertTrue(merged["merge_audit"]["all_events_user_source"])

    def test_generic_gate_accepts_each_supported_answer_shape(self):
        examples = (
            (
                "No. It was at 2:20 PM, but the confirmed time is 5:10 PM now.",
                {"operation": "lookup", "answer_type": "time", "attribute": "appointment time"},
            ),
            (
                "I have eight ceramic mugs now.",
                {"operation": "count", "answer_type": "number", "attribute": "current count"},
            ),
            (
                "Before the change, I practiced every evening.",
                {"operation": "lookup", "answer_type": "frequency", "attribute": "frequency"},
            ),
            (
                "I keep them in the bottom pantry drawer now.",
                {"operation": "locate", "answer_type": "location", "attribute": "location"},
            ),
            (
                "Before the harp, I already owned a violin.",
                {"operation": "yes_no", "answer_type": "yes/no", "attribute": "ownership"},
            ),
            (
                "It used to take twenty-five minutes, and now it takes forty minutes.",
                {
                    "operation": "compare",
                    "time_focus": "change_direction",
                    "answer_type": "direction with values",
                    "attribute": "duration",
                },
            ),
        )
        for quote, frame in examples:
            with self.subTest(quote=quote):
                result = evaluate_evidence_sufficiency(ledger(event(quote)), frame)
                self.assertTrue(result["sufficient"], result)
                self.assertFalse(result["gold_used"])

    def test_generic_gate_rejects_assistant_only_and_pure_uncertainty(self):
        count_frame = {
            "operation": "count",
            "answer_type": "number",
            "attribute": "current count",
        }
        assistant_only = evaluate_evidence_sufficiency(
            ledger(event("There might be twelve.", role="assistant")), count_frame
        )
        self.assertFalse(assistant_only["sufficient"])
        uncertain = evaluate_evidence_sufficiency(
            ledger(event("Twelve is your estimate; I do not know the current count.")),
            count_frame,
        )
        self.assertFalse(uncertain["sufficient"])
        self.assertEqual(uncertain["reason"], "only_uncertain_user_evidence")

    def test_correction_can_contain_a_rejected_guess_and_valid_user_fact(self):
        frame = {
            "operation": "locate",
            "answer_type": "location",
            "attribute": "storage location",
        }
        result = evaluate_evidence_sufficiency(
            ledger(
                event(
                    "No, that was only your guess. I keep them in the bottom pantry drawer now."
                )
            ),
            frame,
        )
        self.assertTrue(result["sufficient"], result)
        self.assertEqual(len(result["uncertain_segments"]), 1)
        self.assertEqual(len(result["eligible_segments"]), 1)

    def test_explicit_abstention_detector_accepts_fixed_and_natural_forms(self):
        fixed = "I do not have enough grounded user evidence to answer that."
        self.assertTrue(explicit_abstention_detected(fixed, fixed))
        self.assertTrue(
            explicit_abstention_detected("The appointment time has not been confirmed.")
        )
        self.assertFalse(explicit_abstention_detected("It is at 3:00 PM."))
        self.assertFalse(explicit_abstention_detected(""))


if __name__ == "__main__":
    unittest.main()
