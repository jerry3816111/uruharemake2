#!/usr/bin/env python3
"""Build frozen V4 cases for cue-driven extractive autobiographical recall."""

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "uruha_memory_cue_extractive_cases_v4"
POSITIONS = ("beginning", "middle", "end")
DEFAULT_OUTPUT = Path("datasets/memory_cue_extractive_v4.json")


FILLER_TURNS = (
    ("I folded the striped picnic blanket this morning.", "It should be ready for the next outing."),
    ("The flower shop displayed yellow tulips.", "That must make the window bright."),
    ("I sharpened the kitchen scissors yesterday.", "They should cut more cleanly now."),
    ("A delivery bicycle stopped near the library.", "That is a common place for deliveries."),
    ("I dusted the top of the bookcase.", "That spot is easy to overlook."),
    ("The cafe changed the picture on its menu board.", "Regular customers may notice that."),
    ("I mailed the warranty card before lunch.", "That task is out of the way."),
    ("The park fountain was running again today.", "It must make the park feel livelier."),
    ("I replaced the batteries in the wall clock.", "It should keep time reliably now."),
    ("A violinist practiced in the next building.", "The sound probably carried through the wall."),
    ("I rinsed the reusable shopping bags.", "They should be clean for the next trip."),
    ("The corner store stacked oranges by the entrance.", "That would be hard to miss."),
)


