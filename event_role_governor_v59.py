#!/usr/bin/env python3
"""Bind grounded actions to event owners, directive governors, and event time."""

import re

from relation_safety_state_v58 import resolve_target_state as resolve_v58


THIRD_PARTY_SUBJECT_RE = re.compile(
    r"(?P<subject>"
    r"彼|彼女|彼ら|彼女ら|あの人|その人|トム|メアリー|"
    r"友人|友達|先生|教師|母|父|母親|父親|兄|姉|弟|妹|"
    r"男性|女性|女の子|男の子|犬|猫|店員|同僚|上司"
    r")(?:は|が)"
)
THIRD_PARTY_ENCOUNTER_RE = re.compile(
    r"(?P<entity>"
    r"彼|彼女|友人|友達|先生|教師|母|父|母親|父親|兄|姉|弟|妹|"
    r"男性|女性|女の子|男の子|店員|同僚|上司"
    r")(?:に|と)(?:会|逢)"
)
ADDRESSEE_SUBJECT_RE = re.compile(r"(?:あなた|君|きみ|お前|そちら)(?:は|が)")
HABITUAL_RE = re.compile(
    r"(?:いつも|普段|ふだん|常に|よく|しばしば|毎日|毎朝|毎晩|毎回|たびに)"
)
RETROSPECTIVE_RE = re.compile(
    r"(?:昔|以前|前に|昨日|一昨日|先日|さっき|当時|あの時|この前)"
)
PAST_EXPERIENCE_RE = re.compile(
    r"(?:"
    r"(?:嬉|うれ|悲|かな|寂|さび|怖|こわ|驚|おどろ|助か|安心|感動|残念)"
    r"[^。！？!?]{0,16}(?:かった|だった|でした)"
    r"|(?:て|で)(?:くれ|もら|いただ|頂)(?:た|ました|って|えて)"
    r")"
)
SPEECH_PREDICATE_RE = re.compile(
    r"(?:教え|おしえ|説明|せつめい|話し|はなし|答え|こたえ|知らせ|しらせ|伝え|つたえ)"
)
REQUEST_MARKER_RE = re.compile(
    r"(?:"
    r"ください|下さい|くれ(?:ませんか|るかな)?|もらえ(?:ますか|る)?|"
    r"いただけ(?:ますか|る)?|頂け(?:ますか|る)?|ほしい|欲しい|"
    r"なさい|おくれ|ちょうだい|お願い"
    r")"
)
COMPLEMENT_MARKER_RE = re.compile(
    r"(?:のか|かどうか|ことを|様子を|(?:た|だ|る|う|す|い)か(?=[^ら]))"
)
DIRECT_TAIL_RE = re.compile(
    r"^[ぁ-ゖー、，,\s]*(?:に|を|へ|で|と|が|っ|い|み|け|か|し|な|"
    r"向|見|振|戻|合|保|続|止|動|頷|微笑|笑)*[ぁ-ゖー、，,\s]*"
    r"(?:ください|下さい|くれ(?:ませんか|るかな)?|もらえ(?:ますか|る)?|"
    r"いただけ(?:ますか|る)?|頂け(?:ますか|る)?|ほしい|欲しい|"
    r"なさい|おくれ|ちょうだい|お願い)"
    r"[。！？!?]*$"
)
COLLOQUIAL_DIRECT_END_RE = re.compile(
    r"^[ぁ-ゖー、，,\s]*(?:に|を|へ|で|と|が|っ|い|み|け|か|し|な|"
    r"向|見|振|戻|合|保|続|止|動|頷|微笑|笑)*[ぁ-ゖー、，,\s]*"
    r"(?:て|で|って|いて|して|なって|向いて|見て|振って)[。！!]*$"
)
COORDINATED_DIRECT_RE = re.compile(
    r"^[^。！？!?]{0,20}(?:て|で)から[^。！？!?]{0,24}"
    r"(?:ください|下さい|くれ(?:ませんか|るかな)?|もらえ(?:ますか|る)?|"
    r"いただけ(?:ますか|る)?|頂け(?:ますか|る)?|ほしい|欲しい|"
    r"なさい|おくれ|ちょうだい|お願い)[。！？!?]*$"
)


def _latest_focus_occurrence(event_map):
    rows = event_map.get("focus_occurrences") or []
    return max(rows, key=lambda row: row.get("order", -1)) if rows else None


def _mention_span(occurrence):
    mentions = (occurrence or {}).get("target_mentions") or []
    if not mentions:
        return None
    return min(row["start"] for row in mentions), max(row["end"] for row in mentions)


def _sentence_bounds(text, mention_start, mention_end):
    start = max(
        text.rfind("。", 0, mention_start),
        text.rfind("！", 0, mention_start),
        text.rfind("？", 0, mention_start),
        text.rfind("!", 0, mention_start),
        text.rfind("?", 0, mention_start),
    ) + 1
    ends = [
        index
        for marker in ("。", "！", "？", "!", "?")
        if (index := text.find(marker, mention_end)) >= 0
    ]
    end = min(ends) + 1 if ends else len(text)
    return start, end


