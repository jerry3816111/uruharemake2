#!/usr/bin/env python3
"""Resolve complete focus-predicate force and aspect above the V59 event roles."""

import re

from event_role_governor_v59 import (
    COMPLEMENT_MARKER_RE,
    SPEECH_PREDICATE_RE,
    _latest_focus_occurrence,
    _mention_span,
    _sentence_bounds,
    resolve_target_state as resolve_v59,
)


CURRENT_REQUEST_MARKER_RE = re.compile(
    r"(?:"
    r"ください|下さい|"
    r"くれ(?:"
    r"ませんか|ます(?:か|[？?])|る(?:かな|[？?])|"
    r"よ?(?=[。！!？?\s]|$)"
    r")|"
    r"もらえ(?:ますか|る)?|"
    r"いただけ(?:ますか|る)?|頂け(?:ますか|る)?|"
    r"ほしい|欲しい|なさい|おくれ|ちょうだい|お願い"
    r")"
)
THIRD_PARTY_BENEFACTIVE_DESCRIPTION_RE = re.compile(
    r"(?:て|で)くれ(?:ます(?:か)?|る(?:の)?)(?=[。！？!?]|$)"
)
COMPLETED_BENEFACTIVE_RE = re.compile(
    r"(?:て|で)(?:"
    r"くれ(?:た|ました|て)|"
    r"もら(?:った|いました|って)|"
    r"いただ(?:いた|きました|いて)|"
    r"頂(?:いた|きました|いて)"
    r")"
)
COLLOQUIAL_SPEECH_DIRECTIVE_RE = re.compile(r"(?:教え|説明|話し|答え|伝え)(?:て|で)[。！!]*$")
COMPLETED_RELATION = "third_party_completed_benefactive_description"
POLITE_DESCRIPTION_RELATION = "third_party_polite_benefactive_description"


def _strict_embedded_speech_governor(tail):
    complement = COMPLEMENT_MARKER_RE.search(tail)
    if complement is None:
        return None
    speech = SPEECH_PREDICATE_RE.search(tail, complement.end())
    if speech is None:
        return None
    request = CURRENT_REQUEST_MARKER_RE.search(tail, speech.end())
    colloquial = COLLOQUIAL_SPEECH_DIRECTIVE_RE.search(tail[speech.start() :])
    if request is None and colloquial is None:
        return None
    end = request.end() if request is not None else len(tail)
    return tail[complement.start() : end]


def _focus_predicate_context(user_input, event_map):
    text = str(user_input or "")
    occurrence = _latest_focus_occurrence(event_map)
    span = _mention_span(occurrence)
    if occurrence is None or span is None:
        return {
            "predicate_span": "",
            "tail_after_grounded_mention": "",
            "span_start": None,
            "span_end": None,
        }
    mention_start, mention_end = span
    sentence_start, sentence_end = _sentence_bounds(text, mention_start, mention_end)
    return {
        "predicate_span": text[mention_start:sentence_end],
        "tail_after_grounded_mention": text[mention_end:sentence_end],
        "span_start": mention_start,
        "span_end": sentence_end,
        "sentence_span": text[sentence_start:sentence_end],
    }


