#!/usr/bin/env python3
"""Query-aware user-turn attention and source-anchored answer propositions."""

import json
import re

from memory_evidence_ledger import ANSWER_STOPWORDS, NUMBER_WORDS


PROPOSITION_SCHEMA = "uruha_memory_answer_proposition_v1"
PROPOSITION_RELATIONS = ("none", "yes", "no", "increase", "decrease", "same", "unknown")
PROPOSITION_ANSWER_TYPES = (
    "lookup",
    "count",
    "location",
    "time",
    "frequency",
    "yes_no",
    "compare",
    "text",
)
ANSWER_PROPOSITION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "schema": {"type": "string", "enum": [PROPOSITION_SCHEMA]},
        "answer_type": {"type": "string", "enum": list(PROPOSITION_ANSWER_TYPES)},
        "relation": {"type": "string", "enum": list(PROPOSITION_RELATIONS)},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target_index": {"type": "integer", "minimum": 0},
                    "answer_span": {"type": "string"},
                },
                "required": ["target_index", "answer_span"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["schema", "answer_type", "relation", "claims"],
    "additionalProperties": False,
}


_ROLE_LINE = re.compile(r"^(User|Assistant):\s*(.*)$", re.IGNORECASE)
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.IGNORECASE)
_TIME = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\s*(?:a\.?m\.?|p\.?m\.?)?\b", re.I)
_NUMBER_WORD_SET = frozenset(
    {
        *NUMBER_WORDS,
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
        "hundred",
    }
)
_QUERY_STOPWORDS = frozenset(
    {
        *ANSWER_STOPWORDS,
        "after",
        "another",
        "besides",
        "did",
        "does",
        "get",
        "how",
        "keep",
        "many",
        "new",
        "other",
        "what",
        "when",
        "where",
        "which",
    }
)
_CURRENT_CUES = re.compile(r"\b(?:now|currently|latest|today|no longer|these days)\b", re.I)
_PAST_CUES = re.compile(
    r"\b(?:before|previously|used to|old|originally|earlier|at that time|already)\b",
    re.I,
)
_CHANGE_CUES = re.compile(
    r"\b(?:changed?|moved?|updated?|instead|actually|correct(?:ed|ion)?|"
    r"no longer|not|but|used to|old|now|later|following)\b",
    re.I,
)
_LOCATION_CUES = re.compile(
    r"\b(?:inside|outside|above|below|under|beside|behind|near|drawer|cabinet|"
    r"shelf|closet|cupboard|box|bowl|desk|table|counter|garage|room)\b",
    re.I,
)
_FREQUENCY_CUES = re.compile(
    r"\b(?:every|daily|weekly|monthly|yearly|once|twice|times?\s+(?:a|per)|"
    r"mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?)\b",
    re.I,
)
_OWNERSHIP_CUES = re.compile(
    r"\b(?:have|had|own|owned|also|alongside|as well as|too|already)\b",
    re.I,
)


def parse_dialogue_turns(session_text):
    """Parse role-labelled history while preserving exact utterance text and order."""
    turns = []
    current = None
    for raw_line in str(session_text or "").splitlines():
        match = _ROLE_LINE.match(raw_line.strip())
        if match:
            if current is not None:
                turns.append(current)
            current = {
                "turn_index": len(turns),
                "role": match.group(1).lower(),
                "text": match.group(2).strip(),
            }
        elif current is not None and raw_line.strip():
            current["text"] = f"{current['text']}\n{raw_line.strip()}"
    if current is not None:
        turns.append(current)
    return turns


def _stem(token):
    token = token.lower().strip("-")
    if "-" in token:
        return " ".join(_stem(part) for part in token.split("-") if part)
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        stem = token[:-3]
        if len(stem) > 2 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if len(token) > 4 and token.endswith("ed"):
        stem = token[:-2]
        return stem[:-1] if len(stem) > 2 and stem[-1] == stem[-2] else stem
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text):
    output = []
    for raw in _TOKEN.findall(str(text or "").lower()):
        output.extend(part for part in _stem(raw).split() if part)
    return output


