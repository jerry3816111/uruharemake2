#!/usr/bin/env python3
"""Information-preserving payload representations for the V31 experiment."""

import hashlib
import json
import re
from dataclasses import dataclass


CONDITION_FACTORS = {
    "mixed_json_control": {
        "instruction_label_language": "mixed_english_labels",
        "serialization": "json",
    },
    "japanese_json": {
        "instruction_label_language": "japanese_labels",
        "serialization": "json",
    },
    "mixed_lines": {
        "instruction_label_language": "mixed_english_labels",
        "serialization": "line_message",
    },
    "japanese_lines": {
        "instruction_label_language": "japanese_labels",
        "serialization": "line_message",
    },
}


KEY_TRANSLATIONS = {
    "contract_version": "契約版",
    "task": "依頼",
    "contract_rule": "意味契約",
    "user_input": "左脳による発話要約",
    "leftbrain_plan": "左脳の発話計画",
    "scene": "場面",
    "intent": "意図",
    "surface_act": "表面行為",
    "dialogue_act": "対話行為",
    "meaning": "伝える意味",
    "content_units": "内容単位",
    "style_operators": "話し方",
    "grounding_terms": "具体語",
    "context": "文脈",
    "memory_summary": "作業記憶の状態",
    "audited_memory_brief": "記憶利用方針",
    "policy": "方針",
    "speakability": "発話可能性",
    "allowed_memory_cues": "使用可能な記憶手掛かり",
    "background_style_cues": "背景のみの記憶手掛かり",
    "forbidden": "禁止事項",
    "kind": "種類",
    "jp_anchor": "記憶要点",
    "terms": "関連語",
    "style_influence": "文体への影響",
    "reason": "理由",
    "persona_expression_brief": "人格表現方針",
    "role": "役割",
    "state": "状態",
    "relationship_distance": "関係距離",
    "stable_traits": "安定した話し方",
    "must_not_override": "上書き禁止",
    "mood": "気分",
    "trust": "信頼度",
    "max_chars": "最大文字数",
    "required_marker_groups": "必須意味群",
    "forbidden_markers": "禁止表現",
    "reply_requirements": "返答条件",
    "surface_failure_watchlist": "表面失敗の注意事項",
    "priority_order": "優先順",
    "semantic_slot_policy": "意味スロット方針",
    "reject_families": "拒否対象",
    "style_guard": "文体ガード",
}