def build_predicate_morphology(user_input, v59_graph):
    """Build an answer-free morphology record for the complete focus predicate."""

    context = _focus_predicate_context(
        user_input, (v59_graph or {}).get("event_map") or {}
    )
    predicate = context["predicate_span"]
    tail = context["tail_after_grounded_mention"]
    completed = COMPLETED_BENEFACTIVE_RE.search(predicate)
    polite_description = THIRD_PARTY_BENEFACTIVE_DESCRIPTION_RE.search(predicate)
    embedded = _strict_embedded_speech_governor(tail)
    current_request = CURRENT_REQUEST_MARKER_RE.search(predicate)

    owner = (v59_graph or {}).get("event_owner", "unknown")
    third_party_polite_description = (
        polite_description is not None
        and owner in {"third_party", "inferred_third_party"}
    )
    direct = (
        current_request is not None
        and embedded is None
        and completed is None
        and not third_party_polite_description
    )
    if direct:
        owner = "addressee"
    completed_third_party = (
        completed is not None
        and owner in {"third_party", "inferred_third_party"}
        and not direct
    )

    if direct:
        predicate_force = "current_directive"
        event_aspect = "current"
        request_governor = "focus_event"
    elif completed_third_party:
        predicate_force = "completed_benefactive"
        event_aspect = "completed"
        request_governor = "none"
    elif embedded is not None:
        predicate_force = "declarative"
        event_aspect = (v59_graph or {}).get("event_time", "unknown")
        request_governor = "speech_act"
    elif predicate:
        predicate_force = "declarative"
        event_aspect = (v59_graph or {}).get("event_time", "unknown")
        request_governor = "none"
    else:
        predicate_force = "unknown"
        event_aspect = "unknown"
        request_governor = "unknown"

    return {
        **context,
        "predicate_force": predicate_force,
        "event_aspect": event_aspect,
        "request_governor": request_governor,
        "event_owner": owner,
        "direct_focus_request": direct,
        "completed_benefactive_evidence": completed.group(0) if completed else None,
        "polite_benefactive_description_evidence": (
            polite_description.group(0) if third_party_polite_description else None
        ),
        "current_request_evidence": (
            current_request.group(0) if current_request is not None else None
        ),
        "embedded_speech_evidence": embedded,
    }


def build_v60_event_role_graph(user_input, v59_graph):
    morphology = build_predicate_morphology(user_input, v59_graph)
    relations = list((v59_graph or {}).get("relations") or [])
    relation_types = {row["type"] for row in relations}
    if (
        morphology["predicate_force"] == "completed_benefactive"
        and "past_experiential_description" not in relation_types
    ):
        relations.append(
            {
                "type": COMPLETED_RELATION,
                "source": "focus_predicate_morphology",
                "target": "focus_event",
                "evidence": morphology["completed_benefactive_evidence"],
            }
        )
    if morphology["polite_benefactive_description_evidence"] is not None:
        relations.append(
            {
                "type": POLITE_DESCRIPTION_RELATION,
                "source": "focus_predicate_morphology",
                "target": "focus_event",
                "evidence": morphology["polite_benefactive_description_evidence"],
            }
        )
    relation_types = [row["type"] for row in relations]

    event_time = (v59_graph or {}).get("event_time", "unknown")
    if morphology["event_aspect"] == "current":
        event_time = "current"
    elif morphology["event_aspect"] == "completed":
        event_time = "past"

    return {
        **(v59_graph or {}),
        "event_owner": morphology["event_owner"],
        "directive_governor": morphology["request_governor"],
        "event_time": event_time,
        "direct_focus_request": morphology["direct_focus_request"],
        "relations": relations,
        "relation_types": relation_types,
        "v60_predicate_morphology": morphology,
    }


def _override_description(result, graph, relation_type):
    evidence = [
        row["evidence"] for row in graph["relations"] if row["type"] == relation_type
    ]
    return {
        **result,
        "resolved": True,
        "commitment": "mentioned",
        "confidence": "high",
        "resolution_rule": f"predicate_morphology_{relation_type}",
        "evidence": evidence,
        "v60_event_role_graph": graph,
        "v60_correction": {
            "relation_type": relation_type,
            "from_rule": result.get("resolution_rule"),
        },
    }


def resolve_target_state(user_input, candidates, focus_target_id, mention_patterns):
    """Apply V60 predicate morphology over the frozen V59 resolver."""

    result = resolve_v59(user_input, candidates, focus_target_id, mention_patterns)
    v59_graph = result.get("v59_event_role_graph") or {}
    if result.get("event_map") and not v59_graph.get("event_map"):
        v59_graph = {**v59_graph, "event_map": result["event_map"]}
    graph = build_v60_event_role_graph(user_input, v59_graph)
    if result.get("commitment") == "requested":
        relation_types = set(graph["relation_types"])
        for relation_type in (COMPLETED_RELATION, POLITE_DESCRIPTION_RELATION):
            if relation_type in relation_types:
                return _override_description(result, graph, relation_type)
    return {**result, "v60_event_role_graph": graph}