def _query_token_weights(question, question_frame):
    frame = question_frame or {}
    weighted_sources = (
        (question, 1.0),
        (frame.get("attribute"), 2.0),
        (frame.get("subject"), 3.0),
    )
    weights = {}
    for text, weight in weighted_sources:
        for token in _tokens(text):
            if len(token) <= 2 or token in _QUERY_STOPWORDS:
                continue
            weights[token] = max(weights.get(token, 0.0), weight)
    return weights


def _number_signal(text):
    tokens = set(_tokens(text))
    return bool(re.search(r"\b\d+(?:\.\d+)?\b", text) or tokens & _NUMBER_WORD_SET)


def _answer_shape_score(text, question_frame):
    frame = question_frame or {}
    answer_key = " ".join(
        str(frame.get(key) or "").lower()
        for key in ("attribute", "answer_type", "operation")
    )
    signals = []
    if "time" in answer_key and _TIME.search(text):
        signals.append(("time_value", 4.0))
    if any(word in answer_key for word in ("count", "number", "amount", "duration", "compare")):
        if _number_signal(text):
            signals.append(("numeric_value", 3.0))
    if any(word in answer_key for word in ("location", "locate", "where")):
        if _LOCATION_CUES.search(text):
            signals.append(("location_value", 3.0))
    if "frequency" in answer_key and _FREQUENCY_CUES.search(text):
        signals.append(("frequency_value", 4.0))
    if frame.get("operation") == "yes_no" and _OWNERSHIP_CUES.search(text):
        signals.append(("binary_support", 2.0))
    if frame.get("operation") == "compare" and re.search(
        r"\b(?:from|to|than|but|old|now|used to|takes?|allow)\b", text, re.I
    ):
        signals.append(("comparison_value", 3.0))
    return signals


def _temporal_signals(text, question_frame):
    focus = str((question_frame or {}).get("time_focus") or "")
    signals = []
    if focus == "current" and _CURRENT_CUES.search(text):
        signals.append(("current_cue", 2.0))
    if focus == "previous" and _PAST_CUES.search(text):
        signals.append(("previous_cue", 3.0))
    if focus == "specific_time" and _PAST_CUES.search(text):
        signals.append(("boundary_cue", 2.0))
    if focus == "change_direction" and (_PAST_CUES.search(text) or _CURRENT_CUES.search(text)):
        signals.append(("change_endpoint_cue", 2.0))
    if _CHANGE_CUES.search(text):
        signals.append(("update_cue", 1.0))
    return signals


def rank_user_utterances(question, question_frame, session_text, limit=4):
    """Rank user utterances without gold answers or source-position preference."""
    if limit <= 0:
        raise ValueError("limit must be positive")
    token_weights = _query_token_weights(question, question_frame)
    user_turns = [turn for turn in parse_dialogue_turns(session_text) if turn["role"] == "user"]
    scored = []
    for user_index, turn in enumerate(user_turns):
        turn_tokens = set(_tokens(turn["text"]))
        overlaps = sorted(token_weights.keys() & turn_tokens)
        lexical_score = sum(token_weights[token] for token in overlaps)
        shape_signals = _answer_shape_score(turn["text"], question_frame)
        temporal_signals = _temporal_signals(turn["text"], question_frame)
        signals = [*(f"term:{token}" for token in overlaps)]
        signals.extend(name for name, _ in shape_signals)
        signals.extend(name for name, _ in temporal_signals)
        scored.append(
            {
                **turn,
                "user_index": user_index,
                "overlap_count": len(overlaps),
                "lexical_score": lexical_score,
                "shape_score": sum(score for _, score in shape_signals),
                "temporal_score": sum(score for _, score in temporal_signals),
                "bridge_score": 0.0,
                "signals": signals,
            }
        )

    # Human working attention often binds an entity-introducing utterance to the
    # immediately following value/correction. Propagate relevance only one user turn.
    for anchor, value in zip(scored, scored[1:]):
        anchor_is_relevant = anchor["lexical_score"] >= 2.0 or (
            anchor["lexical_score"] > 0.0 and anchor["shape_score"] >= 2.0
        )
        if anchor_is_relevant and (
            value["shape_score"] > 0.0 or value["temporal_score"] > 0.0
        ):
            anchor["bridge_score"] += 2.0
            value["bridge_score"] += 4.0
            bridge_signal = f"adjacent_to_user_turn:{anchor['user_index']}"
            if bridge_signal not in value["signals"]:
                value["signals"].append(bridge_signal)

    for row in scored:
        row["score"] = round(
            row["lexical_score"]
            + row["shape_score"]
            + row["temporal_score"]
            + row["bridge_score"],
            4,
        )
    selected = sorted(
        (
            row
            for row in scored
            if row["overlap_count"] >= 2
            or row["bridge_score"] > 0.0
            or (row["lexical_score"] > 0.0 and row["shape_score"] >= 2.0)
        ),
        key=lambda row: (-row["score"], row["user_index"]),
    )[:limit]
    for rank, row in enumerate(selected, start=1):
        row["attention_rank"] = rank
    return sorted(selected, key=lambda row: row["user_index"])


