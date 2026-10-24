"""Behavior-preserving casual-register repair contract for M10.2."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .realization import BEHAVIOR_JP


ONE_PASS = "S0_ONE_PASS"
REGISTER_REPAIR = "S1_REGISTER_REPAIR"
CONDITIONS = (ONE_PASS, REGISTER_REPAIR)

REGISTER_REPAIR_SYSTEM = (
    "あなたは発話内容を決める層ではなく、くだけた日本語の表面だけを直す層。"
    "元の発話が表す行動、肯否、質問か断定か、事実、相手との距離、安全境界を変えてはいけない。"
    "です・ます・ください・ましょう等の敬体を使わず、自然な短い会話にする。"
    "行動ラベルの説明文を読むのではなく、その場で相手に直接話す一文にする。"
    "JSON、ラベル、分析、引用符、英語、中国語、本人宣言、私生活の創作は禁止。返事だけを書く。"
)


def build_register_repair_packet(
    *,
    event_context: str,
    relationship_context: str,
    authoritative_behavior: str,
    original_utterance: str,
    persona_evidence_refs: list[str],
) -> dict[str, Any]:
    if authoritative_behavior not in BEHAVIOR_JP:
        raise ValueError(f"unknown behavior: {authoritative_behavior}")
    return {
        "schema": "ilhdt_behavior_preserving_register_repair_packet_v1",
        "event_context": str(event_context),
        "relationship_context": str(relationship_context),
        "authoritative_behavior": authoritative_behavior,
        "authoritative_behavior_jp": BEHAVIOR_JP[authoritative_behavior],
        "original_utterance": str(original_utterance),
        "allowed_change": "casual Japanese register and surface naturalness only",
        "must_preserve": [
            "authoritative_behavior",
            "affirmation_or_rejection_polarity",
            "question_or_statement_dialogue_act",
            "observable_facts",
            "relationship_distance",
            "safety_boundary",
        ],
        "style_evidence": {
            "status": "public_evidence_development_hypothesis_only",
            "evidence_refs": list(persona_evidence_refs),
            "operators": [
                "casual direct Japanese",
                "not automatically hostile",
                "no forced catchphrase",
            ],
        },
        "output_contract": {
            "one_utterance_only": True,
            "natural_japanese_only": True,
            "maximum_characters": 96,
            "no_polite_register": True,
            "no_labels_or_analysis": True,
        },
    }


def render_register_repair_prompt(packet: Mapping[str, Any]) -> str:
    return (
        REGISTER_REPAIR_SYSTEM
        + "\n次の契約に従って表面だけを直す。\n"
        + json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n修正文:"
    )
