#!/usr/bin/env python3
"""Prompt and validation helpers for chronological memory evidence ledgers."""

import copy
import json
import re


LEDGER_SCHEMA = "uruha_memory_evidence_ledger_v3"
VALUE_ROLES = [
    "state",
    "cumulative_total",
    "incremental_event",
    "threshold",
    "remaining_amount",
    "frequency",
    "location",
    "ownership",
    "binary",
    "other",
]
UPDATEABLE_VALUE_ROLES = frozenset(
    {
        "state",
        "cumulative_total",
        "threshold",
        "remaining_amount",
        "frequency",
        "location",
        "ownership",
        "binary",
    }
)
QUESTION_FRAME_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "attribute": {"type": "string"},
        "time_focus": {
            "type": "string",
            "enum": [
                "current",
                "previous",
                "historical_total",
                "change_direction",
                "specific_time",
                "unspecified",
            ],
        },
        "operation": {
            "type": "string",
            "enum": ["lookup", "count", "compare", "aggregate", "yes_no", "locate"],
        },
        "answer_type": {"type": "string"},
        "evidence_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "subject",
        "attribute",
        "time_focus",
        "operation",
        "answer_type",
        "evidence_requirements",
    ],
    "additionalProperties": False,
}
EVIDENCE_NOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_role": {
                        "type": "string",
                        "enum": ["user", "assistant"],
                    },
                    "quote": {"type": "string"},
                    "attribute": {"type": "string"},
                },
                "required": [
                    "source_role",
                    "quote",
                    "attribute",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["relevant", "facts"],
    "additionalProperties": False,
}
LEDGER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "schema": {"type": "string", "enum": [LEDGER_SCHEMA]},
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "session_id": {"type": "string"},
                    "source_role": {
                        "type": "string",
                        "enum": ["user", "assistant"],
                    },
                    "source_quote": {"type": "string"},
                    "attribute": {"type": "string"},
                    "claim": {"type": "string"},
                    "value": {"type": "string"},
                    "value_role": {"type": "string", "enum": VALUE_ROLES},
                    "relation": {
                        "type": "string",
                        "enum": ["adds", "updates", "confirms", "contradicts"],
                    },
                },
                "required": [
                    "date",
                    "session_id",
                    "source_role",
                    "source_quote",
                    "attribute",
                    "claim",
                    "value",
                    "value_role",
                    "relation",
                ],
                "additionalProperties": False,
            },
        },
        "current_event_indices": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0},
        },
        "superseded_event_indices": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0},
        },
        "historical_event_indices": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0},
        },
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "schema",
        "events",
        "current_event_indices",
        "superseded_event_indices",
        "historical_event_indices",
        "uncertainties",
    ],
    "additionalProperties": False,
}
NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
    "once": "1",
    "twice": "2",
    "thrice": "3",
}
ANSWER_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "are",
        "at",
        "before",
        "currently",
        "do",
        "every",
        "from",
        "have",
        "in",
        "is",
        "it",
        "my",
        "now",
        "of",
        "on",
        "previously",
        "the",
        "to",
        "too",
        "user",
        "was",
        "we",
        "you",
        "your",
    }
)


def chronological_sessions(sessions):
    """Return a copy sorted by timestamp without changing retrieval membership."""
    return sorted(
        [dict(session) for session in sessions],
        key=lambda session: str(session.get("timestamp") or ""),
    )


def build_direct_answer_prompt(question, question_date, sessions):
    history = "\n\n".join(
        f"### Session {index}\n{session['text']}"
        for index, session in enumerate(chronological_sessions(sessions), start=1)
    )
    return (
        "I will give you several history chats between you and a user. "
        "Answer the question using only relevant history. Give only a concise final answer.\n\n"
        f"History Chats:\n{history}\n\n"
        f"Current Date: {question_date}\nQuestion: {question}\nAnswer:"
    )


def build_question_frame_prompt(question, question_date):
    return (
        "Decompose the current question into a memory-search frame. Do not answer it and do "
        "not invent facts. The evidence will come only from past chats, not external records. "
        "Identify the subject, requested attribute, temporal focus, operation, expected answer "
        "type, and what chat evidence would be sufficient. For increase/decrease questions, "
        "attribute must name the underlying quantity or state being changed; encode the direction "
        "request in time_focus and operation, never in attribute. For yes/no questions, use "
        "operation=yes_no and a yes/no answer type.\n\n"
        f"Current Date: {question_date}\nQuestion: {question}\nMemory-search frame JSON:"
    )


