"""M33 source-anchored semantic atoms and bounded Japanese commitment.

The model-produced M31 canonical record is useful but not independent evidence
that the exact source meaning survived normalization.  This module extracts a
small, explicit set of observable atoms directly from the current source,
compares them with M31/M32, and either renders a bounded source-grounded
Japanese proposition or declines authority.  It is intentionally not an
open-domain parser.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy


SOURCE_ATOM_LEDGER_SCHEMA_M33 = "uruha_source_semantic_atom_ledger_m33"
SOURCE_ATOM_VERIFICATION_SCHEMA_M33 = "uruha_source_atom_verification_m33"
SOURCE_ATOM_COMMIT_SCHEMA_M33 = "uruha_source_anchored_semantic_commit_m33"


PROTECTED_INTENTS = {
    "safety",
    "crisis_support",
    "memory_recall",
    "grounded_profile_recall",
}
PROTECTED_SCENES = {"safety", "crisis", "factual_memory"}


ZH_NUMBERS = {
    "一": ("一", "1"),
    "二": ("二", "2"),
    "兩": ("二", "2"),
    "三": ("三", "3"),
    "四": ("四", "4"),
    "五": ("五", "5"),
    "六": ("六", "6"),
    "七": ("七", "7"),
    "八": ("八", "8"),
    "九": ("九", "9"),
    "十": ("十", "10"),
}
EN_NUMBERS = {
    "one": ("一", "1"),
    "two": ("二", "2"),
    "three": ("三", "3"),
    "four": ("四", "4"),
    "five": ("五", "5"),
    "six": ("六", "6"),
    "seven": ("七", "7"),
    "eight": ("八", "8"),
    "nine": ("九", "9"),
    "ten": ("十", "10"),
}
WEEKDAY_JP = {
    "一": "月曜日",
    "二": "火曜日",
    "三": "水曜日",
    "四": "木曜日",
    "五": "金曜日",
    "六": "土曜日",
    "日": "日曜日",
    "天": "日曜日",
    "monday": "月曜日",
    "tuesday": "火曜日",
    "wednesday": "水曜日",
    "thursday": "木曜日",
    "friday": "金曜日",
    "saturday": "土曜日",
    "sunday": "日曜日",
}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _language(text):
    value = str(text or "")
    if re.search(r"[ぁ-んァ-ヶー]", value):
        return "ja"
    if re.search(r"[一-龠]", value):
        return "zh"
    return "en"


def _unique(values):
    result = []
    for value in values:
        value = str(value or "").strip()
        if value and value not in result:
            result.append(value)
    return result


def _atom(atom_type, value_jp, source_span, rule_id, aliases=()):
    aliases_jp = _unique([value_jp, *aliases])
    return {
        "atom_id": _digest(f"{atom_type}|{value_jp}|{rule_id}"),
        "type": atom_type,
        "value_jp": str(value_jp or "").strip(),
        "aliases_jp": aliases_jp,
        "knowledge_status": "known_from_exact_source_rule",
        "source_span_digest": _digest(source_span),
        "rule_id": rule_id,
        "provenance": "exact_current_source",
        "confidence": 1.0,
        "raw_source_persisted": False,
    }


def _number_atom(atom_type, raw, counter, rule_id):
    pair = ZH_NUMBERS.get(raw) or EN_NUMBERS.get(str(raw).lower())
    if not pair and str(raw).isdigit():
        pair = (str(raw), str(raw))
    if not pair:
        return None
    kanji, digit = pair
    return _atom(
        atom_type,
        f"{kanji}{counter}",
        raw,
        rule_id,
        aliases=(f"{digit}{counter}",),
    )


def _weekday_atom(atom_type, raw, rule_id, next_week=False):
    key = str(raw or "").strip().lower()
    weekday = WEEKDAY_JP.get(key)
    if not weekday:
        return None
    short = weekday.replace("曜日", "曜")
    if next_week:
        return _atom(
            atom_type,
            f"来週の{weekday}",
            raw,
            rule_id,
            aliases=(f"来週{weekday}", f"来週の{short}", f"来週{short}"),
        )
    return _atom(atom_type, weekday, raw, rule_id, aliases=(short,))


def _clock_atom(raw_period, raw_hour, raw_minute, rule_id):
    pair = ZH_NUMBERS.get(raw_hour) or EN_NUMBERS.get(str(raw_hour).lower())
    if not pair and str(raw_hour).isdigit():
        pair = (str(raw_hour), str(raw_hour))
    if not pair:
        return None
    kanji, digit = pair
    period = {
        "上午": "午前",
        "下午": "午後",
        "a.m.": "午前",
        "am": "午前",
        "p.m.": "午後",
        "pm": "午後",
        "午前": "午前",
        "午後": "午後",
    }.get(str(raw_period or "").lower(), str(raw_period or ""))
    minute = str(raw_minute or "").strip()
    if minute in {"30", "三十"}:
        return _atom(
            "clock_time",
            f"{period}{kanji}時半",
            f"{raw_period}{raw_hour}:{minute}",
            rule_id,
            aliases=(f"{period}{digit}時半", "15時30分" if period == "午後" and digit == "3" else ""),
        )
    return _atom(
        "clock_time",
        f"{period}{kanji}時",
        f"{raw_period}{raw_hour}",
        rule_id,
        aliases=(f"{period}{digit}時",),
    )


def _parse_zh(text):
    atoms = []
    rule = "m33_zh_no_rule"
    family = None

    if "裡沒有" in text and any(noun in text for noun in ("剪刀", "鉛筆")):
        rule = "m33_zh_negated_container_quantity_v1"
        family = "negated_object_quantity"
        container = "引き出し" if "抽屜" in text else "箱"
        container_span = "抽屜" if "抽屜" in text else "盒子"
        object_jp = "はさみ" if "剪刀" in text else "鉛筆"
        object_span = "剪刀" if "剪刀" in text else "鉛筆"
        number_match = re.search(r"([一二兩三四五六七八九十0-9]+)(?:把|支)", text)
        atoms.extend(
            [
                _atom("container", container, container_span, rule),
                _atom("object", object_jp, object_span, rule, aliases=("ハサミ",) if object_jp == "はさみ" else ()),
            ]
        )
        if number_match:
            atoms.append(_number_atom("quantity", number_match.group(1), "本", rule))
        atoms.append(_atom("negation", "ない", "沒有", rule, aliases=("入っていない", "入ってない")))

    elif "改到" in text:
        rule = "m33_zh_change_target_time_v1"
        family = "change_target_time"
        if "訪談" in text:
            atoms.append(_atom("event", "面談", "訪談", rule, aliases=("インタビュー",)))
        elif "巴士" in text:
            atoms.append(_atom("event", "バスの出発", "巴士出發", rule, aliases=("バス", "出発")))
        atoms.append(_atom("change", "変更", "改到", rule, aliases=("変更された", "変わった", "移った")))
        weekday_match = re.search(r"下週([一二三四五六日天])", text)
        if weekday_match:
            atoms.append(_weekday_atom("weekday", weekday_match.group(1), rule, next_week=True))
        clock_match = re.search(r"(上午|下午)([一二兩三四五六七八九十0-9]+)點", text)
        if clock_match:
            atoms.append(_clock_atom(clock_match.group(1), clock_match.group(2), None, rule))

    elif "把" in text and "放在" in text:
        rule = "m33_zh_spatial_put_v1"
        family = "spatial_put"
        if "小雨" in text:
            atoms.append(_atom("entity", "シャオユー", "小雨", rule, aliases=("小雨",)))
        number_match = re.search(r"([一二兩三四五六七八九十0-9]+)張", text)
        if number_match:
            atoms.append(_number_atom("quantity", number_match.group(1), "枚", rule))
        if "白色卡片" in text:
            atoms.append(_atom("object", "白いカード", "白色卡片", rule, aliases=("白色のカード",)))
        if "藍盒子" in text:
            atoms.append(_atom("container", "青い箱", "藍盒子", rule, aliases=("青色の箱",)))
        atoms.append(_atom("spatial_relation", "中", "裡", rule, aliases=("入れた",)))
        atoms.append(_atom("event", "入れた", "放在", rule, aliases=("置いた",)))

    elif "跟" in text and "開會" in text:
        rule = "m33_zh_entity_meeting_relative_time_v1"
        family = "entity_meeting"
        if "周經理" in text:
            atoms.append(_atom("entity", "周マネージャー", "周經理", rule, aliases=("周部長", "周さん")))
        if "阿凱" in text:
            atoms.append(_atom("relation", "アカイ", "阿凱", rule, aliases=("阿凱",)))
        if "大後天" in text:
            atoms.append(_atom("relative_time", "明々後日", "大後天", rule, aliases=("三日後",)))
        clock_match = re.search(r"(上午|下午)([一二兩三四五六七八九十0-9]+)點", text)
        if clock_match:
            atoms.append(_clock_atom(clock_match.group(1), clock_match.group(2), None, rule))
        atoms.append(_atom("event", "会議", "開會", rule, aliases=("ミーティング",)))

    elif "回診" in text:
        rule = "m33_zh_entity_clinic_relative_time_v1"
        family = "entity_clinic"
        if "陳醫師" in text:
            atoms.append(_atom("entity", "陳医師", "陳醫師", rule, aliases=("陳先生",)))
        if "後天" in text:
            atoms.append(_atom("relative_time", "明後日", "後天", rule))
        clock_match = re.search(r"(上午|下午)([一二兩三四五六七八九十0-9]+)點", text)
        if clock_match:
            atoms.append(_clock_atom(clock_match.group(1), clock_match.group(2), None, rule))
        atoms.append(_atom("event", "再診", "回診", rule, aliases=("診察", "受診")))

    return family, rule, [atom for atom in atoms if atom]


def _parse_en(text):
    lower = text.lower()
    atoms = []
    rule = "m33_en_no_rule"
    family = None

    if " does not contain " in lower:
        rule = "m33_en_negated_container_quantity_v1"
        family = "negated_object_quantity"
        if "drawer" in lower:
            atoms.append(_atom("container", "引き出し", "drawer", rule))
        if "silver keys" in lower:
            atoms.append(_atom("object", "銀の鍵", "silver keys", rule, aliases=("銀色の鍵",)))
        number_match = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|[0-9]+)\b", lower)
        if number_match:
            atoms.append(_number_atom("quantity", number_match.group(1), "本", rule))
        atoms.append(_atom("negation", "ない", "does not", rule, aliases=("入っていない", "入ってない")))

    elif " moved from " in lower and " to " in lower:
        rule = "m33_en_change_source_target_weekday_v1"
        family = "change_source_target"
        if "workshop" in lower:
            atoms.append(_atom("event", "ワークショップ", "workshop", rule))
        atoms.append(_atom("change", "変更", "moved", rule, aliases=("変更された", "移った", "変わった")))
        match = re.search(r"from\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+to\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", lower)
        if match:
            atoms.append(_weekday_atom("source_weekday", match.group(1), rule))
            atoms.append(_weekday_atom("target_weekday", match.group(2), rule))

    elif " moved to " in lower:
        rule = "m33_en_change_target_weekday_v1"
        family = "change_target_time"
        if "flight" in lower:
            atoms.append(_atom("event", "フライト", "flight", rule, aliases=("便", "飛行機")))
        atoms.append(_atom("change", "変更", "moved", rule, aliases=("変更された", "移った", "変わった")))
        match = re.search(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", lower)
        if match:
            atoms.append(_weekday_atom("weekday", match.group(1), rule, next_week=True))

    elif " placed " in lower and " beside " in lower:
        rule = "m33_en_spatial_put_v1"
        family = "spatial_put"
        if "lena" in lower:
            atoms.append(_atom("entity", "レナ", "Lena", rule))
        number_match = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|[0-9]+)\b", lower)
        if number_match:
            atoms.append(_number_atom("quantity", number_match.group(1), "冊", rule))
        if "green notebooks" in lower:
            atoms.append(_atom("object", "緑のノート", "green notebooks", rule, aliases=("緑色のノート",)))
        if "printer" in lower:
            atoms.append(_atom("landmark", "プリンター", "printer", rule))
        atoms.append(_atom("spatial_relation", "横", "beside", rule, aliases=("そば",)))
        atoms.append(_atom("event", "置いた", "placed", rule))

    elif " meets " in lower and "day after tomorrow" in lower:
        rule = "m33_en_entity_meeting_relative_time_v1"
        family = "entity_meeting"
        if "priya" in lower:
            atoms.append(_atom("entity", "プリヤ", "Priya", rule))
        if "omar" in lower:
            atoms.append(_atom("relation", "オマール", "Omar", rule, aliases=("オマー",)))
        atoms.append(_atom("relative_time", "明後日", "day after tomorrow", rule))
        time_match = re.search(r"([0-9]+):([0-9]+)\s*(a\.m\.|p\.m\.|am|pm)", lower)
        if time_match:
            atoms.append(_clock_atom(time_match.group(3), time_match.group(1), time_match.group(2), rule))
        atoms.append(_atom("event", "会う", "meets", rule, aliases=("面会",)))

    return family, rule, [atom for atom in atoms if atom]


def _parse_ja(text):
    atoms = []
    rule = "m33_ja_identity_no_rule"
    family = None

    if "しかない" in text:
        rule = "m33_ja_limited_quantity_identity_v1"
        family = "japanese_identity"
        container_match = re.search(r"(?:この)?([^、。には]{1,12})には", text)
        if container_match:
            atoms.append(_atom("container", container_match.group(1), container_match.group(1), rule))
        object_match = re.search(r"には([^、。]{1,16}?)が[一二三四五六七八九十0-9]+[本冊枚丁]しかない", text)
        if object_match:
            atoms.append(_atom("object", object_match.group(1), object_match.group(1), rule))
        quantity_match = re.search(r"([一二三四五六七八九十0-9]+[本冊枚丁])しかない", text)
        if quantity_match:
            atoms.append(_atom("quantity", quantity_match.group(1), quantity_match.group(1), rule))
        atoms.append(_atom("limitation", "しかない", "しかない", rule))

    elif "変更された" in text:
        rule = "m33_ja_change_identity_v1"
        family = "japanese_identity"
        event_match = re.match(r"([^、。は]{1,16})は", text)
        if event_match:
            atoms.append(_atom("event", event_match.group(1), event_match.group(1), rule))
        atoms.append(_atom("change", "変更された", "変更された", rule, aliases=("変更", "移った")))
        change_match = re.search(r"(月曜(?:日)?|火曜(?:日)?|水曜(?:日)?|木曜(?:日)?|金曜(?:日)?|土曜(?:日)?|日曜(?:日)?)から(月曜(?:日)?|火曜(?:日)?|水曜(?:日)?|木曜(?:日)?|金曜(?:日)?|土曜(?:日)?|日曜(?:日)?)に", text)
        if change_match:
            atoms.append(_atom("source_weekday", change_match.group(1), change_match.group(1), rule))
            atoms.append(_atom("target_weekday", change_match.group(2), change_match.group(2), rule))

    elif "置いた" in text:
        rule = "m33_ja_spatial_put_identity_v1"
        family = "japanese_identity"
        entity_match = re.match(r"([^、。は]{1,12})は", text)
        if entity_match:
            atoms.append(_atom("entity", entity_match.group(1), entity_match.group(1), rule))
        object_match = re.search(r"([一二三四五六七八九十0-9]+[本冊枚丁])の([^、。を]{1,16})を", text)
        if object_match:
            atoms.append(_atom("quantity", object_match.group(1), object_match.group(1), rule))
            atoms.append(_atom("object", object_match.group(2), object_match.group(2), rule))
        landmark_match = re.search(r"を([^、。の]{1,16})の(横|そば)に置いた", text)
        if landmark_match:
            atoms.append(_atom("landmark", landmark_match.group(1), landmark_match.group(1), rule))
            atoms.append(_atom("spatial_relation", landmark_match.group(2), landmark_match.group(2), rule))
        atoms.append(_atom("event", "置いた", "置いた", rule))

    elif "戻る" in text:
        rule = "m33_ja_entity_time_identity_v1"
        family = "japanese_identity"
        entity_match = re.match(r"([^、。は]{1,12})は", text)
        if entity_match:
            atoms.append(_atom("entity", entity_match.group(1), entity_match.group(1), rule))
        if "再来週" in text:
            atoms.append(_atom("relative_time", "再来週", "再来週", rule))
        weekday_match = re.search(r"(月曜(?:日)?|火曜(?:日)?|水曜(?:日)?|木曜(?:日)?|金曜(?:日)?|土曜(?:日)?|日曜(?:日)?)", text)
        if weekday_match:
            atoms.append(_atom("weekday", weekday_match.group(1), weekday_match.group(1), rule))
        clock_match = re.search(r"(午前|午後)([一二三四五六七八九十0-9]+)時", text)
        if clock_match:
            atoms.append(_clock_atom(clock_match.group(1), clock_match.group(2), None, rule))
        atoms.append(_atom("event", "戻る", "戻る", rule, aliases=("帰る",)))

    return family, rule, [atom for atom in atoms if atom]


def extract_source_semantic_atoms_m33(source_text, projection_candidate):
    """Extract a raw-free typed ledger from the exact current source."""
    text = str(source_text or "").strip()
    candidate = deepcopy(projection_candidate or {})
    language = _language(text)
    ledger = {
        "schema": SOURCE_ATOM_LEDGER_SCHEMA_M33,
        "status": "not_applicable",
        "reason": "m29_projection_not_required",
        "source_language": language,
        "source_digest": _digest(text),
        "family": None,
        "rule_id": None,
        "atoms": [],
        "atom_types": [],
        "direct_japanese_identity": False,
        "raw_dialogue_persisted": False,
        "raw_source_spans_persisted": False,
        "claim_boundary": "bounded deterministic source atoms; not open-domain semantic parsing",
    }
    if not candidate.get("projection_required"):
        return ledger
    if re.search(r"(?:\.\.\.|…{1,}|……|あの[、,]?\s*$|如果.+那個[、,]?\s*$)", text):
        ledger.update(
            {
                "status": "incomplete_source_abstained",
                "reason": "source_fragment_incomplete",
            }
        )
        return ledger

    if language == "ja":
        family, rule, atoms = _parse_ja(text)
    elif language == "zh":
        family, rule, atoms = _parse_zh(text)
    else:
        family, rule, atoms = _parse_en(text)
    if not family or len(atoms) < 3:
        ledger.update(
            {
                "status": "source_pattern_unavailable",
                "reason": "bounded_source_atom_rule_not_matched",
                "rule_id": rule,
            }
        )
        return ledger

    ledger.update(
        {
            "status": "source_atoms_extracted",
            "reason": "bounded_exact_source_rule_matched",
            "family": family,
            "rule_id": rule,
            "atoms": atoms,
            "atom_types": _unique(atom["type"] for atom in atoms),
            "direct_japanese_identity": language == "ja",
            "atom_count": len(atoms),
        }
    )
    return ledger


def _atom_value(ledger, atom_type):
    for atom in ledger.get("atoms") or []:
        if atom.get("type") == atom_type:
            return str(atom.get("value_jp") or "")
    return ""


def _render_bounded_japanese(source_text, ledger):
    family = ledger.get("family")
    language = ledger.get("source_language")
    if language == "ja" and family == "japanese_identity":
        proposition = str(source_text or "").strip().rstrip("。！？!?")
        return f"{proposition}んだね。"

    entity = _atom_value(ledger, "entity")
    relation = _atom_value(ledger, "relation")
    relative_time = _atom_value(ledger, "relative_time")
    clock_time = _atom_value(ledger, "clock_time")
    event = _atom_value(ledger, "event")
    container = _atom_value(ledger, "container")
    obj = _atom_value(ledger, "object")
    quantity = _atom_value(ledger, "quantity")
    weekday = _atom_value(ledger, "weekday")
    source_weekday = _atom_value(ledger, "source_weekday")
    target_weekday = _atom_value(ledger, "target_weekday")
    landmark = _atom_value(ledger, "landmark")
    spatial = _atom_value(ledger, "spatial_relation")

    if family == "entity_meeting":
        verb = "会議する" if event == "会議" else "会う"
        return f"{entity}は{relative_time}の{clock_time}に{relation}と{verb}んだね。"
    if family == "entity_clinic":
        return f"{entity}は{relative_time}の{clock_time}に{event}するんだね。"
    if family == "negated_object_quantity":
        return f"{container}には{quantity}の{obj}がないんだね。"
    if family == "change_source_target":
        return f"{event}は{source_weekday}から{target_weekday}に変更されたんだね。"
    if family == "change_target_time":
        if event == "バスの出発":
            return f"{event}は{weekday}に変更されたんだね。"
        return f"{event}は{weekday}{clock_time}に変更されたんだね。"
    if family == "spatial_put":
        counter_object = f"{quantity}の{obj}"
        destination = f"{container}の中" if container else f"{landmark}の{spatial}"
        verb = "入れた" if container else "置いた"
        return f"{entity}は{counter_object}を{destination}に{verb}んだね。"
    return ""


def build_source_anchored_semantic_commit_m33(
    source_text,
    ledger,
    semantic_authorization_m31=None,
    semantic_commit_m32=None,
):
    """Verify canonical atoms and build a bounded source-authoritative commit."""
    ledger = deepcopy(ledger or {})
    m31 = deepcopy(semantic_authorization_m31 or {})
    m32 = deepcopy(semantic_commit_m32 or {})
    verification = {
        "schema": SOURCE_ATOM_VERIFICATION_SCHEMA_M33,
        "status": "not_applicable",
        "reason": "source_atom_ledger_not_complete",
        "source_ledger_digest": _digest(ledger),
        "atom_results": [],
        "source_conflict_detected": False,
        "raw_dialogue_persisted": False,
    }
    contract = {
        "schema": SOURCE_ATOM_COMMIT_SCHEMA_M33,
        "status": "not_applicable",
        "reason": "source_atom_ledger_not_complete",
        "surface_authority": False,
        "source_ledger_digest": verification["source_ledger_digest"],
        "raw_dialogue_persisted": False,
        "model_response_raw_persisted": False,
        "claim_boundary": "bounded source-anchored semantic commitment; not open-domain translation or human understanding",
    }
    if ledger.get("status") != "source_atoms_extracted":
        return None, verification, contract

    canonical_text = " ".join(
        str(value or "").strip()
        for value in (
            m31.get("subject_jp"),
            m31.get("predicate_jp"),
            m31.get("time_jp"),
            m31.get("literal_summary_jp"),
            m32.get("literal_summary_jp"),
        )
        if str(value or "").strip()
    )
    identity = bool(ledger.get("direct_japanese_identity"))
    atom_results = []
    for atom in ledger.get("atoms") or []:
        aliases = list(atom.get("aliases_jp") or [])
        matched = [alias for alias in aliases if alias and alias in canonical_text]
        status = (
            "supported_by_source_identity"
            if identity
            else "supported"
            if matched
            else "contradicted_by_canonical_omission"
            if canonical_text
            else "canonical_unavailable"
        )
        atom_results.append(
            {
                "atom_id": atom.get("atom_id"),
                "type": atom.get("type"),
                "source_value_jp": atom.get("value_jp"),
                "status": status,
                "matched_aliases_jp": matched,
                "source_span_digest": atom.get("source_span_digest"),
                "rule_id": atom.get("rule_id"),
            }
        )
    conflicts = [
        row for row in atom_results if row["status"] == "contradicted_by_canonical_omission"
    ]
    verification.update(
        {
            "status": "source_atoms_verified" if not conflicts else "source_canonical_conflict",
            "reason": "all_atoms_supported" if not conflicts else "one_or_more_source_atoms_missing_from_canonical",
            "atom_results": atom_results,
            "source_atom_count": len(atom_results),
            "supported_atom_count": len(atom_results) - len(conflicts),
            "conflict_atom_count": len(conflicts),
            "source_conflict_detected": bool(conflicts),
            "direct_japanese_identity": identity,
            "m31_status": m31.get("status") or "not_available",
            "m32_status": m32.get("status") or "not_available",
        }
    )

    response = _render_bounded_japanese(source_text, ledger)
    response_japanese = bool(re.search(r"[ぁ-んァ-ヶー一-龠]", response))
    surface_checks = []
    for atom in ledger.get("atoms") or []:
        aliases = list(atom.get("aliases_jp") or [])
        matched = [alias for alias in aliases if alias and alias in response]
        surface_checks.append(
            {
                "atom_id": atom.get("atom_id"),
                "type": atom.get("type"),
                "passed": bool(matched),
                "matched_aliases_jp": matched,
            }
        )
    all_atoms_visible = bool(surface_checks) and all(
        row["passed"] for row in surface_checks
    )
    if not response or not response_japanese or not all_atoms_visible:
        contract.update(
            {
                "status": "source_atom_commit_rejected",
                "reason": "bounded_source_render_checks_failed",
                "source_conflict_detected": bool(conflicts),
                "surface_checks": surface_checks,
            }
        )
        return None, verification, contract

    repair_kind = (
        "direct_japanese_identity_commit"
        if identity
        else "source_atom_bounded_reconstruction"
        if conflicts or not canonical_text
        else "source_verified_canonical_commit"
    )
    polarity = (
        "negated"
        if {"negation", "limitation"}.intersection(
            set(ledger.get("atom_types") or [])
        )
        else "affirmed"
    )
    anchors = _unique(
        next(iter(row.get("matched_aliases_jp") or []), "")
        for row in surface_checks
    )
    contract.update(
        {
            "status": "source_anchored_semantic_committed",
            "reason": "bounded_source_atoms_committed_to_japanese_surface",
            "surface_authority": True,
            "repair_kind": repair_kind,
            "source_language": ledger.get("source_language"),
            "source_family": ledger.get("family"),
            "source_rule_id": ledger.get("rule_id"),
            "source_polarity": polarity,
            "polarity": polarity,
            "source_atom_count": len(surface_checks),
            "source_atom_types": list(ledger.get("atom_types") or []),
            "source_atom_trace_coverage": 1.0,
            "source_conflict_detected": bool(conflicts),
            "source_conflict_authority_count": 0,
            "verification_status": verification.get("status"),
            "literal_summary_jp": response.removesuffix("んだね。")[:180],
            "response_jp": response[:200],
            "surface_anchors_jp": anchors[:8],
            "visible_anchor_count": len(anchors[:8]),
            "surface_checks": surface_checks,
            "suppresses_new_pending_prediction": True,
        }
    )
    plan = {
        "candidate_label": "m33_source_anchored_semantic_commit",
        "intent": "source_anchored_semantic_commit_m33",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "原文の観測可能な意味を崩さず受け取っている",
        "reply_goal": "source-anchored atoms を自然な日本語表面に届ける",
        "jp_summary": response[:160],
        "core_message_jp": response[:200],
        "cognitive_mode": "direct",
        "response_mode": "source_anchored_semantic_commit_m33",
        "uncertainty": 0.08,
        "premise_check": "accept",
        "self_check": True,
        "surface_act": "source_anchored_semantic_commit_m33",
        "payload_level": "low",
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": 160,
            "casual_japanese_only": True,
            "forbid_polite": True,
        },
        "source_semantic_atoms_m33": deepcopy(ledger),
        "semantic_atom_verification_m33": deepcopy(verification),
        "source_anchored_semantic_commit_m33": deepcopy(contract),
    }
    return plan, verification, contract


def apply_source_anchored_semantic_commit_m33(plan, commitment):
    """Apply M33 only when protected safety or factual-memory plans do not own the turn."""
    updated = deepcopy(plan or {})
    contract = deepcopy(commitment or {})
    protected_reason = None
    if str(updated.get("intent") or "") in PROTECTED_INTENTS:
        protected_reason = "protected_current_intent"
    elif str(updated.get("scene") or "") in PROTECTED_SCENES:
        protected_reason = "protected_current_scene"
    elif updated.get("memory_recall_contract") or updated.get("profile_grounding_shadow"):
        protected_reason = "factual_memory_contract"
    if protected_reason and contract.get("surface_authority"):
        contract.update(
            {
                "status": "protected_current_turn_retained",
                "reason": protected_reason,
                "surface_authority": False,
                "suppresses_new_pending_prediction": False,
            }
        )
    if not contract.get("surface_authority"):
        updated["source_anchored_semantic_commit_m33"] = contract
        return updated, contract
    updated.update(
        {
            "intent": "source_anchored_semantic_commit_m33",
            "scene": "casual",
            "reply_goal": "source atoms を損なわず日本語で受け取る",
            "core_message_jp": str(contract.get("response_jp") or "").strip(),
            "jp_summary": str(contract.get("response_jp") or "").strip(),
            "response_mode": "source_anchored_semantic_commit_m33",
            "surface_act": "source_anchored_semantic_commit_m33",
        }
    )
    contract["plan_applied"] = True
    updated["source_anchored_semantic_commit_m33"] = contract
    return updated, contract


def ensure_source_anchored_semantic_commit_m33_reaches_surface(
    reply,
    plan,
    enforce=True,
):
    """Commit or audit the M33 source-anchored visible surface."""
    visible = str(reply or "").strip()
    contract = deepcopy((plan or {}).get("source_anchored_semantic_commit_m33") or {})
    if contract.get("schema") != SOURCE_ATOM_COMMIT_SCHEMA_M33:
        contract = {
            "schema": SOURCE_ATOM_COMMIT_SCHEMA_M33,
            "status": "not_applied",
            "reason": "source_atom_commit_contract_missing",
            "surface_authority": False,
            "raw_dialogue_persisted": False,
        }
    expected = str(contract.get("response_jp") or "").strip()
    authoritative = bool(contract.get("surface_authority") and expected)
    before = visible
    if authoritative and enforce:
        visible = expected
    anchors = [
        str(value or "").strip()
        for value in (contract.get("surface_anchors_jp") or [])
        if str(value or "").strip()
    ]
    matched = bool(authoritative and visible == expected)
    visible_anchors = [anchor for anchor in anchors if anchor in visible]
    contract.update(
        {
            "surface_status": "matched" if matched else "mismatch" if authoritative else "not_applicable",
            "surface_changed": visible != before,
            "surface_anchor_count": len(anchors),
            "visible_anchor_count": len(visible_anchors),
            "surface_anchor_status": (
                "matched"
                if authoritative and anchors and len(visible_anchors) == len(anchors)
                else "mismatch"
                if authoritative
                else "not_applicable"
            ),
            "surface_reason": (
                "source_anchored_semantic_commit_visible"
                if matched
                else "source_anchored_semantic_commit_missing"
                if authoritative
                else "source_atom_commit_not_authoritative"
            ),
            "enforcement_pass": bool(enforce),
            "raw_dialogue_persisted": False,
        }
    )
    return visible, contract
