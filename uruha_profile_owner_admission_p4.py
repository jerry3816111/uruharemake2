"""Product-only, source-span-bound admission for new user profile facts.

This module does not reinterpret existing profile rows or episodes.  The legacy
writer receives only facts supported by bounded, unquoted clauses; P4-I's
selected typed writer is checked before it can mutate either profile store.
Only hashes, classifications, and counts leave the admission boundary.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib
import re

import uruha_multilingual_current_preference_p4 as p4i
from uruha_leftbrain_rules import extract_requested_user_name


LABEL = "profile_owner_admission_p4"
SCHEMA = "uruha_profile_owner_admission_p4_v1"
MAX_INPUT_CHARS = 512
MAX_CLAUSES = 12
MAX_CANDIDATES = 3
_INSTALLED = False
_ORIGINAL_EXTRACT_PROFILE_FACTS = None
_ORIGINAL_REMEMBER_PROFILE_FACTS = None
_ORIGINAL_MEMORY_SNAPSHOT = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None
_ADMITTED_FACTS = ContextVar("p4_profile_owner_admitted_facts", default=None)

_QUOTE_PAIRS = {"「": "」", "『": "』", "“": "”", "‘": "’", '"': '"', "'": "'"}
_CLOSERS = frozenset(_QUOTE_PAIRS.values())
_BOUNDARY = frozenset("。.!?！？；;，,、\n")
_QUESTIONS = frozenset("?？")
_REPORT = re.compile(
    r"\b(?:said|says|wrote|writes|asked|asks|according to)\b|"
    r"(?:と|って)(?:言った|言ってた|書いた|話した)|"
    r"(?:說|说|寫|写|問|问)(?:道|了|過|过)?(?:[:：，,\s]|我|他|她)|"
    r"(?:と言った|って言った|によると)", re.I
)
_THIRD_PERSON = re.compile(
    r"(?:私の|僕の|我(?:的)?|my\s+)?"
    r"(?:友達|友人|友だち|朋友|好友|彼女|彼|母|父|兄|姉|弟|妹|"
    r"同僚|先生|家族|親戚|friend|mother|father|sister|brother)"
    r"(?:の|は|が|も|的|說|说|\b)", re.I
)
_JAPANESE_SELF = re.compile(r"^(?:私は|わたしは|僕は|ぼくは|うちは|自分は|私も)\s*")
_JAPANESE_FAVORITE_NOUN = re.compile(
    r"^(?:私の|わたしの)?一番好きな(?:飲み物|食べ物|おやつ|もの)?(?:は|が)\s*(?P<value>.+)$"
)
_JAPANESE_PREDICATE = re.compile(
    r"^(?P<before>.+?)(?:が|は|を)?"
    r"(?P<predicate>一番好きじゃない|一番好きではない|"
    r"好みじゃない|好みではない|好きじゃない|好きではない|"
    r"一番好き|好き一番|好き|嫌い|無理)$"
)
_EN_FAVORITE = re.compile(
    r"^my favorite(?:\s+(?:drink|food|snack))?\s+is\s+(?P<value>.+)$", re.I
)
_EN_POSITIVE = re.compile(r"^i\s+(?:really\s+)?(?:like|love|prefer)\s+(?P<value>.+)$", re.I)
_EN_NEGATIVE = re.compile(
    r"^i\s+(?:(?:really\s+)?hate|(?:do\s+not|don't|no\s+longer)\s+like|"
    r"(?:can't|cannot)\s+(?:drink|eat))\s+(?P<value>.+)$", re.I
)
_ZH_FAVORITE = re.compile(r"^我最(?:喜歡|喜欢)(?P<value>.+)$")
_ZH_POSITIVE = re.compile(r"^我(?:現在|现在)?(?:比較|比较)?(?:喜歡|喜欢|愛|爱)(?P<value>.+)$")
_ZH_NEGATIVE = re.compile(
    r"^我(?:現在|现在)?(?:(?:不再|不|已經不|已经不)(?:喜歡|喜欢)|"
    r"(?:討厭|讨厌)|不能(?:喝|吃))(?P<value>.+)$"
)
_EMBEDDED_PREFERENCE = re.compile(
    r"\b(?:like|likes|love|loves|prefer|prefers|hate|hates|favorite)\b|"
    r"(?:一番好き|好き|嫌い|好み|喜歡|喜欢|討厭|讨厌)",
    re.I,
)
_EMBEDDED_OWNER_OR_CONTRAST = re.compile(
    r"\b(?:and|but)\s+(?:you|he|she|they|my|your|his|her|their|a\s+friend)\b|"
    r"(?:けど|けれど|しかし|だが|でも|但是|可是)",
    re.I,
)


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _clean_value(value):
    value = str(value or "").strip(" \t\r\n、,，。．.!！?？;；:：")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"(?:\s+anymore|\s+now|了)$", "", value, flags=re.I).strip()
    return value


def _masked_clauses(text):
    """Return original-index clauses with quotation contents blanked, or fail."""
    if len(text) > MAX_INPUT_CHARS:
        return None, "input_over_limit"
    masked = list(text)
    stack = []
    quote_start = None
    quote_spans = []
    for index, char in enumerate(text):
        # Apostrophes inside words are contractions, not quotation boundaries.
        if char == "'" and 0 < index < len(text) - 1 and text[index - 1].isalpha() and text[index + 1].isalpha():
            continue
        if stack and char == stack[-1]:
            masked[index] = " "
            stack.pop()
            if not stack:
                quote_spans.append((quote_start, index + 1))
                quote_start = None
            continue
        if char in _QUOTE_PAIRS:
            if not stack:
                quote_start = index
            stack.append(_QUOTE_PAIRS[char])
            masked[index] = " "
            continue
        if char in _CLOSERS:
            return None, "unbalanced_quote"
        if stack:
            masked[index] = " "
    if stack:
        return None, "unbalanced_quote"
    sanitized = "".join(masked)
    clauses = []
    start = 0
    for index, char in enumerate(sanitized):
        if char in _BOUNDARY:
            clauses.append((start, index, char, sanitized[start:index]))
            start = index + 1
    clauses.append((start, len(text), "", sanitized[start:]))
    if len(clauses) > MAX_CLAUSES:
        return None, "clause_over_limit"
    return (clauses, quote_spans, sanitized), None


def _candidate(clause):
    """Extract one exact preference value from a single unquoted clause."""
    source = clause.strip()
    if not source:
        return None
    # Preserve the existing name recognizer and require its value in this span.
    requested_name = extract_requested_user_name(source)
    if requested_name and requested_name in source:
        return ("name", requested_name, "direct_name")

    match = _EN_FAVORITE.fullmatch(source)
    if match:
        return ("favorite", _clean_value(match.group("value")), "direct_self")
    match = _EN_NEGATIVE.fullmatch(source)
    if match:
        return ("dislike", _clean_value(match.group("value")), "direct_self")
    match = _EN_POSITIVE.fullmatch(source)
    if match:
        return ("like", _clean_value(match.group("value")), "direct_self")
    match = _ZH_FAVORITE.fullmatch(source)
    if match:
        return ("favorite", _clean_value(match.group("value")), "direct_self")
    match = _ZH_NEGATIVE.fullmatch(source)
    if match:
        return ("dislike", _clean_value(match.group("value")), "direct_self")
    match = _ZH_POSITIVE.fullmatch(source)
    if match:
        return ("like", _clean_value(match.group("value")), "direct_self")
    match = _JAPANESE_FAVORITE_NOUN.fullmatch(source)
    if match:
        return ("favorite", _clean_value(match.group("value")), "explicit_self")

    explicit_self = bool(_JAPANESE_SELF.match(source))
    japanese = _JAPANESE_SELF.sub("", source)
    japanese = re.sub(r"(?:だ|です)$", "", japanese).strip()
    if japanese.startswith("もう"):
        japanese = japanese[2:].strip()
        temporal_negative = True
    else:
        temporal_negative = False
    match = _JAPANESE_PREDICATE.fullmatch(japanese)
    if not match:
        return None
    before = match.group("before")
    predicate = match.group("predicate")
    before = re.sub(r"もう$", "", before).strip()
    value = _clean_value(before)
    if predicate in {"一番好きじゃない", "一番好きではない"}:
        return ("favorite", value, "negated_positive")
    if predicate in {"好きじゃない", "好きではない", "好みじゃない", "好みではない"}:
        if not (explicit_self or temporal_negative or "もう" in match.group("before")):
            return ("dislike", value, "negated_positive")
        return ("dislike", value, "explicit_self_negative")
    if predicate in {"嫌い", "無理"}:
        return ("dislike", value, "direct_self")
    return ("favorite" if predicate in {"一番好き", "好き一番"} else "like", value, "direct_self")


def _japanese_named_actor(clause):
    source = clause.strip()
    if _JAPANESE_SELF.match(source) or _JAPANESE_FAVORITE_NOUN.match(source):
        return False
    return bool(re.match(r"^[^はがも]{1,24}(?:は|が|も)[^はがも]{1,36}(?:は|が|を)(?:一番)?好き", source))


def _explicit_self_clause(clause):
    source = clause.strip()
    return bool(
        _JAPANESE_SELF.match(source)
        or _JAPANESE_FAVORITE_NOUN.match(source)
        or re.match(r"^(?:I\b|my\s+favorite\b)", source, re.I)
        or source.startswith("我")
        or re.match(r"^(?:Call me|請叫我|请叫我|叫我)", source, re.I)
    )


def _decision(*, span, fact_type="unknown", value="", owner="unknown", reason, admitted):
    return {
        "source_span_sha256": _digest(span),
        "value_sha256": _digest(value) if value else None,
        "fact_type": fact_type,
        "owner": owner,
        "reason": reason,
        "admitted": bool(admitted),
    }


def _audit(text, decisions, *, path, reason=None):
    result = {
        "schema": SCHEMA,
        "path": path,
        "input_sha256": _digest(text),
        "candidate_count": len(decisions),
        "admitted_count": sum(bool(row["admitted"]) for row in decisions),
        "rejected_count": sum(not row["admitted"] for row in decisions),
        "decisions": decisions,
        "raw_dialogue_persisted": False,
        "answer_use_authorized": False,
    }
    if reason:
        result["reason"] = reason
    return result


def admit_legacy_profile_facts(text):
    """Return runtime-only fact tuples and a dialogue-free candidate audit."""
    text = str(text or "").strip()
    parsed, failure = _masked_clauses(text)
    if failure:
        return [], _audit(text, [_decision(span=text, reason=failure, admitted=False)], path="legacy", reason=failure)
    clauses, quote_spans, _ = parsed
    facts = []
    decisions = []
    for start, end in quote_spans:
        quoted = text[start:end]
        if re.search(r"好き|嫌い|喜歡|喜欢|like|love|hate|favorite|prefer", quoted, re.I):
            decisions.append(_decision(span=quoted, owner="quoted", reason="quoted_scope", admitted=False))
    reported_next = False
    unresolved_owner_next = False
    for start, end, delimiter, sanitized in clauses:
        source = sanitized.strip()
        if not source:
            if delimiter not in {",", "，", "、", ":", "："}:
                reported_next = False
                unresolved_owner_next = False
            continue
        candidate = _candidate(source)
        if candidate:
            fact_type, value, candidate_reason = candidate
            reason = None
            owner = "user"
            if not value or value not in source:
                reason, owner = "value_not_in_source_span", "unknown"
            elif fact_type != "name" and (
                _EMBEDDED_PREFERENCE.search(value) or _EMBEDDED_OWNER_OR_CONTRAST.search(value)
            ):
                reason, owner = "unsupported_mixed_predicate_or_owner_in_value", "unknown"
            elif delimiter in _QUESTIONS:
                reason, owner = "question_scope", "unknown"
            elif reported_next or _REPORT.search(source):
                reason, owner = "reported_scope", "third_party"
            elif unresolved_owner_next and not _explicit_self_clause(source):
                reason, owner = "carried_nonself_or_ambiguous_owner", "unknown"
            elif _THIRD_PERSON.search(source) or _japanese_named_actor(source):
                reason, owner = "third_person_scope", "third_party"
            elif candidate_reason == "negated_positive":
                reason, owner = "negated_positive_without_self_dislike", "unknown"
            elif any(start < quote_end and end > quote_start for quote_start, quote_end in quote_spans):
                reason, owner = "mixed_quote_clause", "unknown"
            if reason:
                decisions.append(_decision(span=text[start:end], fact_type=fact_type, value=value, owner=owner, reason=reason, admitted=False))
            else:
                facts.append((fact_type, value))
                decisions.append(_decision(span=text[start:end], fact_type=fact_type, value=value, owner="user", reason=candidate_reason, admitted=True))
        if delimiter in {",", "，", "、", ":", "："}:
            reported_next = bool(re.search(r"\b(?:said|says|wrote|writes|asked|asks)\s*$|(?:說|说|寫|写|問|问|言った|話した)\s*$", source, re.I))
            unresolved_owner_next = bool(
                _THIRD_PERSON.search(source)
                or _japanese_named_actor(source)
                or (not candidate and re.fullmatch(r"[\u3400-\u9fff\u3040-\u30ff]{2,12}", source))
            )
        else:
            reported_next = False
            unresolved_owner_next = False
    if len(decisions) > MAX_CANDIDATES:
        return [], _audit(text, [_decision(span=text, reason="candidate_over_limit", admitted=False)], path="legacy", reason="candidate_over_limit")
    unique = []
    seen = set()
    for fact_type, value in facts:
        key = (fact_type, value.casefold())
        if key not in seen:
            seen.add(key)
            unique.append((fact_type, value))
    return unique, _audit(text, decisions, path="legacy")


def admit_selected_current_preference(text, extraction):
    """Check P4-I's selected values against their unquoted self source before write."""
    text = str(text or "").strip()
    parsed, failure = _masked_clauses(text)
    reason = failure
    match = None
    if not reason:
        _, quote_spans, _ = parsed
        if quote_spans:
            reason = "quoted_scope"
        elif _THIRD_PERSON.search(text) or _REPORT.search(text):
            reason = "third_person_or_reported_scope"
        elif not extraction.get("selected"):
            reason = "selected_act_ambiguous_extraction"
        else:
            language = extraction.get("language")
            act = extraction.get("act")
            pattern = (p4i._WRITE_PATTERNS if act == "write" else p4i._CORRECTION_PATTERNS).get(language)
            matches = list(pattern.finditer(text)) if pattern else []
            if len(matches) != 1:
                reason = "selected_source_match_not_unique"
            else:
                match = matches[0]
                prefix = text[:match.start()].strip()
                if prefix:
                    correction_marker = bool(
                        act == "correction"
                        and re.fullmatch(r"(?:Correction|更正|訂正)\s*[:：。.!！]?", prefix, re.I)
                    )
                    if not correction_marker:
                        reason = "selected_source_has_unresolved_preamble"
                values = [extraction.get("current_value")]
                if act == "correction":
                    values.append(extraction.get("previous_value"))
                if not reason and any(not value or str(value) not in match.group(0) for value in values):
                    reason = "selected_value_not_in_source_span"
    fact_type = "current_preference_correction" if extraction.get("act") == "correction" else "current_preference_write"
    decisions = [_decision(
        span=match.group(0) if match else text,
        fact_type=fact_type,
        value=extraction.get("current_value") or "",
        owner="user" if not reason else "unknown",
        reason="explicit_self_source_span" if not reason else reason,
        admitted=not reason,
    )]
    return not reason, _audit(text, decisions, path="p4_i_selected", reason=reason)