def augment_question_frame(frame):
    """Add temporal evidence invariants that a single model call may omit."""
    if not isinstance(frame, dict):
        return None
    output = {
        key: list(value) if isinstance(value, list) else value
        for key, value in frame.items()
    }
    requirements = output.setdefault("evidence_requirements", [])
    additions = []
    if output.get("time_focus") == "previous":
        additions.append(
            "Extract every dated value of the requested attribute, including the later/current "
            "value needed to prove which earlier value is previous."
        )
    elif output.get("time_focus") == "current":
        additions.append(
            "Extract dated corrections and competing values so the latest explicit value can "
            "be selected."
        )
    if output.get("time_focus") == "change_direction" or output.get("operation") == "compare":
        additions.append(
            "Extract both the before and after values; neither endpoint alone establishes a change."
        )
    if output.get("time_focus") == "historical_total" or output.get("operation") == "aggregate":
        additions.append(
            "Distinguish cumulative totals from separate incremental events to prevent double counting."
        )
    for addition in additions:
        if addition not in requirements:
            requirements.append(addition)
    return output


def audit_question_frame(question, frame):
    """Correct generic temporal confusions without using any benchmark answer."""
    if not isinstance(frame, dict):
        return None
    output = {
        key: list(value) if isinstance(value, list) else value
        for key, value in frame.items()
    }
    text = str(question or "").lower()
    previous_cue = bool(
        re.search(r"\b(previous|previously|prior)\b", text)
        or re.search(r"\bused to\b", text)
        or re.search(r"\bbefore\b.*\b(current|now|latest)\b", text)
    )
    specific_time_cue = bool(re.search(r"\bbefore\b", text))
    current_cue = bool(
        re.search(r"\b(now|currently|current|latest)\b", text)
        or re.search(r"\bdo i have\b", text)
        or re.search(r"\bhow many\b.*\bdo i need\b", text)
    )
    historical_total_cue = bool(
        re.search(r"\b(in|over|during) the past\b", text)
        or re.search(r"\b(so far|to date)\b", text)
        or re.search(r"\bhow many times\b", text)
        or re.search(r"\bhow many\b.*\bhave i\b", text)
    )
    change_direction_cue = "increase" in text and "decrease" in text
    yes_no_text = re.sub(
        r"^(?:before|after|when|while)\b[^,?]*,\s*",
        "",
        text,
        count=1,
    ).strip()
    yes_no_cue = bool(
        re.match(
            r"^(?:do|did|have|has|am|was|were|can|could|should|would|will)\s+i\b",
            yes_no_text,
        )
    )
    dual_time_cue = bool(
        previous_cue
        and current_cue
        and (
            output.get("time_focus") == "change_direction"
            or output.get("operation") == "compare"
            or text.count("?") >= 2
        )
    )
    if change_direction_cue or dual_time_cue:
        output["time_focus"] = "change_direction"
        output["operation"] = "compare"
        output["answer_type"] = "direction with before and after values"
        changed_attribute = re.search(
            r"\b(?:increase or decrease|decrease or increase)\s+(?:the\s+)?(.+?)(?:\?|$)",
            text,
        )
        if changed_attribute:
            output["attribute"] = changed_attribute.group(1).strip()
    elif previous_cue:
        output["time_focus"] = "previous"
    elif specific_time_cue:
        # A present-tense auxiliary inside a past boundary (for example,
        # "Before X, do I have Y?") must not move the question to now.
        output["time_focus"] = "specific_time"
    elif historical_total_cue and output.get("operation") in {
        "count",
        "aggregate",
        "lookup",
    }:
        output["time_focus"] = "historical_total"
    elif current_cue:
        output["time_focus"] = "current"
    if yes_no_cue and not change_direction_cue:
        output["operation"] = "yes_no"
        output["answer_type"] = "yes/no with a concise supporting fact"
        if not any(
            (previous_cue, specific_time_cue, historical_total_cue, current_cue)
        ):
            output["time_focus"] = "current"
    return output


def _user_utterance_index(session_text):
    return "\n".join(
        line.strip()
        for line in str(session_text or "").splitlines()
        if line.lstrip().startswith("User:")
    )


def focused_user_utterances(question, question_frame, session_text, limit=3):
    """Select high-overlap user turns for one fail-closed extraction retry."""
    frame = question_frame or {}
    target = " ".join(
        (
            str(question or ""),
            str(frame.get("subject") or ""),
            str(frame.get("attribute") or ""),
        )
    )
    target_tokens = {
        token
        for token in normalized_answer_text(target).split()
        if len(token) > 2 and token not in ANSWER_STOPWORDS
    }
    scored = []
    for index, line in enumerate(str(session_text or "").splitlines()):
        if not line.lstrip().startswith("User:"):
            continue
        line_tokens = set(normalized_answer_text(line).split())
        overlap = target_tokens & line_tokens
        if len(overlap) >= 2:
            scored.append((len(overlap), index, line.strip()))
    selected = sorted(
        sorted(scored, key=lambda item: (-item[0], item[1]))[: max(1, limit)],
        key=lambda item: item[1],
    )
    return "\n".join(item[2] for item in selected)