def _embedded_speech_content(tail):
    complement = COMPLEMENT_MARKER_RE.search(tail)
    if complement is None:
        return None
    speech = SPEECH_PREDICATE_RE.search(tail, complement.end())
    if speech is None:
        return None
    request = REQUEST_MARKER_RE.search(tail, speech.end())
    colloquial = re.search(r"(?:て|で)[。！!]*$", tail[speech.start() :])
    if request is None and colloquial is None:
        return None
    end = request.end() if request is not None else len(tail)
    return tail[complement.start() : end]


def _direct_focus_request(tail):
    if _embedded_speech_content(tail) is not None:
        return False
    return bool(
        DIRECT_TAIL_RE.fullmatch(tail)
        or COLLOQUIAL_DIRECT_END_RE.fullmatch(tail)
        or COORDINATED_DIRECT_RE.fullmatch(tail)
    )


def _relation(relation_type, evidence, source, target="focus_event"):
    return {
        "type": relation_type,
        "source": source,
        "target": target,
        "evidence": evidence,
    }


def build_event_role_graph(user_input, event_map, focus_target_id):
    """Build an answer-free role graph for the latest grounded focus event."""

    text = str(user_input or "")
    occurrence = _latest_focus_occurrence(event_map)
    span = _mention_span(occurrence)
    if occurrence is None or span is None:
        return {
            "focus_target_id": focus_target_id,
            "event_owner": "unknown",
            "directive_governor": "unknown",
            "event_time": "unknown",
            "direct_focus_request": False,
            "relations": [],
            "relation_types": [],
        }

    mention_start, mention_end = span
    sentence_start, sentence_end = _sentence_bounds(text, mention_start, mention_end)
    sentence = text[sentence_start:sentence_end]
    prefix = text[sentence_start:mention_start]
    tail = text[mention_end:sentence_end]

    third_party = THIRD_PARTY_SUBJECT_RE.search(prefix)
    encounter = THIRD_PARTY_ENCOUNTER_RE.search(prefix)
    addressee = ADDRESSEE_SUBJECT_RE.search(prefix)
    embedded = _embedded_speech_content(tail)
    direct = _direct_focus_request(tail)
    habitual = HABITUAL_RE.search(sentence)
    retrospective = RETROSPECTIVE_RE.search(sentence)
    past_experience = PAST_EXPERIENCE_RE.search(tail)

    if direct or addressee is not None:
        owner = "addressee"
        owner_evidence = "implicit_addressee" if direct else addressee.group(0)
    elif third_party is not None:
        owner = "third_party"
        owner_evidence = third_party.group(0)
    elif encounter is not None and retrospective is not None:
        owner = "inferred_third_party"
        owner_evidence = encounter.group(0)
    else:
        owner = "unknown"
        owner_evidence = None

    if embedded is not None:
        governor = "speech_act"
    elif direct:
        governor = "focus_event"
    elif REQUEST_MARKER_RE.search(sentence):
        governor = "unknown"
    else:
        governor = "none"

    if direct:
        event_time = "current"
    elif habitual is not None:
        event_time = "habitual"
    elif retrospective is not None and past_experience is not None:
        event_time = "past"
    else:
        event_time = "unknown"

    relations = []
    if embedded is not None and not direct:
        relations.append(
            _relation(
                "embedded_speech_content",
                embedded,
                "directive_governor",
                target="speech_act",
            )
        )
    if owner == "third_party" and habitual is not None and not direct:
        relations.append(
            _relation(
                "third_party_habitual_description",
                f"{owner_evidence} … {habitual.group(0)}",
                "event_owner_and_time",
            )
        )
    if (
        owner in {"third_party", "inferred_third_party"}
        and retrospective is not None
        and past_experience is not None
        and not direct
    ):
        relations.append(
            _relation(
                "past_experiential_description",
                f"{owner_evidence} … {retrospective.group(0)} … {past_experience.group(0)}",
                "event_owner_and_time",
            )
        )

    return {
        "focus_target_id": focus_target_id,
        "event_owner": owner,
        "directive_governor": governor,
        "event_time": event_time,
        "direct_focus_request": direct,
        "relations": relations,
        "relation_types": [row["type"] for row in relations],
    }


def _override(result, graph, relation_type):
    evidence = [
        row["evidence"] for row in graph["relations"] if row["type"] == relation_type
    ]
    return {
        **result,
        "resolved": True,
        "commitment": "mentioned",
        "confidence": "high",
        "resolution_rule": f"event_role_{relation_type}",
        "evidence": evidence,
        "v59_event_role_graph": graph,
        "v59_correction": {
            "relation_type": relation_type,
            "from_rule": result.get("resolution_rule"),
        },
    }


def resolve_target_state(user_input, candidates, focus_target_id, mention_patterns):
    """Apply the preregistered V59 role graph over the frozen V58 resolver."""

    result = resolve_v58(user_input, candidates, focus_target_id, mention_patterns)
    graph = build_event_role_graph(
        user_input, result.get("event_map") or {}, focus_target_id
    )
    if result.get("commitment") != "requested" or graph["direct_focus_request"]:
        return {**result, "v59_event_role_graph": graph}
    types = set(graph["relation_types"])
    for relation_type in (
        "embedded_speech_content",
        "third_party_habitual_description",
        "past_experiential_description",
    ):
        if relation_type in types:
            return _override(result, graph, relation_type)
    return {**result, "v59_event_role_graph": graph}
