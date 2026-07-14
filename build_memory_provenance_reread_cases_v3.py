#!/usr/bin/env python3
"""Build frozen V3 cases for source monitoring and adaptive memory rereading."""

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "uruha_memory_provenance_reread_cases_v3"
POSITIONS = ("beginning", "middle", "end")
DEFAULT_OUTPUT = Path("datasets/memory_provenance_reread_v3.json")


FILLER_TURNS = (
    ("I polished the small brass lamp yesterday.", "It should look brighter now."),
    ("The bakery displayed pear tarts this morning.", "That sounds seasonal."),
    ("I replaced the shoelaces on my walking shoes.", "They should be easier to use."),
    ("A new mural appeared beside the post office.", "That would change the street view."),
    ("I watered the fern before breakfast.", "That should help it through the day."),
    ("The radio played a documentary about lighthouses.", "That is a focused topic."),
    ("I returned the borrowed umbrella at lunch.", "Good, that task is finished."),
    ("The stationery shop put notebooks in the window.", "That must make a neat display."),
    ("I cleaned the lint from the dryer filter.", "The dryer should run more efficiently."),
    ("A cyclist rang a bell outside the market.", "That is an easy sound to notice."),
    ("I moved the potted mint closer to the window.", "It may get more light there."),
    ("The neighborhood bulletin mentioned a book sale.", "That could be worth visiting."),
)