def build_evidence_note_prompt(question, question_date, question_frame, session):
    frame = json.dumps(question_frame, ensure_ascii=False, sort_keys=True)
    attribute = str(question_frame.get("attribute") or "the requested attribute")
    temporal_rule = ""
    if question_frame.get("time_focus") == "previous":
        temporal_rule = (
            "Because time_focus is previous, every explicit dated value of the same attribute "
            "is relevant: a later/current value is required to prove that an earlier value "
            "became previous. Mark a session with either endpoint relevant. "
        )
    elif question_frame.get("time_focus") in {"change_direction", "specific_time"}:
        temporal_rule = (
            "Extract every dated value of the same attribute needed to establish the requested "
            "time relationship, even if one value is not itself the final answer. "
        )
    return (
        "Prepare evidence from one past chat for a current memory question; do not answer the "
        "question. First scan every line in the User-Utterance Index, including the final user "
        "turn, then verify against the full session. Search the entire session, including both "
        "user and assistant lines. Use the "
        "question frame to extract every explicit candidate fact about the user. An older value "
        "may become the requested previous value only after a later session updates it, so keep "
        "all explicit competing values. Preserve corrections, negation, numbers, dates, units, "
        "frequency, location, and ownership. quote must copy the shortest supporting sentence "
        "exactly; do not paraphrase, negate, summarize, or infer its meaning in this stage. "
        "Generic advice, model guesses, and unstated inferences are not user facts. "
        f"{temporal_rule}For each fact, attribute must describe {attribute!r}. If there is no "
        "explicit evidence, set relevant=false and facts=[].\n\n"
        f"Question: {question}\nQuestion Frame: {frame}\n"
        f"Session Date: {session['timestamp']}\n"
        f"User-Utterance Index:\n{_user_utterance_index(session['text']) or '- none'}\n\n"
        f"Session Content:\n{session['text']}\n\n"
        f"Question Date: {question_date}\nGrounded evidence JSON:"
    )


def build_focused_evidence_note_prompt(question_frame, focused_text):
    """Use a small single-purpose prompt after deterministic turn selection."""
    subject = str((question_frame or {}).get("subject") or "the user")
    attribute = str((question_frame or {}).get("attribute") or "the requested attribute")
    attribute_key = re.sub(r"[_-]+", " ", f"{subject} {attribute}".lower())
    if re.search(r"\b(?:frequency|cadence|schedule|interval|how often)\b", attribute_key):
        scan_rule = (
            "First scan each complete sentence for an explicit recurring interval or cadence "
            "tied to the requested activity."
        )
    elif re.search(r"\b(?:location|where|placement|placed|hanging)\b", attribute_key):
        scan_rule = (
            "First scan each complete sentence for an explicit physical placement or location "
            "tied to the requested subject."
        )
    elif re.search(r"\b(?:count|number|quantity|amount|how many)\b", attribute_key):
        scan_rule = (
            "First scan each complete sentence for an explicit number or quantity tied to the "
            "requested subject."
        )
    else:
        scan_rule = (
            "First scan each complete sentence for an explicit value or state tied to the "
            "requested subject and attribute."
        )
    return (
        f"Extract explicit evidence for {subject!r}, attribute {attribute!r}, from the user "
        f"utterances below. {scan_rule} A fact in an incidental comparison, reminder, correction, "
        "or aside still counts. Do not answer any question and do not infer unstated facts. Copy "
        "the shortest supporting sentence exactly and preserve the explicit value or state "
        "verbatim. If explicit evidence exists, relevant must be true. Otherwise return "
        "relevant=false and facts=[].\n\n"
        f"User utterances:\n{focused_text}\n\nGrounded evidence JSON:"
    )