VALUE_TRANSLATIONS = {
    "plan_surface_contract_v1": "発話表現契約第1版",
    "write_one_user_facing_japanese_reply": "ユーザー向けの自然な日本語の返事を一つ書く",
    (
        "required_marker_groups is the semantic contract. Include at least one phrase from "
        "every inner list naturally and avoid every forbidden marker."
    ): "必須意味群が意味の契約。各内側の組から一つ以上を自然に表し、禁止表現は使わない。",
    "support": "支える場面",
    "casual": "日常場面",
    "planning": "相談場面",
    "relationship": "関係についての場面",
    "late_arrival_uncertainty": "遅刻理由が不明な不安と怒り",
    "celebrate_small_win": "小さな達成を一緒に喜ぶ",
    "minor_failure_self_blame": "一度の失敗による自己否定を軽く戻す",
    "reversible_choice": "後で変えられる選択を手伝う",
    "reference_probe": "曖昧な作品の手掛かりを聞く",
    "nonsense_tease": "意味の飛んだ冗談に軽く突っ込む",
    "state_answer": "現在の自分の状態を直接答える",
    "set_gentle_boundary": "親しさを保ちながら軽い限界を示す",
    "accept_correction": "訂正を受け入れて言い直す",
    "relationship_reassurance": "関係への不安を重くせず否定する",
    "food_advice": "食事について具体的に助言する",
    "memory_sensitive_practical_reply": "記憶の扱いに注意した実用的な返答",
    "practical_action_response": "具体的な次の行動を返す",
    "validate_then_check": "感情を認めてから確認を促す",
    "specific_praise": "具体的に褒める",
    "light_reframe": "軽く捉え直す",
    "offer_light_criterion": "軽い選び方を提案する",
    "clarify_reference": "追加の手掛かりを聞く",
    "casual_status": "日常的な状態を直接答える",
    "warm_limit": "親しさのある短い境界を示す",
    "brief_repair": "短く訂正する",
    "light_reassurance": "重くしない安心を返す",
    "no_memory": "記憶を使わない",
    "explicit_allowed": "明示してよい",
    "do_not_mention": "言葉に出さない",
    "private": "非公開",
    "recent_food_update": "最近の食事と体調の更新",
    "surface_style_only": "表面の話し方だけを担当する",
    "neutral_energy": "平常の活力",
    "low_energy": "低い活力",
    "lighter_mood": "少し明るい気分",
    "familiar": "親しい",
    "moderate": "普通",
    "guarded": "距離を置く",
    "lazy_short": "短く少し気だるい",
    "slightly_bratty": "少し生意気",
    "not_customer_service": "接客口調にしない",
    "short": "短く",
    "no_polite_register": "敬語にしない",
    "leftbrain_plan": "左脳の発話計画",
    "required_marker_groups": "必須意味群",
    "audited_memory_policy": "監査済みの記憶方針",
    "do_not_quote_raw_memory": "記憶の原文を引用しない",
    "do_not_reveal_source_text": "記憶の出典文を見せない",
    "do_not_invent_unprovided_profile": "与えられていない人物情報を作らない",
    "V21 source-separated development case": "旧版の出典分離開発ケース",
    "one sentence or short chat reply": "一文または短いチャット返答",
    "natural casual Japanese": "自然でくだけた日本語",
    "no labels or JSON": "ラベルや構造データを出力しない",
    "no Chinese or English": "中国語や英語を出力しない",
    "no first person 私": "一人称の「私」を使わない",
    "semantic_contract_first": "意味契約を最優先",
    "memory_policy_second": "記憶方針を次に優先",
    "casual_surface_third": "くだけた表現を最後に調整",
    "semantic_slots_missing": "必要な意味の欠落",
    "unexpected_ascii_leak": "予期しない英字の混入",
    "cjk_language_leak": "中国語表現の混入",
    "nonstandard_cjk_surface": "不自然な漢字表現",
    "unicode_replacement_character": "文字化け",
    "polite_tone_drift": "敬語へのずれ",
    "over_max_chars": "最大文字数の超過",
}


_ASCII_RE = re.compile(r"[A-Za-z]")
_JAPANESE_ASCII_ALLOWLIST = set()


@dataclass(frozen=True)
class PayloadVariant:
    text: str
    metadata: dict


def _stable_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _leaf_records(value, path=()):
    records = []
    if isinstance(value, dict):
        if not value:
            records.append((path, "empty_dict", {}))
        for key, child in value.items():
            records.extend(_leaf_records(child, (*path, str(key))))
        return records
    if isinstance(value, list):
        if not value:
            records.append((path, "empty_list", []))
        for index, child in enumerate(value):
            records.extend(_leaf_records(child, (*path, index)))
        return records
    records.append((path, "scalar", value))
    return records


