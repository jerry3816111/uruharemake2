"""Bounded past-statement source answer from already-delivered episode evidence.

Research question: can a remembered statement keep its *owner* through retrieval,
planning and Japanese delivery?  This product-only contract does not infer a
private preference, search the whole database, or claim an exhaustive absence.
Unsupported wording and unsupported source forms abstain rather than guessing.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import time
import unicodedata


LABEL = "past_statement_source_answer_p4"
SOURCE_LOOKUP_LABEL = "p4_bounded_source_lookup"
SCHEMA = "uruha_past_statement_source_answer_p4"
_LOOKUP_SENTINEL = 9
_LOOKUP_MAX_DOCUMENT_CHARS = 2048
_LOOKUP_MAX_TOTAL_CHARS = 16384
_INSTALLED = False
_ORIGINAL_QUERY = None
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_ZH_QUERY = re.compile(
    r"^\s*(?:我|本人)(?:以前|之前|曾經|曾经)(?:有沒有|有没有)?(?:說|说)過?"
    r"(?:自己)?(?:最喜[歡欢]|最愛|最爱)(?P<value>[^？?。！，,]{1,40})"
    r"(?:嗎|吗)", re.I,
)
_JA_QUERY = re.compile(
    r"^\s*(?:前に|以前)(?:私|うち)(?:が|は)"
    r"(?P<value>[^？?。が]{1,40})(?:が)?(?:一番|いちばん)?好き"
    r"(?:だと|って)?言った", re.I,
)
_EN_QUERY = re.compile(
    r"^\s*did\s+i\s+(?:ever\s+)?say\s+(?:i\s+)?"
    r"(?:liked|loved|my\s+favorite\s+(?:was|is))\s+"
    r"(?P<value>[^?.,;]{1,40})", re.I,
)
_QUERY_TAILS = {
    "zh": re.compile(
        r"^\s*[?？]\s*(?:如果不是[，,]\s*(?:之前說最喜歡的人是誰|之前说最喜欢的人是谁|是誰說的|是谁说的)[?？])?\s*$"
    ),
    "ja": re.compile(r"^\s*[?？]\s*(?:違うなら誰[?？])?\s*$"),
    "en": re.compile(r"^\s*[?？]\s*(?:if\s+not,?\s+who\s+did[?？])?\s*$", re.I),
}
_META_OR_HYPOTHETICAL = re.compile(
    r"引用|例文|例句|假設|假设|翻譯|翻译|もし|たとえば|例えば|"
    r"\b(?:quote|example|hypothetical|if i asked|translate)\b", re.I,
)
_SOURCE_RETRACTION_OR_QUOTE = re.compile(
    r"[\"「」『』“”]|假消息|假新聞|假新闻|不是真的|不是事實|不是事实|"
    r"廣告文案|广告文案|其實|其实|訂正|订正|更正|"
    r"後來(?:說|说)|后来(?:說|说)|嘘|実は|事実じゃない|本当じゃない|"
    r"\b(?:not true|false report|fake news|ad copy|advertisement|actually|later denied|retracted)\b",
    re.I,
)
_EPISODE = re.compile(
    r" \| User: (.*?) \| Summary: (.*?) \| Uruha: ",
    re.S,
)
_SUMMARY_LIKE = re.compile(
    r"(?P<actor>[\w\u3400-\u9fff]{1,24})は"
    r"(?P<value>[^。|]{1,48}?)が(?:一番|いちばん)?好き"
    r"(?:だ|です|だった)(?=[。！？!?\s]|$)",
)
_SUMMARY_NOT_LIKE = re.compile(
    r"(?P<actor>[\w\u3400-\u9fff]{1,24})は"
    r"(?P<value>[^。|]{1,48}?)が(?:一番|いちばん)?好き"
    r"(?:ではない|じゃない|ではありません|じゃありません|じゃなかった)"
    r"(?=[。！？!?\s]|$)",
)
_SUMMARY_SOURCE_UNCERTAIN = re.compile(
    r"不明|未確認|不确定|不確定|否定された|否定了|撤回|訂正|订正|更正|"
    r"嘘|虚偽|假的|かもしれない|可能性|maybe|uncertain|unverified|retracted",
    re.I,
)
_THIRD_ZH = re.compile(
    r"(?:我(?:的)?朋友|朋友|老師|老师|同學|同学)"
    r"(?P<actor>[\w\u3400-\u9fff]{1,24})"
    r"(?:最喜[歡欢]|最愛|最爱)(?P<value>[^。！？!?,，；;、]{1,48})"
)
_THIRD_JA = re.compile(
    r"(?:友達の|先生の|同級生の)(?P<actor>[\w\u3400-\u9fff]{1,24})"
    r"は(?P<value>[^。！？!?,，；;、]{1,48}?)が(?:一番|いちばん)?好き"
)
_THIRD_EN = re.compile(
    r"\bmy\s+(?:friend|teacher|classmate)\s+(?P<actor>[A-Za-z]{2,24})"
    r"(?:'s\s+favorite(?:\s+\w+){0,2}\s+is|\s+(?:likes|loves))\s+"
    r"(?P<value>[^.!?;,]{1,48})", re.I,
)
_SELF_ZH = re.compile(r"(?:^|[。！？!?,，；;、])\s*我(?:自己|也)?最喜[歡欢](?P<value>[^。！？!?,，；;、]{1,48})")
_SELF_JA = re.compile(r"(?:私|うち)は(?P<value>[^。！？!?,，；;、]{1,48}?)が(?:一番|いちばん)好き")
_SELF_EN = re.compile(r"\b(?:i\s+(?:love|like)|my\s+favorite(?:\s+\w+){0,2}\s+is)\s+(?P<value>[^.!?;,]{1,48})", re.I)
_NEGATED_SELF = re.compile(
    r"我(?:沒有|没有|不曾|未曾).{0,12}(?:喜[歡欢]|最愛|最爱)"
    r"|(?:私|うち)は.{0,24}(?:好きじゃない|好きではない|言ってない)"
    r"|\bi\s+(?:do\s+not|don't|did\s+not|didn't)\s+(?:like|love|say)\b", re.I,
)
_REPORTED_FIRST_PERSON = re.compile(
    r"(?:彼女|彼|她|他|友達|朋友|先生|老師|老师).{0,10}(?:言った|說|说|講|讲)"
    r"|\b(?:she|he|they|friend|teacher)\s+(?:said|says|wrote)\b",
    re.I,
)
_NEGATED_LIKE_SUFFIX = re.compile(r"^(?:じゃない|ではない|じゃありません|ではありません|じゃなかった)")
_COMPOSITE_NAME_OR_VALUE = re.compile(
    r"(?:或者|或是|或者是|或|還是|还是|または|あるいは|それとも|/|／|&|＆|、)"
    r"|^.{2,}(?:和|と|か|や).{2,}$"
)
_ANONYMOUS_ACTORS = {
    "她", "他", "某人", "誰", "谁", "那個人", "那个人", "朋友", "友達",
    "先生", "老師", "老师", "同學", "同学", "彼", "彼女", "あの人", "誰か",
    "私", "うち", "あなた", "ユーザー",
}

# Deliberately closed source grammar.  A legacy episode stores free-form user
# text next to a model summary; an arbitrary substring match can mistake
# quotations, retractions or pronoun shifts for an owned past statement.
_SOURCE_VALUE = r"[\u3040-\u30ff\u3400-\u9fff々ー・]{1,32}"
_SOURCE_ACTOR = r"[\u3040-\u30ff\u3400-\u9fff々ー・]{1,24}"
_SUPPORTED_SOURCE_FORMS = (
    re.compile(
        rf"我朋友(?P<actor>{_SOURCE_ACTOR})最喜[歡欢](?P<value>{_SOURCE_VALUE})。"
        rf"(?:(?:這|这)是她(?:自己)?(?:說|说)的"
        rf"(?:，不是我的(?:飲料|饮料)偏好"
        rf"(?:；我(?:沒有|没有)(?:說|说)自己喜[歡欢](?P=value))?)?。)?"
        rf"(?:先記住說話者。)?"
    ),
    re.compile(rf"我(?:自己|也)?最喜[歡欢](?P<value>{_SOURCE_VALUE})。"),
    re.compile(
        rf"友達の(?P<actor>{_SOURCE_ACTOR})は(?P<value>{_SOURCE_VALUE})が一番好きだ。"
        rf"(?:(?P=actor)が言った。)?"
    ),
    re.compile(rf"(?:私|うち)は(?P<value>{_SOURCE_VALUE})が一番好きだ。"),
)


def _supported_source_form(source: str) -> bool:
    return any(pattern.fullmatch(source.strip()) for pattern in _SUPPORTED_SOURCE_FORMS)


def _third_party_speech_is_explicit(actor: str, source: str, claim_end: int) -> bool:
    """Require the speaker cue to attach locally to this one subject claim."""
    tail = source[claim_end:]
    adjacent_pronoun = re.match(
        r"^\s*[。.!！]?\s*(?:這|这)是(?:她|他)(?:自己)?(?:說|说)的(?:[。.!！,，；;]|$)",
        tail,
    )
    named_speaker = re.match(
        rf"^\s*[。.!！]?\s*{re.escape(actor)}(?:が|は)?(?:言った|說|说)(?:[。.!！,，；;]|$)",
        tail,
    )
    japanese_named = re.match(rf"^だ。{re.escape(actor)}が言った。$", tail)
    return bool(adjacent_pronoun or named_speaker or japanese_named)


def _digest(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    return re.sub(r"[\s\u3000。．，,、！？?!…~～\-_/'\"`「」『』“”()（）:：;；]+", "", text)


def _clean_value(value: object) -> str:
    text = str(value or "").strip(" \t\n。．，,、！？?!;；：:")
    return re.sub(r"(?:だ|です|って)$", "", text).strip()


def _friend_source(source: str) -> bool:
    return source.strip().startswith(("我朋友", "朋友", "友達の"))


def _summary_actor_key(actor: str, source: str) -> str:
    # A summary may retain the relation prefix, but only a friend source can
    # license removing it.  In particular, "友達のユーザー" is not the user.
    if _friend_source(source) and actor.startswith("友達の"):
        return actor[len("友達の"):]
    return actor


def _japanese_surface_safe(value: str) -> bool:
    # An unlocalized Latin phrase is not silently presented as natural Japanese.
    return bool(
        re.fullmatch(r"[\u3040-\u30ff\u3400-\u9fff々ー・]{1,32}", value)
        and not _COMPOSITE_NAME_OR_VALUE.search(value)
    )


def classify_past_statement_query_p4(user_input: object) -> dict:
    """Select an explicit first-person past favourite claim question only."""
    text = str(user_input or "")
    base = {
        "schema": SCHEMA,
        "input_sha256": _digest(text),
        "selected": False,
        "status": "not_selected",
        "raw_dialogue_persisted": False,
    }
    if _META_OR_HYPOTHETICAL.search(text):
        return {**base, "reason": "quoted_hypothetical_or_metalinguistic_query"}
    for language, pattern in (("zh", _ZH_QUERY), ("ja", _JA_QUERY), ("en", _EN_QUERY)):
        match = pattern.match(text)
        if not match:
            continue
        if not _QUERY_TAILS[language].fullmatch(text[match.end():]):
            return {**base, "reason": "unsupported_multiple_intent_or_ambiguous_query_tail"}
        value = _clean_value(match.group("value"))
        if not _japanese_surface_safe(value):
            return {**base, "reason": "value_not_safely_localized_to_japanese"}
        return {
            **base,
            "selected": True,
            "status": "explicit_past_first_person_favorite_source_query",
            "query_language": language,
            "value": value,
            "value_sha256": _digest(_norm(value)),
            "epistemic_status": "observable_question_not_memory_truth",
        }
    return {**base, "reason": "past_first_person_favorite_source_query_not_detected"}


def _bounded_source_lookup(collection, value: str) -> tuple[dict, list[dict]]:
    """Read at most eight raw literal hits plus one overflow sentinel."""
    started = time.perf_counter()
    base = {
        "schema": "uruha_p4_bounded_source_lookup_v1",
        "value_sha256": _digest(value),
        "match_scope": "literal_value_in_turn_episode_collection_only",
        "limit": _LOOKUP_SENTINEL - 1,
        "source_memory_ids": [],
        "matched_count": 0,
        "extra_model_calls": 0,
        "raw_dialogue_persisted": False,
    }

    def finish(status: str, reason: str, rows: list[dict] | None = None):
        rows = rows or []
        return ({
            **base,
            "status": status,
            "reason": reason,
            "source_memory_ids": [row["memory_id"] for row in rows],
            "matched_count": len(rows),
            "lookup_elapsed_seconds": round(time.perf_counter() - started, 6),
        }, rows)

    try:
        result = collection.get(
            where={"source": "turn_episode"},
            where_document={"$contains": value},
            limit=_LOOKUP_SENTINEL,
            include=["documents", "metadatas"],
        )
    except Exception:
        return finish("lookup_unavailable", "collection_get_failed")
    if not isinstance(result, dict):
        return finish("lookup_unavailable", "collection_result_not_mapping")
    ids, documents, metadatas = (
        result.get("ids"), result.get("documents"), result.get("metadatas")
    )
    if not all(isinstance(value, list) for value in (ids, documents, metadatas)):
        return finish("lookup_unavailable", "collection_result_fields_not_lists")
    if not (len(ids) == len(documents) == len(metadatas)):
        return finish("lookup_unavailable", "collection_result_fields_misaligned")
    if len(ids) >= _LOOKUP_SENTINEL:
        return finish("overflow", "at_least_nine_literal_hits")
    rows = []
    seen_ids = set()
    total_chars = 0
    for memory_id, document, metadata in zip(ids, documents, metadatas):
        if not isinstance(memory_id, str) or not memory_id.strip() or len(memory_id) > 256:
            return finish("lookup_unavailable", "invalid_memory_id")
        if memory_id in seen_ids:
            return finish("lookup_unavailable", "duplicate_memory_id")
        if not isinstance(document, str) or not document.strip() or value not in document:
            return finish("lookup_unavailable", "invalid_or_nonmatching_document")
        if not isinstance(metadata, dict) or metadata.get("source") != "turn_episode":
            return finish("lookup_unavailable", "invalid_episode_metadata")
        total_chars += len(document)
        if len(document) > _LOOKUP_MAX_DOCUMENT_CHARS or total_chars > _LOOKUP_MAX_TOTAL_CHARS:
            return finish("lookup_unavailable", "episode_document_size_exceeded")
        seen_ids.add(memory_id)
        rows.append({
            "source": "episode",
            "collection_name": "episode",
            "memory_id": memory_id,
            "text": document,
        })
    return finish("complete", "all_bounded_literal_hits_delivered", rows)


def _delivered_source_lookup_gap(memory_data: dict, requested_value: str, lookup_rows: list[dict]) -> bool:
    by_id = {row["memory_id"]: row["text"] for row in lookup_rows}
    provenance = (memory_data or {}).get("memory_provenance") or {}
    for item in provenance.get("passed_to_leftbrain") or []:
        if item.get("source") != "episode":
            continue
        text = str(item.get("text") or "")
        memory_id = str(item.get("memory_id") or "")
        if memory_id in by_id:
            if text != by_id[memory_id]:
                return True
            continue
        if _norm(requested_value) not in _norm(text):
            continue
        # A normalization-equivalent source or inconsistent direct payload
        # means literal get cannot certify even the bounded delivered set.
        return True
    return False


def _episode_rows(memory_data: dict, requested_value: str) -> tuple[list[dict], list[dict]]:
    """Use only persisted episodes already delivered to this turn's left brain."""
    provenance = (memory_data or {}).get("memory_provenance") or {}
    rows = []
    malformed = []
    seen = set()
    for item in provenance.get("passed_to_leftbrain") or []:
        if item.get("source") != "episode" or item.get("channel") not in {
            "direct_episode", "selected_working_memory", "bounded_source_lookup"
        }:
            continue
        memory_id = str(item.get("memory_id") or "")
        trace_id = str(item.get("trace_id") or "")
        text = str(item.get("text") or "")
        relevant = _norm(requested_value) in _norm(text)
        if not memory_id or trace_id != f"stored:episode:{memory_id}":
            if relevant and (memory_data or {}).get(SOURCE_LOOKUP_LABEL):
                malformed.append({"memory_id": memory_id, "trace_id": trace_id})
            continue
        if memory_id in seen:
            continue
        # Legacy episode documents interpolate unescaped user text.  An input
        # containing a field delimiter cannot be parsed as trusted structure.
        if any(text.count(delimiter) != 1 for delimiter in (
            " | User: ", " | Summary: ", " | Uruha: ", " | Mood: "
        )):
            if relevant:
                malformed.append({"memory_id": memory_id, "trace_id": trace_id})
            continue
        match = _EPISODE.search(text)
        if not match:
            if relevant:
                malformed.append({"memory_id": memory_id, "trace_id": trace_id})
            continue
        if re.search(r"\|\s*(?:User|Summary|Uruha|Mood):", match.group(1)):
            if relevant:
                malformed.append({"memory_id": memory_id, "trace_id": trace_id})
            continue
        if re.search(r"\|\s*(?:User|Summary|Uruha|Mood):", match.group(2)):
            if relevant:
                malformed.append({"memory_id": memory_id, "trace_id": trace_id})
            continue
        seen.add(memory_id)
        rows.append({
            "memory_id": memory_id,
            "trace_id": trace_id,
            "source_channel": str(item.get("channel")),
            "user": match.group(1).strip(),
            "summary": match.group(2).strip(),
        })
    for turn in (memory_data or {}).get("recent_turns") or []:
        memory_id = str(turn.get("episode_id") or "")
        if not memory_id or memory_id in seen:
            continue
        lookup = (memory_data or {}).get(SOURCE_LOOKUP_LABEL)
        if lookup and memory_id not in set(lookup.get("source_memory_ids") or []):
            continue
        user = str(turn.get("user") or "").strip()
        reply = str(turn.get("reply") or "").strip()
        summary = str(turn.get("summary") or "").strip()
        if not user or not reply or not summary:
            continue
        passed_text = f"User:{user} -> Uruha:{reply}"
        passed = next((
            item for item in provenance.get("passed_to_leftbrain") or []
            if item.get("source") == "recent_turn"
            and item.get("channel") == "recent_turns"
            and str(item.get("text") or "") == passed_text
            and str(item.get("trace_id") or "").startswith("derived:recent_turn:")
        ), None)
        if passed is None:
            continue
        seen.add(memory_id)
        rows.append({
            "memory_id": memory_id,
            "trace_id": str(passed["trace_id"]),
            "source_channel": "recent_turn",
            "user": user,
            "summary": summary,
        })
    return rows, malformed


