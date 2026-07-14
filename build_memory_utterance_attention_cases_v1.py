#!/usr/bin/env python3
"""Build source-separated development cases for utterance-level memory attention."""

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "uruha_memory_utterance_attention_cases_v1"
POSITIONS = ("beginning", "middle", "end")
DEFAULT_OUTPUT = Path("datasets/memory_utterance_attention_v1.json")


FILLER_TURNS = (
    ("I replaced the batteries in the hallway clock.", "That should keep it reliable."),
    ("The bakery near the station has a new rye loaf.", "That sounds worth trying."),
    ("I washed the green blanket this morning.", "It should be fresh now."),
    ("My neighbor planted flowers by the front gate.", "That will brighten the entrance."),
    ("I downloaded a documentary about coastal birds.", "That sounds interesting."),
    ("The kitchen light flickered once yesterday.", "It may be worth monitoring."),
    ("I sent a birthday card to my cousin.", "Good, it should arrive in time."),
    ("The weather forecast says it may rain tomorrow.", "An umbrella may be useful."),
    ("I cleaned the dust from the bookshelf.", "That is a satisfying job to finish."),
    ("The corner shop changed its paper bags.", "Small changes like that are noticeable."),
    ("I watched half of a mystery film last night.", "You can finish it when you have time."),
    ("The train was quieter than usual this morning.", "That makes the commute easier."),
)


