"""Bounded, answer-independent current-turn quote and outer-act certificate.

This observes text roles; it neither infers private intent nor grants surface
authority. In particular an M31 input digest proves matching text, not the
event/cycle lineage needed to displace an authoritative M31 or M32 reply.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata


LABEL = "current_turn_source_role_p4"
SCHEMA = "uruha_current_turn_source_role_p4_v1"
_QUOTE = re.compile(
    r'「(?P<corner>[^「」\n]{1,80})」|“(?P<curly>[^“”\n]{1,80})”|"(?P<ascii>[^"\n]{1,80})"'
)
_QUOTE_MARK = re.compile(r'[「」“”"『』]')
_REWRITE = re.compile(r'言い換え|書き換え|改成|改寫|改写|\b(?:rewrite|rephrase|paraphrase)\b', re.I)
_STYLE = re.compile(r'柔らか|やわらか|友達|親し|くだけ|カジュアル|委婉|柔和|口語|比较|比較|\b(?:warmer|casual|softer|gentler)\b', re.I)
_DEFINITION = re.compile(r'意味|定義|とは|翻訳|英訳|和訳|translate|meaning|define|definition|翻譯|翻译|意思', re.I)
_REPORT = re.compile(r'と言(?:った|ってた|う|われ)|と話し|とあった|と書い|って頼んだ|と頼んだ|頼まれた|\b(?:said|wrote|told me|asked me to)\b|說了|说了|寫著|写着', re.I)
_EVALUATION = re.compile(r'聞こえる|自然|遠回し|不自然|どう思う|\b(?:sound|natural|awkward)\b', re.I)
_OTHER_TASK = re.compile(r'教えて|覚えて|思い出して|送って|開いて|調べて|やって|連絡して|迎えに来て|どうしたら|\b(?:also|and tell|and remember|and send|contact|what should i do)\b|也告訴|也告诉|順便|顺便', re.I)
_HYPOTHETICAL = re.compile(r'書かれたら|言われたら|訊かれたら|聞かれたら|\bif .*\b(?:said|asked)\b', re.I)
_RESPONSE_QUESTION = re.compile(r'どう答える|どう返す|\bhow .*respond\b', re.I)
_SENSITIVE = re.compile(
    r'パスワード|暗証番号|認証コード|ログイン|住所|電話番号|個人情報|自傷|自殺|死にたい|殺す|殺して|'
    r'password|passcode|secret|suicide|self.harm|kill|密碼|密码|驗證碼|验证码|住址|電話|殺人|杀人',
    re.I,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _nfkc(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip()


def _single_rewrite_grammar(prefix_raw: str, suffix_raw: str) -> bool:
    """Require a complete outer command, not a cue found inside a report.

    This intentionally recognizes only three bounded written forms. Other
    grammars abstain rather than guessing that a quoted line is an instruction.
    """
    prefix = _nfkc(prefix_raw)
    suffix = _nfkc(suffix_raw)
    if "\n" in prefix_raw + suffix_raw or _OTHER_TASK.search(prefix + " " + suffix):
        return False
    if not prefix:
        japanese = re.fullmatch(r'を[、,\s]*(?P<style>[^。.!！?？\n]{1,100})(?:言い換えて|書き換えて)[。!！]?', suffix)
        if not japanese:
            return False
        style = japanese.group("style")
        return bool(re.fullmatch(
            r'(?:[ぁ-んァ-ヶー一-龠]{1,10}(?:に(?:話すみたいに|返す感じで|送る感じで|自然に聞こえるよう)|向けに|が読んでも角が立たないように))?'
            r'(?:もう少し|少し|もっと)?(?:自然で|自然に聞こえるよう)?(?:柔らかく|やわらかく|カジュアルに|親しみやすく)',
            style,
        ))
    if re.fullmatch(r'(?i)(?:please\s+)?(?:rewrite|rephrase|paraphrase)', prefix):
        return bool(re.fullmatch(
            r'(?i)(?:in|as)\s+(?:a\s+)?(?:warmer|softer|gentler|casual)'
            r'(?:,\s*(?:warmer|softer|gentler|casual)){0,2}\s+Japanese(?:\s+reply)?[.!]?',
            suffix,
        ))
    if prefix in {"把", "請把", "请把"}:
        return bool(re.fullmatch(
            r'改成(?:比較|比较|更)?(?:柔和|委婉|口語|口语|自然)的'
            r'(?:日文|日語|日语)(?:說法|说法|口語|口语)[。!！]?', suffix,
        ))
    return False


def classify_current_turn_source_role_p4(user_input: str, *, cycle_index: int | None = None) -> dict:
    """Certify one observable quote/outer act; abstain on unresolved structure."""
    raw = str(user_input or "")
    normal = _nfkc(raw)
    certificate = {
        "schema": SCHEMA,
        "raw_input_sha256": _sha(raw),
        "normalized_input_sha256": _sha(normal),
        "raw_input_length": len(raw),
        "coordinate_system": "python_unicode_codepoints_in_raw_input",
        "cycle_index": cycle_index if isinstance(cycle_index, int) and cycle_index >= 0 else "unavailable",
        "act": "unknown",
        "quote_role": "unknown",
        "outer_role": "unknown",
        "rewrite_eligible": False,
        "certainty": "observable_structure_only",
        "reason": "unresolved",
        "evidence_ids": [],
        "raw_dialogue_persisted": False,
        "authority_transfer_permitted": False,
        "claim_boundary": "bounded text-role certificate; not semantic equivalence or event-lineage proof",
    }
    if not normal or len(raw) > 240:
        return {**certificate, "reason": "empty_or_long"}

    matches = list(_QUOTE.finditer(raw))
    if not matches:
        if _QUOTE_MARK.search(raw):
            return {**certificate, "reason": "unbalanced_quote"}
        if _SENSITIVE.search(raw):
            return {**certificate, "act": "protected", "quote_role": "none", "outer_role": "current_user_utterance", "reason": "observable_sensitive_content", "evidence_ids": ["sensitive_content"]}
        if _REWRITE.search(normal) or _OTHER_TASK.search(normal) or _DEFINITION.search(normal):
            return {**certificate, "act": "unquoted_request", "quote_role": "none", "outer_role": "current_user_instruction", "reason": "no_quoted_object_for_role_split"}
        return {**certificate, "act": "ordinary_chat", "quote_role": "none", "outer_role": "current_user_utterance", "reason": "no_quoted_object"}
    if len(matches) != 1:
        return {**certificate, "reason": "multiple_quotes"}
    match = matches[0]
    quote_group = next(name for name, value in match.groupdict().items() if value is not None)
    quote_raw = match.group(quote_group)
    prefix_raw = raw[:match.start()]
    suffix_raw = raw[match.end():]
    outer_raw = prefix_raw + " " + suffix_raw
    if _QUOTE_MARK.search(quote_raw) or _QUOTE_MARK.search(outer_raw):
        return {**certificate, "reason": "nested_or_unbalanced_quote"}
    quote = _nfkc(quote_raw)
    outer = _nfkc(outer_raw)
    certificate.update({
        "quote_span_raw": [match.start(), match.end()],
        "quote_content_span_raw": [match.start(quote_group), match.end(quote_group)],
        "outside_spans_raw": [[0, match.start()], [match.end(), len(raw)]],
        "quote_raw_sha256": _sha(quote_raw),
        "quote_normalized_sha256": _sha(quote),
        "outside_raw_sha256": _sha(prefix_raw + suffix_raw),
        "outside_classifier_normalized_sha256": _sha(outer),
        "quote_length": len(quote_raw),
        "outer_role": "current_user_context_or_instruction",
        "_quote_nfkc": quote,
        "_outside_nfkc": outer,
    })
    if _SENSITIVE.search(raw):
        return {**certificate, "act": "protected", "quote_role": "sensitive_content", "reason": "observable_sensitive_content", "evidence_ids": ["sensitive_content"]}

    rewrite = bool(_REWRITE.search(outer))
    style = bool(_STYLE.search(outer))
    definition = bool(_DEFINITION.search(outer))
    reported = bool(_REPORT.search(outer))
    other_task = bool(_OTHER_TASK.search(outer))
    evaluation = bool(_EVALUATION.search(outer) and re.search(r'[?？]\s*$', outer))
    command = _single_rewrite_grammar(prefix_raw, suffix_raw)
    cues = [name for name, present in (
        ("rewrite_request", rewrite), ("style_goal", style), ("definition_or_translation", definition),
        ("reported_speech", reported), ("other_action", other_task), ("wording_evaluation", evaluation),
    ) if present]
    certificate["evidence_ids"] = cues
    if rewrite and (definition or other_task or evaluation):
        return {**certificate, "act": "mixed_request", "quote_role": "rewrite_object", "reason": "multiple_outer_acts"}
    if reported:
        return {**certificate, "act": "reported_speech", "quote_role": "reported_content", "outer_role": "current_user_report", "reason": "outside_reporting_predicate"}
    if definition:
        return {**certificate, "act": "definition_request", "quote_role": "term_to_define", "reason": "outside_definition_request"}
    if _HYPOTHETICAL.search(outer) and _RESPONSE_QUESTION.search(outer):
        return {**certificate, "act": "hypothetical_identity", "quote_role": "hypothetical_content", "reason": "quoted_hypothetical_response_question"}
    if evaluation:
        return {**certificate, "act": "quoted_evaluation", "quote_role": "object_of_evaluation", "reason": "outside_wording_evaluation"}
    if rewrite and style and command and 2 <= len(quote) <= 40:
        return {
            **certificate, "act": "single_rewrite", "quote_role": "rewrite_object",
            "outer_role": "current_user_instruction", "rewrite_eligible": True,
            "reason": "single_observable_outer_rewrite_request",
        }
    return {**certificate, "reason": "quoted_act_not_resolved"}


def public_source_role_certificate_p4(certificate: dict) -> dict:
    """Never put private quote or outer text into graph/logic receipts."""
    return {key: value for key, value in certificate.items() if not key.startswith("_")}


def audit_current_turn_lineage_p4(certificate: dict, logic: dict) -> dict:
    """A matching M31 text digest is not an event or M32 parent certificate."""
    source = logic if isinstance(logic, dict) else {}
    m29 = source.get("literal_topic_projection_m29")
    m31 = source.get("semantic_authorization_m31")
    m32 = source.get("semantic_commit_repair_m32")
    raw_sha = str(certificate.get("raw_input_sha256") or "")
    expected = raw_sha[:16] if len(raw_sha) == 64 else ""
    m29_match = isinstance(m29, dict) and m29.get("input_digest") == expected
    m31_match = isinstance(m31, dict) and m31.get("input_digest") == expected
    m31_authority = isinstance(m31, dict) and m31.get("surface_authority") is True
    m32_authority = isinstance(m32, dict) and m32.get("surface_authority") is True
    return {
        "schema": "uruha_current_turn_surface_lineage_audit_p4_v1",
        "expected_raw_input_digest16": expected,
        "m29_raw_digest_matches": bool(m29_match),
        "m31_raw_digest_matches": bool(m31_match),
        "m31_surface_authority": bool(m31_authority),
        "m32_surface_authority": bool(m32_authority),
        "status": (
            "same_text_but_event_and_parent_lineage_unproven"
            if m31_match and (m31_authority or m32_authority)
            else "m31_digest_mismatch_or_missing"
            if m31_authority or m32_authority
            else "no_authoritative_m31_m32_to_transfer"
        ),
        "authority_transfer_permitted": False,
        "reason": "lineage_insufficient_for_authority_transfer",
        "decision_uses_model_answer_text": False,
        "raw_dialogue_persisted": False,
    }


__all__ = [
    "LABEL", "SCHEMA", "classify_current_turn_source_role_p4",
    "public_source_role_certificate_p4", "audit_current_turn_lineage_p4",
]
