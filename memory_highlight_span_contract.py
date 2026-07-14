#!/usr/bin/env python3
"""Reversible evidence highlights and controller-owned answer span contracts."""

import json
import re

from memory_evidence_ledger import NUMBER_WORDS
from memory_utterance_attention import canonical_answer_type


SPAN_CONTRACT_SCHEMA = "uruha_memory_span_contract_v2"
KNOWN_SLOTS = ("answer", "before", "current", "previous", "support")
POLARITIES = ("none", "yes", "no", "unknown")


_ROLE_HEADER = re.compile(r"(?m)^(User|Assistant):[ \t]*")
_HIGHLIGHT_TAG = re.compile(
    r"<memory-highlight rank=\"[1-9][0-9]*\">|</memory-highlight>"
)
_NEGATION = re.compile(
    r"\b(?:did\s+not|do\s+not|does\s+not|not|never|no|none|neither|without|"
    r"didn't|don't|doesn't)\b",
    re.IGNORECASE,
)
_DIGIT_NUMBER = re.compile(r"(?<!\w)-?\d+(?:\.\d+)?(?!\w)")
_WORD_TOKEN = re.compile(r"[a-z]+", re.IGNORECASE)
_TENS = {
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_UNITS = {
    word: int(value)
    for word, value in NUMBER_WORDS.items()
    if value.isdigit() and word not in {"once", "twice", "thrice"}
}


def _dialogue_content_spans(session_text):
    """Locate role content without rewriting any source bytes."""
    source = str(session_text or "")
    headers = list(_ROLE_HEADER.finditer(source))
    spans = []
    for turn_index, header in enumerate(headers):
        block_end = headers[turn_index + 1].start() if turn_index + 1 < len(headers) else len(source)
        content_end = block_end
        while content_end > header.end() and source[content_end - 1] in "\r\n":
            content_end -= 1
        spans.append(
            {
                "turn_index": turn_index,
                "role": header.group(1).lower(),
                "content_start": header.end(),
                "content_end": content_end,
            }
        )
    return spans


def annotate_highlights(session_text, selected_utterances):
    """Insert minimal inline tags around selected user turns while retaining all context."""
    source = str(session_text or "")
    spans = {row["turn_index"]: row for row in _dialogue_content_spans(source)}
    insertions = []
    seen = set()
    for fallback_rank, selected in enumerate(selected_utterances or [], start=1):
        turn_index = selected.get("turn_index")
        if not isinstance(turn_index, int) or isinstance(turn_index, bool):
            raise ValueError("selected turn_index must be an integer")
        if turn_index in seen:
            raise ValueError(f"duplicate selected turn_index: {turn_index}")
        seen.add(turn_index)
        span = spans.get(turn_index)
        if span is None:
            raise ValueError(f"selected turn_index out of range: {turn_index}")
        if span["role"] != "user":
            raise ValueError(f"only user turns may be highlighted: {turn_index}")
        rank = selected.get("attention_rank", fallback_rank)
        if not isinstance(rank, int) or isinstance(rank, bool) or rank <= 0:
            raise ValueError("attention_rank must be a positive integer")
        # At an empty turn both offsets are equal. Apply the closing insertion
        # first so reverse-offset editing still yields <open></close>.
        insertions.append(
            (span["content_start"], 0, f'<memory-highlight rank="{rank}">')
        )
        insertions.append((span["content_end"], 1, "</memory-highlight>"))

    annotated = source
    for offset, _priority, value in sorted(
        insertions, key=lambda item: (item[0], item[1]), reverse=True
    ):
        annotated = f"{annotated[:offset]}{value}{annotated[offset:]}"
    if strip_highlight_tags(annotated) != source:
        raise AssertionError("highlight annotation did not preserve the source context")
    return annotated


def strip_highlight_tags(highlighted_text):
    """Remove only controller-inserted highlight tags."""
    return _HIGHLIGHT_TAG.sub("", str(highlighted_text or ""))


def required_slots(question_frame):
    """Derive semantic answer slots from the controller-owned question frame."""
    frame = question_frame or {}
    operation = str(frame.get("operation") or "lookup")
    time_focus = str(frame.get("time_focus") or "unspecified")
    if operation == "yes_no":
        return ("support",)
    if operation == "compare" or time_focus == "change_direction":
        return ("before", "current")
    if time_focus == "previous":
        return ("previous",)
    if time_focus == "current":
        return ("current",)
    return ("answer",)


def build_controller_contract(question_frame):
    """Freeze fields already known by the system instead of asking the model to choose them."""
    slots = required_slots(question_frame)
    answer_type = canonical_answer_type(question_frame)
    return {
        "schema": SPAN_CONTRACT_SCHEMA,
        "answer_type": answer_type,
        "required_slots": list(slots),
        "polarity_mode": "model_binds_yes_or_no" if answer_type == "yes_no" else "none",
        "relation_mode": (
            "controller_derives_from_numeric_spans" if answer_type == "compare" else "none"
        ),
    }


def build_span_binding_json_schema(question_frame):
    """Constrain model output to source binding only; contract fields stay controller-owned."""
    slots = required_slots(question_frame)
    answer_type = canonical_answer_type(question_frame)
    return {
        "type": "object",
        "properties": {
            "bindings": {
                "type": "array",
                "minItems": len(slots),
                "maxItems": len(slots),
                "items": {
                    "type": "object",
                    "properties": {
                        "slot": {"type": "string", "enum": list(slots)},
                        "source_index": {"type": "integer", "minimum": 0},
                        "answer_span": {"type": "string"},
                    },
                    "required": ["slot", "source_index", "answer_span"],
                    "additionalProperties": False,
                },
            },
            "polarity": {
                "type": "string",
                "enum": ["yes", "no", "unknown"] if answer_type == "yes_no" else ["none"],
            },
        },
        "required": ["bindings", "polarity"],
        "additionalProperties": False,
    }


def source_records_from_ledger(ledger):
    """Project grounded ledger events to immutable source records, ignoring coarse event roles."""
    records = []
    seen = set()
    for event in (ledger or {}).get("events") or []:
        record = {
            key: str(event.get(key) or "")
            for key in ("date", "session_id", "source_role", "source_quote", "attribute")
        }
        if not record["source_quote"]:
            continue
        key = tuple(record.values())
        if key in seen:
            continue
        seen.add(key)
        records.append({"source_index": len(records), **record})
    return records


def build_span_binding_prompt(question, question_date, source_records, question_frame):
    """Ask only for exact source bindings; no gold values or expected relation are exposed."""
    contract = build_controller_contract(question_frame)
    contract_text = json.dumps(contract, ensure_ascii=False, sort_keys=True)
    source_text = json.dumps(source_records or [], ensure_ascii=False, sort_keys=True)
    return (
        "Bind the controller-required semantic slots to exact source spans. Do not answer the "
        "question and do not alter the controller contract. Return exactly one binding for every "
        "required slot and no additional slots. source_index must reference one Source Record. "
        "answer_span must be the shortest verbatim substring of that record's source_quote that "
        "contains the requested value or explicit support. The same source_index may be reused "
        "when one sentence contains multiple values. For before/current slots, bind the earlier "
        "and later values separately. For a yes/no question, polarity must follow the explicit "
        "evidence; a no binding must retain the source negation. If the evidence is insufficient, "
        "use polarity=unknown for yes/no, but never invent a span.\n\n"
        f"Controller Contract: {contract_text}\n"
        f"Source Records: {source_text}\n\n"
        f"Current Date: {question_date}\nQuestion: {question}\nSource bindings JSON:"
    )


def _extract_json_object(value):
    text = str(value or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    elif not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def parse_span_binding(value):
    payload = _extract_json_object(value)
    if not isinstance(payload, dict) or set(payload) != {"bindings", "polarity"}:
        return None
    if payload.get("polarity") not in POLARITIES or not isinstance(payload.get("bindings"), list):
        return None
    for binding in payload["bindings"]:
        if not isinstance(binding, dict) or set(binding) != {
            "slot",
            "source_index",
            "answer_span",
        }:
            return None
        if binding["slot"] not in KNOWN_SLOTS:
            return None
        if (
            not isinstance(binding["source_index"], int)
            or isinstance(binding["source_index"], bool)
            or not isinstance(binding["answer_span"], str)
        ):
            return None
    return payload


def _anchored_span(source_quote, candidate):
    source = str(source_quote or "")
    span = str(candidate or "").strip()
    if not source or not span:
        return ""
    parts = re.split(r"(\s+)", span)
    pattern = "".join(r"\s+" if part.isspace() else re.escape(part) for part in parts)
    left = r"(?<!\w)" if span[0].isalnum() else ""
    right = r"(?!\w)" if span[-1].isalnum() else ""
    match = re.search(f"{left}{pattern}{right}", source, re.IGNORECASE)
    return source[match.start() : match.end()] if match else ""


def _extract_scalar(value):
    """Parse the first simple numeric value used by deterministic comparison rendering."""
    text = str(value or "")
    digit = _DIGIT_NUMBER.search(text)
    if digit:
        return float(digit.group(0))
    current = 0
    total = 0
    found = False
    for token in _WORD_TOKEN.findall(text.lower().replace("-", " ")):
        if token in _UNITS:
            current += _UNITS[token]
            found = True
        elif token in _TENS:
            current += _TENS[token]
            found = True
        elif token == "hundred" and found:
            current = max(1, current) * 100
        elif token == "thousand" and found:
            total += max(1, current) * 1000
            current = 0
        elif found:
            break
    return float(total + current) if found else None


def _derived_relation(bindings_by_slot):
    before = _extract_scalar((bindings_by_slot.get("before") or {}).get("answer_span"))
    current = _extract_scalar((bindings_by_slot.get("current") or {}).get("answer_span"))
    if before is None or current is None:
        return "unknown"
    if current > before:
        return "increase"
    if current < before:
        return "decrease"
    return "same"


def validate_span_binding(binding_payload, source_records, question_frame):
    """Validate exact slots and source spans, then derive system-owned relation fields."""
    required = required_slots(question_frame)
    answer_type = canonical_answer_type(question_frame)
    errors = []
    if binding_payload is None:
        return {
            "valid": False,
            "errors": ["schema_parse_failed"],
            "contract": None,
            "audits": {
                "slot_complete": False,
                "all_spans_grounded": False,
                "grounded_binding_count": 0,
                "binding_count": 0,
            },
        }

    raw_bindings = list(binding_payload.get("bindings") or [])
    slots = [binding.get("slot") for binding in raw_bindings]
    missing = [slot for slot in required if slot not in slots]
    extras = [slot for slot in slots if slot not in required]
    duplicates = sorted({slot for slot in slots if slots.count(slot) > 1})
    if missing:
        errors.append(f"missing_slots:{','.join(missing)}")
    if extras:
        errors.append(f"unexpected_slots:{','.join(sorted(set(extras)))}")
    if duplicates:
        errors.append(f"duplicate_slots:{','.join(duplicates)}")
    slot_complete = not missing and not extras and not duplicates and len(slots) == len(required)

    records = list(source_records or [])
    grounded = []
    seen_bindings = set()
    for binding in raw_bindings:
        source_index = binding.get("source_index")
        if not isinstance(source_index, int) or not 0 <= source_index < len(records):
            errors.append("source_index_out_of_range")
            continue
        record = records[source_index]
        anchored = _anchored_span(record.get("source_quote"), binding.get("answer_span"))
        if not anchored:
            errors.append("answer_span_not_grounded")
            continue
        key = (binding.get("slot"), source_index, anchored)
        if key in seen_bindings:
            continue
        seen_bindings.add(key)
        grounded.append(
            {
                "slot": binding.get("slot"),
                "source_index": source_index,
                "answer_span": anchored,
                "source_quote": record.get("source_quote"),
                "date": record.get("date"),
                "session_id": record.get("session_id"),
                "source_role": record.get("source_role"),
                "attribute": record.get("attribute"),
            }
        )

    all_spans_grounded = bool(raw_bindings) and len(grounded) == len(raw_bindings)
    by_slot = {binding["slot"]: binding for binding in grounded}
    polarity = binding_payload.get("polarity")
    relation = "none"
    if answer_type == "yes_no":
        if polarity not in {"yes", "no"}:
            errors.append("yes_no_polarity_unresolved")
        support = by_slot.get("support") or {}
        has_negation = bool(_NEGATION.search(str(support.get("answer_span") or "")))
        source_has_negation = bool(
            _NEGATION.search(str(support.get("source_quote") or ""))
        )
        if polarity == "no" and not has_negation:
            errors.append("no_polarity_without_grounded_negation")
        if polarity == "yes" and (has_negation or source_has_negation):
            errors.append("yes_polarity_conflicts_with_grounded_negation")
    elif polarity != "none":
        errors.append("nonbinary_polarity_must_be_none")

    if answer_type == "compare":
        relation = _derived_relation(by_slot)
        if relation == "unknown":
            errors.append("numeric_relation_unresolved")

    contract = {
        **build_controller_contract(question_frame),
        "polarity": polarity,
        "relation": relation,
        "bindings": grounded,
    }
    return {
        "valid": not errors,
        "errors": errors,
        "contract": contract,
        "audits": {
            "slot_complete": slot_complete,
            "all_spans_grounded": all_spans_grounded,
            "grounded_binding_count": len(grounded),
            "binding_count": len(raw_bindings),
        },
    }


def render_span_contract(validation):
    """Render only a validated semantic contract; personality styling remains downstream."""
    if not validation or not validation.get("valid"):
        return ""
    contract = validation["contract"]
    by_slot = {binding["slot"]: binding["answer_span"] for binding in contract["bindings"]}
    if contract["answer_type"] == "yes_no":
        prefix = "Yes" if contract["polarity"] == "yes" else "No"
        return f"{prefix} - {by_slot['support']}."
    if contract["answer_type"] == "compare":
        return f"{by_slot['before']} -> {by_slot['current']}; {contract['relation']}."
    values = [by_slot[slot] for slot in contract["required_slots"]]
    return "; ".join(values) + "."