def _source_candidates(row: dict, requested_value: str) -> tuple[list[dict], bool]:
    source = row["user"]
    summary = row["summary"]
    if classify_past_statement_query_p4(source).get("selected"):
        # A prior question is not a positive statement of anyone's preference.
        return [], False
    if _META_OR_HYPOTHETICAL.search(source) or _SOURCE_RETRACTION_OR_QUOTE.search(source):
        return [], _norm(requested_value) in _norm(source)
    if not _supported_source_form(source):
        # A same-value record outside our tiny grammar may still be a second
        # speaker or a correction.  Ignoring it would manufacture uniqueness.
        return [], _norm(requested_value) in _norm(source)
    if sum(source.count(marker) for marker in ("最喜歡", "最喜欢", "最愛", "最爱", "一番好き", "いちばん好き")) > 1:
        return [], True
    summaries = list(_SUMMARY_LIKE.finditer(summary))
    relevant_summary_actors = {
        _norm(_summary_actor_key(match.group("actor"), source))
        for match in summaries
        if _norm(_clean_value(match.group("value"))) == _norm(requested_value)
    }
    if (
        (len(relevant_summary_actors) > 1)
        or (_norm(requested_value) in _norm(summary) and _SUMMARY_SOURCE_UNCERTAIN.search(summary))
    ):
        return [], True
    candidates = []
    uncorroborated_relevant_claim = False
    for role, patterns in (
        ("third_party", (_THIRD_ZH, _THIRD_JA, _THIRD_EN)),
        ("user", (_SELF_ZH, _SELF_JA, _SELF_EN)),
    ):
        if role == "user" and _NEGATED_SELF.search(source):
            continue
        for pattern in patterns:
            for source_match in pattern.finditer(source):
                actor = source_match.group("actor") if role == "third_party" else "ユーザー"
                value = _clean_value(source_match.group("value"))
                if _norm(value) != _norm(requested_value):
                    continue
                lookup = row.get("literal_lookup_required")
                if lookup and value != requested_value:
                    uncorroborated_relevant_claim = True
                    continue
                if not _japanese_surface_safe(actor) or not _japanese_surface_safe(value):
                    uncorroborated_relevant_claim = True
                    continue
                if role == "third_party" and actor in _ANONYMOUS_ACTORS:
                    uncorroborated_relevant_claim = True
                    continue
                if _NEGATED_LIKE_SUFFIX.search(source[source_match.end():]):
                    continue
                if role == "user" and _REPORTED_FIRST_PERSON.search(source):
                    # An embedded "I" may be the reporter's quote, not the user.
                    uncorroborated_relevant_claim = True
                    continue
                corroborated = any(
                    _norm(_summary_actor_key(s.group("actor"), source)) == _norm(actor)
                    and _norm(_clean_value(s.group("value"))) == _norm(value)
                    for s in summaries
                )
                if not corroborated:
                    uncorroborated_relevant_claim = True
                    continue
                candidates.append({
                    "speaker_role": role,
                    "actor": actor,
                    "value": value,
                    "memory_id": row["memory_id"],
                    "trace_id": row["trace_id"],
                    "source_channel": row["source_channel"],
                    "source_input_sha256": _digest(source),
                    "source_summary_sha256": _digest(summary),
                    "third_party_self_report_cue": (
                        _third_party_speech_is_explicit(actor, source, source_match.end())
                    ) if role == "third_party" else None,
                })
    return candidates, uncorroborated_relevant_claim


