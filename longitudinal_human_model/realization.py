"""Behavior-authoritative natural-language realization contracts for M10.

This module is person-independent.  It compiles a frozen behavior decision into
a downstream language packet and never estimates a behavior itself.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from .metrics import normalize_distribution


DIRECT = "L0_DIRECT"
PREDICTED = "L1_PREDICTED_BEHAVIOR"
ORACLE = "L2_ORACLE_BEHAVIOR"
CONDITIONS = (DIRECT, PREDICTED, ORACLE)

BEHAVIOR_JP = {
    "accept_support_and_continue": "支援を受け入れ、感謝を示して作業を続ける",
    "acknowledge_then_continue": "状況を短く認め、そのまま作業を続ける",
    "ask_clarification": "曖昧な点を一つ確認する",
    "defer_commitment": "今は確約せず、確認後に判断すると伝える",
    "direct_rejection": "要求を直接、短く断る",
    "pause_and_reassess": "一度止め、見直してから再開すると伝える",
}

SYSTEM_INSTRUCTION = (
    "あなたは計算済みの行動決定を自然な発話に変換する下流層。"
    "行動権限がある場合、その行動を変更、再判断、弱めてはいけない。"
    "返答は自然で短い日本語一文だけ。JSON、分析、ラベル、引用符、敬語、英語、中国語は禁止。"
    "公開情報に基づく開発用の表現仮説として、くだけた直接的な口調を使うが、理由なく攻撃的にしない。"
    "一ノ瀬うるは本人を名乗らず、私生活、未公開の経験、内心を作らない。"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def extract_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    candidates = [raw]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.I | re.S)
    if fenced:
        candidates.append(fenced.group(1))
    first, last = raw.find("{"), raw.rfind("}")
    if first >= 0 and last > first:
        candidates.append(raw[first : last + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("model output was not a JSON object")


def normalize_reply(text: str) -> str:
    reply = str(text or "").strip()
    wrappers = (("\"", "\""), ("'", "'"), ("「", "」"), ("『", "』"), ("“", "”"))
    changed = True
    while changed and len(reply) >= 2:
        changed = False
        for left, right in wrappers:
            if reply.startswith(left) and reply.endswith(right):
                reply = reply[len(left) : -len(right)].strip()
                changed = True
                break
    return re.sub(r"[ \t]+", " ", reply).strip()


def validate_behavior_labels(labels: list[str]) -> None:
    if set(labels) != set(BEHAVIOR_JP):
        raise ValueError("M10 behavior taxonomy differs from the frozen six-label contract")


def behavior_authority(
    condition: str,
    prediction: Mapping[str, Any],
    actual_behavior: str,
    labels: list[str],
) -> dict[str, Any]:
    validate_behavior_labels(labels)
    if condition == DIRECT:
        return {
            "available": False,
            "selected_behavior": None,
            "probabilities": None,
            "source": "none_direct_generation_baseline",
            "future_information_used": False,
        }
    if condition == PREDICTED:
        probabilities = normalize_distribution(dict(prediction["probabilities"]), labels)
        selected = str(prediction["selected_behavior"])
        if selected != max(labels, key=lambda label: (probabilities[label], -labels.index(label))):
            raise ValueError("selected behavior is inconsistent with the frozen probability maximum")
        return {
            "available": True,
            "selected_behavior": selected,
            "selected_behavior_jp": BEHAVIOR_JP[selected],
            "probabilities": probabilities,
            "source": "frozen_m9_1_mira_full_adaptation",
            "future_information_used": False,
        }
    if condition == ORACLE:
        if actual_behavior not in labels:
            raise ValueError(f"unknown oracle behavior: {actual_behavior}")
        return {
            "available": True,
            "selected_behavior": actual_behavior,
            "selected_behavior_jp": BEHAVIOR_JP[actual_behavior],
            "probabilities": {label: float(label == actual_behavior) for label in labels},
            "source": "future_leaking_oracle_diagnostic_only",
            "future_information_used": True,
        }
    raise ValueError(f"unknown language condition: {condition}")


def build_realization_packet(
    *,
    condition: str,
    event: Mapping[str, Any],
    prediction: Mapping[str, Any],
    labels: list[str],
    persona_evidence_refs: list[str],
) -> dict[str, Any]:
    authority = behavior_authority(
        condition,
        prediction,
        str(event["actual_observed_behavior"]),
        labels,
    )
    return {
        "schema": "ilhdt_behavior_authoritative_realization_packet_v1",
        "condition": condition,
        "task": "次の状況で対象が発する自然な日本語一文を書く",
        "event_context": str(event["observable_text"]),
        "previous_state": dict(prediction.get("previous_state") or event.get("previous_state") or {}),
        "transitioned_state": dict(prediction.get("features") or {}),
        "behavior_authority": authority,
        "behavior_rule": (
            "行動権限なし。現在の状況から直接返す。"
            if not authority["available"]
            else "selected_behavior を必ず発話行為として実現し、別の行動に変更しない。"
        ),
        "style_evidence": {
            "status": "public_evidence_development_hypothesis_only",
            "evidence_refs": list(persona_evidence_refs),
            "operators": [
                "自然で短いくだけた日本語",
                "直接的だが理由なく攻撃的にしない",
                "低信頼の関係では過度に親密にしない",
                "口癖を強制しない",
            ],
            "must_not_override": ["behavior_authority", "safety", "factual_boundary"],
        },
        "output_contract": {
            "one_utterance_only": True,
            "natural_japanese_only": True,
            "maximum_characters": 96,
            "no_labels_or_analysis": True,
            "no_private_person_facts": True,
            "no_real_person_identity_claim": True,
        },
    }


def render_realization_prompt(packet: Mapping[str, Any]) -> str:
    return (
        SYSTEM_INSTRUCTION
        + "\n以下の入力契約に従う。\n"
        + json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n発話:"
    )


def build_classifier_prompt(event_text: str, utterance: str, labels: list[str]) -> str:
    validate_behavior_labels(labels)
    payload = {
        "task": "Classify only the observable dialogue act expressed by the Japanese utterance.",
        "event_context": str(event_text),
        "utterance": str(utterance),
        "labels": {label: BEHAVIOR_JP[label] for label in labels},
        "output_contract": {
            "probabilities": {label: "number from 0 to 1" for label in labels},
            "brief_evidence": "one short sentence",
        },
        "constraints": [
            "Return JSON only.",
            "Use every label exactly once.",
            "Probabilities must sum to 1.",
            "Classify the utterance, not the likely hidden intention or the event outcome.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_classifier_reply(text: str, labels: list[str]) -> dict[str, Any]:
    parsed = extract_json_object(text)
    probabilities = parsed.get("probabilities")
    if not isinstance(probabilities, dict):
        raise ValueError("classifier output lacks probabilities")
    normalized = normalize_distribution(probabilities, labels)
    selected = max(labels, key=lambda label: (normalized[label], -labels.index(label)))
    return {
        "probabilities": normalized,
        "selected_behavior": selected,
        "brief_evidence": str(parsed.get("brief_evidence") or "")[:500],
    }


def padding_for_prompt_token_delta(delta: int) -> str:
    """Use the frozen Qwen/Ollama development tokenization approximation.

    A following scored call is the authority.  If the resulting three-way
    prompt range exceeds the preregistered gate, the case fails without retry.
    """
    magnitude = max(0, int(delta))
    return " 0" * (magnitude // 2) + ("。" if magnitude % 2 else "")


def insert_padding(prompt: str, padding: str) -> str:
    anchor = "\n発話:"
    if anchor not in prompt:
        raise ValueError("realization prompt anchor missing")
    return prompt.replace(anchor, f"\n意味なし長さ調整領域:{padding}{anchor}", 1)
