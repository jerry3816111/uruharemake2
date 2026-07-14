#!/usr/bin/env python3
"""Build source-separated V2 cases for full-context highlights and span slots."""

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "uruha_memory_highlight_span_cases_v2"
POSITIONS = ("beginning", "middle", "end")
DEFAULT_OUTPUT = Path("datasets/memory_highlight_span_v2.json")


FILLER_TURNS = (
    ("I shook the dust from the balcony mat.", "That should make the entrance cleaner."),
    ("The cafe added pumpkin soup to its lunch menu.", "That sounds seasonal."),
    ("I charged my wireless headphones last night.", "They should be ready to use."),
    ("A small museum opened near the river path.", "That could be interesting to visit."),
    ("I folded the striped towels after breakfast.", "That is one task out of the way."),
    ("The elevator made a soft chime this morning.", "That is a subtle change."),
    ("I mailed the library book back yesterday.", "Good, it should arrive before the deadline."),
    ("The florist displayed yellow tulips outside.", "That must look bright."),
    ("I replaced the cracked phone case.", "The phone should be better protected now."),
    ("A podcast episode discussed old bridges.", "That sounds like a focused topic."),
    ("I rinsed the glass vase before dinner.", "It will be ready for fresh flowers."),
    ("The morning bus had new seat covers.", "That is an easy detail to notice."),
)