def _extract_with_admitted_facts(self, user_input):
    context = _ADMITTED_FACTS.get()
    if context and context["memory"] is self and context["input"] == user_input:
        return list(context["facts"])
    return _ORIGINAL_EXTRACT_PROFILE_FACTS(self, user_input)


def _profile_count(collection):
    try:
        return int(collection.count())
    except Exception:
        return None


def _observe_collection_delta(audit, before, after):
    if before is not None and after is not None:
        audit["profile_collection_count_delta"] = max(0, after - before)
        audit["persistence_observed"] = True
        audit["persistence_evidence"] = "collection_count_delta_not_id_attributed"
    else:
        audit["profile_collection_count_delta"] = None
        audit["persistence_observed"] = False
        audit["persistence_evidence"] = "unavailable"


def _not_written_p4_i_audit(extraction, reason, *, selected_act):
    """Replace P4-I's previous-turn audit when the outer gate returns early."""
    return {
        "schema": p4i.SCHEMA,
        "selected": False,
        "status": "blocked_by_profile_owner_admission_p4" if selected_act else "not_selected",
        "input_sha256": extraction.get("input_sha256"),
        "classifier_cue_id": extraction.get("classifier_cue_id"),
        "reason": reason,
        "raw_dialogue_persisted": False,
        "answer_use_authorized": False,
    }


