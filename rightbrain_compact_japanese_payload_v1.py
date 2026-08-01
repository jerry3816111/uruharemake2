#!/usr/bin/env python3
"""Verify the compact Japanese RightBrain payload without model generation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from transformers import AutoTokenizer

import uruha_persona_policy as persona_policy
import uruha_surface_payload_v2 as surface_payload
from persona_policy_local_model_pilot_v1 import EMPTY_MEMORY, PSYCHE
from uruha_brain_mac import (
    RIGHT_BRAIN_BASE_MODEL,
    RIGHT_BRAIN_STRUCTURED_PAYLOAD_MODE,
    RightBrain,
    StructuredSurfaceUnavailableError,
)


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_compact_japanese_payload_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_compact_japanese_payload_v1_preregistration.json"
DEFAULT_BASELINE = ROOT / "configs/rightbrain_compact_japanese_payload_v1_legacy_baseline.json"
DEFAULT_CASES = ROOT / "configs/persona_policy_local_model_pilot_v1_cases.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_compact_japanese_payload_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_compact_japanese_payload_v1_construction.md"
PASS_DECISION = "authorize_preregistered_base_only_serializer_experiment"
FAIL_DECISION = "repair_compact_serializer_before_model_generation"
ASCII_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def binding(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def load_local_tokenizer():
    return AutoTokenizer.from_pretrained(
        RIGHT_BRAIN_BASE_MODEL,
        trust_remote_code=True,
        local_files_only=True,
    )


def _logic(case):
    logic = copy.deepcopy(case["logic"])
    logic["public_persona_context"] = case["context"]
    return logic


def _protected(logic):
    return {
        key: copy.deepcopy(logic.get(key))
        for key in persona_policy.PROTECTED_PLAN_FIELDS
    }


def _rightbrain(provider_id, mode):
    rightbrain = RightBrain(
        load_model=False,
        persona_policy_provider=persona_policy.build_persona_policy_provider(provider_id),
    )
    rightbrain.structured_payload_mode = mode
    return rightbrain


def _prompt_tokens(tokenizer, rightbrain, payload):
    prompt = tokenizer.apply_chat_template(
        [
            {"role": "system", "content": rightbrain._model_surface_system_instruction()},
            {"role": "user", "content": payload},
        ],
        tokenize=False,
        add_generation_prompt=True,
    )
    return len(tokenizer(prompt, add_special_tokens=False)["input_ids"])


def _all_text_present(text, values):
    return all(str(value) in text for value in values if str(value))


def _all_codes_present(text, values):
    return all(
        surface_payload.CODE_LABELS[str(value)] in text
        for value in values
        if str(value)
    )


def _semantic_is_rendered(text, contract):
    plan = contract["leftbrain_plan"]
    values = [
        plan.get("meaning"),
        *(plan.get("content_units") or []),
        *(plan.get("grounding_terms") or []),
        *[
            marker
            for group in contract.get("required_marker_groups") or []
            for marker in group
        ],
    ]
    return _all_text_present(text, values)


def _persona_is_rendered(text, contract):
    persona = contract["context"]["persona_expression_brief"]
    policy = persona.get("expression_policy") or {}
    codes = [
        persona.get("state"),
        persona.get("relationship_distance"),
        *(persona.get("stable_traits") or []),
        persona.get("conditional_context"),
        policy.get("tone"),
        policy.get("energy"),
        policy.get("brevity"),
        policy.get("social_distance"),
        *(policy.get("operations") or []),
        *(policy.get("avoid") or []),
    ]
    guards_rendered = (
        "人格は計画・必須意味・記憶・行動・道具を変更不可" in text
        and "表現担当" in surface_payload.COMPACT_JAPANESE_SYSTEM_INSTRUCTION
    )
    return _all_codes_present(text, codes) and guards_rendered


def _memory_is_rendered(text, contract):
    memory = contract["context"]["audited_memory_brief"]
    codes = [
        memory.get("policy"),
        memory.get("speakability"),
        *(memory.get("forbidden") or []),
    ]
    literal_values = []
    for cue in memory.get("allowed_memory_cues") or []:
        codes.append(cue.get("kind"))
        literal_values.extend([cue.get("jp_anchor"), *(cue.get("terms") or [])])
    for cue in memory.get("background_style_cues") or []:
        codes.extend([cue.get("kind"), cue.get("style_influence")])
    if memory.get("reason"):
        literal_values.append(memory["reason"])
    return _all_codes_present(text, codes) and _all_text_present(text, literal_values)


def _unknown_code_check():
    payload = {
        "contract_version": "plan_surface_contract_v1",
        "task": "write_one_user_facing_japanese_reply",
        "contract_rule": surface_payload.EXPECTED_CONTRACT_RULE,
        "user_input": "短い返答を求められている。",
        "leftbrain_plan": {
            "scene": "casual",
            "intent": "unsupported_synthetic_intent",
            "surface_act": "",
            "dialogue_act": "navigation_announcement",
            "meaning": "開始を知らせる",
            "content_units": ["開始"],
            "style_operators": ["short"],
            "grounding_terms": ["開始"],
        },
        "context": {
            "memory_summary": "左脳が選択した作業記憶は発話計画に統合済み。",
            "audited_memory_brief": {
                "policy": "no_memory",
                "speakability": "no_memory",
                "allowed_memory_cues": [],
                "background_style_cues": [],
                "forbidden": [
                    "do_not_quote_raw_memory",
                    "do_not_reveal_source_text",
                    "do_not_invent_unprovided_profile",
                ],
            },
            "procedural_guidance": {},
            "persona_expression_brief": {
                "role": "surface_style_only",
                "state": "neutral_energy",
                "relationship_distance": "moderate",
                "stable_traits": ["neutral_casual"],
                "must_not_override": [
                    "leftbrain_plan",
                    "required_marker_groups",
                    "audited_memory_policy",
                ],
            },
            "mood": -12,
            "trust": 58,
            "max_chars": 48,
        },
        "required_marker_groups": [["開始"]],
        "forbidden_markers": [],
        "reply_requirements": [
            "one sentence or short chat reply",
            "natural casual Japanese",
            "no labels or JSON",
            "no Chinese or English",
        ],
    }
    direct_error = None
    try:
        surface_payload.serialize_compact_japanese_payload(payload)
    except surface_payload.CompactPayloadSerializationError as exc:
        direct_error = exc

    rightbrain = _rightbrain(
        persona_policy.TARGET_PROVIDER,
        surface_payload.COMPACT_JAPANESE_V2,
    )
    logic = {
        "scene": "casual",
        "intent": "unsupported_synthetic_intent",
        "jp_summary": "短い返答を求められている。",
        "core_message_jp": "開始を知らせる",
        "required_marker_groups": [["開始"]],
        "human_speech_plan": {
            "dialogue_act": "navigation_announcement",
            "content_units": ["開始"],
            "grounding_terms": ["開始"],
            "style_operators": ["short"],
        },
    }
    integration_error = None
    try:
        rightbrain._build_model_surface_payload(logic, PSYCHE, 48, memory_data={})
    except StructuredSurfaceUnavailableError as exc:
        integration_error = exc
    return {
        "direct_typed_error": isinstance(
            direct_error,
            surface_payload.CompactPayloadSerializationError,
        ),
        "direct_field": direct_error.field if direct_error else None,
        "integration_typed_error": isinstance(
            integration_error,
            StructuredSurfaceUnavailableError,
        ),
        "integration_reason": integration_error.reason if integration_error else None,
    }


def build_report(preregistration, baseline, case_bundle):
    tokenizer = load_local_tokenizer()
    expected = {
        (row["case_id"], row["provider_id"]): row
        for row in baseline["rows"]
    }
    rows = []
    for case in case_bundle["cases"]:
        for provider_id in case["condition_order"]:
            legacy_logic = _logic(case)
            legacy_before = _protected(legacy_logic)
            legacy = _rightbrain(provider_id, surface_payload.LEGACY_JSON_V1)
            legacy_text = legacy._build_model_surface_payload(
                legacy_logic,
                PSYCHE,
                int(case["logic"]["constraints"]["max_chars"]),
                memory_data=copy.deepcopy(EMPTY_MEMORY),
            )
            legacy_after = _protected(legacy_logic)
            legacy_contract = json.loads(legacy_text)

            compact_logic = _logic(case)
            compact_before = _protected(compact_logic)
            compact = _rightbrain(provider_id, surface_payload.COMPACT_JAPANESE_V2)
            compact_text = compact._build_model_surface_payload(
                compact_logic,
                PSYCHE,
                int(case["logic"]["constraints"]["max_chars"]),
                memory_data=copy.deepcopy(EMPTY_MEMORY),
            )
            compact_after = _protected(compact_logic)
            direct = surface_payload.serialize_compact_japanese_payload(legacy_contract)
            expected_row = expected[(case["case_id"], provider_id)]
            legacy_tokens = _prompt_tokens(tokenizer, legacy, legacy_text)
            compact_tokens = _prompt_tokens(tokenizer, compact, compact_text)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "provider_id": provider_id,
                    "legacy_payload_sha256": sha256_text(legacy_text),
                    "legacy_payload_hash_matches": (
                        sha256_text(legacy_text) == expected_row["payload_sha256"]
                    ),
                    "legacy_payload_character_count": len(legacy_text),
                    "legacy_payload_ascii_word_count": len(ASCII_WORD_RE.findall(legacy_text)),
                    "legacy_active_prompt_tokens": legacy_tokens,
                    "legacy_metrics_match": (
                        len(legacy_text) == expected_row["payload_chars"]
                        and len(ASCII_WORD_RE.findall(legacy_text))
                        == expected_row["payload_ascii_word_count"]
                        and legacy_tokens == expected_row["active_prompt_tokens"]
                    ),
                    "compact_payload_sha256": sha256_text(compact_text),
                    "compact_payload_character_count": len(compact_text),
                    "compact_payload_ascii_word_count": len(ASCII_WORD_RE.findall(compact_text)),
                    "compact_active_prompt_tokens": compact_tokens,
                    "active_prompt_token_reduction_fraction": round(
                        1.0 - compact_tokens / legacy_tokens,
                        6,
                    ),
                    "integration_matches_direct_serializer": compact_text == direct.text,
                    "semantic_contract_preserved": (
                        direct.audit["semantic_contract"]
                        == {
                            "meaning": legacy_contract["leftbrain_plan"]["meaning"],
                            "content_units": legacy_contract["leftbrain_plan"]["content_units"],
                            "grounding_terms": legacy_contract["leftbrain_plan"]["grounding_terms"],
                            "required_marker_groups": legacy_contract["required_marker_groups"],
                        }
                        and _semantic_is_rendered(compact_text, legacy_contract)
                    ),
                    "persona_policy_preserved": (
                        direct.audit["persona_policy"]
                        == legacy_contract["context"]["persona_expression_brief"]
                        and _persona_is_rendered(compact_text, legacy_contract)
                    ),
                    "memory_policy_preserved": (
                        direct.audit["memory_policy"]
                        == legacy_contract["context"]["audited_memory_brief"]
                        and _memory_is_rendered(compact_text, legacy_contract)
                    ),
                    "forbidden_surface_policy_preserved": (
                        direct.audit["forbidden_surface_policy"]
                        == legacy_contract["forbidden_markers"]
                        and _all_text_present(
                            compact_text,
                            legacy_contract["forbidden_markers"],
                        )
                    ),
                    "protected_cognitive_fields_unchanged": (
                        legacy_before == legacy_after
                        and compact_before == compact_after
                    ),
                    "contains_fixed_reply": bool(
                        (compact_logic.get("persona_policy_provider_trace") or {}).get(
                            "contains_fixed_reply"
                        )
                    ),
                    "contains_target_utterance": bool(
                        (compact_logic.get("persona_policy_provider_trace") or {}).get(
                            "contains_target_utterance"
                        )
                    ),
                }
            )

    legacy_system = _rightbrain(
        persona_policy.TARGET_PROVIDER,
        surface_payload.LEGACY_JSON_V1,
    )._model_surface_system_instruction()
    compact_system = _rightbrain(
        persona_policy.TARGET_PROVIDER,
        surface_payload.COMPACT_JAPANESE_V2,
    )._model_surface_system_instruction()
    unknown = _unknown_code_check()
    counts = {
        "legacy_payload_case_count": len(rows),
        "legacy_payload_hash_mismatch_count": sum(
            not row["legacy_payload_hash_matches"] for row in rows
        ),
        "legacy_payload_metric_mismatch_count": sum(
            not row["legacy_metrics_match"] for row in rows
        ),
        "legacy_system_instruction_hash_mismatch_count": int(
            sha256_text(legacy_system) != baseline["system_instruction_sha256"]
        ),
        "compact_payload_case_count": len(rows),
        "compact_payload_ascii_word_count_maximum": max(
            row["compact_payload_ascii_word_count"] for row in rows
        ),
        "compact_system_instruction_ascii_word_count": len(
            ASCII_WORD_RE.findall(compact_system)
        ),
        "minimum_active_prompt_token_reduction_fraction": min(
            row["active_prompt_token_reduction_fraction"] for row in rows
        ),
        "semantic_contract_preserved_case_count": sum(
            row["semantic_contract_preserved"] for row in rows
        ),
        "persona_policy_preserved_case_count": sum(
            row["persona_policy_preserved"] for row in rows
        ),
        "memory_policy_preserved_case_count": sum(
            row["memory_policy_preserved"] for row in rows
        ),
        "forbidden_surface_policy_preserved_case_count": sum(
            row["forbidden_surface_policy_preserved"] for row in rows
        ),
        "protected_cognitive_field_mutation_count": sum(
            not row["protected_cognitive_fields_unchanged"] for row in rows
        ),
        "contains_fixed_reply_count": sum(row["contains_fixed_reply"] for row in rows),
        "contains_target_utterance_count": sum(
            row["contains_target_utterance"] for row in rows
        ),
        "legacy_default_runtime_behavior_change_count": int(
            RIGHT_BRAIN_STRUCTURED_PAYLOAD_MODE != surface_payload.LEGACY_JSON_V1
        ),
        "actual_model_weight_load_count": 0,
        "actual_model_generation_count": 0,
    }
    required = preregistration["construction_success_requires"]
    checks = {
        "legacy_payloads_locked": (
            counts["legacy_payload_case_count"]
            == required["legacy_payload_case_count_exact"]
            and counts["legacy_payload_hash_mismatch_count"]
            == required["legacy_payload_hash_mismatch_count_exact"]
            and counts["legacy_payload_metric_mismatch_count"] == 0
        ),
        "legacy_system_instruction_locked": (
            counts["legacy_system_instruction_hash_mismatch_count"]
            == required["legacy_system_instruction_hash_mismatch_count_exact"]
        ),
        "compact_payload_count": (
            counts["compact_payload_case_count"]
            == required["compact_payload_case_count_exact"]
        ),
        "compact_payload_has_no_ascii_words": (
            counts["compact_payload_ascii_word_count_maximum"]
            <= required["compact_payload_ascii_word_count_maximum"]
            and counts["compact_system_instruction_ascii_word_count"] == 0
        ),
        "compact_prompt_reduction": (
            counts["minimum_active_prompt_token_reduction_fraction"]
            >= required["compact_active_prompt_token_reduction_minimum_fraction"]
        ),
        "semantic_contract_preserved": (
            counts["semantic_contract_preserved_case_count"]
            == required["semantic_contract_preserved_case_count_exact"]
        ),
        "persona_policy_preserved": (
            counts["persona_policy_preserved_case_count"]
            == required["persona_policy_preserved_case_count_exact"]
        ),
        "memory_policy_preserved": (
            counts["memory_policy_preserved_case_count"]
            == required["memory_policy_preserved_case_count_exact"]
        ),
        "forbidden_surface_policy_preserved": (
            counts["forbidden_surface_policy_preserved_case_count"]
            == required["forbidden_surface_policy_preserved_case_count_exact"]
        ),
        "protected_cognitive_fields_unchanged": (
            counts["protected_cognitive_field_mutation_count"]
            == required["protected_cognitive_field_mutation_count_exact"]
        ),
        "no_fixed_reply_or_target_utterance": (
            counts["contains_fixed_reply_count"]
            == required["contains_fixed_reply_count_exact"]
            and counts["contains_target_utterance_count"]
            == required["contains_target_utterance_count_exact"]
        ),
        "unsupported_control_code_fails_closed": (
            unknown["direct_typed_error"]
            and unknown["direct_field"] == "plan.intent"
            and unknown["integration_typed_error"]
            and str(unknown["integration_reason"]).startswith(
                "compact_payload_serialization_failed:plan.intent:"
            )
        )
        is required["unsupported_control_code_fails_closed"],
        "legacy_default_unchanged": (
            counts["legacy_default_runtime_behavior_change_count"]
            == required["legacy_default_runtime_behavior_change_count_exact"]
        ),
        "no_model_generation": (
            counts["actual_model_generation_count"]
            == required["actual_model_generation_count_exact"]
            and counts["actual_model_weight_load_count"] == 0
        ),
        "integration_matches_direct_serializer": all(
            row["integration_matches_direct_serializer"] for row in rows
        ),
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_rightbrain_compact_japanese_payload_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "construction_passed" if passed else "construction_failed",
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "legacy_baseline": binding(DEFAULT_BASELINE),
            "cases": binding(DEFAULT_CASES),
            "serializer_source": binding(ROOT / "uruha_surface_payload_v2.py"),
            "brain_source": binding(ROOT / "uruha_brain_mac.py"),
            "tokenizer": RIGHT_BRAIN_BASE_MODEL,
            "tokenizer_local_files_only": True,
        },
        "counts": counts,
        "checks": checks,
        "unsupported_code_check": unknown,
        "rows": rows,
        "authorizations": {
            "preregistered_base_only_serializer_experiment": passed,
            "production_default_enablement": False,
            "persona_similarity_claim": False,
            "human_blind_rating": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
        },
        "evidence_boundary": (
            "This construction check proves serialization integrity and prompt-size reduction only; "
            "it contains no model generation and cannot establish response quality or persona similarity."
        ),
    }


def render_markdown(report):
    counts = report["counts"]
    return "\n".join(
        [
            "# 右腦精簡日文載荷 V1 建構驗證",
            "",
            f"**{report['status']}**",
            "",
            "| 指標 | 結果 |",
            "|---|---:|",
            f"| 舊格式雜湊不一致 | {counts['legacy_payload_hash_mismatch_count']}/10 |",
            f"| 新格式英文字詞上限 | {counts['compact_payload_ascii_word_count_maximum']} |",
            f"| 最小 prompt token 降幅 | {counts['minimum_active_prompt_token_reduction_fraction']:.1%} |",
            f"| 語意契約完整 | {counts['semantic_contract_preserved_case_count']}/10 |",
            f"| 人格策略完整 | {counts['persona_policy_preserved_case_count']}/10 |",
            f"| 記憶策略完整 | {counts['memory_policy_preserved_case_count']}/10 |",
            f"| 認知欄位變更 | {counts['protected_cognitive_field_mutation_count']} |",
            f"| 實際模型生成 | {counts['actual_model_generation_count']} |",
            "",
            f"決策：`{report['decision']}`",
            "",
            "本結果只授權預註冊的 base-only 舊格式對新格式實際生成實驗，不授權上線或人格相似度主張。",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    args = parser.parse_args()
    preregistration = load_json(args.preregistration)
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit("wrong preregistration experiment_id")
    report = build_report(
        preregistration,
        load_json(args.baseline),
        load_json(args.cases),
    )
    Path(args.report_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.report_md).write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "decision": report["decision"],
                "counts": report["counts"],
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report["status"] == "construction_passed" else 1)


if __name__ == "__main__":
    main()