def _grounded_note_lines(notes):
    lines = []
    for note in sorted(notes, key=lambda item: str(item.get("timestamp") or "")):
        evidence = note.get("evidence") or {}
        for fact in evidence.get("facts") or []:
            lines.append(
                json.dumps(
                    {
                        "date": note.get("timestamp"),
                        "session_id": note.get("session_id"),
                        **fact,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    return lines


def build_notes_answer_prompt(question, question_date, question_frame, notes):
    note_text = "\n".join(f"- {line}" for line in _grounded_note_lines(notes))
    frame = json.dumps(question_frame, ensure_ascii=False, sort_keys=True)
    return (
        "You are given grounded chronological evidence independently extracted from past chat "
        "sessions. Use only this evidence and the question frame. Later explicit updates replace "
        "earlier values of the same state or threshold. A newer cumulative_total replaces an "
        "older cumulative_total; incremental_event values are added only when they are distinct "
        "events. Give only a concise final answer.\n\n"
        f"Question Frame: {frame}\n"
        f"Evidence Notes:\n{note_text or '- no relevant evidence'}\n\n"
        f"Current Date: {question_date}\nQuestion: {question}\nAnswer:"
    )


def build_ledger_prompt(question, question_date, question_frame, notes):
    note_text = "\n".join(f"- {line}" for line in _grounded_note_lines(notes))
    frame = json.dumps(question_frame, ensure_ascii=False, sort_keys=True)
    return (
        "Convert grounded chronological evidence into a versioned memory ledger. Do not answer "
        "the question and do not add unstated facts. Use the question frame only to decide which "
        "attribute and time relationship matter. A later explicit state, threshold, frequency, "
        "location, ownership, or binary fact updates an earlier value of the same attribute. A "
        "newer cumulative_total replaces the older total. Keep distinct incremental events as "
        "historical event indices instead of erasing or double-counting them. Copy each input "
        "date, session_id, source_role, source quote, and attribute exactly into its event. Group "
        "updates only when attribute matches. Create exactly one event for every grounded fact: "
        "do not omit, merge, or duplicate source facts. Number events from zero in array order, "
        "then place every event index in at least one index list. current_event_indices and "
        "superseded_event_indices must not overlap; historical_event_indices may overlap either "
        "because a present or superseded state is also part of history. Do not write free-form "
        "state summaries outside grounded events. "
        "When user and assistant claims conflict in the same session, an explicit user correction "
        "supersedes the assistant claim; assistant guesses must never override user self-report. "
        "value_role must describe the semantic role of the value, never the speaker role. The "
        "first dated value of an attribute normally adds it; a later changed value updates it. "
        "The grounded evidence contains exact source quotes; interpret those quotes directly and "
        "never invent a negation or value absent from them.\n\n"
        f"Question Frame: {frame}\n"
        f"Grounded Evidence:\n{note_text or '- no relevant evidence'}\n\n"
        f"Current Date: {question_date}\nQuestion: {question}\nEvidence ledger JSON:"
    )


def _parse_json_object(value):
    text = str(value or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    elif not text.startswith("{"):
        object_match = re.search(r"\{.*\}", text, re.DOTALL)
        if object_match:
            text = object_match.group(0)
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _matches_schema_keys(payload, schema):
    required = set(schema.get("required") or [])
    return isinstance(payload, dict) and set(payload) == required


def parse_question_frame(value):
    payload = _parse_json_object(value)
    if not _matches_schema_keys(payload, QUESTION_FRAME_SCHEMA):
        return None
    if payload["time_focus"] not in QUESTION_FRAME_SCHEMA["properties"]["time_focus"]["enum"]:
        return None
    if payload["operation"] not in QUESTION_FRAME_SCHEMA["properties"]["operation"]["enum"]:
        return None
    if not isinstance(payload["evidence_requirements"], list):
        return None
    scalar_keys = {"subject", "attribute", "time_focus", "operation", "answer_type"}
    return payload if all(isinstance(payload[key], str) for key in scalar_keys) else None


def parse_evidence_note(value):
    payload = _parse_json_object(value)
    if not _matches_schema_keys(payload, EVIDENCE_NOTE_SCHEMA):
        return None
    if not isinstance(payload["relevant"], bool) or not isinstance(payload["facts"], list):
        return None
    fact_schema = EVIDENCE_NOTE_SCHEMA["properties"]["facts"]["items"]
    for fact in payload["facts"]:
        if not _matches_schema_keys(fact, fact_schema):
            return None
        if not all(isinstance(value, str) for value in fact.values()):
            return None
        if fact["source_role"] not in {"user", "assistant"}:
            return None
    if payload["relevant"] != bool(payload["facts"]):
        return None
    return payload


_QUOTE_EQUIVALENCE = str.maketrans(
    {
        '"': "'",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": "'",
        "\u201d": "'",
    }
)
_QUOTE_WRAPPERS = frozenset({'"', "'", "\u2018", "\u2019", "\u201c", "\u201d"})


def align_quote_to_source(quote, source_text):
    """Return the exact source span when only quote punctuation differs."""
    if not isinstance(quote, str) or not quote or not isinstance(source_text, str):
        return None
    if quote in source_text:
        return quote
    candidate = quote.strip()
    if (
        len(candidate) >= 2
        and candidate[0] in _QUOTE_WRAPPERS
        and candidate[-1] in _QUOTE_WRAPPERS
    ):
        candidate = candidate[1:-1].strip()
    canonical_candidate = candidate.translate(_QUOTE_EQUIVALENCE)
    canonical_source = source_text.translate(_QUOTE_EQUIVALENCE)
    start = canonical_source.find(canonical_candidate)
    if start < 0:
        return None
    return source_text[start : start + len(candidate)]


def align_fact_to_source(quote, source_text, source_role):
    """Align a quote to its exact turn and repair a uniquely wrong speaker role."""
    requested_role = str(source_role or "").lower()
    role_lines = {"user": [], "assistant": []}
    for line in str(source_text or "").splitlines():
        match = re.match(r"\s*(User|Assistant):\s*(.*)", line, re.IGNORECASE)
        if match:
            role_lines[match.group(1).lower()].append(match.group(2))
    role_order = [requested_role] if requested_role in role_lines else []
    role_order.extend(role for role in ("user", "assistant") if role not in role_order)
    for role in role_order:
        for utterance in role_lines[role]:
            aligned = align_quote_to_source(quote, utterance)
            if aligned is not None:
                return {
                    "quote": aligned,
                    "source_role": role,
                    "quote_repaired": aligned != quote,
                    "role_repaired": role != requested_role,
                }
    aligned = align_quote_to_source(quote, source_text)
    if aligned is None:
        return None
    return {
        "quote": aligned,
        "source_role": requested_role,
        "quote_repaired": aligned != quote,
        "role_repaired": False,
    }


def evidence_quotes_are_grounded(evidence, source_text):
    """Require every quote to align exactly or by quote-punctuation equivalence."""
    if not isinstance(evidence, dict) or not isinstance(source_text, str):
        return False
    return all(
        align_fact_to_source(
            fact.get("quote"), source_text, fact.get("source_role")
        )
        is not None
        for fact in evidence.get("facts") or []
    )


def filter_grounded_evidence(evidence, source_text):
    """Drop ungrounded extracted facts while preserving independently valid facts."""
    if not isinstance(evidence, dict) or not isinstance(source_text, str):
        return None
    facts = []
    for fact in evidence.get("facts") or []:
        alignment = align_fact_to_source(
            fact.get("quote"), source_text, fact.get("source_role")
        )
        if alignment is None:
            continue
        grounded_fact = copy.deepcopy(fact)
        grounded_fact["quote"] = alignment["quote"]
        grounded_fact["source_role"] = alignment["source_role"]
        facts.append(grounded_fact)
    return {"relevant": bool(facts), "facts": facts}


def parse_ledger(value):
    payload = _parse_json_object(value)
    if not _matches_schema_keys(payload, LEDGER_JSON_SCHEMA):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != LEDGER_SCHEMA:
        return None
    if not isinstance(payload.get("events"), list):
        return None
    event_schema = LEDGER_JSON_SCHEMA["properties"]["events"]["items"]
    for event in payload["events"]:
        if not _matches_schema_keys(event, event_schema):
            return None
        if not all(isinstance(value, str) for value in event.values()):
            return None
        if event["source_role"] not in {"user", "assistant"}:
            return None
        if event["relation"] not in {"adds", "updates", "confirms", "contradicts"}:
            return None
        if event["value_role"] not in VALUE_ROLES:
            return None
    index_keys = (
        "current_event_indices",
        "superseded_event_indices",
        "historical_event_indices",
    )
    index_groups = []
    for key in index_keys:
        values = payload.get(key)
        if not isinstance(values, list) or not all(
            isinstance(item, int)
            and not isinstance(item, bool)
            and 0 <= item < len(payload["events"])
            for item in values
        ):
            return None
        if len(values) != len(set(values)):
            return None
        index_groups.append(set(values))
    if index_groups[0] & index_groups[1]:
        return None
    if set().union(*index_groups) != set(range(len(payload["events"]))):
        return None
    if not isinstance(payload.get("uncertainties"), list) or not all(
        isinstance(item, str) for item in payload["uncertainties"]
    ):
        return None
    return payload


def ground_ledger_events(ledger, notes):
    """Validate source provenance and restore canonical dates from grounded notes."""
    if not isinstance(ledger, dict) or not isinstance(notes, list):
        return None
    grounded = {}
    grounded_order = []
    grounded_count = 0
    for note in notes:
        evidence = note.get("evidence") or {}
        facts = evidence.get("facts") or []
        offsets = note.get("fact_source_offsets") or list(range(len(facts)))
        ordered_facts = sorted(
            zip(facts, offsets),
            key=lambda item: item[1],
        )
        for fact, _ in ordered_facts:
            key = (
                str(note.get("session_id") or ""),
                fact.get("source_role"),
                fact.get("quote"),
                fact.get("attribute"),
            )
            grounded_count += 1
            if key in grounded:
                return None
            grounded[key] = str(note.get("timestamp") or "")
            grounded_order.append(key)
    ledger_provenance = []
    ledger_quote_alignment_repairs = []
    ledger_role_alignment_repairs = []
    for index, event in enumerate(ledger.get("events") or []):
        exact_key = (
            event.get("session_id"),
            event.get("source_role"),
            event.get("source_quote"),
            event.get("attribute"),
        )
        if exact_key in grounded:
            ledger_provenance.append(exact_key)
            continue
        candidates = [
            key
            for key in grounded
            if key[0] == event.get("session_id")
            and key[3] == event.get("attribute")
            and align_quote_to_source(event.get("source_quote"), key[2]) is not None
        ]
        if len(candidates) != 1:
            return None
        canonical_key = candidates[0]
        ledger_provenance.append(canonical_key)
        if canonical_key[2] != event.get("source_quote"):
            ledger_quote_alignment_repairs.append(index)
        if canonical_key[1] != event.get("source_role"):
            ledger_role_alignment_repairs.append(index)
    if (
        len(set(ledger_provenance)) != len(ledger_provenance)
        or not set(ledger_provenance).issubset(grounded)
    ):
        return None
    event_by_key = {
        key: copy.deepcopy(event)
        for key, event in zip(ledger_provenance, ledger["events"])
    }
    old_key_by_index = list(ledger_provenance)
    included_order = [key for key in grounded_order if key in event_by_key]
    omitted_order = [key for key in grounded_order if key not in event_by_key]
    new_index_by_key = {key: index for index, key in enumerate(included_order)}
    output = copy.deepcopy(ledger)
    output["events"] = []
    for key in included_order:
        event = event_by_key[key]
        event["date"] = grounded[key]
        event["source_role"] = key[1]
        event["source_quote"] = key[2]
        output["events"].append(event)
    for list_name in (
        "current_event_indices",
        "superseded_event_indices",
        "historical_event_indices",
    ):
        output[list_name] = sorted(
            new_index_by_key[old_key_by_index[index]]
            for index in ledger.get(list_name) or []
        )
    output["ledger_quote_alignment_repairs"] = ledger_quote_alignment_repairs
    output["ledger_role_alignment_repairs"] = ledger_role_alignment_repairs
    output["omitted_grounded_facts"] = [
        {
            "session_id": key[0],
            "source_role": key[1],
            "source_quote": key[2],
            "attribute": key[3],
        }
        for key in omitted_order
    ]
    output["ledger_fact_coverage"] = (
        len(included_order) / grounded_count if grounded_count else 1.0
    )
    return output


def ledger_events_are_grounded(ledger, notes):
    """Return whether every ledger event has exact extracted source provenance."""
    return ground_ledger_events(ledger, notes) is not None


def _numeric_tokens(value):
    text = re.sub(r"\[\s*\d+\s*\]", " ", str(value or ""))
    text = re.sub(r"\b(?:incremental_)?event[_\s-]*\d+\b", " ", text, flags=re.I)
    return {
        token
        for token in normalized_answer_text(text).split()
        if token.isdigit()
    }


def ledger_derived_numeric_conflicts(ledger):
    """Find derived numbers that are absent from the exact source quote."""
    conflicts = []
    for index, event in enumerate((ledger or {}).get("events") or []):
        quote_numbers = _numeric_tokens(event.get("source_quote"))
        derived_numbers = _numeric_tokens(
            f"{event.get('claim') or ''} {event.get('value') or ''}"
        )
        unsupported = sorted(derived_numbers - quote_numbers)
        if quote_numbers and unsupported:
            conflicts.append(
                {
                    "event_index": index,
                    "source_quote_numbers": sorted(quote_numbers),
                    "unsupported_derived_numbers": unsupported,
                }
            )
    return conflicts


def reconcile_ledger_state(ledger):
    """Apply generic chronology and user-source authority to state-like events."""
    if not isinstance(ledger, dict):
        return None
    output = copy.deepcopy(ledger)
    events = output.get("events") or []
    semantic_repairs = []
    for index, event in enumerate(events):
        if (
            event.get("value_role") == "incremental_event"
            and event.get("relation") == "updates"
        ):
            # An update replaces a running value; treating it as an additive
            # event would double-count when an older observation also exists.
            event["value_role"] = "cumulative_total"
            semantic_repairs.append(
                {
                    "event_index": index,
                    "field": "value_role",
                    "from": "incremental_event",
                    "to": "cumulative_total",
                    "reason": "updates_relation_is_non_additive",
                }
            )
    current = set(output.get("current_event_indices") or [])
    superseded = set(output.get("superseded_event_indices") or [])
    by_attribute = {}
    for index, event in enumerate(events):
        if event.get("value_role") in UPDATEABLE_VALUE_ROLES:
            by_attribute.setdefault(event.get("attribute"), []).append(index)
    for indices in by_attribute.values():
        latest_date = max(events[index]["date"] for index in indices)
        latest = [index for index in indices if events[index]["date"] == latest_date]
        latest_user = [
            index for index in latest if events[index].get("source_role") == "user"
        ]
        winner = max(latest_user or latest)
        current.difference_update(indices)
        superseded.difference_update(indices)
        current.add(winner)
        superseded.update(index for index in indices if index != winner)
    output["current_event_indices"] = sorted(current)
    output["superseded_event_indices"] = sorted(superseded)
    output["historical_event_indices"] = list(range(len(events)))
    output["semantic_repairs"] = semantic_repairs
    output["derived_numeric_conflicts"] = ledger_derived_numeric_conflicts(output)
    return output


def _indexed_events(ledger, index_key):
    events = ledger.get("events") or []
    return [
        (index, events[index])
        for index in ledger.get(index_key) or []
        if isinstance(index, int) and 0 <= index < len(events)
    ]


def _latest_authoritative_event(indexed_events):
    if not indexed_events:
        return []
    latest_date = max(event.get("date", "") for _, event in indexed_events)
    latest = [
        (index, event)
        for index, event in indexed_events
        if event.get("date", "") == latest_date
    ]
    user_events = [
        (index, event)
        for index, event in latest
        if event.get("source_role") == "user"
    ]
    return [max(user_events or latest, key=lambda item: item[0])[1]]


def _prefer_explicit_numeric_events(indexed_events):
    numeric = [
        (index, event)
        for index, event in indexed_events
        if _numeric_tokens(event.get("source_quote"))
    ]
    return numeric or indexed_events


def _source_anchored_span(source_quote, candidate):
    """Return the exact source span only when a derived phrase is verbatim-grounded."""
    source = str(source_quote or "")
    phrase = str(candidate or "").strip()
    if not source or not phrase or not re.search(r"[A-Za-z0-9]", phrase):
        return ""
    parts = re.split(r"(\s+)", phrase)
    pattern = "".join(r"\s+" if part.isspace() else re.escape(part) for part in parts)
    match = re.search(rf"(?<!\w){pattern}(?!\w)", source, flags=re.IGNORECASE)
    return source[match.start() : match.end()] if match else ""


def _answer_event_projection(event, evidence_role):
    """Expose provenance to the reader, never unverified model-derived values."""
    output = {"evidence_role": evidence_role}
    output.update(
        {
            key: event.get(key)
            for key in ("date", "session_id", "source_role", "source_quote", "attribute")
        }
    )
    anchored_claim = _source_anchored_span(
        event.get("source_quote"), event.get("claim")
    )
    if anchored_claim:
        output["source_anchored_claim"] = anchored_claim
    return output


def ledger_answer_view(ledger, question_frame):
    """Project the ledger into the smallest evidence view needed by the question."""
    frame = question_frame or {}
    time_focus = frame.get("time_focus") or "unspecified"
    operation = frame.get("operation") or "lookup"
    current = _indexed_events(ledger, "current_event_indices")
    superseded = _indexed_events(ledger, "superseded_event_indices")
    historical = _indexed_events(ledger, "historical_event_indices")
    target_events = []
    context_events = []
    if time_focus == "previous":
        target_events = [
            _answer_event_projection(event, "previous")
            for event in _latest_authoritative_event(superseded)
        ]
        context_events = [
            _answer_event_projection(event, "current_context")
            for _, event in current
        ]
        rule = "Answer from the latest superseded event; current events are contrast only."
    elif time_focus == "change_direction" or operation == "compare":
        before_events = _prefer_explicit_numeric_events(superseded)
        current_events = _prefer_explicit_numeric_events(current)
        target_events = [
            *(
                _answer_event_projection(event, "before")
                for _, event in before_events
            ),
            *(
                _answer_event_projection(event, "current")
                for _, event in current_events
            ),
        ]
        rule = "Answer both before and current roles, then state the direction of change."
    elif time_focus == "specific_time":
        target_events = [
            *(
                _answer_event_projection(event, "earlier_state")
                for _, event in superseded
            ),
            *(
                _answer_event_projection(event, "later_state_or_boundary_context")
                for _, event in current
            ),
        ]
        rule = "Use all dated states to answer the requested historical boundary."
    elif time_focus == "historical_total" or operation == "aggregate":
        current_cumulative = [
            event for _, event in current if event.get("value_role") == "cumulative_total"
        ]
        if current_cumulative:
            target_events = [
                _answer_event_projection(event, "current_cumulative_total")
                for event in current_cumulative
            ]
            rule = "Use the latest current cumulative total; do not add superseded totals."
        else:
            additive_events = [
                event
                for _, event in historical
                if event.get("value_role") == "incremental_event"
                and event.get("relation") == "adds"
            ]
            if additive_events:
                target_events = [
                    _answer_event_projection(event, "distinct_increment")
                    for event in additive_events
                ]
                rule = "Add only distinct incremental events marked as additions."
            else:
                target_events = [
                    _answer_event_projection(event, "latest_observation")
                    for event in _latest_authoritative_event(historical)
                ]
                rule = (
                    "No validated additive events exist; use only the latest authoritative "
                    "historical observation instead of summing ambiguous evidence."
                )
    else:
        target_events = [
            _answer_event_projection(event, "current") for _, event in current
        ]
        rule = "Answer only from current events; superseded events are intentionally excluded."
    return {
        "time_focus": time_focus,
        "operation": operation,
        "selection_rule": rule,
        "target_events": target_events,
        "context_events": context_events,
        "uncertainties": ledger.get("uncertainties") or [],
    }


def build_ledger_answer_prompt(question, question_date, ledger, question_frame=None):
    payload = json.dumps(
        ledger_answer_view(ledger, question_frame),
        ensure_ascii=False,
        sort_keys=True,
    )
    return (
        "Answer the current question using only the audited memory evidence view. target_events "
        "are the only facts allowed to determine the answer. context_events may explain a change "
        "but must never replace target_events. The view deliberately contains exact source_quote "
        "evidence and excludes model-derived claim/value fields. evidence_role states how each "
        "quote participates in the answer; do not copy a before value into the current role. "
        "When source_anchored_claim is present, it is a verbatim span validated against that "
        "event's source_quote: preserve it exactly for that evidence_role and never simplify, "
        "broaden, or substitute it. "
        "For compare or change_direction views, explicitly state the before value and current "
        "value from their separate target_events before the direction, even if the question "
        "only asks whether something increased or decreased. "
        "Follow selection_rule exactly and answer every role requested by the question. "
        "If evidence is insufficient, say so. Give only a concise final answer.\n\n"
        f"Audited Evidence View:\n{payload}\n\n"
        f"Current Date: {question_date}\nQuestion: {question}\nAnswer:"
    )


def normalized_answer_text(value):
    text = str(value or "").lower().replace("’", "'")
    contractions = {
        r"\b([a-z]+)'ve\b": r"\1 have",
        r"\b([a-z]+)'re\b": r"\1 are",
        r"\b([a-z]+)'ll\b": r"\1 will",
        r"\b([a-z]+)'d\b": r"\1 would",
        r"\b([a-z]+)n't\b": r"\1 not",
    }
    for pattern, replacement in contractions.items():
        text = re.sub(pattern, replacement, text)
    for word, number in NUMBER_WORDS.items():
        text = re.sub(rf"\b{word}\b", number, text)
    frequency_equivalents = {
        "weekly": "every week",
        "daily": "every day",
        "monthly": "every month",
        "yearly": "every year",
        "annually": "every year",
    }
    for word, phrase in frequency_equivalents.items():
        text = re.sub(rf"\b{word}\b", phrase, text)
    text = re.sub(r"\b(my|your)\b", "user", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _explicit_frequency_phrases(normalized_text):
    patterns = (
        r"\bevery other (?:day|week|month|year)s?\b",
        r"\bevery \d+ (?:day|week|month|year)s?\b",
        r"\b\d+ times? (?:a|per) (?:day|week|month|year)\b",
        r"\bevery (?:day|week|month|year)\b",
    )
    return {
        match.group(0)
        for pattern in patterns
        for match in re.finditer(pattern, normalized_text)
    }


def strict_answer_support(gold, response, question=""):
    """Conservative lexical diagnostic; official LLM judging remains separate."""
    gold_text = normalized_answer_text(gold)
    response_text = normalized_answer_text(response)
    if not gold_text or not response_text:
        return False
    unanswerable_markers = (
        "not explicitly mentioned",
        "not specified",
        "not documented",
        "cannot determine",
        "insufficient evidence",
        "no relevant evidence",
    )
    if any(marker in str(response or "").lower() for marker in unanswerable_markers):
        return False
    if gold_text in response_text:
        return True
    gold_tokens = [
        token for token in gold_text.split() if token not in ANSWER_STOPWORDS
    ]
    response_tokens = set(response_text.split())
    if not gold_tokens:
        return False
    numeric_tokens = {token for token in gold_tokens if token.isdigit()}
    if numeric_tokens and not numeric_tokens.issubset(response_tokens):
        return False
    normalized_question = normalized_answer_text(question)
    response_numeric_tokens = {
        token for token in response_tokens if token.isdigit()
    }
    if (
        len(numeric_tokens) == 1
        and normalized_question.startswith("how many")
        and response_numeric_tokens == numeric_tokens
    ):
        return True
    gold_frequencies = _explicit_frequency_phrases(gold_text)
    response_frequencies = _explicit_frequency_phrases(response_text)
    if gold_frequencies and not gold_frequencies.issubset(response_frequencies):
        return False
    if gold_frequencies and "how often" in normalized_question:
        return True
    if gold_tokens[0] in {"yes", "no"} and gold_tokens[0] not in response_tokens:
        return False
    coverage = sum(token in response_tokens for token in gold_tokens) / len(gold_tokens)
    return coverage >= 0.8
