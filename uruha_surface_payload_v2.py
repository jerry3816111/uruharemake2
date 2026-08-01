"""Compact Japanese serialization for the structured RightBrain surface contract."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass


LEGACY_JSON_V1 = "legacy_json_v1"
COMPACT_JAPANESE_V2 = "compact_japanese_v2"
SUPPORTED_MODES = frozenset({LEGACY_JSON_V1, COMPACT_JAPANESE_V2})
EXPECTED_CONTRACT_RULE = (
    "required_marker_groups is the semantic contract. Include at least one phrase from "
    "every inner list naturally and avoid every forbidden marker."
)
EXPECTED_LENGTH_COUNTING_RULE = (
    "count every visible character, including Japanese punctuation"
)
EXPECTED_COMPRESSION_ORDER = [
    "preserve required_marker_groups",
    "remove prefaces and explanations",
    "remove repetition and optional elaboration",
]


class CompactPayloadSerializationError(ValueError):
    def __init__(self, field, value, reason="unsupported_value"):
        self.field = str(field)
        self.value = deepcopy(value)
        self.reason = str(reason)
        super().__init__(f"{self.field}:{self.reason}:{self.value!r}")


@dataclass(frozen=True)
class CompactPayloadResult:
    text: str
    audit: dict


CODE_LABELS = {
    "plan_surface_contract_v1": "発話計画表面化契約第一版",
    "write_one_user_facing_japanese_reply": "利用者向けの短い日本語返答を一つ作る",
    "casual": "雑談",
    "support": "支援",
    "invite": "誘い",
    "jealousy": "嫉妬",
    "boundary": "境界設定",
    "refusal": "拒否",
    "ooc_defense": "役割外要求への防御",
    "self_introduction": "自己紹介",
    "schedule_update": "予定案内",
    "state_update": "状態更新",
    "schedule_uncertainty": "予定未確定",
    "stream_start_notice": "配信開始案内",
    "self_introduction_with_affiliation": "所属付き自己紹介",
    "acknowledge_then_recommend": "認めてから勧める",
    "state_update_then_action_plan": "状態後に次の行動",
    "uncertain_status_and_defer_commitment": "不確かさと保留",
    "navigation_announcement": "開始と行き先案内",
    "short": "短く",
    "minimal": "最小限",
    "uncertain": "不確かさ明示",
    "surface_style_only": "表現のみ",
    "neutral_energy": "平常",
    "low_energy": "低活力",
    "lighter_mood": "軽い気分",
    "moderate": "普通",
    "familiar": "親しい",
    "guarded": "慎重",
    "lazy_short": "脱力短文",
    "slightly_bratty": "少し生意気",
    "not_customer_service": "非接客",
    "neutral_casual": "中立くだけ口調",
    "moderate_directness": "ほどよく直接的",
    "leftbrain_plan": "意味計画",
    "required_marker_groups": "必須意味",
    "audited_memory_policy": "記憶権限",
    "informal_public_self_introduction": "公開くだけた自己紹介",
    "minor_delay_then_positive_promotion": "遅れ後の前向き案内",
    "fatigue_update_with_near_term_plan": "疲労と次の行動",
    "minor_health_uncertainty_affecting_schedule": "体調不確実性と予定",
    "functional_stream_start_notification": "配信開始通知",
    "playful_self_deprecating": "軽い自虐と遊び",
    "briefly_accountable_then_positive": "短く認めて前向き",
    "candid_low_energy": "率直で低活力",
    "cautious_non_dramatic": "慎重大げさなし",
    "direct_functional": "直接用件中心",
    "medium": "中",
    "high_only_for_promotion": "案内だけ高め",
    "low_but_willing": "低めだが応じる",
    "low": "低め",
    "neutral_active": "平常で能動的",
    "context_matched": "状況に合わせる",
    "in_group_audience": "仲間距離",
    "friendly_public_audience": "親しい公開距離",
    "familiar_public_audience": "慣れた公開距離",
    "public_audience": "公開距離",
    "use_at_most_one_mild_self_tease": "軽い自虐は一度まで",
    "keep_public_affiliation_visible": "公開活動とのつながりを残す",
    "keep_acknowledgement_to_one_clause": "遅れ言及は一節だけ",
    "shift_emphasis_to_shared_content": "共有内容へ重点移動",
    "state_condition_directly": "状態を直接伝える",
    "end_after_concrete_next_step": "次の一歩で終える",
    "mark_uncertainty_explicitly": "不確かさ明示",
    "soften_without_inventing": "創作せず柔らげる",
    "lead_with_actionable_information": "行動情報を先に置く",
    "stop_after_navigation": "視聴案内で終える",
    "neutral_surface_operation_1": "中立表現の第一操作",
    "neutral_surface_operation_2": "中立表現の第二操作",
    "perfect_idol_register": "完璧アイドル口調",
    "repeated_self_deprecation": "自虐反復",
    "private_life_claims": "私生活創作",
    "extended_apology": "長い謝罪",
    "self_punishment": "自己処罰表現",
    "global_high_energy": "全体高活力",
    "long_justification": "長い言い訳",
    "caregiver_register": "世話役口調",
    "crisis_dramatization": "危機の誇張",
    "medical_detail": "根拠なき医療詳細",
    "diagnosis_claim": "診断断定",
    "false_commitment": "根拠なき確約",
    "persona_catchphrase": "人物固有口癖",
    "emotional_preface": "感情的前置き",
    "background_story": "未提供の背景話",
    "neutral_surface_avoid_1": "中立表現で避ける第一項目",
    "neutral_surface_avoid_2": "中立表現で避ける第二項目",
    "neutral_surface_avoid_3": "中立表現で避ける第三項目",
    "core_message_jp": "中心意味",
    "memory_anchor": "記憶手掛かり",
    "memory_speakability": "記憶発話範囲",
    "memory_use_expected": "記憶使用要否",
    "action_intent_frame": "行動意図",
    "authorized_action": "許可行動",
    "tool_calls": "道具呼び出し",
    "human_speech_plan.content_units": "内容単位",
    "human_speech_plan.grounding_terms": "根拠語",
    "no_memory": "記憶を使わない",
    "explicit_allowed": "明示許可された記憶だけ使える",
    "do_not_mention": "記憶を発話に出さない",
    "background_only": "記憶は背景としてだけ使う",
    "latent_ok": "潜在的な背景利用だけ許可",
    "low_trust_background": "信頼が低いため背景利用だけ許可",
    "private_background": "私的情報のため背景利用だけ許可",
    "do_not_quote_raw_memory": "原文引用禁止",
    "do_not_reveal_source_text": "出典開示禁止",
    "do_not_invent_unprovided_profile": "人物情報創作禁止",
    "context": "文脈",
    "fact": "事実",
    "preference": "好み",
    "episode": "経験",
    "soft_context_only": "語調への弱い影響だけ",
}


REPLY_REQUIREMENTS = {
    "one sentence or short chat reply": "一文か短い会話返答にする",
    "natural casual Japanese": "自然でくだけた日本語にする",
    "no labels or JSON": "見出しや構造記号を出力しない",
    "no Chinese or English": "中国語や英語を混ぜない",
    "no first person 私": "一人称の「私」を使わない",
}


def normalize_mode(value):
    mode = str(value or LEGACY_JSON_V1).strip().lower()
    if mode not in SUPPORTED_MODES:
        raise ValueError(
            "structured payload mode must be one of: " + ", ".join(sorted(SUPPORTED_MODES))
        )
    return mode


def _label(value, field, *, allow_empty=False):
    code = str(value or "").strip()
    if not code and allow_empty:
        return ""
    if code not in CODE_LABELS:
        raise CompactPayloadSerializationError(field, value)
    return CODE_LABELS[code]


def _safe_text(value, field):
    text = str(value or "").strip()
    if re.search(r"[A-Za-z]", text):
        raise CompactPayloadSerializationError(field, value, "ascii_text_not_allowed")
    if "\n" in text or "\r" in text:
        raise CompactPayloadSerializationError(field, value, "multiline_text_not_allowed")
    return text


def _safe_list(values, field):
    return [_safe_text(value, f"{field}[{index}]") for index, value in enumerate(values or [])]


def _translated_list(values, field):
    return [_label(value, f"{field}[{index}]") for index, value in enumerate(values or [])]


def _joined(values, empty="なし"):
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return "、".join(cleaned) if cleaned else empty


def _reject_unknown_keys(value, allowed, field):
    if not isinstance(value, dict):
        raise CompactPayloadSerializationError(field, value, "not_object")
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        raise CompactPayloadSerializationError(field, unknown, "unknown_fields")


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompactPayloadSerializationError(field, value, "not_number")
    return str(value)


def _memory_lines(memory):
    _reject_unknown_keys(
        memory,
        {
            "policy",
            "speakability",
            "allowed_memory_cues",
            "background_style_cues",
            "forbidden",
            "reason",
        },
        "context.audited_memory_brief",
    )
    policy = _label(memory.get("policy"), "memory.policy")
    speakability = _label(memory.get("speakability"), "memory.speakability")
    lines = [f"記憶：{policy}／{speakability}"]
    allowed = []
    for index, cue in enumerate(memory.get("allowed_memory_cues") or []):
        if not isinstance(cue, dict):
            raise CompactPayloadSerializationError(f"memory.allowed[{index}]", cue, "not_object")
        _reject_unknown_keys(
            cue,
            {"kind", "jp_anchor", "terms"},
            f"memory.allowed[{index}]",
        )
        kind = _label(cue.get("kind"), f"memory.allowed[{index}].kind")
        anchor = _safe_text(cue.get("jp_anchor"), f"memory.allowed[{index}].anchor")
        terms = _safe_list(cue.get("terms") or [], f"memory.allowed[{index}].terms")
        allowed.append(f"{kind}：{_joined([anchor, *terms])}")
    if allowed:
        lines.append(f"明示可能：{_joined(allowed)}")

    background = []
    for index, cue in enumerate(memory.get("background_style_cues") or []):
        if not isinstance(cue, dict):
            raise CompactPayloadSerializationError(f"memory.background[{index}]", cue, "not_object")
        _reject_unknown_keys(
            cue,
            {"kind", "style_influence"},
            f"memory.background[{index}]",
        )
        kind = _label(cue.get("kind"), f"memory.background[{index}].kind")
        influence = _label(cue.get("style_influence"), f"memory.background[{index}].influence")
        background.append(f"{kind}：{influence}")
    if background:
        lines.append(f"背景のみ：{_joined(background)}")
    lines.append(f"記憶禁止：{_joined(_translated_list(memory.get('forbidden') or [], 'memory.forbidden'))}")
    reason = memory.get("reason")
    if reason:
        lines.append(f"理由：{_safe_text(reason, 'memory.reason')}")
    return lines


def _persona_lines(persona):
    _reject_unknown_keys(
        persona,
        {
            "role",
            "state",
            "relationship_distance",
            "stable_traits",
            "must_not_override",
            "conditional_context",
            "expression_policy",
            "protected_fields",
        },
        "context.persona_expression_brief",
    )
    _label(persona.get("role"), "persona.role")
    _translated_list(persona.get("must_not_override") or [], "persona.must_not_override")
    lines = [
        "人格："
        + "／".join(
            [
                _label(persona.get("state"), "persona.state"),
                _label(persona.get("relationship_distance"), "persona.relationship_distance"),
                _joined(_translated_list(persona.get("stable_traits") or [], "persona.stable_traits")),
            ]
        )
    ]
    context = persona.get("conditional_context")
    if context:
        lines.append(f"人格場面：{_label(context, 'persona.conditional_context')}")
    policy = persona.get("expression_policy") or {}
    if policy:
        if not isinstance(policy, dict):
            raise CompactPayloadSerializationError("persona.expression_policy", policy, "not_object")
        _reject_unknown_keys(
            policy,
            {"tone", "energy", "brevity", "social_distance", "operations", "avoid"},
            "persona.expression_policy",
        )
        lines.extend(
            [
                "人格表現："
                + "／".join(
                    [
                        _label(policy.get("tone"), "persona.policy.tone"),
                        _label(policy.get("energy"), "persona.policy.energy"),
                        _label(policy.get("brevity"), "persona.policy.brevity"),
                        _label(policy.get("social_distance"), "persona.policy.social_distance"),
                    ]
                ),
                f"人格操作：{_joined(_translated_list(policy.get('operations') or [], 'persona.policy.operations'))}",
                f"人格禁止：{_joined(_translated_list(policy.get('avoid') or [], 'persona.policy.avoid'))}",
            ]
        )
    protected = persona.get("protected_fields") or []
    if protected:
        _translated_list(protected, "persona.protected_fields")
        lines.append("人格は計画・必須意味・記憶・行動・道具を変更不可")
    return lines


def serialize_compact_japanese_payload(payload):
    _reject_unknown_keys(
        payload,
        {
            "contract_version",
            "task",
            "contract_rule",
            "user_input",
            "leftbrain_plan",
            "context",
            "required_marker_groups",
            "forbidden_markers",
            "reply_requirements",
            "output_budget",
            "surface_failure_watchlist",
        },
        "payload",
    )
    plan = payload.get("leftbrain_plan")
    context = payload.get("context")
    _reject_unknown_keys(
        plan,
        {
            "scene",
            "intent",
            "surface_act",
            "dialogue_act",
            "meaning",
            "content_units",
            "style_operators",
            "grounding_terms",
        },
        "leftbrain_plan",
    )
    _reject_unknown_keys(
        context,
        {
            "memory_summary",
            "audited_memory_brief",
            "procedural_guidance",
            "persona_expression_brief",
            "mood",
            "trust",
            "max_chars",
        },
        "context",
    )
    if payload.get("contract_rule") != EXPECTED_CONTRACT_RULE:
        raise CompactPayloadSerializationError(
            "contract_rule",
            payload.get("contract_rule"),
            "unsupported_contract_rule",
        )
    if context.get("memory_summary") != "左脳が選択した作業記憶は発話計画に統合済み。":
        raise CompactPayloadSerializationError(
            "context.memory_summary",
            context.get("memory_summary"),
            "unsupported_memory_summary",
        )
    if context.get("procedural_guidance"):
        raise CompactPayloadSerializationError(
            "context.procedural_guidance",
            context.get("procedural_guidance"),
            "unsupported_nonempty_guidance",
        )
    if payload.get("surface_failure_watchlist"):
        raise CompactPayloadSerializationError(
            "surface_failure_watchlist",
            payload.get("surface_failure_watchlist"),
            "unsupported_nonempty_watchlist",
        )
    output_budget = payload.get("output_budget")
    if output_budget:
        _reject_unknown_keys(
            output_budget,
            {"maximum_characters", "counting_rule", "compression_order"},
            "output_budget",
        )
        if int(output_budget.get("maximum_characters") or 0) != int(
            context.get("max_chars") or 48
        ):
            raise CompactPayloadSerializationError(
                "output_budget.maximum_characters",
                output_budget.get("maximum_characters"),
                "does_not_match_context",
            )
        if output_budget.get("counting_rule") != EXPECTED_LENGTH_COUNTING_RULE:
            raise CompactPayloadSerializationError(
                "output_budget.counting_rule",
                output_budget.get("counting_rule"),
                "unsupported_counting_rule",
            )
        if output_budget.get("compression_order") != EXPECTED_COMPRESSION_ORDER:
            raise CompactPayloadSerializationError(
                "output_budget.compression_order",
                output_budget.get("compression_order"),
                "unsupported_compression_order",
            )

    required_groups = []
    for index, group in enumerate(payload.get("required_marker_groups") or []):
        values = _safe_list(group, f"required_marker_groups[{index}]")
        if not values:
            raise CompactPayloadSerializationError(
                f"required_marker_groups[{index}]", group, "empty_group"
            )
        required_groups.append("／".join(values))
    if not required_groups:
        raise CompactPayloadSerializationError("required_marker_groups", [], "empty_contract")

    requirements = []
    for index, requirement in enumerate(payload.get("reply_requirements") or []):
        if str(requirement).startswith("reply must contain at most "):
            requirements.append(f"返答は句読点を含めて{int(context.get('max_chars') or 48)}字以内にする")
            continue
        translated = REPLY_REQUIREMENTS.get(str(requirement))
        if translated is None:
            raise CompactPayloadSerializationError(
                f"reply_requirements[{index}]", requirement
            )
        requirements.append(translated)

    _label(payload.get("contract_version"), "contract_version")
    _label(payload.get("task"), "task")
    scene = _label(plan.get("scene"), "plan.scene", allow_empty=True) or "指定なし"
    intent = _label(plan.get("intent"), "plan.intent", allow_empty=True) or "指定なし"
    surface_act = _label(plan.get("surface_act"), "plan.surface_act", allow_empty=True)
    dialogue_act = _label(plan.get("dialogue_act"), "plan.dialogue_act", allow_empty=True)
    plan_codes = [scene, intent, surface_act, dialogue_act]
    plan_codes = [value for value in plan_codes if value]
    _ = requirements
    lines = [
        f"要約：{_safe_text(payload.get('user_input'), 'user_input')}",
        f"計画：{'／'.join(plan_codes)}",
        f"意味：{_safe_text(plan.get('meaning'), 'plan.meaning')}",
        f"要素：{_joined(_safe_list(plan.get('content_units') or [], 'plan.content_units'))}",
        f"話題：{_joined(_safe_list(plan.get('grounding_terms') or [], 'plan.grounding_terms'))}",
        f"整え：{_joined(_translated_list(plan.get('style_operators') or [], 'plan.style_operators'))}",
        f"必須（各組から一つ）：{'｜'.join(required_groups)}",
        f"禁止語：{_joined(_safe_list(payload.get('forbidden_markers') or [], 'forbidden_markers'))}",
        *_persona_lines(context.get("persona_expression_brief")),
        f"内部値：気分{_number(context.get('mood'), 'context.mood')}／信頼{_number(context.get('trust'), 'context.trust')}",
        *_memory_lines(context.get("audited_memory_brief")),
        f"出力：{int(context.get('max_chars') or 48)}字以内／一文か短文／自然なくだけた日本語／本文のみ／中英混入禁止",
    ]
    text = "\n".join(lines)
    if re.search(r"[A-Za-z]", text):
        raise CompactPayloadSerializationError("rendered_payload", text, "ascii_text_not_allowed")

    audit = {
        "contract_version": deepcopy(payload.get("contract_version")),
        "semantic_contract": {
            "meaning": deepcopy(plan.get("meaning")),
            "content_units": deepcopy(plan.get("content_units") or []),
            "grounding_terms": deepcopy(plan.get("grounding_terms") or []),
            "required_marker_groups": deepcopy(payload.get("required_marker_groups") or []),
        },
        "persona_policy": deepcopy(context.get("persona_expression_brief")),
        "memory_policy": deepcopy(context.get("audited_memory_brief")),
        "forbidden_surface_policy": deepcopy(payload.get("forbidden_markers") or []),
        "reply_requirements": deepcopy(payload.get("reply_requirements") or []),
    }
    return CompactPayloadResult(text=text, audit=audit)


COMPACT_JAPANESE_SYSTEM_INSTRUCTION = (
    "左脳計画を短く自然な日本語会話にする表現担当。勝手に推理せず意味と話題を保つ。"
    "必須の各組から一つ以上を含め、禁止語と記憶権限を守る。人格は意味を変えない。"
    "返答本文を一つだけ出し、分析、指示、中国語、英語を出さない。"
)


COMPACT_JAPANESE_REPAIR_SUFFIX = (
    "前の案は条件違反だった。一度だけ直し、修正した返答本文だけを出す。"
)


COMPACT_JAPANESE_LENGTH_SUFFIX = (
    "文字数上限がある場合は句読点も数え、必須意味を先に残して前置き、反復、任意説明の順に削る。"
)