def _source_lookup_abstention(query: dict, lookup: dict) -> dict:
    status = "source_lookup_" + str(lookup.get("status") or "unavailable")
    core = "その好みを誰が言ったか、今の記録じゃ分からない。"
    return {
        **query,
        "status": status,
        "reason": str(lookup.get("reason") or "bounded_literal_source_lookup_not_complete"),
        "surface_authority": True,
        "answer_use_authorized": False,
        "selected_speaker_role": None,
        "selected_actor": None,
        "candidate_count": 0,
        "candidate_actors": [],
        "source_memory_ids": [],
        "source_trace_ids": [],
        "unresolved_source_memory_ids": list(lookup.get("source_memory_ids") or []),
        "unresolved_source_trace_ids": [
            f"stored:episode:{item}" for item in lookup.get("source_memory_ids") or []
        ],
        "bounded_source_lookup": deepcopy(lookup),
        "candidates": [],
        "selected_core_jp": core,
        "selected_core_sha256": _digest(core),
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "profile_memory_write_count": 0,
        "private_state_truth_claimed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": "bounded literal episode lookup failed; no source answer authorized",
    }


def build_past_statement_source_contract_p4(user_input: object, memory_data: dict) -> dict:
    query = classify_past_statement_query_p4(user_input)
    if not query["selected"]:
        return query
    lookup = deepcopy((memory_data or {}).get(SOURCE_LOOKUP_LABEL) or {})
    if lookup and lookup.get("status") != "complete":
        return _source_lookup_abstention(query, lookup)
    candidates = []
    uncorroborated_relevant_claim = False
    unresolved_rows = []
    rows, malformed_rows = _episode_rows(memory_data, query["value"])
    if lookup:
        for row in rows:
            row["literal_lookup_required"] = True
    negative_actor_values = {
        (
            _norm(_summary_actor_key(match.group("actor"), row["user"])),
            _norm(_clean_value(match.group("value"))),
        )
        for row in rows
        for match in _SUMMARY_NOT_LIKE.finditer(row["summary"])
    }
    for row in rows:
        found, unresolved = _source_candidates(row, query["value"])
        candidates.extend(found)
        uncorroborated_relevant_claim |= unresolved
        if unresolved:
            unresolved_rows.append(row)
    actors = {(row["speaker_role"], row["actor"]) for row in candidates}
    contradicted_source_claim = any(
        (_norm(row["actor"]), _norm(row["value"])) in negative_actor_values
        for row in candidates
    )
    if malformed_rows:
        status = "malformed_relevant_source_episode"
        core = "記録の形が崩れてる。誰の発言かは断定しない。"
        reason = "relevant_delivered_episode_could_not_be_safely_parsed"
        role = actor = None
    elif contradicted_source_claim:
        status = "contradicted_source_claim"
        core = "記録が食い違ってる。誰の発言か、今は断定しない。"
        reason = "same_actor_and_value_have_positive_and_negative_delivered_episode_summaries"
        role = actor = None
    elif uncorroborated_relevant_claim:
        status = "uncorroborated_relevant_source_claim"
        core = "記録の原文と要約が合わない。誰の発言かは断定しない。"
        reason = "relevant_original_claim_is_unsupported_or_lacks_matching_positive_summary"
        role = actor = None
    elif len(actors) == 1:
        role, actor = next(iter(actors))
        if role == "user":
            status = "resolved_user_source"
            core = (
                f"見つかった記録じゃ、あんたが{query['value']}を一番好きって言ってた。"
                if lookup else
                f"今の記録では、あんたが{query['value']}を一番好きだって言ってた。"
            )
            reason = "unique_source_actor_and_value_corrobated_by_original_and_summary"
        elif not all(row.get("third_party_self_report_cue") for row in candidates):
            status = "subject_known_speaker_unverified"
            core = f"記録に{actor}の好みとある。でも本人が言ったかは不明。"
            reason = "third_party_preference_subject_known_but_self_report_not_observed"
            role = actor = None
        else:
            status = "resolved_third_party_source"
            if lookup:
                core = f"見つかった記録じゃ、{actor}が{query['value']}を一番好きって言ったとあんたが話してた。"
            else:
                core = f"記録では、あんたは「{query['value']}が一番好き」と言ったのは{actor}だって話してた。"
            reason = "unique_source_actor_and_value_corrobated_by_original_and_summary"
    elif actors:
        status = "ambiguous_multiple_source_actors"
        core = "記録に複数人の発言がある。誰の場面か断定しない。"
        reason = "multiple_distinct_actor_roles_or_names_in_delivered_episodes"
        role = actor = None
    else:
        status = "source_not_found_in_delivered_episodes"
        core = "その好みを誰が言ったか、今の記録じゃ分からない。"
        reason = "no_source_corrobated_by_original_and_summary"
        role = actor = None
    if len(core) > 40:
        status = "answer_exceeds_plan_surface_limit"
        reason = "source_bound_japanese_core_longer_than_plan_limit"
        core = "その好みを誰が言ったか、今の記録じゃ分からない。"
        role = actor = None
    return {
        **query,
        "status": status,
        "reason": reason,
        "surface_authority": True,
        "answer_use_authorized": status in {"resolved_user_source", "resolved_third_party_source"},
        "selected_speaker_role": role,
        "selected_actor": actor,
        "candidate_count": len(candidates),
        "uncorroborated_relevant_claim": uncorroborated_relevant_claim,
        "contradicted_source_claim": contradicted_source_claim,
        "candidate_actors": sorted(f"{row['speaker_role']}:{row['actor']}" for row in candidates),
        "source_memory_ids": sorted({row["memory_id"] for row in candidates}),
        "source_trace_ids": sorted({row["trace_id"] for row in candidates}),
        "unresolved_source_memory_ids": sorted({row["memory_id"] for row in unresolved_rows + malformed_rows}),
        "unresolved_source_trace_ids": sorted({row["trace_id"] for row in unresolved_rows + malformed_rows}),
        "bounded_source_lookup": lookup or None,
        "candidates": candidates[:8],
        "selected_core_jp": core,
        "selected_core_sha256": _digest(core),
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "profile_memory_write_count": 0,
        "private_state_truth_claimed": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "bounded literal current-turn delivered-episode source attribution, not "
            "NFKC/semantic-global uniqueness or private preference truth"
        ),
    }