SCENARIOS = (
    {
        "scenario_id": "dev_spare_key_location",
        "split": "development",
        "capability": "current_location",
        "question": "Where do I keep my spare apartment key now?",
        "question_frame": {
            "subject": "spare apartment key",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["current user-stated storage location"],
        },
        "evidence_turns": (
            "About my spare apartment key, I reorganized the entryway yesterday.",
            "I used to leave it in the blue bowl, but now it is inside the cedar drawer.",
        ),
        "gold_answer_spans": ("inside the cedar drawer",),
        "gold_relation": "none",
    },
    {
        "scenario_id": "dev_running_previous_frequency",
        "split": "development",
        "capability": "previous_frequency",
        "question": "What was my running schedule before I changed it to Saturdays?",
        "question_frame": {
            "subject": "running schedule",
            "attribute": "frequency",
            "time_focus": "previous",
            "operation": "lookup",
            "answer_type": "frequency",
            "evidence_requirements": ["previous and current user-stated cadence"],
        },
        "evidence_turns": (
            "My running schedule changed after I started the new job.",
            "I run on Saturdays now; before that, I went three times a week.",
        ),
        "gold_answer_spans": ("three times a week",),
        "gold_relation": "none",
    },
    {
        "scenario_id": "dev_vehicle_historical_ownership",
        "split": "development",
        "capability": "historical_yes_no",
        "question": (
            "Before I bought the electric scooter, did I own another vehicle besides my city "
            "bicycle?"
        ),
        "question_frame": {
            "subject": "vehicles owned before buying the electric scooter",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with a concise supporting fact",
            "evidence_requirements": ["vehicle ownership before the purchase boundary"],
        },
        "evidence_turns": (
            "I already owned a small motorcycle alongside my city bicycle.",
            "Months later, I bought the electric scooter for the commute.",
        ),
        "gold_answer_spans": ("small motorcycle",),
        "gold_relation": "yes",
    },
    {
        "scenario_id": "dev_houseplant_current_count",
        "split": "development",
        "capability": "current_count",
        "question": "How many houseplants do I have now?",
        "question_frame": {
            "subject": "houseplants",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["latest corrected user-stated count"],
        },
        "evidence_turns": (
            "I counted the houseplants again after repotting them.",
            "The old total was eight, but there are eleven now.",
        ),
        "gold_answer_spans": ("eleven",),
        "gold_relation": "none",
    },
    {
        "scenario_id": "dev_coffee_limit_change",
        "split": "development",
        "capability": "change_direction",
        "question": "Did my daily coffee limit increase or decrease, and from what to what?",
        "question_frame": {
            "subject": "daily coffee limit",
            "attribute": "amount",
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
            "evidence_requirements": ["before and current user-stated limits"],
        },
        "evidence_turns": (
            "My daily coffee limit changed after I started sleeping better.",
            "I used to allow three cups, but now I stop after one cup.",
        ),
        "gold_answer_spans": ("three cups", "one cup"),
        "gold_relation": "decrease",
    },
    {
        "scenario_id": "dev_dentist_current_time",
        "split": "development",
        "capability": "current_time",
        "question": "What time is my dentist appointment now?",
        "question_frame": {
            "subject": "dentist appointment",
            "attribute": "appointment time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["latest corrected appointment time"],
        },
        "evidence_turns": (
            "The dentist's office changed my appointment.",
            "It was at 10:30 AM, but it is at 2:20 PM now.",
        ),
        "gold_answer_spans": ("2:20 PM",),
        "gold_relation": "none",
    },
    {
        "scenario_id": "transfer_passport_location",
        "split": "transfer",
        "capability": "current_location",
        "question": "Where is my passport stored now?",
        "question_frame": {
            "subject": "passport",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["current user-stated storage location"],
        },
        "evidence_turns": (
            "I moved my passport after reorganizing the bedroom documents.",
            "It is no longer in the bedside drawer; I keep it in the locked metal cabinet.",
        ),
        "gold_answer_spans": ("locked metal cabinet",),
        "gold_relation": "none",
    },
    {
        "scenario_id": "transfer_parent_call_previous_frequency",
        "split": "transfer",
        "capability": "previous_frequency",
        "question": "How often did I call my parents before the new twice-a-week schedule?",
        "question_frame": {
            "subject": "calls to parents",
            "attribute": "frequency",
            "time_focus": "previous",
            "operation": "lookup",
            "answer_type": "frequency",
            "evidence_requirements": ["previous and current user-stated cadence"],
        },
        "evidence_turns": (
            "I changed how often I call my parents after their move.",
            "Now I call twice a week; before the move, I called every Sunday.",
        ),
        "gold_answer_spans": ("every Sunday",),
        "gold_relation": "none",
    },
    {
        "scenario_id": "transfer_pet_historical_ownership",
        "split": "transfer",
        "capability": "historical_yes_no",
        "question": "Before adopting the cat, did I have another pet besides my dog?",
        "question_frame": {
            "subject": "pets owned before adopting the cat",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with a concise supporting fact",
            "evidence_requirements": ["pet ownership before the adoption boundary"],
        },
        "evidence_turns": (
            "I had a hamster as well as my dog at that time.",
            "The cat joined the household the following spring.",
        ),
        "gold_answer_spans": ("hamster",),
        "gold_relation": "yes",
    },
    {
        "scenario_id": "transfer_notebook_current_count",
        "split": "transfer",
        "capability": "current_count",
        "question": "How many paper notebooks do I own now?",
        "question_frame": {
            "subject": "paper notebooks",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["latest corrected user-stated count"],
        },
        "evidence_turns": (
            "I counted my paper notebooks while clearing the desk.",
            "There were four before, and after the gifts I own seven now.",
        ),
        "gold_answer_spans": ("seven",),
        "gold_relation": "none",
    },
    {
        "scenario_id": "transfer_commute_duration_change",
        "split": "transfer",
        "capability": "change_direction",
        "question": "Did my commute get longer or shorter, and from what duration to what?",
        "question_frame": {
            "subject": "commute duration",
            "attribute": "duration",
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
            "evidence_requirements": ["before and current user-stated durations"],
        },
        "evidence_turns": (
            "Changing from the bus to the train altered my commute duration.",
            "The old bus ride took fifty minutes; the train takes thirty-five minutes now.",
        ),
        "gold_answer_spans": ("fifty minutes", "thirty-five minutes"),
        "gold_relation": "decrease",
    },
    {
        "scenario_id": "transfer_class_current_time",
        "split": "transfer",
        "capability": "current_time",
        "question": "What time does my evening class start now?",
        "question_frame": {
            "subject": "evening class",
            "attribute": "start time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["latest corrected class start time"],
        },
        "evidence_turns": (
            "The school changed the start time of my evening class.",
            "It used to begin at 6:00 PM, but it starts at 7:30 PM now.",
        ),
        "gold_answer_spans": ("7:30 PM",),
        "gold_relation": "none",
    },
)


def canonical_sha256(payload):
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evidence_block(scenario):
    turns = []
    for index, text in enumerate(scenario["evidence_turns"], start=1):
        turns.append((text, f"I will remember that detail ({index})."))
    return turns


def insertion_index(position):
    if position == "beginning":
        return 0
    if position == "middle":
        return len(FILLER_TURNS) // 2
    if position == "end":
        return len(FILLER_TURNS)
    raise ValueError(f"Unknown position: {position}")


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
    return {
        "case_id": case_id,
        "scenario_id": scenario["scenario_id"],
        "split": scenario["split"],
        "capability": scenario["capability"],
        "evidence_position": position,
        "question": scenario["question"],
        "question_date": "2026-07-14 12:00:00",
        "question_frame": scenario["question_frame"],
        "session": {
            "session_id": f"session_{case_id}",
            "timestamp": "2026-07-13 12:00:00",
            "text": render_session(turns),
        },
        "gold": {
            "attention_quotes": list(scenario["evidence_turns"]),
            "answer_spans": list(scenario["gold_answer_spans"]),
            "relation": scenario["gold_relation"],
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
        "generated_at": "2026-07-14T00:00:00+00:00",
        "research_boundary": {
            "purpose": "development-only architecture experiment",
            "official_benchmark_items_used": 0,
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