def _translate_tree(value, path=()):
    if isinstance(value, dict):
        return {
            KEY_TRANSLATIONS.get(str(key), str(key)): _translate_tree(
                child,
                (*path, str(key)),
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [
            _translate_tree(child, (*path, index))
            for index, child in enumerate(value)
        ]
    if isinstance(value, str):
        if value == "casual" and "style_operators" in path:
            return "くだけた口調"
        return VALUE_TRANSLATIONS.get(value, value)
    return value


def _reverse_translate_tree(value, path=()):
    reverse_keys = {translated: source for source, translated in KEY_TRANSLATIONS.items()}
    reverse_values = {
        translated: source for source, translated in VALUE_TRANSLATIONS.items()
    }
    if isinstance(value, dict):
        restored = {}
        for key, child in value.items():
            source_key = reverse_keys.get(str(key), str(key))
            restored[source_key] = _reverse_translate_tree(
                child,
                (*path, source_key),
            )
        return restored
    if isinstance(value, list):
        return [
            _reverse_translate_tree(child, (*path, index))
            for index, child in enumerate(value)
        ]
    if isinstance(value, str):
        if value == "くだけた口調" and "style_operators" in path:
            return "casual"
        return reverse_values.get(value, value)
    return value


def _path_text(path):
    output = ""
    for part in path:
        if isinstance(part, int):
            output += f"[{part + 1}]"
        else:
            output += ("." if output else "") + str(part)
    return output or "内容"


def _line_value(kind, value):
    if kind == "empty_dict":
        return "{}"
    if kind == "empty_list":
        return "[]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


def _render_lines(value):
    lines = []

    def visit(node, path=()):
        if isinstance(node, dict):
            if not node:
                lines.append(f"{_path_text(path)}: {{}}")
            for key, child in node.items():
                visit(child, (*path, str(key)))
            return
        if isinstance(node, list):
            if not node:
                lines.append(f"{_path_text(path)}: []")
                return
            if all(not isinstance(child, (dict, list)) for child in node):
                values = "｜".join(_line_value("scalar", child) for child in node)
                lines.append(f"{_path_text(path)}: {values}")
                return
            if all(
                isinstance(child, list)
                and all(not isinstance(item, (dict, list)) for item in child)
                for child in node
            ):
                groups = [
                    "／".join(_line_value("scalar", item) for item in child)
                    for child in node
                ]
                lines.append(f"{_path_text(path)}: " + "；".join(groups))
                return
            for index, child in enumerate(node):
                visit(child, (*path, index))
            return
        lines.append(f"{_path_text(path)}: {_line_value('scalar', node)}")

    visit(value)
    return "\n".join(lines)


def _unmapped_ascii_values(value):
    return sorted(
        {
            str(leaf)
            for _, kind, leaf in _leaf_records(value)
            if kind == "scalar"
            and isinstance(leaf, str)
            and _ASCII_RE.search(leaf)
            and leaf not in _JAPANESE_ASCII_ALLOWLIST
        }
    )


def build_payload_variant(control_payload, condition):
    if condition not in CONDITION_FACTORS:
        raise ValueError(f"Unknown V31 payload condition: {condition}")
    canonical = json.loads(str(control_payload))
    factors = CONDITION_FACTORS[condition]
    japanese = factors["instruction_label_language"] == "japanese_labels"
    represented = _translate_tree(canonical) if japanese else canonical
    if factors["serialization"] == "json":
        text = json.dumps(represented, ensure_ascii=False, separators=(",", ":"))
    else:
        text = _render_lines(represented)

    canonical_leaves = _leaf_records(canonical)
    represented_leaves = _leaf_records(represented)
    metadata = {
        "condition": condition,
        **factors,
        "canonical_payload_sha256": _sha256_text(_stable_json(canonical)),
        "rendered_payload_sha256": _sha256_text(text),
        "canonical_leaf_count": len(canonical_leaves),
        "represented_leaf_count": len(represented_leaves),
        "leaf_count_matches": len(canonical_leaves) == len(represented_leaves),
        "translation_roundtrip_matches": (
            _reverse_translate_tree(represented) == canonical if japanese else True
        ),
        "unmapped_ascii_values": _unmapped_ascii_values(represented) if japanese else [],
        "rendered_character_count": len(text),
        "rendered_ascii_letter_count": len(re.findall(r"[A-Za-z]", text)),
    }
    metadata["representation_integrity_pass"] = all(
        [
            metadata["leaf_count_matches"],
            metadata["translation_roundtrip_matches"],
            not metadata["unmapped_ascii_values"],
        ]
    )
    return PayloadVariant(text=text, metadata=metadata)
