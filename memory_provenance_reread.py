#!/usr/bin/env python3
"""Source monitoring and deterministic sufficiency checks for memory answers."""

import copy
import re

from memory_evidence_ledger import align_fact_to_source, reconcile_ledger_state
from memory_highlight_span_contract import strip_highlight_tags
from memory_utterance_attention import canonical_answer_type


_UNCERTAINTY_PATTERNS = (
    re.compile(r"\b(?:do not|don't|cannot|can't) (?:know|remember)\b", re.I),
    re.compile(r"\bnot (?:decided|confirmed|counted|known|sure)\b", re.I),
    re.compile(r"\bhave not (?:decided|confirmed|counted)\b", re.I),
    re.compile(r"\bhas not (?:decided|confirmed|counted)\b", re.I),
    re.compile(r"\bneed to (?:choose|decide|confirm|count)\b", re.I),
    re.compile(r"\bonly (?:your|a) (?:guess|suggestion|estimate|assumption)\b", re.I),
    re.compile(r"\byour (?:guess|suggestion|estimate|assumption)\b", re.I),
    re.compile(r"\bnot something I confirmed\b", re.I),
    re.compile(r"\b(?:still )?unknown\b", re.I),
    re.compile(r"\bno (?:location|time|count|answer) (?:has been|is) confirmed\b", re.I),
)
_TIME = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\s*(?:a\.?m\.?|p\.?m\.?)?\b", re.I)
_FREQUENCY = re.compile(
    r"\b(?:every(?: other)? (?:morning|evening|day|week|month|year)|"
    r"once|twice|thrice|\d+ times?)\s*(?:a|per|each)?\s*"
    r"(?:morning|evening|day|week|month|year)?\b",
    re.I,
)
_LOCATION = re.compile(
    r"\b(?:in|inside|into|on|under|beneath|beside|near|at)\s+"
    r"(?:the\s+|my\s+)?(?:[a-z][a-z-]*\s+){0,4}[a-z][a-z-]*\b",
    re.I,
)
_OWNERSHIP = re.compile(
    r"\b(?:own|owned|have|had|did not own|didn't own|do not own|don't own)\b",
    re.I,
)
_CHANGE_CUE = re.compile(
    r"\b(?:used to|before|previously|now|current|from|to|increase|increased|"
    r"decrease|decreased|longer|shorter|more|less)\b",
    re.I,
)
_NUMBER_EXPRESSION = re.compile(
    r"(?<!\w)(?:\d+(?:\.\d+)?|once|twice|thrice|zero|one|two|three|four|five|"
    r"six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty(?:[- ](?:one|two|three|four|five|six|"
    r"seven|eight|nine))?|thirty(?:[- ](?:one|two|three|four|five|six|seven|"
    r"eight|nine))?|forty(?:[- ](?:one|two|three|four|five|six|seven|eight|"
    r"nine))?|fifty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?)"
    r"(?!\w)",
    re.I,
)


def sanitize_extracted_evidence(evidence, original_context):
    """Ground extracted facts and repair only controller-owned highlight markup."""
    source = str(original_context or "")
    facts = []
    repairs = []
    dropped = []
    for index, fact in enumerate((evidence or {}).get("facts") or []):
        raw_quote = str(fact.get("quote") or "")
        raw_role = str(fact.get("source_role") or "")
        alignment = align_fact_to_source(raw_quote, source, raw_role)
        repair_attempted = False
        if alignment is None:
            stripped = strip_highlight_tags(raw_quote)
            if stripped != raw_quote:
                repair_attempted = True
                alignment = align_fact_to_source(stripped, source, raw_role)
                repairs.append(
                    {
                        "fact_index": index,
                        "raw_quote": raw_quote,
                        "stripped_quote": stripped,
                        "grounded": alignment is not None,
                    }
                )
        if alignment is None:
            dropped.append(
                {
                    "fact_index": index,
                    "quote": raw_quote,
                    "repair_attempted": repair_attempted,
                }
            )
            continue
        grounded = copy.deepcopy(fact)
        grounded["quote"] = alignment["quote"]
        grounded["source_role"] = alignment["source_role"]
        facts.append(grounded)
    return {
        "evidence": {"relevant": bool(facts), "facts": facts},
        "audit": {
            "input_fact_count": len((evidence or {}).get("facts") or []),
            "accepted_fact_count": len(facts),
            "dropped_fact_count": len(dropped),
            "markup_repair_attempt_count": len(repairs),
            "markup_repair_success_count": sum(row["grounded"] for row in repairs),
            "all_markup_repairs_grounded": all(row["grounded"] for row in repairs),
            "repairs": repairs,
            "dropped": dropped,
        },
    }


def filter_note_to_authoritative_user(note):
    """Keep the user's own autobiographical evidence without changing source text."""
    output = copy.deepcopy(note)
    evidence = output.get("evidence") or {"relevant": False, "facts": []}
    facts = [
        copy.deepcopy(fact)
        for fact in evidence.get("facts") or []
        if fact.get("source_role") == "user"
    ]
    output["evidence"] = {"relevant": bool(facts), "facts": facts}
    output["accepted_grounded_fact_count"] = len(facts)
    output["source_filter_audit"] = {
        "input_fact_count": len(evidence.get("facts") or []),
        "accepted_user_fact_count": len(facts),
        "rejected_nonuser_fact_count": len(evidence.get("facts") or []) - len(facts),
    }
    return output