def query_all_layers_with_past_statement_source_p4(self, text):
    data = _ORIGINAL_QUERY(self, text)
    query = classify_past_statement_query_p4(text)
    if query.get("selected") and hasattr(self, "episode_col"):
        lookup, lookup_rows = _bounded_source_lookup(self.episode_col, query["value"])
        provenance = data.setdefault("memory_provenance", {})
        if lookup.get("status") == "complete":
            if _delivered_source_lookup_gap(data, query["value"], lookup_rows):
                lookup["status"] = "incomplete"
                lookup["reason"] = "other_delivered_episode_outside_literal_lookup_or_inconsistent_document"
            passed = provenance.setdefault("passed_to_leftbrain", [])
            existing_ids = {
                str(row.get("memory_id")) for row in passed
                if row.get("source") == "episode" and row.get("memory_id")
            }
            import uruha_memory_runtime as memory_runtime

            for row in lookup_rows:
                if row["memory_id"] not in existing_ids:
                    passed.append(memory_runtime.memory_trace_row(
                        row, channel="bounded_source_lookup"
                    ))
            provenance["passed_to_leftbrain_trace_ids"] = list(dict.fromkeys(
                str(row.get("trace_id")) for row in passed if row.get("trace_id")
            ))
        data[SOURCE_LOOKUP_LABEL] = lookup
    data[LABEL] = build_past_statement_source_contract_p4(text, data)
    return data