def render_attention_context(selected_utterances):
    return "\n".join(
        f"User: {row['text']}" for row in selected_utterances if row.get("text")
    )


def canonical_answer_type(question_frame):
    frame = question_frame or {}
    operation = str(frame.get("operation") or "lookup")
    answer_type = str(frame.get("answer_type") or "").lower()
    attribute = str(frame.get("attribute") or "").lower()
    if operation == "yes_no":
        return "yes_no"
    if operation == "compare" or frame.get("time_focus") == "change_direction":
        return "compare"
    if operation == "count" or any(word in answer_type for word in ("number", "count")):
        return "count"
    if operation == "locate" or "location" in answer_type or "location" in attribute:
        return "location"
    if "time" in answer_type or "time" in attribute:
        return "time"
    if "frequency" in answer_type or "frequency" in attribute:
        return "frequency"
    if operation == "lookup":
        return "lookup"
    return "text"


def build_answer_proposition_prompt(question, question_date, answer_view, question_frame):
    indexed_view = dict(answer_view or {})
    indexed_view["target_events"] = [
        {"target_index": index, **event}
        for index, event in enumerate((answer_view or {}).get("target_events") or [])
    ]
    payload = json.dumps(indexed_view, ensure_ascii=False, sort_keys=True)
    answer_type = canonical_answer_type(question_frame)
    return (
        "Create a typed answer proposition from the audited evidence view; do not write the "
        "surface answer. Use target_events only. For every claim, target_index must reference "
        "one listed target event. answer_span must be the shortest verbatim substring of that "
        "event's source_quote that carries the answer value or supporting entity. Do not copy "
        "source_quote into the output because the system resolves provenance from target_index. Never "
        "copy from the question and never infer a value absent from a source quote. For a yes/no "
        "question, relation must be yes or no and a yes claim must preserve the concrete entity "
        "that makes it true. For comparison, include separate before and current claims and set "
        "relation to increase, decrease, or same. For other questions relation must be none. If "
        "evidence is insufficient, use relation=unknown and claims=[].\n\n"
        f"Required answer_type: {answer_type}\n"
        f"Audited Evidence View: {payload}\n\n"
        f"Current Date: {question_date}\nQuestion: {question}\nTyped proposition JSON:"
    )