SCENARIOS = (
    {
        "scenario_id": "dev_recipe_cards_current_location",
        "split": "development",
        "capability": "current_location",
        "answerable": True,
        "question": "Where do I keep my recipe cards now?",
        "question_frame": {
            "subject": "recipe cards",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["latest explicit user-stated storage location"],
        },
        "evidence_dialogue": (
            (
                "I moved my recipe cards again after clearing the kitchen shelf.",
                "So they are probably in the top kitchen cabinet now.",
            ),
            (
                "No, that was only your guess. I keep them in the bottom pantry drawer now.",
                "Thanks for correcting me.",
            ),
        ),
        "required_evidence_quotes": (
            "No, that was only your guess. I keep them in the bottom pantry drawer now.",
        ),
        "slot_spans": {"current": "bottom pantry drawer"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_yoga_previous_frequency",
        "split": "development",
        "capability": "previous_frequency",
        "answerable": True,
        "question": "How often did I practice yoga before changing to the Tuesday routine?",
        "question_frame": {
            "subject": "yoga routine",
            "attribute": "practice frequency",
            "time_focus": "previous",
            "operation": "lookup",
            "answer_type": "frequency",
            "evidence_requirements": ["previous and current explicit user-stated cadence"],
        },
        "evidence_dialogue": (
            (
                "I changed my yoga routine when the evening class closed.",
                "You probably used to practice only on weekends.",
            ),
            (
                "No. I practice on Tuesdays now; before the change, I practiced every evening.",
                "I understand that the old and new routines differ.",
            ),
        ),
        "required_evidence_quotes": (
            "No. I practice on Tuesdays now; before the change, I practiced every evening.",
        ),
        "slot_spans": {"previous": "every evening"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_preharp_violin_ownership",
        "split": "development",
        "capability": "historical_yes_no",
        "answerable": True,
        "question": "Before I bought the harp, did I own another instrument besides my clarinet?",
        "question_frame": {
            "subject": "instruments owned before buying the harp",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with concise support",
            "evidence_requirements": ["explicit user-stated ownership before the purchase boundary"],
        },
        "evidence_dialogue": (
            (
                "Before I bought the harp, I already owned a violin as well as my clarinet.",
                "I thought the violin came after the harp.",
            ),
            (
                "No, the violin was already mine before the harp.",
                "Thanks for fixing that timeline.",
            ),
        ),
        "required_evidence_quotes": (
            "Before I bought the harp, I already owned a violin as well as my clarinet.",
            "No, the violin was already mine before the harp.",
        ),
        "slot_spans": {"support": "violin"},
        "polarity": "yes",
        "relation": "none",
    },
    {
        "scenario_id": "dev_mug_current_count",
        "split": "development",
        "capability": "current_count",
        "answerable": True,
        "question": "How many ceramic mugs do I have now?",
        "question_frame": {
            "subject": "ceramic mugs",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["latest corrected user-stated count"],
        },
        "evidence_dialogue": (
            (
                "I counted the ceramic mugs after unpacking the last box.",
                "That should leave you with six mugs.",
            ),
            (
                "No, six was the old count; I have eight ceramic mugs now.",
                "Thanks for giving the corrected count.",
            ),
        ),
        "required_evidence_quotes": (
            "No, six was the old count; I have eight ceramic mugs now.",
        ),
        "slot_spans": {"current": "eight"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_commute_increase",
        "split": "development",
        "capability": "change_direction",
        "answerable": True,
        "question": "Did my bus commute increase or decrease, and from what to what?",
        "question_frame": {
            "subject": "bus commute",
            "attribute": "duration",
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
            "evidence_requirements": ["before and current explicit user-stated durations"],
        },
        "evidence_dialogue": (
            (
                "My bus commute changed after the roadwork started.",
                "It probably became shorter, from forty minutes to twenty-five.",
            ),
            (
                "The opposite: it used to take twenty-five minutes, and now it takes forty minutes.",
                "I see; the commute became longer.",
            ),
        ),
        "required_evidence_quotes": (
            "The opposite: it used to take twenty-five minutes, and now it takes forty minutes.",
        ),
        "slot_spans": {"before": "twenty-five minutes", "current": "forty minutes"},
        "polarity": "none",
        "relation": "increase",
    },
    {
        "scenario_id": "dev_optometrist_current_time",
        "split": "development",
        "capability": "current_time",
        "answerable": True,
        "question": "What time is my optometrist appointment now?",
        "question_frame": {
            "subject": "optometrist appointment",
            "attribute": "appointment time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["latest corrected user-stated appointment time"],
        },
        "evidence_dialogue": (
            (
                "The optometrist moved my appointment.",
                "Then it is probably still at 2:20 PM.",
            ),
            (
                "No. It was at 2:20 PM, but the confirmed time is 5:10 PM now.",
                "Thanks, I will use the confirmed time.",
            ),
        ),
        "required_evidence_quotes": (
            "No. It was at 2:20 PM, but the confirmed time is 5:10 PM now.",
        ),
        "slot_spans": {"current": "5:10 PM"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "dev_spare_glasses_unknown_location",
        "split": "development",
        "capability": "unanswerable_location",
        "answerable": False,
        "question": "Where do I keep my spare glasses now?",
        "question_frame": {
            "subject": "spare glasses",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["explicit user-stated current storage location"],
        },
        "evidence_dialogue": (
            (
                "I still need to choose a permanent place for my spare glasses.",
                "The bedroom drawer would make sense.",
            ),
            (
                "That is only your suggestion; I have not decided where to keep them.",
                "Understood; no location has been chosen.",
            ),
        ),
        "required_evidence_quotes": (
            "That is only your suggestion; I have not decided where to keep them.",
        ),
        "slot_spans": {},
        "polarity": "unknown",
        "relation": "none",
    },
    {
        "scenario_id": "dev_tablet_unknown_historical_ownership",
        "split": "development",
        "capability": "unanswerable_yes_no",
        "answerable": False,
        "question": "Before I moved apartments, did I own a tablet?",
        "question_frame": {
            "subject": "tablet ownership before moving apartments",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with concise support",
            "evidence_requirements": ["explicit user-stated ownership or non-ownership before moving"],
        },
        "evidence_dialogue": (
            (
                "I cannot remember whether I owned a tablet before I moved apartments.",
                "You probably did own one.",
            ),
            (
                "That is your guess, not something I confirmed.",
                "I understand that the ownership is unknown.",
            ),
        ),
        "required_evidence_quotes": (
            "I cannot remember whether I owned a tablet before I moved apartments.",
            "That is your guess, not something I confirmed.",
        ),
        "slot_spans": {},
        "polarity": "unknown",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_warranty_papers_current_location",
        "split": "transfer",
        "capability": "current_location",
        "answerable": True,
        "question": "Where are my warranty papers stored now?",
        "question_frame": {
            "subject": "warranty papers",
            "attribute": "storage location",
            "time_focus": "current",
            "operation": "locate",
            "answer_type": "location",
            "evidence_requirements": ["latest explicit user-stated storage location"],
        },
        "evidence_dialogue": (
            (
                "I reorganized the warranty papers after checking the appliance files.",
                "They are probably still in the red folder.",
            ),
            (
                "No. They used to be there; I store them in the blue document case now.",
                "Thanks for correcting the location.",
            ),
        ),
        "required_evidence_quotes": (
            "No. They used to be there; I store them in the blue document case now.",
        ),
        "slot_spans": {"current": "blue document case"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_laundry_previous_frequency",
        "split": "transfer",
        "capability": "previous_frequency",
        "answerable": True,
        "question": "How often did I do laundry before changing to the Sunday routine?",
        "question_frame": {
            "subject": "laundry routine",
            "attribute": "frequency",
            "time_focus": "previous",
            "operation": "lookup",
            "answer_type": "frequency",
            "evidence_requirements": ["previous and current explicit user-stated cadence"],
        },
        "evidence_dialogue": (
            (
                "I changed my laundry routine when the building schedule changed.",
                "You likely used to do it once a week.",
            ),
            (
                "No. I do laundry on Sundays now; before the change, I did it twice a week.",
                "I understand the previous cadence was different.",
            ),
        ),
        "required_evidence_quotes": (
            "No. I do laundry on Sundays now; before the change, I did it twice a week.",
        ),
        "slot_spans": {"previous": "twice a week"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_preparrot_hamster_nonownership",
        "split": "transfer",
        "capability": "historical_yes_no",
        "answerable": True,
        "question": "Before I adopted the parrot, did I own a hamster in addition to my cat?",
        "question_frame": {
            "subject": "pets owned before adopting the parrot",
            "attribute": "ownership",
            "time_focus": "specific_time",
            "operation": "yes_no",
            "answer_type": "yes/no with concise support",
            "evidence_requirements": ["explicit user-stated ownership or non-ownership before adoption"],
        },
        "evidence_dialogue": (
            (
                "Before adopting the parrot, I had my cat, but I did not own a hamster.",
                "I thought you had mentioned a hamster before.",
            ),
            (
                "No, that was your assumption; I definitely did not own one then.",
                "Thanks for correcting that assumption.",
            ),
        ),
        "required_evidence_quotes": (
            "Before adopting the parrot, I had my cat, but I did not own a hamster.",
            "No, that was your assumption; I definitely did not own one then.",
        ),
        "slot_spans": {"support": "did not own a hamster"},
        "polarity": "no",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_unused_notebook_current_count",
        "split": "transfer",
        "capability": "current_count",
        "answerable": True,
        "question": "How many unused notebooks do I have now?",
        "question_frame": {
            "subject": "unused notebooks",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["latest corrected user-stated count"],
        },
        "evidence_dialogue": (
            (
                "I counted the unused notebooks after sorting the cabinet.",
                "There must be nine of them.",
            ),
            (
                "No, nine included two used ones; I have seven unused notebooks now.",
                "Thanks for separating the used notebooks.",
            ),
        ),
        "required_evidence_quotes": (
            "No, nine included two used ones; I have seven unused notebooks now.",
        ),
        "slot_spans": {"current": "seven"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_takeout_frequency_decrease",
        "split": "transfer",
        "capability": "change_direction",
        "answerable": True,
        "question": "Did my weekly takeout frequency increase or decrease, and from what to what?",
        "question_frame": {
            "subject": "weekly takeout frequency",
            "attribute": "number of takeout meals per week",
            "time_focus": "change_direction",
            "operation": "compare",
            "answer_type": "direction with before and after values",
            "evidence_requirements": ["before and current explicit user-stated frequencies"],
        },
        "evidence_dialogue": (
            (
                "My takeout habit changed after I started meal preparation.",
                "It probably increased from two meals a week to five.",
            ),
            (
                "It actually decreased: I used to order five times a week, and now I order twice a week.",
                "I see; the weekly frequency went down.",
            ),
        ),
        "required_evidence_quotes": (
            "It actually decreased: I used to order five times a week, and now I order twice a week.",
        ),
        "slot_spans": {"before": "five times a week", "current": "twice a week"},
        "polarity": "none",
        "relation": "decrease",
    },
    {
        "scenario_id": "transfer_ferry_current_time",
        "split": "transfer",
        "capability": "current_time",
        "answerable": True,
        "question": "What time is my ferry reservation now?",
        "question_frame": {
            "subject": "ferry reservation",
            "attribute": "departure time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["latest corrected user-stated departure time"],
        },
        "evidence_dialogue": (
            (
                "The ferry company changed my departure time.",
                "It is probably still the original 6:20 AM sailing.",
            ),
            (
                "No. The old time was 6:20 AM, and the confirmed departure is 7:55 AM now.",
                "Thanks, I will use the confirmed departure.",
            ),
        ),
        "required_evidence_quotes": (
            "No. The old time was 6:20 AM, and the confirmed departure is 7:55 AM now.",
        ),
        "slot_spans": {"current": "7:55 AM"},
        "polarity": "none",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_board_games_unknown_count",
        "split": "transfer",
        "capability": "unanswerable_count",
        "answerable": False,
        "question": "How many board games do I own now?",
        "question_frame": {
            "subject": "board games",
            "attribute": "current count",
            "time_focus": "current",
            "operation": "count",
            "answer_type": "number",
            "evidence_requirements": ["explicit user-stated current count"],
        },
        "evidence_dialogue": (
            (
                "I have not counted my board games since moving the shelf.",
                "There might be twelve of them.",
            ),
            (
                "Twelve is your estimate; I do not know the current count.",
                "Understood; the count is unknown.",
            ),
        ),
        "required_evidence_quotes": (
            "I have not counted my board games since moving the shelf.",
            "Twelve is your estimate; I do not know the current count.",
        ),
        "slot_spans": {},
        "polarity": "unknown",
        "relation": "none",
    },
    {
        "scenario_id": "transfer_dental_unknown_time",
        "split": "transfer",
        "capability": "unanswerable_time",
        "answerable": False,
        "question": "What time is my dental appointment?",
        "question_frame": {
            "subject": "dental appointment",
            "attribute": "appointment time",
            "time_focus": "current",
            "operation": "lookup",
            "answer_type": "time",
            "evidence_requirements": ["explicit user-stated confirmed appointment time"],
        },
        "evidence_dialogue": (
            (
                "The dental clinic has not confirmed my appointment time yet.",
                "Maybe it will be at 3:00 PM.",
            ),
            (
                "That dental appointment time is only your suggestion; the clinic has confirmed no time.",
                "I understand that the time is still unknown.",
            ),
        ),
        "required_evidence_quotes": (
            "The dental clinic has not confirmed my appointment time yet.",
            "That dental appointment time is only your suggestion; the clinic has confirmed no time.",
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
        "question_date": "2026-07-14 18:00:00",
        "question_frame": scenario["question_frame"],
        "session": {
            "session_id": f"session_{case_id}",
            "timestamp": "2026-07-13 18:00:00",
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
        "generated_at": "2026-07-14T08:06:21+00:00",
        "research_boundary": {
            "purpose": "development-only matched source-monitoring experiment",
            "official_benchmark_items_used": 0,
            "v1_case_reuse_count": 0,
            "v2_case_reuse_count": 0,
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