def _plan_from_contract(contract: dict) -> dict:
    resolved = bool(contract.get("answer_use_authorized"))
    return {
        "candidate_label": "p4_past_statement_source",
        "intent": "past_statement_source_recall",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "前の発言の持ち主を確認している",
        "reply_goal": "取得済みの記憶にある話者と値だけを答え、なければ推測しない",
        "jp_summary": "ユーザーが過去の好みの発言者を確認している。",
        "core_message_jp": contract["selected_core_jp"],
        "cognitive_mode": "direct" if resolved else "reflective",
        "response_mode": "direct_answer" if resolved else "direct_answer_with_hedge",
        "uncertainty": 0.08 if resolved else 0.75,
        "premise_check": "accept" if resolved else "question",
        "self_check": True,
        "subjective_note_jp": "話者が明示された取得済み記憶だけを使う",
        "hidden_intent": "memory_probe",
        "user_belief": "前に誰が言ったか確かめたい。",
        "my_hidden_knowledge": "今取得できた記憶以外は不明。",
        "user_expectation": "発言者を根拠付きで短く答える。",
        "surface_act": "memory_presence_reply",
        "grounding": {
            "speaker_role": contract.get("selected_speaker_role") or "unknown",
            "source_evidence_count": len(contract.get("source_trace_ids") or []),
            "evidence_status": contract.get("status"),
        },
        "payload_level": "medium",
        "memory_recall_contract": deepcopy(contract),
        LABEL: deepcopy(contract),
        "planner_path": "past_statement_source_delivered_episode_p4",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": 100,
            "casual_japanese_only": True,
            "forbid_polite": True,
            "forbid_knowledge": True,
            "forbid_lore": True,
            "forbid_self_variants": True,
        },
        "must_avoid": ["私", "わかりました", "たぶん", "きっと", "AI"],
    }