SCENARIOS = (
    {
        "scenario_id": "dev_water_bottles_current_count",
        "split": "development",
        "capability": "current_count",
        "answerable": True,
        "question": "How many stainless steel water bottles do I have now?",
        "question_frame": {
            "subject": "stainless steel water bottles",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["latest explicit user-stated total"],
        },
        "evidence_dialogue": (
            (
                "I counted my stainless steel water bottles after washing them.",
                "You probably have four bottles now.",
            ),
            (
                "That estimate was off. Counting the new blue one, the total is seven now.",
                "Thanks for giving the actual total.",
            ),
        ),
        "required_evidence_quotes": (
            "That estimate was off. Counting the new blue one, the total is seven now.",
        ),
        "slot_spans": {"current": "seven"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_passport_current_location",
        "split": "development",
        "capability": "current_location",
        "answerable": True,
        "question": "Which compartment contains my passport at present?",
        "question_frame": {
            "subject": "passport",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["latest explicit user-stated storage location"],
        },
        "evidence_dialogue": (
            (
                "I moved my passport while organizing the travel papers.",
                "It is probably in the top desk drawer.",
            ),
            (
                "Not the desk. I put it inside the zipped pocket of my travel backpack.",
                "I will use the backpack location.",
            ),
        ),
        "required_evidence_quotes": (
            "Not the desk. I put it inside the zipped pocket of my travel backpack.",
        ),
        "slot_spans": {"current": "zipped pocket of my travel backpack"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_lap_pool_previous_frequency",
        "split": "development",
        "capability": "previous_frequency",
        "answerable": True,
        "question": "How often did I swim before changing to the Saturday schedule?",
        "question_frame": {
            "subject": "swimming schedule",
            "attribute": "practice frequency",
            "time_focus": "previous",
            "operation": "lookup",
            "answer_type": "frequency",
            "evidence_requirements": ["previous and current explicit user-stated cadence"],
        },
        "evidence_dialogue": (
            (
                "I changed my swimming schedule after the weekday pool hours were reduced.",
                "You may have gone only once a month before that.",
            ),
            (
                "Before this month I swam three mornings a week; now I only go on Saturday.",
                "I understand the old and current schedules.",
            ),
        ),
        "required_evidence_quotes": (
            "Before this month I swam three mornings a week; now I only go on Saturday.",
        ),
        "slot_spans": {"previous": "three mornings a week"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_train_trip_decrease",
        "split": "development",
        "capability": "change_direction",
        "answerable": True,
        "question": "Did my train trip become longer or shorter, and from what duration to what duration?",
        "question_frame": {
            "subject": "train trip",
            "attribute": "duration",
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
            "evidence_requirements": ["before and current explicit user-stated durations"],
        },
        "evidence_dialogue": (
            (
                "My train trip changed after the express service opened.",
                "It probably became longer than before.",
            ),
            (
                "Actually, it dropped from fifty minutes to thirty-five minutes.",
                "So the train trip became shorter.",
            ),
        ),
        "required_evidence_quotes": (
            "Actually, it dropped from fifty minutes to thirty-five minutes.",
        ),
        "slot_spans": {"before": "fifty minutes", "current": "thirty-five minutes"},
        "polarity": "none",
        "relation": "decrease",
    },
    {
        "scenario_id": "dev_precamera_binoculars_ownership",
        "split": "development",
        "capability": "historical_yes_no",
        "answerable": True,
        "question": "Before buying my camera, did I own binoculars?",
        "question_frame": {
            "subject": "binocular ownership before buying the camera",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with concise support",
            "evidence_requirements": ["explicit user-stated ownership before the boundary"],
        },
        "evidence_dialogue": (
            (
                "Before I bought the camera, I already owned binoculars but no telescope.",
                "I thought the binoculars came later.",
            ),
            (
                "The binoculars were already mine; the telescope was not.",
                "Thanks for correcting the equipment timeline.",
            ),
        ),
        "required_evidence_quotes": (
            "Before I bought the camera, I already owned binoculars but no telescope.",
            "The binoculars were already mine; the telescope was not.",
        ),
        "slot_spans": {"support": "binoculars"},
        "polarity": "yes",
        "relation": "none",
    },
    {
        "scenario_id": "dev_physiotherapy_current_time",
        "split": "development",
        "capability": "current_time",
        "answerable": True,
        "question": "What time is my physiotherapy appointment now?",
        "question_frame": {
            "subject": "physiotherapy appointment",
            "attribute": "appointment time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["latest confirmed user-stated appointment time"],
        },
        "evidence_dialogue": (
            (
                "The physiotherapy clinic moved my appointment.",
                "Then it may still be at 11:30 AM.",
            ),
            (
                "The old slot was 11:30 AM. The new confirmation says 4:45 PM.",
                "I will use the confirmed afternoon time.",
            ),
        ),
        "required_evidence_quotes": (
            "The old slot was 11:30 AM. The new confirmation says 4:45 PM.",
        ),
        "slot_spans": {"current": "4:45 PM"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_house_key_unknown_location",
        "split": "development",
        "capability": "unanswerable_location",
        "answerable": False,
        "question": "Where do I keep the spare house key now?",
        "question_frame": {
            "subject": "spare house key",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["explicit user-stated current storage location"],
        },
        "evidence_dialogue": (
            (
                "I still need to choose a safe place for the spare house key.",
                "The ceramic bowl near the door might work.",
            ),
            (
                "The bowl is only your suggestion; I have not decided where to keep the key.",
                "Understood; the location is still unknown.",
            ),
        ),
        "required_evidence_quotes": (
            "I still need to choose a safe place for the spare house key.",
            "The bowl is only your suggestion; I have not decided where to keep the key.",
        ),
        "slot_spans": {},
        "polarity": "unknown",
        "relation": "none",
    },
    {
        "scenario_id": "dev_houseplants_unknown_count",
        "split": "development",
        "capability": "unanswerable_count",
        "answerable": False,
        "question": "What is the current total of my indoor potted plants?",
        "question_frame": {
            "subject": "houseplants",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["explicit user-stated current total"],
        },
        "evidence_dialogue": (
            (
                "I have not counted my houseplants since moving the pots.",
                "There could be twelve by now.",
            ),
            (
                "Twelve is only your estimate; the actual number is still unknown.",
                "I will not treat the estimate as a count.",
            ),
        ),
        "required_evidence_quotes": (
            "I have not counted my houseplants since moving the pots.",
            "Twelve is only your estimate; the actual number is still unknown.",
        ),
        "slot_spans": {},
        "polarity": "unknown",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_sketchbooks_current_count",
        "split": "transfer",
        "capability": "current_count",
        "answerable": True,
        "question": "What is my current number of sketchbooks?",
        "question_frame": {
            "subject": "sketchbooks",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["latest explicit user-stated total"],
        },
        "evidence_dialogue": (
            (
                "I sorted my sketchbooks after donating the unused ones.",
                "Maybe five sketchbooks remain.",
            ),
            (
                "After the donation and buying one new book, I counted nine sketchbooks in total.",
                "I will use nine as the current total.",
            ),
        ),
        "required_evidence_quotes": (
            "After the donation and buying one new book, I counted nine sketchbooks in total.",
        ),
        "slot_spans": {"current": "nine"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_tax_folder_current_location",
        "split": "transfer",
        "capability": "current_location",
        "answerable": True,
        "question": "Where is my tax folder now?",
        "question_frame": {
            "subject": "tax folder",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["latest explicit user-stated storage location"],
        },
        "evidence_dialogue": (
            (
                "I relocated the tax folder while clearing the study shelf.",
                "It is probably still on that shelf.",
            ),
            (
                "No; the shelf was temporary. It is under the green box in the hall closet now.",
                "Thanks, I will use the hall closet location.",
            ),
        ),
        "required_evidence_quotes": (
            "No; the shelf was temporary. It is under the green box in the hall closet now.",
        ),
        "slot_spans": {"current": "under the green box in the hall closet"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_language_exchange_previous_frequency",
        "split": "transfer",
        "capability": "previous_frequency",
        "answerable": True,
        "question": "How often was my language exchange before I switched to Thursdays?",
        "question_frame": {
            "subject": "language exchange",
            "attribute": "meeting frequency",
            "time_focus": "previous",
            "operation": "lookup",
            "answer_type": "frequency",
            "evidence_requirements": ["previous and current explicit user-stated cadence"],
        },
        "evidence_dialogue": (
            (
                "I changed my language exchange routine when a new partner joined.",
                "It may previously have been weekly.",
            ),
            (
                "I meet every Thursday now; before changing, I met twice a month.",
                "I understand both schedules.",
            ),
        ),
        "required_evidence_quotes": (
            "I meet every Thursday now; before changing, I met twice a month.",
        ),
        "slot_spans": {"previous": "twice a month"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_bike_route_increase",
        "split": "transfer",
        "capability": "change_direction",
        "answerable": True,
        "question": "How did my bicycle route distance change, including both distances?",
        "question_frame": {
            "subject": "bicycle route",
            "attribute": "distance",
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
            "evidence_requirements": ["before and current explicit user-stated distances"],
        },
        "evidence_dialogue": (
            (
                "My bicycle route changed after the bridge closed.",
                "The replacement route may be shorter.",
            ),
            (
                "It went from six kilometers to nine kilometers, so the route became longer.",
                "I see that the distance increased.",
            ),
        ),
        "required_evidence_quotes": (
            "It went from six kilometers to nine kilometers, so the route became longer.",
        ),
        "slot_spans": {"before": "six kilometers", "current": "nine kilometers"},
        "polarity": "none",
        "relation": "increase",
    },
    {
        "scenario_id": "transfer_predog_rabbit_nonownership",
        "split": "transfer",
        "capability": "historical_yes_no",
        "answerable": True,
        "question": "Before adopting my dog, did I own a rabbit?",
        "question_frame": {
            "subject": "rabbit ownership before adopting the dog",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with concise support",
            "evidence_requirements": ["explicit user-stated non-ownership before the boundary"],
        },
        "evidence_dialogue": (
            (
                "Before adopting the dog, I had a turtle but never owned a rabbit.",
                "I thought there had been a rabbit too.",
            ),
            (
                "No rabbit; the turtle was my only pet then.",
                "Thanks for correcting the earlier pet history.",
            ),
        ),
        "required_evidence_quotes": (
            "Before adopting the dog, I had a turtle but never owned a rabbit.",
            "No rabbit; the turtle was my only pet then.",
        ),
        "slot_spans": {"support": "rabbit"},
        "polarity": "no",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_dentist_current_time",
        "split": "transfer",
        "capability": "current_time",
        "answerable": True,
        "question": "At what time is my dentist visit currently scheduled?",
        "question_frame": {
            "subject": "dentist visit",
            "attribute": "appointment time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["latest confirmed user-stated appointment time"],
        },
        "evidence_dialogue": (
            (
                "The dentist rescheduled my visit again.",
                "It might still be at 3:00 PM.",
            ),
            (
                "The 3:00 PM slot was canceled; the confirmed time is 8:40 AM.",
                "I will use the morning confirmation.",
            ),
        ),
        "required_evidence_quotes": (
            "The 3:00 PM slot was canceled; the confirmed time is 8:40 AM.",
        ),
        "slot_spans": {"current": "8:40 AM"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_garage_code_unknown_count",
        "split": "transfer",
        "capability": "unanswerable_count",
        "answerable": False,
        "question": "How many digits will my new garage code contain?",
        "question_frame": {
            "subject": "new garage code",
            "attribute": "digit count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["explicit user-confirmed digit count"],
        },
        "evidence_dialogue": (
            (
                "I have not decided how many digits the new garage code should contain.",
                "A six-digit code might be convenient.",
            ),
            (
                "Six is only your suggestion; no digit count has been confirmed.",
                "Understood; the length remains unknown.",
            ),
        ),
        "required_evidence_quotes": (
            "I have not decided how many digits the new garage code should contain.",
            "Six is only your suggestion; no digit count has been confirmed.",
        ),
        "slot_spans": {},
        "polarity": "unknown",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_emergency_contact_unknown_identity",
        "split": "transfer",
        "capability": "unanswerable_identity",
        "answerable": False,
        "question": "Who is my emergency contact now?",
        "question_frame": {
            "subject": "emergency contact",
            "attribute": "current identity",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "text",
            "evidence_requirements": ["explicit user-confirmed contact identity"],
        },
        "evidence_dialogue": (
            (
                "I still need to choose a new emergency contact.",
                "Your cousin Mina could be a good choice.",
            ),
            (
                "Mina is only your suggestion; the contact is still unknown.",
                "I will not treat that suggestion as confirmed.",
            ),
        ),
        "required_evidence_quotes": (
            "I still need to choose a new emergency contact.",
            "Mina is only your suggestion; the contact is still unknown.",
        ),
        "slot_spans": {},
        "polarity": "unknown",
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


def render_session(turns):
    lines = []
    for user_text, assistant_text in turns:
        lines.extend((f"User: {user_text}", f"Assistant: {assistant_text}"))
    return "\n".join(lines)


def build_case(scenario, position):
    at = insertion_index(position)
    turns = [
        *FILLER_TURNS[:at],
        *scenario["evidence_dialogue"],
        *FILLER_TURNS[at:],
    ]
    case_id = f"{scenario['scenario_id']}__{position}"
    attention_quotes = [user for user, _assistant in scenario["evidence_dialogue"]]
    slot_spans = dict(scenario["slot_spans"])
    return {
        "case_id": case_id,
        "scenario_id": scenario["scenario_id"],
        "split": scenario["split"],
        "capability": scenario["capability"],
        "evidence_position": position,
        "question": scenario["question"],
        "question_date": "2026-07-17 18:00:00",
        "question_frame": scenario["question_frame"],
        "session": {
            "session_id": f"session_{case_id}",
            "timestamp": "2026-07-16 18:00:00",
            "text": render_session(turns),
        },
        "gold": {
            "answerable": scenario["answerable"],
            "expected_abstention": not scenario["answerable"],
            "attention_quotes": attention_quotes,
            "required_evidence_quotes": list(scenario["required_evidence_quotes"]),
            "assistant_decoy_quotes": [
                assistant for _user, assistant in scenario["evidence_dialogue"][:1]
            ],
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
        "generated_at": "2026-07-14T09:05:00+00:00",
        "research_boundary": {
            "purpose": "development-only cue-driven extractive recall experiment",
            "official_benchmark_items_used": 0,
            "v1_case_reuse_count": 0,
            "v2_case_reuse_count": 0,
            "v3_case_reuse_count": 0,
            "heldout_promotion_authorized": False,
            "runtime_change_authorized": False,
            "split_note": (
                "Development and transfer use disjoint scenarios. Transfer is an internal "
                "diagnostic rather than an external heldout claim."
            ),
        },
        "positions": list(POSITIONS),
        "scenario_count": len(SCENARIOS),
        "answerable_scenario_count": sum(row["answerable"] for row in SCENARIOS),
        "unanswerable_scenario_count": sum(not row["answerable"] for row in SCENARIOS),
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
                "answerable_scenario_count": payload["answerable_scenario_count"],
                "unanswerable_scenario_count": payload["unanswerable_scenario_count"],
                "case_count": payload["case_count"],
                "cases_sha256": payload["cases_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
