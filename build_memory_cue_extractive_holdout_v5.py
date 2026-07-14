#!/usr/bin/env python3
"""Build the frozen, scenario-disjoint V5 memory fallback holdout."""

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "uruha_memory_cue_extractive_holdout_v5"
POSITIONS = ("beginning", "middle", "end")
DEFAULT_OUTPUT = Path("datasets/memory_cue_extractive_holdout_v5.json")


FILLER_TURNS = (
    ("I aired out the winter scarf this morning.", "It should smell fresher now."),
    ("A red bus waited beside the museum.", "That route often stops there."),
    ("I polished the handle of the old kettle.", "The metal should look brighter."),
    ("The bakery put sesame rolls in the front window.", "They must be easy to notice."),
    ("I sorted the spare charging cables.", "That should make the drawer less tangled."),
    ("A gardener trimmed the hedge near the station.", "The path may feel wider now."),
    ("I washed the small paint tray after lunch.", "It will be ready for the next project."),
    ("The stationery shop changed its paper display.", "Regular visitors may spot that."),
    ("I tightened the loose screw on the coat hook.", "It should hold weight more safely."),
    ("A delivery van paused outside the pharmacy.", "It was probably unloading supplies."),
    ("I wiped the dust from the radio dial.", "The markings should be easier to read."),
    ("The river path had new direction signs.", "That may help first-time walkers."),
)


def scenario(
    scenario_id,
    split,
    capability,
    question,
    subject,
    attribute,
    time_focus,
    operation,
    answer_type,
    evidence_dialogue,
    required_evidence_quotes,
    slot_spans,
    *,
    answerable=True,
    polarity="none",
    relation="none",
):
    return {
        "scenario_id": scenario_id,
        "split": split,
        "capability": capability,
        "answerable": answerable,
        "question": question,
        "question_frame": {
            "subject": subject,
            "attribute": attribute,
            "time_focus": time_focus,
            "operation": operation,
            "answer_type": answer_type,
            "evidence_requirements": ["explicit user-grounded evidence matching the requested answer shape"],
        },
        "evidence_dialogue": evidence_dialogue,
        "required_evidence_quotes": required_evidence_quotes,
        "slot_spans": slot_spans,
        "polarity": polarity,
        "relation": relation,
    }