def filter_ledger_to_authoritative_user(ledger):
    """Project a ledger to user-source events and remap every event index."""
    if not isinstance(ledger, dict):
        return None
    output = copy.deepcopy(ledger)
    events = list(output.get("events") or [])
    kept_old_indices = [
        index for index, event in enumerate(events) if event.get("source_role") == "user"
    ]
    remap = {old: new for new, old in enumerate(kept_old_indices)}
    output["events"] = [copy.deepcopy(events[index]) for index in kept_old_indices]
    for key in (
        "current_event_indices",
        "superseded_event_indices",
        "historical_event_indices",
    ):
        output[key] = [
            remap[index]
            for index in output.get(key) or []
            if index in remap
        ]
    output["source_filter_audit"] = {
        "input_event_count": len(events),
        "accepted_user_event_count": len(output["events"]),
        "rejected_nonuser_event_count": len(events) - len(output["events"]),
    }
    return reconcile_ledger_state(output)


def merge_authoritative_ledgers(*ledgers):
    """Merge deduplicated user-source events from independent evidence passes."""
    filtered = [
        filter_ledger_to_authoritative_user(ledger)
        for ledger in ledgers
        if isinstance(ledger, dict)
    ]
    if not filtered:
        return None
    base = copy.deepcopy(filtered[0])
    events = []
    seen = set()
    uncertainties = []
    for ledger in filtered:
        uncertainties.extend(str(item) for item in ledger.get("uncertainties") or [])
        for event in ledger.get("events") or []:
            key = tuple(
                str(event.get(field) or "")
                for field in ("date", "session_id", "source_role", "source_quote", "attribute")
            )
            if key in seen:
                continue
            seen.add(key)
            events.append(copy.deepcopy(event))
    base["events"] = events
    base["current_event_indices"] = list(range(len(events)))
    base["superseded_event_indices"] = []
    base["historical_event_indices"] = list(range(len(events)))
    base["uncertainties"] = list(dict.fromkeys(uncertainties))
    base["merge_audit"] = {
        "input_ledger_count": len(filtered),
        "merged_event_count": len(events),
        "all_events_user_source": all(
            event.get("source_role") == "user" for event in events
        ),
    }
    return reconcile_ledger_state(base)


def ledger_source_audit(ledger):
    events = list((ledger or {}).get("events") or [])
    user_count = sum(event.get("source_role") == "user" for event in events)
    assistant_count = sum(event.get("source_role") == "assistant" for event in events)
    return {
        "event_count": len(events),
        "user_event_count": user_count,
        "assistant_event_count": assistant_count,
        "authoritative_user_evidence_rate": user_count / len(events) if events else 1.0,
        "assistant_fact_admission_rate": assistant_count / len(events) if events else 0.0,
    }


def _segments_from_user_ledger(ledger):
    quotes = []
    seen = set()
    for event in (ledger or {}).get("events") or []:
        if event.get("source_role") != "user":
            continue
        quote = str(event.get("source_quote") or "").strip()
        if not quote or quote in seen:
            continue
        seen.add(quote)
        quotes.append(quote)
    segments = []
    for quote in quotes:
        for segment in re.split(r"(?<=[.!?])\s+|;\s*", quote):
            segment = segment.strip()
            if segment:
                segments.append(segment)
    return quotes, segments


def _is_uncertain(segment):
    return any(pattern.search(segment) for pattern in _UNCERTAINTY_PATTERNS)


def _shape_check(answer_type, eligible_segments):
    text = " ".join(eligible_segments)
    if answer_type == "time":
        return bool(_TIME.search(text)), "explicit_clock_time"
    if answer_type == "count":
        return bool(_NUMBER_EXPRESSION.search(text)), "explicit_numeric_quantity"
    if answer_type == "frequency":
        return bool(_FREQUENCY.search(text)), "explicit_cadence"
    if answer_type == "location":
        return bool(_LOCATION.search(text)), "explicit_placement"
    if answer_type == "yes_no":
        return bool(_OWNERSHIP.search(text)), "explicit_ownership_proposition"
    if answer_type == "compare":
        numbers = _NUMBER_EXPRESSION.findall(text)
        return bool(len(numbers) >= 2 and _CHANGE_CUE.search(text)), "two_endpoints_and_change"
    return bool(text.strip()), "explicit_text"


def evaluate_evidence_sufficiency(ledger, question_frame):
    """Evaluate evidence shape without access to gold answers or answerability labels."""
    authoritative = filter_ledger_to_authoritative_user(ledger)
    source_audit = ledger_source_audit(authoritative)
    quotes, segments = _segments_from_user_ledger(authoritative)
    uncertain = [segment for segment in segments if _is_uncertain(segment)]
    eligible = [segment for segment in segments if not _is_uncertain(segment)]
    answer_type = canonical_answer_type(question_frame)
    shape_ok, required_shape = _shape_check(answer_type, eligible)
    sufficient = bool(source_audit["user_event_count"] and eligible and shape_ok)
    if not source_audit["user_event_count"]:
        reason = "no_grounded_user_events"
    elif not eligible:
        reason = "only_uncertain_user_evidence"
    elif not shape_ok:
        reason = f"missing_{required_shape}"
    else:
        reason = "sufficient_grounded_user_evidence"
    return {
        "sufficient": sufficient,
        "reason": reason,
        "answer_type": answer_type,
        "required_shape": required_shape,
        "source_audit": source_audit,
        "source_quotes": quotes,
        "eligible_segments": eligible,
        "uncertain_segments": uncertain,
        "gold_used": False,
    }


def explicit_abstention_detected(response, fixed_abstention=""):
    text = str(response or "").strip().lower()
    if not text:
        return False
    if fixed_abstention and text == fixed_abstention.strip().lower():
        return True
    markers = (
        "not enough grounded",
        "insufficient evidence",
        "not enough evidence",
        "cannot determine",
        "can't determine",
        "do not know",
        "don't know",
        "is unknown",
        "not been decided",
        "hasn't been decided",
        "not been confirmed",
        "hasn't been confirmed",
        "no confirmed",
        "not specified",
    )
    return any(marker in text for marker in markers)