def rule_plan_with_past_statement_source_p4(self, user_input, current_psyche, memory_data=None):
    contract = (memory_data or {}).get(LABEL) or {}
    if contract.get("schema") == SCHEMA and contract.get("selected") and contract.get("surface_authority"):
        # Preserve the predecessor's protective classification, rather than
        # making a memory-looking substring suppress crisis/boundary handling.
        predecessor = _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)
        import uruha_adaptive_person_model as adaptive_person

        if (
            str((predecessor or {}).get("intent") or "") in adaptive_person.PROTECTED_INTENTS
            or str((predecessor or {}).get("scene") or "") in adaptive_person.PROTECTED_SCENES
        ):
            return predecessor
        return _plan_from_contract(contract)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


_SOURCE_ABSTENTION_JP = "その好みを誰が言ったか、今の記録じゃ分からない。"


def _commit_visible_surface(logic_data: dict, contract: dict, before: str, final: str, status: str) -> str:
    contract.update(
        visible_surface_status=status,
        pre_authority_surface_sha256=_digest(before),
        final_visible_surface_jp=final,
        final_visible_surface_sha256=_digest(final),
        final_visible_surface_matches_contract=final == contract.get("selected_core_jp"),
        visible_surface_changed=final != before,
    )
    logic_data[LABEL] = contract
    if (logic_data.get("memory_recall_contract") or {}).get("schema") == SCHEMA:
        logic_data["memory_recall_contract"] = deepcopy(contract)
    language_guard = deepcopy(logic_data.get("visible_language_guard") or {})
    language_guard.update(
        final_reply=final,
        final_reply_sha256=_digest(final),
        past_statement_source_answer_p4=True,
        past_statement_source_surface_status=status,
    )
    logic_data["visible_language_guard"] = language_guard
    m39 = deepcopy(logic_data.get("semantic_persona_surface_verifier_m39") or {})
    if m39:
        m39.update(
            effective_after_past_source_p4=False,
            downstream_authority=LABEL,
            pre_authority_status=m39.get("status"),
        )
        logic_data["semantic_persona_surface_verifier_m39"] = m39
    return final