SCENARIOS = (
    scenario(
        "holdout_a_ceramic_bowls_current_count",
        "holdout_a",
        "current_count",
        "How many handmade ceramic bowls do I have now?",
        "handmade ceramic bowls",
        "current count",
        "current",
        "count",
        "number",
        (
            ("I recounted my handmade ceramic bowls after clearing the cabinet.", "You may have six bowls now."),
            ("Six was only your guess. Including the two from my aunt, I have eleven handmade ceramic bowls altogether now.", "I will use your confirmed total."),
        ),
        ("Six was only your guess. Including the two from my aunt, I have eleven handmade ceramic bowls altogether now.",),
        {"current": "eleven"},
    ),
    scenario(
        "holdout_a_vaccination_card_current_location",
        "holdout_a",
        "current_location",
        "Where is my vaccination card currently stored?",
        "vaccination card",
        "storage location",
        "current",
        "locate",
        "location",
        (
            ("I moved my vaccination card while checking my travel documents.", "It may be in the kitchen drawer."),
            ("It is not in the kitchen. I slid it into the clear sleeve behind my passport.", "I will remember the clear sleeve location."),
        ),
        ("It is not in the kitchen. I slid it into the clear sleeve behind my passport.",),
        {"current": "clear sleeve behind my passport"},
    ),
    scenario(
        "holdout_a_farmers_market_previous_frequency",
        "holdout_a",
        "previous_frequency",
        "How often did I visit the farmers market before changing jobs?",
        "farmers market visits",
        "visit frequency",
        "previous",
        "lookup",
        "frequency",
        (
            ("My farmers market routine changed when my work schedule shifted.", "Perhaps you used to go every week."),
            ("Before changing jobs I went every other Sunday; now I visit on the first Saturday of each month.", "I understand the old and new routines."),
        ),
        ("Before changing jobs I went every other Sunday; now I visit on the first Saturday of each month.",),
        {"previous": "every other Sunday"},
    ),
    scenario(
        "holdout_a_walking_commute_decrease",
        "holdout_a",
        "change_direction",
        "Did my walking commute become longer or shorter, and from how long to how long?",
        "walking commute",
        "duration",
        "change_direction",
        "compare",
        "direction with before and after values",
        (
            ("My walking commute changed after the riverside shortcut opened.", "The shortcut may still take longer."),
            ("It used to take forty-two minutes and now takes twenty-eight minutes, so it became shorter.", "That is a clear decrease in duration."),
        ),
        ("It used to take forty-two minutes and now takes twenty-eight minutes, so it became shorter.",),
        {"before": "forty-two minutes", "current": "twenty-eight minutes"},
        relation="decrease",
    ),
    scenario(
        "holdout_a_premove_rice_cooker_ownership",
        "holdout_a",
        "historical_yes_no",
        "Before moving into this apartment, did I own a rice cooker?",
        "rice cooker ownership before moving",
        "ownership",
        "specific_time",
        "yes_no",
        "yes/no with concise support",
        (
            ("Before moving here, I already owned the rice cooker but not the toaster oven.", "I thought both appliances were new."),
            ("The rice cooker came with me from the old place; only the toaster oven was bought later.", "Thanks for correcting the appliance history."),
        ),
        (
            "Before moving here, I already owned the rice cooker but not the toaster oven.",
            "The rice cooker came with me from the old place; only the toaster oven was bought later.",
        ),
        {"support": "rice cooker"},
        polarity="yes",
    ),
    scenario(
        "holdout_a_optometrist_current_time",
        "holdout_a",
        "current_time",
        "At what time is my rescheduled optometrist visit?",
        "optometrist appointment",
        "appointment time",
        "current",
        "lookup",
        "time",
        (
            ("The optometrist changed my appointment again.", "It may still be at 1:20 PM."),
            ("The 1:20 PM slot was canceled. My confirmed appointment is at 9:10 AM.", "I will use the confirmed morning time."),
        ),
        ("The 1:20 PM slot was canceled. My confirmed appointment is at 9:10 AM.",),
        {"current": "9:10 AM"},
    ),
    scenario(
        "holdout_a_fountain_pens_current_count",
        "holdout_a",
        "current_count",
        "What is my current total number of fountain pens?",
        "fountain pens",
        "current count",
        "current",
        "count",
        "number",
        (
            ("I counted my fountain pens after giving one away.", "Maybe eight remain."),
            ("After the gift and the recent purchase, the total is thirteen fountain pens now.", "I will use thirteen as the current total."),
        ),
        ("After the gift and the recent purchase, the total is thirteen fountain pens now.",),
        {"current": "thirteen"},
    ),
    scenario(
        "holdout_a_spare_glasses_current_location",
        "holdout_a",
        "current_location",
        "Where are my spare glasses now?",
        "spare glasses",
        "storage location",
        "current",
        "locate",
        "location",
        (
            ("I relocated my spare glasses before going to the gym.", "They are probably on the bathroom shelf."),
            ("Not the bathroom shelf. I put them in the side pocket of my blue gym bag.", "I will remember the gym bag pocket."),
        ),
        ("Not the bathroom shelf. I put them in the side pocket of my blue gym bag.",),
        {"current": "side pocket of my blue gym bag"},
    ),
    scenario(
        "holdout_a_choir_previous_frequency",
        "holdout_a",
        "previous_frequency",
        "How often did choir rehearsal happen before it became weekly?",
        "choir rehearsal",
        "rehearsal frequency",
        "previous",
        "lookup",
        "frequency",
        (
            ("The choir changed its rehearsal schedule for the concert season.", "It may always have met weekly."),
            ("Before the weekly schedule, we rehearsed three evenings per month.", "I understand the earlier cadence."),
        ),
        ("Before the weekly schedule, we rehearsed three evenings per month.",),
        {"previous": "three evenings per month"},
    ),
    scenario(
        "holdout_a_bike_lock_unknown_digit_count",
        "holdout_a",
        "unanswerable_count",
        "How many digits will my replacement bicycle-lock code have?",
        "replacement bicycle-lock code",
        "digit count",
        "current",
        "count",
        "number",
        (
            ("I have not chosen the length of the replacement bicycle-lock code.", "A five-digit code might work."),
            ("Five is only your suggestion; no number of digits has been confirmed.", "Understood; the code length is unknown."),
        ),
        (
            "I have not chosen the length of the replacement bicycle-lock code.",
            "Five is only your suggestion; no number of digits has been confirmed.",
        ),
        {},
        answerable=False,
        polarity="unknown",
    ),
    scenario(
        "holdout_a_parcel_locker_unknown_location",
        "holdout_a",
        "unanswerable_location",
        "Which parcel locker contains my delivery?",
        "parcel delivery",
        "locker location",
        "current",
        "locate",
        "location",
        (
            ("The delivery notice has not assigned a parcel locker yet.", "It could be locker C-14."),
            ("C-14 is only your guess; no locker has been confirmed for the delivery.", "I will keep the locker location unknown."),
        ),
        (
            "The delivery notice has not assigned a parcel locker yet.",
            "C-14 is only your guess; no locker has been confirmed for the delivery.",
        ),
        {},
        answerable=False,
        polarity="unknown",
    ),
    scenario(
        "holdout_a_weekend_pet_sitter_unknown_identity",
        "holdout_a",
        "unanswerable_identity",
        "Who will be my weekend pet sitter?",
        "weekend pet sitter",
        "person identity",
        "current",
        "lookup",
        "text",
        (
            ("I still have not selected a pet sitter for the weekend.", "Your neighbor Ken may be available."),
            ("Ken is only your suggestion; I have not confirmed any sitter.", "Understood; the sitter is still unknown."),
        ),
        (
            "I still have not selected a pet sitter for the weekend.",
            "Ken is only your suggestion; I have not confirmed any sitter.",
        ),
        {},
        answerable=False,
        polarity="unknown",
    ),
    scenario(
        "holdout_b_baking_tins_current_count",
        "holdout_b",
        "current_count",
        "How many round baking tins do I currently have?",
        "round baking tins",
        "current count",
        "current",
        "count",
        "number",
        (
            ("I counted the round baking tins after replacing the damaged one.", "You may have four tins."),
            ("Four was not the count. With the replacement included, I have eight round baking tins now.", "I will use the confirmed total of eight."),
        ),
        ("Four was not the count. With the replacement included, I have eight round baking tins now.",),
        {"current": "eight"},
    ),
    scenario(
        "holdout_b_insurance_policy_current_location",
        "holdout_b",
        "current_location",
        "Where is my insurance policy document now?",
        "insurance policy document",
        "storage location",
        "current",
        "locate",
        "location",
        (
            ("I moved the insurance policy document while reorganizing the office.", "It might be in the filing cabinet."),
            ("It is no longer in the cabinet. I placed it in the black binder on the bottom shelf.", "I will remember the black binder location."),
        ),
        ("It is no longer in the cabinet. I placed it in the black binder on the bottom shelf.",),
        {"current": "black binder on the bottom shelf"},
    ),
    scenario(
        "holdout_b_yoga_previous_frequency",
        "holdout_b",
        "previous_frequency",
        "How often did I attend yoga before switching to Friday mornings?",
        "yoga attendance",
        "attendance frequency",
        "previous",
        "lookup",
        "frequency",
        (
            ("My yoga routine changed after the studio revised its timetable.", "Perhaps you attended once a month."),
            ("Before switching to Friday mornings, I attended twice every week.", "I understand the previous frequency."),
        ),
        ("Before switching to Friday mornings, I attended twice every week.",),
        {"previous": "twice every week"},
    ),
    scenario(
        "holdout_b_laundry_cycle_decrease",
        "holdout_b",
        "change_direction",
        "How did my laundry cycle duration change, including both durations?",
        "laundry cycle",
        "duration",
        "change_direction",
        "compare",
        "direction with before and after values",
        (
            ("The laundry cycle changed after the machine update.", "The update may have made it slower."),
            ("The cycle fell from seventy-five minutes to fifty-two minutes, so it is shorter now.", "That is a decrease in duration."),
        ),
        ("The cycle fell from seventy-five minutes to fifty-two minutes, so it is shorter now.",),
        {"before": "seventy-five minutes", "current": "fifty-two minutes"},
        relation="decrease",
    ),
    scenario(
        "holdout_b_precollege_guitar_nonownership",
        "holdout_b",
        "historical_yes_no",
        "Before starting college, did I own a guitar?",
        "guitar ownership before college",
        "ownership",
        "specific_time",
        "yes_no",
        "yes/no with concise support",
        (
            ("Before college I owned a violin, but I had never owned a guitar.", "I thought both instruments were yours."),
            ("No guitar then; the violin was my only string instrument.", "Thanks for correcting the instrument history."),
        ),
        (
            "Before college I owned a violin, but I had never owned a guitar.",
            "No guitar then; the violin was my only string instrument.",
        ),
        {"support": "guitar"},
        polarity="no",
    ),
    scenario(
        "holdout_b_vaccination_appointment_current_time",
        "holdout_b",
        "current_time",
        "At what time is my vaccination appointment currently scheduled?",
        "vaccination appointment",
        "appointment time",
        "current",
        "lookup",
        "time",
        (
            ("The clinic rescheduled my vaccination appointment.", "It may remain at 11:50 AM."),
            ("The 11:50 AM booking was replaced; the confirmed time is 2:25 PM.", "I will use the afternoon confirmation."),
        ),
        ("The 11:50 AM booking was replaced; the confirmed time is 2:25 PM.",),
        {"current": "2:25 PM"},
    ),
    scenario(
        "holdout_b_hiking_route_increase",
        "holdout_b",
        "change_direction",
        "Did my hiking route become longer or shorter, and from what distance to what distance?",
        "hiking route",
        "distance",
        "change_direction",
        "compare",
        "direction with before and after values",
        (
            ("My hiking route changed after the lower trail closed.", "The detour may be shorter."),
            ("It increased from five kilometers to eight kilometers, so the route became longer.", "I see that the distance increased."),
        ),
        ("It increased from five kilometers to eight kilometers, so the route became longer.",),
        {"before": "five kilometers", "current": "eight kilometers"},
        relation="increase",
    ),
    scenario(
        "holdout_b_prephone_tablet_ownership",
        "holdout_b",
        "historical_yes_no",
        "Before buying my current phone, did I own a tablet?",
        "tablet ownership before current phone",
        "ownership",
        "specific_time",
        "yes_no",
        "yes/no with concise support",
        (
            ("I already owned the tablet before buying my current phone, but not a smartwatch.", "I assumed the tablet came later."),
            ("The tablet was already mine; the smartwatch was the later purchase.", "Thanks for clarifying the device timeline."),
        ),
        (
            "I already owned the tablet before buying my current phone, but not a smartwatch.",
            "The tablet was already mine; the smartwatch was the later purchase.",
        ),
        {"support": "tablet"},
        polarity="yes",
    ),
    scenario(
        "holdout_b_piano_lesson_current_time",
        "holdout_b",
        "current_time",
        "What time is my piano lesson now?",
        "piano lesson",
        "lesson time",
        "current",
        "lookup",
        "time",
        (
            ("My piano teacher moved this week's lesson.", "It may still begin at 4:30 PM."),
            ("The 4:30 PM slot is gone. The lesson is confirmed for 6:15 PM.", "I will remember the evening time."),
        ),
        ("The 4:30 PM slot is gone. The lesson is confirmed for 6:15 PM.",),
        {"current": "6:15 PM"},
    ),
    scenario(
        "holdout_b_volunteer_shift_unknown_frequency",
        "holdout_b",
        "unanswerable_frequency",
        "How often will I take a volunteer shift next month?",
        "volunteer shifts next month",
        "shift frequency",
        "current",
        "lookup",
        "frequency",
        (
            ("I have not chosen how often to volunteer next month.", "Twice a month might be manageable."),
            ("Twice a month is only your suggestion; no schedule has been decided.", "Understood; the frequency remains unknown."),
        ),
        (
            "I have not chosen how often to volunteer next month.",
            "Twice a month is only your suggestion; no schedule has been decided.",
        ),
        {},
        answerable=False,
        polarity="unknown",
    ),
    scenario(
        "holdout_b_charity_pickup_unknown_time",
        "holdout_b",
        "unanswerable_time",
        "What time will the charity pickup arrive?",
        "charity pickup",
        "arrival time",
        "current",
        "lookup",
        "time",
        (
            ("The charity has not confirmed a pickup time yet.", "They may arrive at 10:00 AM."),
            ("10:00 AM is only your guess; the arrival time is still unconfirmed.", "I will keep the time unknown."),
        ),
        (
            "The charity has not confirmed a pickup time yet.",
            "10:00 AM is only your guess; the arrival time is still unconfirmed.",
        ),
        {},
        answerable=False,
        polarity="unknown",
    ),
    scenario(
        "holdout_b_soldering_iron_unknown_ownership",
        "holdout_b",
        "unanswerable_ownership",
        "Do I currently own a soldering iron?",
        "current soldering iron ownership",
        "ownership",
        "current",
        "yes_no",
        "yes/no with concise support",
        (
            ("I have not checked whether the old soldering iron is still in my tools.", "You probably threw it away."),
            ("That is only your guess; I have not confirmed whether I still own it.", "Understood; current ownership is unknown."),
        ),
        (
            "I have not checked whether the old soldering iron is still in my tools.",
            "That is only your guess; I have not confirmed whether I still own it.",
        ),
        {},
        answerable=False,
        polarity="unknown",
    ),
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


def build_case(item, position):
    at = insertion_index(position)
    turns = [
        *FILLER_TURNS[:at],
        *item["evidence_dialogue"],
        *FILLER_TURNS[at:],
    ]
    case_id = f"{item['scenario_id']}__{position}"
    attention_quotes = [user for user, _assistant in item["evidence_dialogue"]]
    slot_spans = dict(item["slot_spans"])
    return {
        "case_id": case_id,
        "scenario_id": item["scenario_id"],
        "split": item["split"],
        "capability": item["capability"],
        "evidence_position": position,
        "question": item["question"],
        "question_date": "2026-08-01 18:00:00",
        "question_frame": item["question_frame"],
        "session": {
            "session_id": f"session_{case_id}",
            "timestamp": "2026-07-31 18:00:00",
            "text": render_session(turns),
        },
        "gold": {
            "answerable": item["answerable"],
            "expected_abstention": not item["answerable"],
            "attention_quotes": attention_quotes,
            "required_evidence_quotes": list(item["required_evidence_quotes"]),
            "assistant_decoy_quotes": [
                assistant for _user, assistant in item["evidence_dialogue"][:1]
            ],
            "slot_spans": slot_spans,
            "answer_spans": list(slot_spans.values()),
            "polarity": item["polarity"],
            "relation": item["relation"],
        },
    }


def build_payload():
    cases = [
        build_case(item, position)
        for item in SCENARIOS
        for position in POSITIONS
    ]
    payload = {
        "schema": SCHEMA,
        "generated_at": "2026-07-14T10:30:00+00:00",
        "research_boundary": {
            "purpose": "untouched replication of the frozen V4 fallback",
            "official_benchmark_items_used": 0,
            "v1_v2_v3_v4_scenario_or_question_reuse_count": 0,
            "all_cases_unseen_by_v4_treatment": True,
            "runtime_change_authorized": False,
            "split_note": "Both holdout_a and holdout_b contain only new, source-disjoint scenarios.",
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