def parse_answer_proposition(value):
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
    if not isinstance(payload, dict):
        return None
    if set(payload) != {"schema", "answer_type", "relation", "claims"}:
        return None
    if payload.get("schema") != PROPOSITION_SCHEMA:
        return None
    if payload.get("answer_type") not in PROPOSITION_ANSWER_TYPES:
        return None
    if payload.get("relation") not in PROPOSITION_RELATIONS:
        return None
    if not isinstance(payload.get("claims"), list):
        return None
    for claim in payload["claims"]:
        if not isinstance(claim, dict) or set(claim) != {"target_index", "answer_span"}:
            return None
        if not isinstance(claim["target_index"], int) or not isinstance(
            claim["answer_span"], str
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
    match = re.search(pattern, source, re.IGNORECASE)
    return source[match.start() : match.end()] if match else ""


def _required_roles(question_frame):
    frame = question_frame or {}
    if frame.get("operation") == "compare" or frame.get("time_focus") == "change_direction":
        return {"before", "current"}
    if frame.get("time_focus") == "previous":
        return {"previous"}
    if frame.get("time_focus") == "current":
        return {"current"}
    return set()


def validate_answer_proposition(proposition, answer_view, question_frame):
    """Validate schema, role, quote, and answer span without semantic guessing."""
    errors = []
    if proposition is None:
        return {"valid": False, "errors": ["schema_parse_failed"], "proposition": None}
    expected_type = canonical_answer_type(question_frame)
    if proposition.get("answer_type") != expected_type:
        errors.append("answer_type_mismatch")
    operation = str((question_frame or {}).get("operation") or "lookup")
    relation = proposition.get("relation")
    if operation == "yes_no" and relation not in {"yes", "no", "unknown"}:
        errors.append("yes_no_relation_invalid")
    elif expected_type == "compare" and relation not in {
        "increase",
        "decrease",
        "same",
        "unknown",
    }:
        errors.append("comparison_relation_invalid")
    elif operation != "yes_no" and expected_type != "compare" and relation not in {
        "none",
        "unknown",
    }:
        errors.append("nonrelational_relation_invalid")

    target_events = list((answer_view or {}).get("target_events") or [])
    grounded_claims = []
    seen = set()
    for claim in proposition.get("claims") or []:
        target_index = claim.get("target_index")
        if not isinstance(target_index, int) or not 0 <= target_index < len(target_events):
            errors.append("target_index_out_of_range")
            continue
        event = target_events[target_index]
        role = str(event.get("evidence_role") or "")
        quote = str(event.get("source_quote") or "")
        anchored = _anchored_span(quote, claim.get("answer_span"))
        if not anchored:
            errors.append("answer_span_not_grounded")
            continue
        key = (target_index, anchored)
        if key in seen:
            continue
        seen.add(key)
        grounded_claims.append(
            {
                "target_index": target_index,
                "evidence_role": role,
                "source_quote": quote,
                "answer_span": anchored,
            }
        )

    if relation == "unknown":
        if grounded_claims:
            errors.append("unknown_with_claims")
    elif not grounded_claims:
        errors.append("missing_grounded_claim")
    roles = {claim["evidence_role"] for claim in grounded_claims}
    missing_roles = _required_roles(question_frame) - roles
    if missing_roles:
        errors.append(f"missing_roles:{','.join(sorted(missing_roles))}")
    sanitized = {
        "schema": PROPOSITION_SCHEMA,
        "answer_type": proposition.get("answer_type"),
        "relation": relation,
        "claims": grounded_claims,
    }
    return {"valid": not errors, "errors": errors, "proposition": sanitized}


def render_answer_proposition(validated):
    """Render only validated semantic content; styling remains a later-stage concern."""
    if not validated or not validated.get("valid"):
        return ""
    proposition = validated["proposition"]
    relation = proposition["relation"]
    claims = proposition["claims"]
    if relation == "unknown":
        return "I do not have enough grounded evidence."
    if proposition["answer_type"] == "yes_no":
        support = "; ".join(claim["answer_span"] for claim in claims)
        prefix = "Yes" if relation == "yes" else "No"
        return f"{prefix} — {support}." if support else f"{prefix}."
    if proposition["answer_type"] == "compare":
        before = [
            claim["answer_span"] for claim in claims if claim["evidence_role"] == "before"
        ]
        current = [
            claim["answer_span"] for claim in claims if claim["evidence_role"] == "current"
        ]
        return f"{'; '.join(before)} -> {'; '.join(current)}; {relation}."
    return "; ".join(claim["answer_span"] for claim in claims) + "."