def _fail_closed_visible(logic_data: dict, before: str, reason: str) -> str:
    final = _SOURCE_ABSTENTION_JP
    failed = {
        "schema": SCHEMA,
        "selected": True,
        "status": "surface_integrity_failed_closed",
        "reason": reason,
        "surface_authority": True,
        "answer_use_authorized": False,
        "selected_speaker_role": None,
        "selected_actor": None,
        "candidate_count": 0,
        "source_memory_ids": [],
        "source_trace_ids": [],
        "unresolved_source_memory_ids": [],
        "unresolved_source_trace_ids": [],
        "selected_core_jp": final,
        "selected_core_sha256": _digest(final),
        "model_call_added": False,
        "fact_memory_write_count": 0,
        "profile_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "claim_boundary": "current-turn source-answer integrity failure, not a memory truth claim",
    }
    return _commit_visible_surface(logic_data, failed, before, final, "failed_closed")


def visible_guard_with_past_statement_source_p4(self, reply, logic_data, user_input="", memory_data=None):
    visible = _ORIGINAL_VISIBLE_GUARD(
        self, reply, logic_data, user_input=user_input, memory_data=memory_data
    )
    route = str(((logic_data or {}).get("semantic_route_m22") or {}).get("selected_type") or "")
    routed = (logic_data or {}).get("semantic_route_m22") or {}
    contract = deepcopy(
        (logic_data or {}).get(LABEL)
        or (logic_data or {}).get("memory_recall_contract")
        or (memory_data or {}).get(LABEL)
        or {}
    )
    fresh = build_past_statement_source_contract_p4(user_input, memory_data or {})
    integrity_fields = (
        "schema", "input_sha256", "selected", "status", "value_sha256",
        "selected_speaker_role", "selected_actor", "source_memory_ids",
        "source_trace_ids", "unresolved_source_memory_ids", "bounded_source_lookup",
        "selected_core_sha256", "selected_core_jp",
    )
    contract_matches_source = all(contract.get(key) == fresh.get(key) for key in integrity_fields)
    selected_route = route == "factual_or_memory"
    intent = str((logic_data or {}).get("intent") or "")
    scene = str((logic_data or {}).get("scene") or "")
    selected_intent = intent == "past_statement_source_recall"
    import uruha_adaptive_person_model as adaptive_person

    if (
        route == "safety_sensitive"
        or intent in adaptive_person.PROTECTED_INTENTS
        or scene in adaptive_person.PROTECTED_SCENES
    ):
        return visible
    before = str(visible or "").strip()
    if not fresh.get("selected"):
        return visible
    if not selected_route or not selected_intent:
        return _fail_closed_visible(logic_data, before, "selected_source_query_route_or_intent_drift")
    if routed.get("contract_status") != "matched" or routed.get("performed_route") != "deterministic_rule_plan":
        return _fail_closed_visible(logic_data, before, "factual_route_or_performed_route_not_matched")
    if (
        contract.get("schema") != SCHEMA
        or contract.get("selected") is not True
        or contract.get("surface_authority") is not True
        or not contract_matches_source
        or not str(contract.get("selected_core_jp") or "").strip()
    ):
        return _fail_closed_visible(logic_data, before, "source_contract_integrity_mismatch")
    final = str(contract["selected_core_jp"]).strip()
    language_check = getattr(self, "_user_visible_language_rejection_reasons", None)
    if not callable(language_check):
        return _fail_closed_visible(logic_data, before, "language_checker_unavailable")
    try:
        rejection_reasons = language_check(
            final, user_input=user_input, logic_data=logic_data, memory_data=memory_data
        )
    except Exception:
        rejection_reasons = ["language_checker_exception"]
    if rejection_reasons:
        return _fail_closed_visible(logic_data, before, "source_core_language_guard_rejected")
    return _commit_visible_surface(logic_data, contract, before, final, "matched")