def remember_profile_facts_with_owner_admission_p4(self, user_input):
    """Decide before either writer can mutate session or Chroma state."""
    text = str(user_input or "")
    extraction = p4i.extract_explicit_current_preference_p4(text)
    selected_act = bool(extraction.get("classifier_cue_id"))
    if selected_act:
        allowed, audit = admit_selected_current_preference(text, extraction)
        if not allowed:
            audit["profile_collection_count_delta"] = 0
            audit["persistence_observed"] = True
            audit["persistence_evidence"] = "writer_not_invoked"
            self._last_multilingual_current_preference_p4 = _not_written_p4_i_audit(
                extraction, audit.get("reason") or "selected_source_rejected", selected_act=True
            )
            self._last_profile_owner_admission_p4 = audit
            return None
        before = _profile_count(self.profile_col)
        try:
            result = _ORIGINAL_REMEMBER_PROFILE_FACTS(self, user_input)
        except Exception as exc:
            audit["writer_status"] = "writer_exception"
            audit["writer_error_type"] = type(exc).__name__
            _observe_collection_delta(audit, before, _profile_count(self.profile_col))
            self._last_profile_owner_admission_p4 = audit
            raise
        p4_i_audit = getattr(self, "_last_multilingual_current_preference_p4", {})
        audit["writer_status"] = (
            "typed_write_completed"
            if p4_i_audit.get("status") == "typed_current_preference_written"
            else "typed_write_not_completed"
        )
    else:
        facts, audit = admit_legacy_profile_facts(text)
        if not facts:
            audit["profile_collection_count_delta"] = 0
            audit["persistence_observed"] = True
            audit["persistence_evidence"] = "writer_not_invoked"
            self._last_multilingual_current_preference_p4 = _not_written_p4_i_audit(
                extraction, "legacy_no_admitted_facts", selected_act=False
            )
            self._last_profile_owner_admission_p4 = audit
            return None
        before = _profile_count(self.profile_col)
        token = _ADMITTED_FACTS.set({"memory": self, "input": user_input, "facts": facts})
        try:
            result = _ORIGINAL_REMEMBER_PROFILE_FACTS(self, user_input)
        except Exception as exc:
            audit["writer_status"] = "writer_exception"
            audit["writer_error_type"] = type(exc).__name__
            _observe_collection_delta(audit, before, _profile_count(self.profile_col))
            self._last_profile_owner_admission_p4 = audit
            raise
        finally:
            _ADMITTED_FACTS.reset(token)
        audit["writer_status"] = "legacy_writer_returned"
    _observe_collection_delta(audit, before, _profile_count(self.profile_col))
    self._last_profile_owner_admission_p4 = audit
    return result


