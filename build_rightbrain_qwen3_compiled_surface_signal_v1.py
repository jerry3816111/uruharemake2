#!/usr/bin/env python3
"""Freeze a source-disjoint compiled surface-signal experiment."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import build_rightbrain_qwen3_4b_trainability_v1 as model_parent
import build_rightbrain_qwen3_active_head_multibatch_v1 as data_parent
import build_rightbrain_qwen3_provider_signal_position_v1 as position_parent


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_qwen3_compiled_surface_signal_v1"
CONDITIONS = ("abstract_top_level_control", "compiled_surface_signal")
REPEATS = (1, 2, 3)
CONDITION_ORDERS = {
    1: CONDITIONS,
    2: tuple(reversed(CONDITIONS)),
    3: CONDITIONS,
}
PRIMARY_ROW_INDICES = (0, 2, 4, 6, 8, 10, 12, 14)
REFERENCE_ALT_ROW_INDICES = (1, 3, 5, 7, 9, 11, 13, 15)
MAX_GENERATION_TOKENS = 80
SYSTEM_MESSAGE = (
    "You are the RightBrain surface formulator for UruhaBrain. Your job is "
    "semantic realization, not roleplay improvisation. Return exactly one short, "
    "natural casual Japanese chat reply. For every required_marker_group in the "
    "input contract, include at least one marker from that group naturally in the "
    "reply. Do not include any forbidden_marker. Keep the concrete topic and "
    "grounding terms. Use audited_memory_brief only as a surface cue; never infer "
    "from hidden memory or reveal memory that is not explicitly allowed. Do not "
    "output analysis, labels, JSON, metadata, English, Chinese, or system text. "
    "Do not explain the contract."
)
TARGET_PROVIDER = "structured_target_public_persona"
NEUTRAL_PROVIDER = "structured_neutral_dialogue"
PROVIDERS = (TARGET_PROVIDER, NEUTRAL_PROVIDER)

DEFAULT_DATASET = ROOT / "datasets/rightbrain_compiled_surface_signal_holdout_v1.json"
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/rightbrain_qwen3_compiled_surface_signal_v1_preregistration.json"
)
DEFAULT_EXECUTION_LOCK = (
    ROOT / "configs/rightbrain_qwen3_compiled_surface_signal_v1_execution_lock.json"
)
DEFAULT_CONSTRUCTION_JSON = (
    ROOT / "reports/rightbrain_qwen3_compiled_surface_signal_v1_construction.json"
)
DEFAULT_CONSTRUCTION_MD = (
    ROOT / "reports/rightbrain_qwen3_compiled_surface_signal_v1_construction.md"
)
RUNNER_PATH = ROOT / "run_rightbrain_qwen3_compiled_surface_signal_v1.py"
TEST_PATH = ROOT / "test_rightbrain_qwen3_compiled_surface_signal_v1.py"
VERIFIER_PATH = ROOT / "verify_rightbrain_qwen3_compiled_surface_signal_v1_result.py"
MODEL_PREREGISTRATION = model_parent.DEFAULT_PREREGISTRATION
PRIOR_DATASET = data_parent.DATASET_PATH
PARENT_RESULT = ROOT / "reports/rightbrain_qwen3_provider_signal_position_v1_result.json"
PARENT_RESULT_LOCK = (
    ROOT / "configs/rightbrain_qwen3_provider_signal_position_v1_result_lock.json"
)
PARENT_DIAGNOSIS = ROOT / "reports/rightbrain_qwen3_provider_signal_position_v1_diagnosis.md"

load_json = model_parent.load_json
sha256_file = model_parent.sha256_file
atomic_json = model_parent.atomic_json
atomic_text = model_parent.atomic_text
file_binding = model_parent.file_binding

SIGNAL_FORBIDDEN_CASE_TERMS = (
    "来て",
    "見に来て",
    "遅れ",
    "終わ",
    "連絡",
    "知らせ",
    "麺",
    "食べ",
    "作業",
    "九時",
    "約束",
)


def canonical_json_sha256(value):
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _persona_brief(provider_id):
    common = {
        "role": "surface_style_only",
        "conditional_context": "casual_public_reply",
        "relationship_distance": "moderate",
        "state": "neutral_energy",
        "must_not_override": [
            "leftbrain_plan",
            "required_marker_groups",
            "audited_memory_policy",
            "tool_calls",
        ],
        "protected_fields": [
            "required_marker_groups",
            "forbidden_markers",
            "audited_memory_brief",
            "leftbrain_plan.content_units",
            "leftbrain_plan.grounding_terms",
            "tool_calls",
        ],
    }
    if provider_id == TARGET_PROVIDER:
        return {
            **common,
            "stable_traits": [
                "lazy_short",
                "slightly_bratty",
                "not_customer_service",
            ],
            "expression_policy": {
                "brevity": "short",
                "energy": "context_matched",
                "tone": "slightly_blunt_friendly",
                "social_distance": "in_group_audience",
                "operations": [
                    "prefer_direct_opening",
                    "allow_one_light_tease_only_if_meaning_already_supports_it",
                ],
                "avoid": [
                    "polished_customer_service_register",
                    "added_facts",
                    "repeated_catchphrase",
                ],
            },
        }
    if provider_id == NEUTRAL_PROVIDER:
        return {
            **common,
            "stable_traits": [
                "neutral_casual",
                "moderate_directness",
                "not_customer_service",
            ],
            "expression_policy": {
                "brevity": "short",
                "energy": "context_matched",
                "tone": "neutral_casual",
                "social_distance": "moderate",
                "operations": [
                    "neutral_surface_operation_1",
                    "neutral_surface_operation_2",
                ],
                "avoid": [
                    "strong_teasing",
                    "added_facts",
                    "formal_customer_service_register",
                ],
            },
        }
    raise ValueError(f"Unknown provider: {provider_id}")


def compile_surface_signal(persona):
    """Compile abstract provider state into generic executable surface actions."""
    provider_signature = tuple(persona["stable_traits"])
    common = {
        "scope": "surface_realization_only",
        "priority": (
            "意味、必須語、記憶の発話可否、禁止語、tool_callsを先に守り、"
            "文体は最後にだけ変える。"
        ),
        "sentence_shape": "一文、最大二節の短い返答にする。",
        "register": "自然な日本語の普通体を使い、です・ます調にしない。",
        "never_change": [
            "required_marker_groupsの意味",
            "forbidden_markers",
            "audited_memory_briefの発話可否",
            "leftbrain_planの内容",
            "tool_calls",
        ],
        "hard_limit": "新しい事実、理由、行動方針、感情、記憶を足さない。",
    }
    if provider_signature == (
        "lazy_short",
        "slightly_bratty",
        "not_customer_service",
    ):
        return {
            **common,
            "delivery": (
                "結論から直接言う。少しぶっきらぼうでも親しみは残し、"
                "意味に既に含まれる場合だけ軽いツッコミを一度まで使う。"
            ),
            "ending": "終助詞を増やしすぎず、短く言い切る。",
        }
    if provider_signature == (
        "neutral_casual",
        "moderate_directness",
        "not_customer_service",
    ):
        return {
            **common,
            "delivery": (
                "穏やかで標準的なカジュアル表現にする。親しみは示すが、"
                "強いツッコミや挑発を足さない。"
            ),
            "ending": "必要なら短い終助詞を一つ使い、柔らかく閉じる。",
        }
    raise ValueError(f"Unsupported persona signature: {provider_signature}")


def _memory(mode):
    common = {
        "reason": f"compiled_surface_signal_holdout_{mode}",
        "speakability": mode,
        "policy": mode,
        "allowed_memory_cues": [],
        "background_style_cues": [],
        "forbidden": [
            "do_not_quote_raw_memory",
            "do_not_reveal_source_text",
            "do_not_invent_unprovided_profile",
        ],
    }
    if mode == "background_only":
        common["background_style_cues"] = [
            {"kind": "audience_distance", "style_influence": "soft_context_only"}
        ]
    elif mode == "do_not_mention":
        common["forbidden"].extend(["寝坊", "アラーム", "二度寝"])
    elif mode == "explicit_allowed":
        common["allowed_memory_cues"] = [
            {
                "kind": "shared_commitment",
                "jp_anchor": "九時に連絡する約束",
                "terms": ["九時に", "約束どおり"],
            }
        ]
    elif mode != "no_memory":
        raise ValueError(f"Unknown memory mode: {mode}")
    return common


SCENARIOS = (
    {
        "source_id": "compiled_signal_closing_thanks_invitation_01",
        "memory_mode": "background_only",
        "user_input": "配信の終わりに、初めて来た視聴者へ短く礼を言い、また気軽に来てと伝える。",
        "content_units": ["来てくれたことに礼を言う", "また気軽に来られると伝える"],
        "grounding_terms": ["来て", "また", "気軽"],
        "meaning": "来てくれたことへの感謝と、また気軽に来てほしいという招待",
        "required_marker_groups": [
            ["来て", "見に来て"],
            ["ありがと", "ありがとう"],
            ["また"],
            ["気軽", "ふらっと"],
        ],
        "forbidden_markers": ["AI", "技術説明", "です", "ます", "初見対応は緊張する"],
        "references": {
            TARGET_PROVIDER: (
                "来てくれてありがと、また気軽にふらっと来てな。",
                "見に来てくれてありがと。また気軽に来て。",
            ),
            NEUTRAL_PROVIDER: (
                "来てくれてありがとう、また気軽に見に来てね。",
                "見に来てくれてありがとう。また気軽に来てね。",
            ),
        },
    },
    {
        "source_id": "compiled_signal_schedule_delay_notice_01",
        "memory_mode": "do_not_mention",
        "user_input": "予定が少し遅れることと、終わり次第すぐ連絡することだけを短く伝える。",
        "content_units": ["予定が少し遅れると伝える", "終わり次第すぐ連絡すると伝える"],
        "grounding_terms": ["遅れる", "終わったら", "連絡"],
        "meaning": "予定の遅れと、終了後すぐ知らせるという連絡",
        "required_marker_groups": [
            ["遅れ", "予定"],
            ["終わ", "済ん"],
            ["連絡", "知らせ"],
        ],
        "forbidden_markers": ["AI", "技術説明", "です", "ます", "寝坊", "アラーム", "二度寝"],
        "references": {
            TARGET_PROVIDER: (
                "ちょい遅れる、終わったらすぐ知らせるわ。",
                "少し遅れるけど、済んだらすぐ連絡する。",
            ),
            NEUTRAL_PROVIDER: (
                "少し遅れるよ。終わったらすぐ連絡するね。",
                "予定が少し遅れる。終わったらすぐ知らせるね。",
            ),
        },
    },
    {
        "source_id": "compiled_signal_noodle_meal_invitation_01",
        "memory_mode": "no_memory",
        "user_input": "今日は麺にすると決めたことを伝え、相手も一緒に食べるか短く誘う。",
        "content_units": ["今日は麺にすると伝える", "一緒に食べるか誘う"],
        "grounding_terms": ["麺", "一緒", "食べる"],
        "meaning": "麺を選んだことと、一緒に食べようという誘い",
        "required_marker_groups": [["麺"], ["一緒"], ["食べ", "どう", "来る"]],
        "forbidden_markers": ["AI", "技術説明", "です", "ます"],
        "references": {
            TARGET_PROVIDER: (
                "今日は麺にする。一緒に食べるなら来る？",
                "麺に決めた、一緒に食べる？",
            ),
            NEUTRAL_PROVIDER: (
                "今日は麺にするよ。一緒に食べない？",
                "麺に決めたよ。一緒にどう？",
            ),
        },
    },
    {
        "source_id": "compiled_signal_nine_pm_progress_commitment_01",
        "memory_mode": "explicit_allowed",
        "user_input": "共有済みの九時の約束を使い、作業の進み具合を九時に連絡すると短く伝える。",
        "content_units": ["作業の進み具合について伝える", "九時に連絡すると伝える"],
        "grounding_terms": ["作業", "九時", "連絡"],
        "meaning": "共有済みの約束どおり、作業の進捗を九時に知らせる",
        "required_marker_groups": [["作業"], ["九時"], ["連絡", "知らせ"]],
        "forbidden_markers": ["AI", "技術説明", "です", "ます", "非公開メモ"],
        "references": {
            TARGET_PROVIDER: (
                "作業の進み、約束どおり九時に連絡するわ。",
                "作業どうなったか、九時にちゃんと知らせる。",
            ),
            NEUTRAL_PROVIDER: (
                "作業の進み具合は、約束どおり九時に連絡するね。",
                "作業の状況は、九時にちゃんと知らせるね。",
            ),
        },
    },
)


def _payload(scenario, provider_id):
    return {
        "context": {
            "audited_memory_brief": _memory(scenario["memory_mode"]),
            "max_chars": 62,
            "memory_summary": "左脳が選択した作業記憶は発話計画に統合済み。",
            "mood": -8,
            "persona_expression_brief": _persona_brief(provider_id),
            "procedural_guidance": {
                "priority": "semantic_then_memory_then_style",
                "source": "generic_leftbrain_procedure",
                "steps": [
                    "preserve_every_required_semantic_group",
                    "obey_memory_speakability",
                    "apply_surface_style_last",
                ],
            },
            "trust": 58,
        },
        "contract_rule": (
            "required_marker_groups is the semantic contract. Include at least one "
            "phrase from every inner list naturally and avoid every forbidden marker."
        ),
        "contract_version": "plan_surface_contract_v1",
        "forbidden_markers": scenario["forbidden_markers"],
        "leftbrain_plan": {
            "content_units": scenario["content_units"],
            "dialogue_act": "short_casual_reply",
            "grounding_terms": scenario["grounding_terms"],
            "intent": "short_casual_reply",
            "meaning": scenario["meaning"],
            "scene": "public_conversation",
            "style_operators": ["short", "casual"],
            "surface_act": "plain_reply",
        },
        "reply_requirements": [
            "one sentence or short chat reply",
            "natural casual Japanese",
            "no labels or JSON",
            "no Chinese or English",
        ],
        "required_marker_groups": scenario["required_marker_groups"],
        "task": "write_one_user_facing_japanese_reply",
        "user_input": scenario["user_input"],
    }


def build_dataset():
    rows = []
    row_number = 1
    for scenario in SCENARIOS:
        for provider_id in PROVIDERS:
            payload = _payload(scenario, provider_id)
            for variant_index, reference in enumerate(
                scenario["references"][provider_id], start=1
            ):
                rows.append(
                    {
                        "id": f"rb_compiled_surface_signal_v1_{row_number:04d}",
                        "source_id": scenario["source_id"],
                        "category": "compiled_surface_signal_source_disjoint_holdout",
                        "training_role": "evaluation_only_surface_realization",
                        "provider_id": provider_id,
                        "memory_mode": scenario["memory_mode"],
                        "variant_index": variant_index,
                        "provenance": {
                            "synthetic": True,
                            "source_independent": True,
                            "authoring_method": "codex_assisted_synthetic",
                            "contains_target_utterance": False,
                            "contains_benchmark_item": False,
                            "runtime_fixed_reply": False,
                            "training_authorized": False,
                        },
                        "messages": [
                            {"role": "system", "content": SYSTEM_MESSAGE},
                            {"role": "user", "content": _compact_json(payload)},
                            {"role": "assistant", "content": reference},
                        ],
                    }
                )
                row_number += 1
    return rows


def _extract_persona(payload):
    payload = copy.deepcopy(payload)
    persona = payload["context"].pop("persona_expression_brief")
    return payload, persona


def condition_messages(row, condition):
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    payload = json.loads(row["messages"][1]["content"])
    payload, persona = _extract_persona(payload)
    if condition == "abstract_top_level_control":
        payload = {"persona_expression_brief": persona, **payload}
    else:
        payload = {"compiled_surface_signal": compile_surface_signal(persona), **payload}
    return [
        copy.deepcopy(row["messages"][0]),
        {"role": "user", "content": _compact_json(payload)},
    ]


def _opposite_map(rows):
    grouped = {}
    for index in PRIMARY_ROW_INDICES:
        row = rows[index]
        grouped.setdefault(row["source_id"], {})[row["provider_id"]] = index
    result = {}
    for providers in grouped.values():
        target = providers[TARGET_PROVIDER]
        neutral = providers[NEUTRAL_PROVIDER]
        result[target] = neutral
        result[neutral] = target
    return result


def _references_by_row(rows):
    alt_by_primary = dict(
        zip(PRIMARY_ROW_INDICES, REFERENCE_ALT_ROW_INDICES, strict=True)
    )
    opposite = _opposite_map(rows)
    references = {}
    for index in PRIMARY_ROW_INDICES:
        opposite_index = opposite[index]
        references[rows[index]["id"]] = {
            "own": [
                rows[index]["messages"][-1]["content"],
                rows[alt_by_primary[index]]["messages"][-1]["content"],
            ],
            "opposite": [
                rows[opposite_index]["messages"][-1]["content"],
                rows[alt_by_primary[opposite_index]]["messages"][-1]["content"],
            ],
        }
    return references


def prompt_contract(rows):
    cases = []
    for index in PRIMARY_ROW_INDICES:
        row = rows[index]
        control = condition_messages(row, "abstract_top_level_control")
        candidate = condition_messages(row, "compiled_surface_signal")
        control_payload = json.loads(control[1]["content"])
        candidate_payload = json.loads(candidate[1]["content"])
        control_signal = control_payload.pop("persona_expression_brief")
        candidate_signal = candidate_payload.pop("compiled_surface_signal")
        if control_payload != candidate_payload:
            raise RuntimeError(f"Non-signal payload drift: {row['id']}")
        if candidate_signal != compile_surface_signal(control_signal):
            raise RuntimeError(f"Compiler drift: {row['id']}")
        if any(
            term in _compact_json(candidate_signal)
            for term in SIGNAL_FORBIDDEN_CASE_TERMS
        ):
            raise RuntimeError(f"Compiled signal leaked case content: {row['id']}")
        cases.append(
            {
                "row_index": index,
                "row_id": row["id"],
                "source_id": row["source_id"],
                "provider_id": row["provider_id"],
                "memory_mode": row["memory_mode"],
                "variant_index": row["variant_index"],
                "scoring_payload": json.loads(row["messages"][1]["content"]),
                "abstract_top_level_control_messages": control,
                "compiled_surface_signal_messages": candidate,
            }
        )
    return {
        "cases": cases,
        "case_count": len(cases),
        "abstract_top_level_control_prompt_sha256": canonical_json_sha256(
            [case["abstract_top_level_control_messages"] for case in cases]
        ),
        "compiled_surface_signal_prompt_sha256": canonical_json_sha256(
            [case["compiled_surface_signal_messages"] for case in cases]
        ),
        "all_content_outside_signal_equal": True,
        "candidate_is_deterministic_compilation_of_control": True,
        "both_signals_are_first_top_level_field": True,
        "assistant_references_in_prompt": False,
    }


def _validate_dataset(rows):
    if len(rows) != 16:
        raise RuntimeError("Unexpected compiled holdout row count")
    prior_rows = load_json(PRIOR_DATASET)
    sources = {row["source_id"] for row in rows}
    prior_sources = {row["source_id"] for row in prior_rows}
    answers = {row["messages"][-1]["content"].strip() for row in rows}
    prior_answers = {
        row["messages"][-1]["content"].strip() for row in prior_rows
    }
    if sources & prior_sources:
        raise RuntimeError("Compiled holdout source overlaps prior curriculum")
    if answers & prior_answers:
        raise RuntimeError("Compiled holdout reference overlaps prior curriculum")
    if len(sources) != 4 or len(answers) != 16:
        raise RuntimeError("Compiled holdout source/reference diversity failed")
    if not all(
        row["provenance"]["synthetic"] is True
        and row["provenance"]["source_independent"] is True
        and row["provenance"]["contains_target_utterance"] is False
        and row["provenance"]["contains_benchmark_item"] is False
        and row["provenance"]["training_authorized"] is False
        for row in rows
    ):
        raise RuntimeError("Compiled holdout violates provenance boundary")
    return {
        "source_ids": sorted(sources),
        "prior_source_overlap": 0,
        "prior_exact_answer_overlap": 0,
        "provider_counts": dict(sorted(Counter(row["provider_id"] for row in rows).items())),
        "memory_mode_counts": dict(sorted(Counter(row["memory_mode"] for row in rows).items())),
    }


def build():
    required = (
        MODEL_PREREGISTRATION,
        PRIOR_DATASET,
        PARENT_RESULT,
        PARENT_RESULT_LOCK,
        PARENT_DIAGNOSIS,
        RUNNER_PATH,
        TEST_PATH,
        VERIFIER_PATH,
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    base = load_json(MODEL_PREREGISTRATION)
    parent_result = load_json(PARENT_RESULT)
    parent_lock = load_json(PARENT_RESULT_LOCK)
    if parent_result["decision"]["outcome"] != "provider_signal_position_contract_regressed":
        raise RuntimeError("Unexpected provider-position parent outcome")
    if parent_result["decision"]["authorized_next_step"] != "diagnose_provider_signal_position_failure":
        raise RuntimeError("Provider-position parent does not authorize diagnosis")
    if any(parent_lock["authorization"].values()):
        raise RuntimeError("Provider-position parent grants persistent authorization")

    rows = build_dataset()
    dataset_contract = _validate_dataset(rows)
    atomic_json(DEFAULT_DATASET, rows)
    prompt = prompt_contract(rows)
    references = _references_by_row(rows)
    reference_hash = canonical_json_sha256(
        [references[row_id] for row_id in sorted(references)]
    )
    primary = [rows[index] for index in PRIMARY_ROW_INDICES]
    prereg = {
        "schema": "uruha_rightbrain_qwen3_compiled_surface_signal_preregistration_v1",
        "experiment_id": EXPERIMENT_ID,
        "research_question": (
            "Does deterministically compiling abstract provider labels into concrete, "
            "surface-only Japanese operations improve provider-conditioned generation "
            "on four new sources without changing semantic, memory, or tool contracts?"
        ),
        "conditions": {
            "abstract_top_level_control": "the current abstract persona object at the first top-level field",
            "compiled_surface_signal": "a deterministic generic compilation of that object at the first top-level field",
        },
        "causal_scope": {
            "only_changed_variable": "provider_signal_representation",
            "control_value": "abstract_structured_labels",
            "candidate_value": "concrete_surface_only_operations",
            "unchanged": [
                "signal_position_first_top_level",
                "system_message",
                "all_non_signal_payload_fields",
                "base_model_snapshot_and_weights",
                "greedy_decoding",
                "probe_rows_and_order",
                "references_and_scoring",
                "device_and_environment",
            ],
        },
        "evidence_parent": {
            "result": file_binding(PARENT_RESULT),
            "result_lock": file_binding(PARENT_RESULT_LOCK),
            "diagnosis": file_binding(PARENT_DIAGNOSIS),
            "outcome": parent_result["decision"]["outcome"],
            "observed_failure": {
                "provider_alignment_margin_delta": parent_result["measurements"]["candidate_minus_control"]["provider_alignment_margin_delta"],
                "joint_contract_pass_rate_delta": parent_result["measurements"]["candidate_minus_control"]["joint_contract_pass_rate_delta"],
            },
        },
        "local_environment": base["local_environment"],
        "local_model_contract": base["local_model_contract"],
        "external_model_bindings": base["external_model_bindings"],
        "dataset_contract": {
            "path": str(DEFAULT_DATASET.relative_to(ROOT)),
            "sha256": sha256_file(DEFAULT_DATASET),
            "row_count": len(rows),
            "primary_row_count": len(primary),
            "synthetic_source_independent": True,
            "contains_target_utterances": False,
            "contains_benchmark_items_or_answers": False,
            **dataset_contract,
        },
        "source_split_contract": {
            "primary_row_indices": list(PRIMARY_ROW_INDICES),
            "reference_alt_row_indices": list(REFERENCE_ALT_ROW_INDICES),
            "primary_provider_counts": dict(sorted(Counter(row["provider_id"] for row in primary).items())),
            "primary_memory_mode_counts": dict(sorted(Counter(row["memory_mode"] for row in primary).items())),
        },
        "compiler_contract": {
            "deterministic": True,
            "input_fields": ["stable_traits", "expression_policy"],
            "case_specific_content_allowed": False,
            "forbidden_case_terms": list(SIGNAL_FORBIDDEN_CASE_TERMS),
            "may_modify_only": [
                "sentence_shape",
                "register",
                "directness",
                "hedge_strength",
                "ending",
                "surface_energy",
            ],
            "must_preserve": [
                "required_marker_groups",
                "forbidden_markers",
                "audited_memory_brief",
                "leftbrain_plan",
                "tool_calls",
            ],
        },
        "prompt_contract": prompt,
        "reference_contract": {
            "sha256": reference_hash,
            "loaded_only_after_all_generation_conditions": True,
            "passed_to_model": False,
            "variants_per_provider_source": 2,
        },
        "generation_contract": {
            "decode_mode": "greedy",
            "temperature": 0.0,
            "top_p": 0.0,
            "maximum_new_tokens": MAX_GENERATION_TOKENS,
            "repetitions": list(REPEATS),
            "condition_orders": {str(key): list(value) for key, value in CONDITION_ORDERS.items()},
        },
        "exact_probe": {
            "conditions": list(CONDITIONS),
            "repetitions": list(REPEATS),
            "generation_calls_each_repeat": len(CONDITIONS) * len(PRIMARY_ROW_INDICES),
            "model_loads_each_repeat": 1,
            "optimizer_updates": 0,
            "adapter_initialized": False,
            "memory_limit_bytes": base["exact_probe"]["memory_limit_bytes"],
            "wired_limit_bytes": base["exact_probe"]["wired_limit_bytes"],
            "random_seed": 20260803,
        },
        "falsifiable_hypothesis": {
            "confirm_if_all": {
                "all_repetitions_successful": True,
                "each_condition_reproducible": True,
                "candidate_changed_output_count_minimum": 2,
                "provider_pair_difference_rate_delta_minimum": 0.0,
                "provider_alignment_margin_gain_minimum": 0.02,
                "correct_provider_alignment_rate_gain_minimum": 0.125,
                "joint_contract_pass_rate_delta_minimum": 0.0,
                "joint_contract_regression_count_maximum": 0,
                "semantic_complete_rate_delta_minimum": 0.0,
                "memory_policy_pass_rate_delta_minimum": 0.0,
                "forbidden_pass_rate_delta_minimum": 0.0,
                "exact_reference_copy_count_maximum": 0,
                "peak_memory_bytes_maximum": base["exact_probe"]["memory_limit_bytes"],
            },
            "success_outcome": "compiled_surface_signal_effect_confirmed",
            "failure_outcomes": [
                "compiled_surface_signal_execution_failed",
                "compiled_surface_signal_not_reproducible",
                "compiled_surface_signal_contract_regressed",
                "compiled_surface_signal_alignment_not_improved",
            ],
        },
        "success_authorization": {
            "maximum_positive_next_step": "preregister_compiled_signal_source_disjoint_full_pipeline_holdout",
            "persistent_training": False,
            "persona_training": False,
            "adapter_save": False,
            "runtime_activation": False,
            "persona_similarity_claim": False,
        },
        "boundaries": {
            "text_generation": True,
            "training": False,
            "optimizer_updates": 0,
            "adapter_or_model_save": False,
            "target_person_utterance_training": False,
            "benchmark_training": False,
            "production_runtime_change": False,
            "scope": "qwen3_prompt_only_compiled_surface_signal_probe",
        },
        "interpretation_limits": [
            "A pass would show only that concrete generic surface operations improve provider-conditioned generation on this source-disjoint prompt-only probe.",
            "It would authorize only a separately preregistered full-pipeline holdout.",
            "It would not prove target-person fidelity, persistent learning, training value, or production readiness.",
        ],
        "result_paths": {
            "repeat_prefix": "reports/rightbrain_qwen3_compiled_surface_signal_v1_repeat_",
            "aggregate_json": "reports/rightbrain_qwen3_compiled_surface_signal_v1_result.json",
            "aggregate_markdown": "reports/rightbrain_qwen3_compiled_surface_signal_v1_result.md",
            "result_lock": "configs/rightbrain_qwen3_compiled_surface_signal_v1_result_lock.json",
        },
    }
    atomic_json(DEFAULT_PREREGISTRATION, prereg)
    construction = {
        "schema": "uruha_rightbrain_qwen3_compiled_surface_signal_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "preregistration": file_binding(DEFAULT_PREREGISTRATION),
        "dataset": file_binding(DEFAULT_DATASET),
        "causal_scope": prereg["causal_scope"],
        "source_split_contract": prereg["source_split_contract"],
        "prompt_hashes": {
            condition: prompt[f"{condition}_prompt_sha256"] for condition in CONDITIONS
        },
        "ready": True,
    }
    atomic_json(DEFAULT_CONSTRUCTION_JSON, construction)
    atomic_text(
        DEFAULT_CONSTRUCTION_MD,
        "\n".join(
            [
                "# Qwen3 compiled surface-signal probe",
                "",
                "- Only variable: abstract provider labels versus their deterministic concrete surface-only compilation.",
                "- Both signals occupy the first top-level JSON field.",
                "- Eight prompts from four new synthetic sources; two references per provider and source.",
                "- Base Qwen3-4B, greedy decoding, three isolated repeats, no training or save.",
                "- References are loaded only after both conditions finish generation.",
            ]
        )
        + "\n",
    )
    external_bindings = [
        {**binding, "scope": "external_local"}
        for binding in prereg["external_model_bindings"]
    ]
    lock = {
        "schema": "uruha_rightbrain_qwen3_compiled_surface_signal_execution_lock_v1",
        "experiment_id": EXPERIMENT_ID,
        "bindings": [
            file_binding(DEFAULT_PREREGISTRATION),
            file_binding(DEFAULT_DATASET),
            file_binding(DEFAULT_CONSTRUCTION_JSON),
            file_binding(DEFAULT_CONSTRUCTION_MD),
            file_binding(Path(__file__).resolve()),
            file_binding(RUNNER_PATH),
            file_binding(TEST_PATH),
            file_binding(VERIFIER_PATH),
            file_binding(MODEL_PREREGISTRATION),
            file_binding(PRIOR_DATASET),
            file_binding(PARENT_RESULT),
            file_binding(PARENT_RESULT_LOCK),
            file_binding(PARENT_DIAGNOSIS),
            *external_bindings,
        ],
        "authorization": {
            "conditions": list(CONDITIONS),
            "repetitions": list(REPEATS),
            "condition_orders": prereg["generation_contract"]["condition_orders"],
            "primary_row_indices": list(PRIMARY_ROW_INDICES),
            "reference_alt_row_indices": list(REFERENCE_ALT_ROW_INDICES),
            "prior_source_overlap_exact": 0,
            "prior_answer_overlap_exact": 0,
            "base_model": prereg["local_model_contract"]["base_model"],
            "device": "gpu",
            "generation_contract": prereg["generation_contract"],
            "optimizer_updates": 0,
            "adapter_initialized": False,
            "adapter_or_model_save": False,
            "target_person_utterance_training": False,
            "benchmark_training": False,
            "production_runtime_change": False,
        },
    }
    atomic_json(DEFAULT_EXECUTION_LOCK, lock)
    return construction


def main():
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