def materialize_past_statement_source_p4(result: dict) -> None:
    logic = result.setdefault("logic", {})
    contract = deepcopy(logic.get(LABEL) or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [
        row for row in trace.get("blackboard", [])
        if row.get("label") not in {LABEL, SOURCE_LOOKUP_LABEL}
    ]
    if contract.get("schema") == SCHEMA and contract.get("surface_authority"):
        final = str(result.get("reply") or result.get("response") or "").strip()
        status = str(contract.get("status") or "")
        lookup = deepcopy(contract.get("bounded_source_lookup") or {})
        if status == "surface_integrity_failed_closed":
            flow = ["explicit_past_source_query", "source_contract_integrity_failure", "visible_japanese_abstention"]
        elif status.startswith("source_lookup_"):
            flow = ["explicit_past_source_query", "bounded_literal_episode_lookup", status, "visible_japanese_abstention"]
        elif status == "source_not_found_in_delivered_episodes":
            flow = ([
                "explicit_past_source_query", "bounded_literal_episode_lookup",
                "no_qualifying_source_episode", "visible_japanese_abstention",
            ] if lookup else [
                "explicit_past_source_query", "no_qualifying_delivered_episode",
                "visible_japanese_abstention",
            ])
        else:
            flow = [
                "explicit_past_source_query",
                "bounded_literal_episode_lookup" if lookup else "already_delivered_persisted_episode",
                "source_actor_value_join", "unique_or_abstain", "visible_japanese_surface",
            ]
        contract.update(
            final_visible_surface_jp=final,
            final_visible_surface_sha256=_digest(final),
            final_visible_surface_matches_contract=final == contract.get("selected_core_jp"),
            flow=flow,
        )
        logic[LABEL] = deepcopy(contract)
        position = next(
            (index for index, row in enumerate(rows) if row.get("label") == "selected_plan"),
            next((index for index, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
        )
        if lookup:
            rows.insert(position, {
                "stage": "retrieve",
                "label": SOURCE_LOOKUP_LABEL,
                "payload": lookup,
                "salience": 1.0,
            })
            position += 1
        rows.insert(position, {
            "stage": "select",
            "label": LABEL,
            "payload": deepcopy(contract),
            "salience": 1.0,
        })
        trace[LABEL] = deepcopy(contract)
    trace["blackboard"] = rows


def install_past_statement_source_answer_p4() -> bool:
    global _INSTALLED, _ORIGINAL_QUERY, _ORIGINAL_RULE_PLAN, _ORIGINAL_VISIBLE_GUARD
    global _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import MemoryManager, LeftBrain, RightBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_QUERY = MemoryManager.query_all_layers
    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    MemoryManager.query_all_layers = query_all_layers_with_past_statement_source_p4
    LeftBrain._rule_based_plan = rule_plan_with_past_statement_source_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_past_statement_source_p4

    def finish(self, result):
        materialize_past_statement_source_p4(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if (
            self.runtime.turn_traces
            and self.runtime.turn_traces[-1].get("cycle_index")
            == result["runtime_trace"].get("cycle_index")
        ):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def run(self, user_input, input_context=None):
        return finish(self, _ORIGINAL_RUN(self, user_input, input_context=input_context))

    def emit(self, event, tick_result):
        return finish(self, _ORIGINAL_EMIT(self, event, tick_result))

    UruhaBrainV4_Mac.run_turn_debug = run
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "classify_past_statement_query_p4",
    "build_past_statement_source_contract_p4", "install_past_statement_source_answer_p4",
    "materialize_past_statement_source_p4",
]