def memory_snapshot_with_owner_admission_p4(self):
    snapshot = _ORIGINAL_MEMORY_SNAPSHOT(self)
    snapshot[LABEL] = deepcopy(getattr(self, "_last_profile_owner_admission_p4", {
        "schema": SCHEMA,
        "path": "none",
        "candidate_count": 0,
        "admitted_count": 0,
        "rejected_count": 0,
        "decisions": [],
        "profile_collection_count_delta": 0,
        "persistence_observed": False,
        "persistence_evidence": "not_observed",
        "raw_dialogue_persisted": False,
        "answer_use_authorized": False,
    }))
    return snapshot


def materialize_profile_owner_admission_p4(result):
    payload = deepcopy((result.get("memory_runtime") or {}).get(LABEL) or {})
    if payload.get("schema") != SCHEMA:
        return
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    insert_at = next(
        (index + 1 for index, row in enumerate(rows) if row.get("label") == "memory_updates"),
        next((index for index, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
    )
    rows.insert(insert_at, {"stage": "memory", "label": LABEL, "payload": payload, "salience": 0.96})
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(payload)
    result.setdefault("logic", {})[LABEL] = deepcopy(payload)


def install_profile_owner_admission_p4():
    global _INSTALLED, _ORIGINAL_EXTRACT_PROFILE_FACTS, _ORIGINAL_REMEMBER_PROFILE_FACTS
    global _ORIGINAL_MEMORY_SNAPSHOT, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import MemoryManager, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_EXTRACT_PROFILE_FACTS = MemoryManager._extract_profile_facts
    _ORIGINAL_REMEMBER_PROFILE_FACTS = MemoryManager._remember_profile_facts
    _ORIGINAL_MEMORY_SNAPSHOT = MemoryManager.get_runtime_snapshot
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    MemoryManager._extract_profile_facts = _extract_with_admitted_facts
    MemoryManager._remember_profile_facts = remember_profile_facts_with_owner_admission_p4
    MemoryManager.get_runtime_snapshot = memory_snapshot_with_owner_admission_p4

    def finish(self, result):
        materialize_profile_owner_admission_p4(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if (
            self.runtime.turn_traces
            and self.runtime.turn_traces[-1].get("cycle_index") == result["runtime_trace"].get("cycle_index")
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
