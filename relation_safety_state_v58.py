#!/usr/bin/env python3
"""Add answer-free non-execution relations over the frozen V56 state resolver."""

import re

from relation_bound_event_graph_v56 import resolve_target_state as resolve_v56


ALTERNATIVE_MARKER_RE = re.compile(r"(?:どちらか|いずれか|(?:く|る|う|す)?か(?!ら))")
ORDERED_SEQUENCE_RE = re.compile(
    r"(?:まず|先に|それから|そのあと|その後|次に|最後に|最初に|(?:て|で)から)"
)
TENTATIVE_PREFERENCE_RE = re.compile(
    r"(?:ほしい|欲しい)[^。！？!?]{0,16}(?:気もする|けれど|けど|が)"
)
UNSETTLED_DECISION_RE = re.compile(
    r"(?:決められない|決めかね(?:る|ている)|まだ決めない|結論(?:は|が)?出ていない)"
)
PAST_BENEFACTIVE_RE = re.compile(
    r"(?:て|で)(?:くださいました|下さいました|くれました|もらいました|いただきました|頂きました)"
)


def _target_domain(target_id):
    return str(target_id or "").split(".", 1)[0]


def _mention_span(occurrence):
    mentions = occurrence.get("target_mentions") or []
    if not mentions:
        return None
    return min(row["start"] for row in mentions), max(row["end"] for row in mentions)


def _group_occurrences(event_map):
    groups = {}
    for occurrence in event_map.get("ordered_grounded_occurrences") or []:
        key = (occurrence.get("sentence_index"), occurrence.get("clause_index"))
        groups.setdefault(key, []).append(occurrence)
    return groups


def _exclusive_alternative_relation(text, event_map, focus_target_id):
    focus_domain = _target_domain(focus_target_id)
    focus_keys = {
        (row.get("sentence_index"), row.get("clause_index"))
        for row in event_map.get("focus_occurrences") or []
    }
    groups = _group_occurrences(event_map)
    for key in focus_keys:
        rows = [
            row
            for row in groups.get(key, [])
            if _target_domain(row.get("target_id")) == focus_domain
        ]
        if len({row.get("target_id") for row in rows}) < 2:
            continue
        spans = [span for row in rows if (span := _mention_span(row)) is not None]
        if len(spans) < 2:
            continue
        clause_text = str(rows[0].get("clause_text") or "")
        between_targets = text[min(start for start, _ in spans) : max(end for _, end in spans)]
        evidence = ALTERNATIVE_MARKER_RE.search(between_targets)
        if evidence is None:
            evidence = ALTERNATIVE_MARKER_RE.search(clause_text)
        if evidence is None or ORDERED_SEQUENCE_RE.search(clause_text):
            continue
        return {
            "type": "exclusive_alternative",
            "source": "choice_relation",
            "target": "focus_event",
            "evidence": evidence.group(0),
        }
    return None


def _deferred_preference_relation(text, event_map):
    unsettled = UNSETTLED_DECISION_RE.search(text)
    if unsettled is None:
        return None
    for occurrence in event_map.get("focus_occurrences") or []:
        preference = TENTATIVE_PREFERENCE_RE.search(
            str(occurrence.get("clause_text") or "")
        )
        span = _mention_span(occurrence)
        if preference is None or span is None or unsettled.start() <= span[0]:
            continue
        return {
            "type": "deferred_preference",
            "source": "decision_state",
            "target": "focus_event",
            "evidence": f"{preference.group(0)} … {unsettled.group(0)}",
        }
    return None


def _past_benefactive_relation(event_map):
    for occurrence in event_map.get("focus_occurrences") or []:
        marker = PAST_BENEFACTIVE_RE.search(str(occurrence.get("clause_text") or ""))
        if marker is not None:
            return {
                "type": "past_benefactive_description",
                "source": "tense_aspect",
                "target": "focus_event",
                "evidence": marker.group(0),
            }
    return None


def build_safety_relations(user_input, event_map, focus_target_id):
    """Build relation types without labels, answers, case IDs, or model output."""

    text = str(user_input or "")
    relations = []
    for relation in (
        _past_benefactive_relation(event_map),
        _exclusive_alternative_relation(text, event_map, focus_target_id),
        _deferred_preference_relation(text, event_map),
    ):
        if relation is not None and relation not in relations:
            relations.append(relation)
    return {
        "focus_target_id": focus_target_id,
        "relations": relations,
        "relation_types": [row["type"] for row in relations],
    }


def _override(result, graph, commitment, relation_type):
    evidence = [
        row["evidence"] for row in graph["relations"] if row["type"] == relation_type
    ]
    return {
        **result,
        "resolved": True,
        "commitment": commitment,
        "confidence": "high",
        "resolution_rule": f"relation_safety_{relation_type}",
        "evidence": evidence,
        "v58_relation_graph": graph,
        "v58_correction": {
            "relation_type": relation_type,
            "from_rule": result.get("resolution_rule"),
        },
    }


def resolve_target_state(user_input, candidates, focus_target_id, mention_patterns):
    """Apply the three preregistered V58 safety relations over V56."""

    result = resolve_v56(user_input, candidates, focus_target_id, mention_patterns)
    graph = build_safety_relations(
        user_input, result.get("event_map") or {}, focus_target_id
    )
    types = set(graph["relation_types"])
    if "past_benefactive_description" in types:
        return _override(result, graph, "mentioned", "past_benefactive_description")
    if "exclusive_alternative" in types:
        return _override(result, graph, "ambiguous", "exclusive_alternative")
    if "deferred_preference" in types:
        return _override(result, graph, "ambiguous", "deferred_preference")
    return {**result, "v58_relation_graph": graph}