SCENARIOS = (
    {
        "scenario_id": "dev_camera_battery_location",
        "split": "development",
        "capability": "current_location",
        "question": "Where do I keep the backup camera battery now?",
        "question_frame": {
            "subject": "backup camera battery",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["current user-stated storage location"],
        },
        "evidence_turns": (
            "I reviewed where I keep the backup camera battery after reorganizing my gear.",
            "It used to sit in the backpack pocket, but now it stays in the upper desk compartment.",
        ),
        "slot_spans": {"current": "upper desk compartment"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_swimming_previous_frequency",
        "split": "development",
        "capability": "previous_frequency",
        "question": "How often did I swim before changing to the Wednesday schedule?",
        "question_frame": {
            "subject": "swimming routine",
            "attribute": "frequency",
            "time_focus": "previous",
            "operation": "lookup",
            "answer_type": "frequency",
            "evidence_requirements": ["previous and current user-stated cadence"],
        },
        "evidence_turns": (
            "My swimming routine changed when the pool schedule shifted.",
            "I swim on Wednesdays now; before the change, I went every morning.",
        ),
        "slot_spans": {"previous": "every morning"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_instrument_historical_yes",
        "split": "development",
        "capability": "historical_yes_no",
        "question": (
            "Before I ordered the digital piano, did I own another instrument besides my "
            "ukulele?"
        ),
        "question_frame": {
            "subject": "instruments owned before ordering the digital piano",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with a concise supporting fact",
            "evidence_requirements": ["instrument ownership before the order boundary"],
        },
        "evidence_turns": (
            "Before ordering the digital piano, I already had an acoustic guitar as well as my ukulele.",
            "The digital piano arrived several months afterward.",
        ),
        "slot_spans": {"support": "acoustic guitar"},
        "polarity": "yes",
        "relation": "none",
    },
    {
        "scenario_id": "dev_bottle_current_count",
        "split": "development",
        "capability": "current_count",
        "question": "How many reusable water bottles do I have now?",
        "question_frame": {
            "subject": "reusable water bottles",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["latest corrected user-stated count"],
        },
        "evidence_turns": (
            "I counted my reusable water bottles while organizing the cupboard.",
            "There used to be five, but after the gifts I have nine now.",
        ),
        "slot_spans": {"current": "nine"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_study_time_increase",
        "split": "development",
        "capability": "change_direction",
        "question": "Did my weekly study time increase or decrease, and from what to what?",
        "question_frame": {
            "subject": "weekly study time",
            "attribute": "duration",
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
            "evidence_requirements": ["before and current user-stated durations"],
        },
        "evidence_turns": (
            "My weekly study time changed after I joined the evening course.",
            "I used to study four hours per week; now I study seven hours per week.",
        ),
        "slot_spans": {"before": "four hours per week", "current": "seven hours per week"},
        "polarity": "none",
        "relation": "increase",
    },
    {
        "scenario_id": "dev_therapy_current_time",
        "split": "development",
        "capability": "current_time",
        "question": "What time is my therapy appointment now?",
        "question_frame": {
            "subject": "therapy appointment",
            "attribute": "appointment time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["latest corrected appointment time"],
        },
        "evidence_turns": (
            "The clinic rescheduled my therapy appointment.",
            "It was at 11:15 AM, but now it is at 4:45 PM.",
        ),
        "slot_spans": {"current": "4:45 PM"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_insurance_papers_location",
        "split": "transfer",
        "capability": "current_location",
        "question": "Where are my insurance papers stored now?",
        "question_frame": {
            "subject": "insurance papers",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["current user-stated storage location"],
        },
        "evidence_turns": (
            "I reorganized my insurance papers after reviewing the household files.",
            "They were in the kitchen basket, but now they are sealed in the fireproof safe.",
        ),
        "slot_spans": {"current": "fireproof safe"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_grocery_previous_frequency",
        "split": "transfer",
        "capability": "previous_frequency",
        "question": "How often did my grocery delivery arrive before the new schedule?",
        "question_frame": {
            "subject": "grocery delivery schedule",
            "attribute": "frequency",
            "time_focus": "previous",
            "operation": "lookup",
            "answer_type": "frequency",
            "evidence_requirements": ["previous and current user-stated cadence"],
        },
        "evidence_turns": (
            "The grocery delivery schedule changed after I updated the subscription.",
            "It comes every two weeks now; before the update, it arrived once a month.",
        ),
        "slot_spans": {"previous": "once a month"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_pet_historical_no",
        "split": "transfer",
        "capability": "historical_yes_no",
        "question": "Before adopting the rabbit, did I own a bird in addition to my turtle?",
        "question_frame": {
            "subject": "pets owned before adopting the rabbit",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with a concise supporting fact",
            "evidence_requirements": ["explicit ownership or non-ownership before adoption"],
        },
        "evidence_turns": (
            "At that time I had only my turtle, and I definitely did not own a bird.",
            "I adopted the rabbit the following winter.",
        ),
        "slot_spans": {"support": "did not own a bird"},
        "polarity": "no",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_pen_current_count",
        "split": "transfer",
        "capability": "current_count",
        "question": "How many fountain pens do I own now?",
        "question_frame": {
            "subject": "fountain pens",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["latest corrected user-stated count"],
        },
        "evidence_turns": (
            "I checked the fountain pens in my writing case.",
            "I owned three before the sale, and I own six now.",
        ),
        "slot_spans": {"current": "six"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_screen_time_decrease",
        "split": "transfer",
        "capability": "change_direction",
        "question": "Did my evening screen time increase or decrease, and from what to what?",
        "question_frame": {
            "subject": "evening screen time",
            "attribute": "duration",
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
            "evidence_requirements": ["before and current user-stated durations"],
        },
        "evidence_turns": (
            "My evening screen time changed after I set the new limit.",
            "It used to be six hours each evening; now it is two hours.",
        ),
        "slot_spans": {"before": "six hours", "current": "two hours"},
        "polarity": "none",
        "relation": "decrease",
    },
    {
        "scenario_id": "transfer_train_current_time",
        "split": "transfer",
        "capability": "current_time",
        "question": "What time is my train reservation now?",
        "question_frame": {
            "subject": "train reservation",
            "attribute": "departure time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["latest corrected departure time"],
        },
        "evidence_turns": (
            "The railway changed the departure time on my train reservation.",
            "The old time was 8:10 AM, and the new departure is 9:35 AM.",
        ),
        "slot_spans": {"current": "9:35 AM"},
        "polarity": "none",
        "relation": "none",
    },
)


def canonical_sha256(payload):
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def insertion_index(position):
    if position == "beginning":
        return 0
    if position == "middle":
        return len(FILLER_TURNS) // 2
    if position == "end":
        return len(FILLER_TURNS)
    raise ValueError(f"Unknown position: {position}")


def evidence_block(scenario):
    return [
        (text, f"I will keep that detail in context ({index}).")
        for index, text in enumerate(scenario["evidence_turns"], start=1)
    ]


def render_session(turns):
    lines = []
    for user_text, assistant_text in turns:
        lines.extend((f"User: {user_text}", f"Assistant: {assistant_text}"))
    return "\n".join(lines)


def build_case(scenario, position):
    at = insertion_index(position)
    turns = [
        *FILLER_TURNS[:at],
        *evidence_block(scenario),
        *FILLER_TURNS[at:],
    ]
    case_id = f"{scenario['scenario_id']}__{position}"
    slot_spans = dict(scenario["slot_spans"])
    return {
        "case_id": case_id,
        "scenario_id": scenario["scenario_id"],
        "split": scenario["split"],
        "capability": scenario["capability"],
        "evidence_position": position,
        "question": scenario["question"],
        "question_date": "2026-07-14 18:00:00",
        "question_frame": scenario["question_frame"],
        "session": {
            "session_id": f"session_{case_id}",
            "timestamp": "2026-07-13 18:00:00",
            "text": render_session(turns),
        },
        "gold": {
            "attention_quotes": list(scenario["evidence_turns"]),
            "slot_spans": slot_spans,
            "answer_spans": list(slot_spans.values()),
            "polarity": scenario["polarity"],
            "relation": scenario["relation"],
        },
    }


def build_payload():
    cases = [
        build_case(scenario, position)
        for scenario in SCENARIOS
        for position in POSITIONS
    ]
    payload = {
        "schema": SCHEMA,
        "generated_at": "2026-07-14T07:00:00+00:00",
        "research_boundary": {
            "purpose": "development-only matched architecture experiment",
            "official_benchmark_items_used": 0,
            "v1_case_reuse_count": 0,
            "heldout_promotion_authorized": False,
            "runtime_change_authorized": False,
            "split_note": (
                "Development and transfer use disjoint scenario entities. Transfer remains an "
                "internal diagnostic, not an external heldout claim."
            ),
        },
        "positions": list(POSITIONS),
        "scenario_count": len(SCENARIOS),
        "case_count": len(cases),
        "cases": cases,
    }
    payload["cases_sha256"] = canonical_sha256(cases)
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_payload()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "scenario_count": payload["scenario_count"],
                "case_count": payload["case_count"],
                "cases_sha256": payload["cases_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
