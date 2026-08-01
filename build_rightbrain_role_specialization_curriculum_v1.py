#!/usr/bin/env python3
"""Build and audit a source-independent curriculum for the current RightBrain contract."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path

import audit_rightbrain_current_contract_curriculum_v1 as contract_audit
import uruha_brain_mac as brain_module
import uruha_persona_policy as persona_policy
import uruha_surface_payload_v2 as surface_payload
from persona_policy_local_model_pilot_v1 import EMPTY_MEMORY, PSYCHE


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_role_specialization_curriculum_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_role_specialization_curriculum_v1_preregistration.json"
DEFAULT_SPECS = ROOT / "configs/rightbrain_role_specialization_curriculum_v1_specs.json"
DEFAULT_DATASET = ROOT / "datasets/rightbrain_role_specialization_curriculum_v1.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_role_specialization_curriculum_v1.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_role_specialization_curriculum_v1.md"
PROVIDERS = (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER)
MEMORY_POLICIES = {
    "no_memory": ("no_memory", False),
    "explicit_allowed": ("explicit_ok", True),
    "background_only": ("background_only", False),
    "do_not_mention": ("private_blocked", False),
}
TARGET_IDENTITY_MARKERS = ("一ノ瀬", "うるは", "ichinose")
BENCHMARK_ANSWER_KEYS = frozenset(
    {
        "answer_key",
        "benchmark_answer",
        "correct_answer",
        "expected_reply",
        "gold",
        "gold_answer",
    }
)
POLITE_MARKERS = ("です", "ます", "ください", "ございます")
JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶー一-龠]")
LATIN_RE = re.compile(r"[A-Za-z]")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalized_text(value):
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return "".join(character for character in text if character.isalnum())


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value.rstrip() + "\n", encoding="utf-8")
    os.replace(temporary, path)


def file_binding(path):
    path = Path(path)
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def _contains_forbidden_key(value):
    if isinstance(value, dict):
        return sum(
            int(key in BENCHMARK_ANSWER_KEYS) + _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return sum(_contains_forbidden_key(item) for item in value)
    return 0


def _procedural_guidance(memory_mode):
    if memory_mode == "explicit_allowed":
        return {
            "source": "generic_leftbrain_procedure",
            "priority": "semantic_then_memory_then_style",
            "steps": [
                "preserve_every_required_semantic_group",
                "mention_only_the_explicitly_allowed_memory_cue",
                "apply_surface_policy_without_adding_facts",
            ],
        }
    if memory_mode == "background_only":
        return {
            "source": "generic_leftbrain_procedure",
            "priority": "semantic_then_memory_then_style",
            "steps": [
                "preserve_every_required_semantic_group",
                "use_background_memory_only_to_adjust_delivery",
                "do_not_state_the_background_memory",
            ],
        }
    return {}


def logic_from_spec(spec):
    memory_mode = spec["memory_mode"]
    speakability, explicit = MEMORY_POLICIES[memory_mode]
    memory = copy.deepcopy(spec.get("memory") or {})
    must_avoid = ["AI", "技術説明", "です", "ます"]
    if memory_mode in {"background_only", "do_not_mention"}:
        must_avoid.extend(memory.get("terms") or [])
    return {
        "public_persona_context": spec["context"],
        "scene": "public_conversation",
        "intent": spec["context"],
        "surface_act": "plain_reply",
        "dialogue_act": spec["context"],
        "jp_summary": spec["jp_summary"],
        "core_message_jp": spec["core_message_jp"],
        "required_marker_groups": copy.deepcopy(spec["required_marker_groups"]),
        "constraints": {
            "max_chars": int(spec["max_chars"]),
            "sentence_count": 2,
            "casual_japanese_only": True,
            "forbid_polite": True,
        },
        "must_avoid": list(dict.fromkeys(must_avoid)),
        "memory_anchor": memory,
        "memory_speakability": speakability,
        "memory_use_expected": explicit,
        "memory_speakability_reason": f"synthetic_curriculum_{memory_mode}",
        "procedural_guidance": _procedural_guidance(memory_mode),
        "action_intent_frame": {"decision": "none", "reason": "conversation_only"},
        "authorized_action": None,
        "tool_calls": [],
        "human_speech_plan": {
            "dialogue_act": spec["context"],
            "content_units": copy.deepcopy(spec["content_units"]),
            "grounding_terms": copy.deepcopy(spec["grounding_terms"]),
            "style_operators": ["short", "casual"],
            "target_length": "one_or_two_short_sentences",
            "forbidden_repetition": {
                "recent_openings": [],
                "avoid_generic_frames": [],
                "avoid_same_refusal_strategy": False,
            },
            "turn_opening_potential": False,
            "prosody_hint": {
                "emotion": "context_matched",
                "speed": "normal",
                "energy": 0.5,
                "pause_after_first_unit": False,
            },
            "content_density_target": 0.45,
        },
    }


def build_payload(logic, context, provider_id, psyche=None):
    rightbrain = brain_module.RightBrain(
        load_model=False,
        persona_policy_provider=persona_policy.build_persona_policy_provider(provider_id),
    )
    rightbrain.structured_payload_mode = surface_payload.LEGACY_JSON_V1
    rightbrain.model_repair_enabled = False
    rightbrain.model_candidate_count = 1
    rightbrain.surface_watchlist_enabled = False
    rightbrain.explicit_length_contract_enabled = False
    rightbrain.memory_cue_canonicalization_enabled = False
    rightbrain.forbidden_conflict_projection_enabled = False
    projected = copy.deepcopy(logic)
    projected["public_persona_context"] = context
    max_chars = int((projected.get("constraints") or {}).get("max_chars") or 64)
    payload_text = rightbrain._build_model_surface_payload(
        projected,
        dict(psyche or PSYCHE),
        max_chars,
        memory_data=copy.deepcopy(EMPTY_MEMORY),
    )
    return json.loads(payload_text), rightbrain._model_surface_system_instruction()


def _runtime_case_payloads(cases):
    rows = []
    for case in cases:
        logic = copy.deepcopy(case["logic"])
        context = case.get("context") or logic.get("public_persona_context") or ""
        for provider_id in PROVIDERS:
            payload, instruction = build_payload(
                logic,
                context,
                provider_id,
                psyche=case.get("psyche") or PSYCHE,
            )
            rows.append(
                {
                    "case_id": case["case_id"],
                    "provider_id": provider_id,
                    "payload": payload,
                    "system_instruction": instruction,
                }
            )
    return rows


def _old_training_targets(preregistration):
    targets = set()
    source_rows = 0
    for source in preregistration["frozen_inputs"]["excluded_training_targets"]:
        rows = load_json(ROOT / source["path"])
        source_rows += len(rows)
        for row in rows:
            for message in row.get("messages") or []:
                if message.get("role") == "assistant":
                    target = str(message.get("content") or "").strip()
                    if target:
                        targets.add(target)
    return targets, source_rows


def _collect_key_strings(value, keys):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, str) and item.strip():
                found.add(item.strip())
            found.update(_collect_key_strings(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_key_strings(item, keys))
    return found


def _existing_development_outputs():
    paths = [
        ROOT / "reports/persona_policy_local_model_pilot_v1_result.json",
        ROOT / "reports/rightbrain_carrier_model_screen_v1_qwen2_5_7b.json",
        ROOT / "reports/rightbrain_carrier_model_screen_v1_qwen3_5_4b.json",
        ROOT / "reports/rightbrain_carrier_model_screen_v1_qwen3_5_9b.json",
    ]
    outputs = set()
    bindings = []
    for path in paths:
        if not path.is_file():
            continue
        report = load_json(path)
        outputs.update(
            _collect_key_strings(
                report,
                {"raw_generation", "final_output", "model_output", "reply"},
            )
        )
        bindings.append(file_binding(path))
    return outputs, bindings


def validate_frozen_inputs(preregistration):
    reports = []
    bindings = []
    for key in ("runtime_source", "persona_policy_source", "public_persona_contract_source"):
        bindings.append(preregistration["frozen_inputs"][key])
    bindings.append(preregistration["frozen_inputs"]["previous_construction_authorization"])
    bindings.extend(preregistration["frozen_inputs"]["excluded_development_sets"])
    bindings.extend(preregistration["frozen_inputs"]["excluded_training_targets"])
    for binding in bindings:
        path = ROOT / binding["path"]
        actual_hash = sha256_file(path) if path.is_file() else None
        reports.append(
            {
                "path": binding["path"],
                "expected_sha256": binding["sha256"],
                "actual_sha256": actual_hash,
                "match": actual_hash == binding["sha256"],
            }
        )
    previous = load_json(
        ROOT / preregistration["frozen_inputs"]["previous_construction_authorization"]["path"]
    )
    expected_decision = preregistration["frozen_inputs"]["previous_construction_authorization"][
        "required_decision"
    ]
    authorization_match = previous["decision"]["outcome"] == expected_decision
    return {
        "passed": all(row["match"] for row in reports) and authorization_match,
        "bindings": reports,
        "previous_authorization_match": authorization_match,
        "previous_authorization": previous["decision"]["outcome"],
    }


def build_curriculum(specs):
    rows = []
    payload_rows = []
    for spec in specs["cases"]:
        logic = logic_from_spec(spec)
        for provider_id in PROVIDERS:
            payload, system_instruction = build_payload(logic, spec["context"], provider_id)
            payload_rows.append(
                {
                    "case_id": spec["case_id"],
                    "context": spec["context"],
                    "memory_mode": spec["memory_mode"],
                    "provider_id": provider_id,
                    "payload": payload,
                    "system_instruction": system_instruction,
                }
            )
            for variant_index, target in enumerate(spec["outputs"][provider_id], start=1):
                rows.append(
                    {
                        "id": f"rb_role_specialization_v1_{len(rows) + 1:04d}",
                        "source_id": spec["case_id"],
                        "category": "current_joint_contract_role_specialization",
                        "training_role": "policy_conditioned_surface_realization",
                        "provider_id": provider_id,
                        "memory_mode": spec["memory_mode"],
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
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": canonical_json(payload)},
                            {"role": "assistant", "content": target},
                        ],
                    }
                )
    return rows, payload_rows


def _assistant_target(row):
    return next(
        message["content"]
        for message in row["messages"]
        if message["role"] == "assistant"
    )


def _user_payload(row):
    return json.loads(
        next(message["content"] for message in row["messages"] if message["role"] == "user")
    )


def audit_balance(rows, preregistration):
    expected = preregistration["balance_requirements"]
    provider_counts = Counter(row["provider_id"] for row in rows)
    context_counts = Counter(_user_payload(row)["context"]["persona_expression_brief"]["conditional_context"] for row in rows)
    memory_counts = Counter(row["memory_mode"] for row in rows)
    procedural_count = sum(bool((_user_payload(row).get("context") or {}).get("procedural_guidance")) for row in rows)
    base_counts = Counter(row["source_id"] for row in rows)
    checks = {
        "row_count": len(rows) == preregistration["curriculum_design"]["row_count"],
        "provider_balance": set(provider_counts.values()) == {expected["rows_per_provider"]},
        "context_balance": set(context_counts.values()) == {expected["rows_per_persona_context"]},
        "memory_balance": set(memory_counts.values()) == {expected["rows_per_memory_mode"]},
        "procedural_active_balance": procedural_count == expected["rows_with_procedural_guidance"],
        "procedural_inactive_balance": len(rows) - procedural_count == expected["rows_without_procedural_guidance"],
        "base_case_balance": set(base_counts.values()) == {expected["rows_per_base_case"]},
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "provider_counts": dict(sorted(provider_counts.items())),
        "context_counts": dict(sorted(context_counts.items())),
        "memory_mode_counts": dict(sorted(memory_counts.items())),
        "rows_with_procedural_guidance": procedural_count,
        "rows_without_procedural_guidance": len(rows) - procedural_count,
    }


def audit_quality(rows, payload_rows, preregistration, current_reference_rows, specs):
    semantic_pass = 0
    forbidden_pass = 0
    length_pass = 0
    casual_japanese_pass = 0
    memory_policy_pass = 0
    runtime_candidate_gate_pass = 0
    failures = []
    spec_by_id = {spec["case_id"]: spec for spec in specs["cases"]}
    for row in rows:
        target = _assistant_target(row)
        payload = _user_payload(row)
        spec = spec_by_id[row["source_id"]]
        required_groups = payload.get("required_marker_groups") or []
        missing_groups = [group for group in required_groups if not any(marker in target for marker in group)]
        forbidden_hits = [marker for marker in payload.get("forbidden_markers") or [] if marker and marker in target]
        max_chars = int(payload["context"]["max_chars"])
        casual_ok = bool(JAPANESE_RE.search(target)) and not LATIN_RE.search(target) and not any(
            marker in target for marker in POLITE_MARKERS
        )
        memory = payload["context"]["audited_memory_brief"]
        policy = memory["policy"]
        if policy == "explicit_allowed":
            cue_terms = []
            for cue in memory.get("allowed_memory_cues") or []:
                cue_terms.extend([cue.get("jp_anchor"), *(cue.get("terms") or [])])
            memory_ok = any(str(term or "") in target for term in cue_terms if str(term or ""))
        elif policy in {"background_only", "do_not_mention"}:
            memory_ok = not any(
                marker in target
                for marker in payload.get("forbidden_markers") or []
                if marker not in {"AI", "技術説明", "です", "ます"}
            )
        else:
            memory_ok = policy == "no_memory"
        runtime_rightbrain = brain_module.RightBrain(
            load_model=False,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                row["provider_id"]
            ),
        )
        runtime_rightbrain.structured_payload_mode = surface_payload.LEGACY_JSON_V1
        runtime_rightbrain.surface_watchlist_enabled = False
        runtime_rightbrain.explicit_length_contract_enabled = False
        runtime_rightbrain.memory_cue_canonicalization_enabled = False
        runtime_rightbrain.forbidden_conflict_projection_enabled = False
        runtime_rejection_reasons = runtime_rightbrain._model_candidate_rejection_reasons(
            target,
            logic_from_spec(spec),
            max_chars,
            user_input=spec["user_input"],
        )
        semantic_pass += not missing_groups
        forbidden_pass += not forbidden_hits
        length_pass += len(target) <= max_chars
        casual_japanese_pass += casual_ok
        memory_policy_pass += memory_ok
        runtime_candidate_gate_pass += not runtime_rejection_reasons
        if (
            missing_groups
            or forbidden_hits
            or len(target) > max_chars
            or not casual_ok
            or not memory_ok
            or runtime_rejection_reasons
        ):
            failures.append(
                {
                    "row_id": row["id"],
                    "missing_semantic_groups": missing_groups,
                    "forbidden_hits": forbidden_hits,
                    "length": len(target),
                    "maximum_length": max_chars,
                    "casual_japanese": casual_ok,
                    "memory_policy": policy,
                    "memory_policy_pass": memory_ok,
                    "runtime_candidate_gate_rejection_reasons": runtime_rejection_reasons,
                }
            )

    targets = [_assistant_target(row) for row in rows]
    normalized_targets = [normalized_text(target) for target in targets]
    prefix_counts = Counter(target[:6] for target in normalized_targets if target)
    pair_map = {}
    for row in rows:
        pair_map[(row["source_id"], row["variant_index"], row["provider_id"])] = normalized_text(
            _assistant_target(row)
        )
    pair_differences = []
    for source_id in sorted({row["source_id"] for row in rows}):
        for variant_index in (1, 2):
            left = pair_map[(source_id, variant_index, persona_policy.TARGET_PROVIDER)]
            right = pair_map[(source_id, variant_index, persona_policy.NEUTRAL_PROVIDER)]
            pair_differences.append(left != right and bool(left) and bool(right))

    reference_profile = contract_audit.merge_contract_profiles(
        [row["payload"] for row in current_reference_rows]
    )
    curriculum_profile = contract_audit.merge_contract_profiles(
        [row["payload"] for row in payload_rows]
    )
    persona_path_coverage = contract_audit.path_coverage(
        reference_profile,
        curriculum_profile,
        prefix="context.persona_expression_brief",
    )
    persona_value_coverage = contract_audit.value_coverage(
        reference_profile,
        curriculum_profile,
        prefix="context.persona_expression_brief",
    )
    current_instructions = {row["system_instruction"] for row in current_reference_rows}
    exact_instruction_count = sum(
        row["messages"][0]["content"] in current_instructions for row in rows
    )
    joint_count = sum(contract_audit.has_joint_contract(_user_payload(row)) for row in rows)
    retired_rule_count = sum(
        "no first person 私" in (_user_payload(row).get("reply_requirements") or [])
        for row in rows
    )
    count = len(rows)
    rates = {
        "joint_contract_coverage": round(joint_count / count, 6),
        "current_persona_policy_path_coverage": persona_path_coverage["coverage"],
        "current_persona_policy_value_coverage": persona_value_coverage["coverage"],
        "exact_current_system_instruction_coverage": round(exact_instruction_count / count, 6),
        "semantic_contract_pass_rate": round(semantic_pass / count, 6),
        "forbidden_marker_pass_rate": round(forbidden_pass / count, 6),
        "maximum_length_pass_rate": round(length_pass / count, 6),
        "casual_japanese_surface_pass_rate": round(casual_japanese_pass / count, 6),
        "memory_policy_pass_rate": round(memory_policy_pass / count, 6),
        "runtime_candidate_gate_pass_rate": round(runtime_candidate_gate_pass / count, 6),
        "provider_pair_output_difference_rate": round(sum(pair_differences) / len(pair_differences), 6),
    }
    requirements = preregistration["quality_requirements"]
    checks = {
        key: rates[key] == expected
        for key, expected in requirements.items()
        if key in rates
    }
    checks.update(
        {
            "unique_normalized_target_count": len(set(normalized_targets))
            == requirements["unique_normalized_target_count"],
            "maximum_shared_six_character_prefix_count": max(prefix_counts.values())
            <= requirements["maximum_shared_six_character_prefix_count"],
            "retired_no_first_person_rule_row_count": retired_rule_count
            == requirements["retired_no_first_person_rule_row_count"],
            "memory_policy_pass_rate": rates["memory_policy_pass_rate"] == 1.0,
            "runtime_candidate_gate_pass_rate": rates["runtime_candidate_gate_pass_rate"] == 1.0,
        }
    )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "rates": rates,
        "counts": {
            "row_count": count,
            "joint_contract_row_count": joint_count,
            "exact_current_system_instruction_row_count": exact_instruction_count,
            "unique_normalized_target_count": len(set(normalized_targets)),
            "provider_pair_count": len(pair_differences),
            "provider_pair_different_count": sum(pair_differences),
            "maximum_shared_six_character_prefix_count": max(prefix_counts.values()),
            "retired_no_first_person_rule_row_count": retired_rule_count,
        },
        "persona_policy_path_coverage": persona_path_coverage,
        "persona_policy_value_coverage": persona_value_coverage,
        "most_common_six_character_prefixes": prefix_counts.most_common(10),
        "failures": failures,
    }


def audit_separation(rows, payload_rows, preregistration, specs, development_rows):
    current_inputs = {row["payload"].get("user_input", "") for row in payload_rows}
    development_inputs = {row["payload"].get("user_input", "") for row in development_rows}
    current_normalized_inputs = {normalized_text(value) for value in current_inputs if value}
    development_normalized_inputs = {normalized_text(value) for value in development_inputs if value}
    current_payloads = {canonical_json(row["payload"]) for row in payload_rows}
    development_payloads = {canonical_json(row["payload"]) for row in development_rows}
    targets = {_assistant_target(row) for row in rows}
    normalized_targets = {normalized_text(value) for value in targets}
    old_targets, old_source_rows = _old_training_targets(preregistration)
    development_outputs, development_output_bindings = _existing_development_outputs()
    excluded_targets = old_targets | development_outputs
    normalized_excluded_targets = {normalized_text(value) for value in excluded_targets if value}
    training_message_text = "\n".join(
        message["content"]
        for row in rows
        for message in row["messages"]
    ).lower()
    target_identity_hits = [
        marker for marker in TARGET_IDENTITY_MARKERS if marker.lower() in training_message_text
    ]
    provenance = [row["provenance"] for row in rows]
    checks = {
        "exact_user_input_overlap_count": len(current_inputs & development_inputs),
        "normalized_user_input_overlap_count": len(current_normalized_inputs & development_normalized_inputs),
        "exact_payload_overlap_count": len(current_payloads & development_payloads),
        "exact_target_overlap_count": len(targets & excluded_targets),
        "normalized_target_overlap_count": len(normalized_targets & normalized_excluded_targets),
        "target_identity_marker_count": len(target_identity_hits),
        "target_utterance_count": sum(bool(row["contains_target_utterance"]) for row in provenance),
        "benchmark_or_answer_key_field_count": _contains_forbidden_key(specs),
        "runtime_fixed_reply_count": sum(bool(row["runtime_fixed_reply"]) for row in provenance),
    }
    requirements = preregistration["separation_requirements"]
    result_checks = {key: checks[key] == expected for key, expected in requirements.items()}
    provenance_requirements = preregistration["row_provenance_requirements"]
    provenance_checks = {
        key: all(row[key] is expected for row in provenance)
        for key, expected in provenance_requirements.items()
    }
    return {
        "passed": all(result_checks.values()) and all(provenance_checks.values()),
        "checks": checks,
        "result_checks": result_checks,
        "provenance_checks": provenance_checks,
        "excluded_development_payload_count": len(development_rows),
        "excluded_historical_training_row_count": old_source_rows,
        "excluded_target_count": len(excluded_targets),
        "target_identity_hits": target_identity_hits,
        "development_output_bindings": development_output_bindings,
        "target_utterance_operationalization": (
            "All exemplars were project-authored as generic synthetic Japanese with Codex assistance; the builder "
            "reads no public-persona "
            "source text, and every row declares contains_target_utterance=false. The repository's persona evidence "
            "contains no raw transcript, so semantic originality beyond these provenance and overlap checks is not "
            "independently provable by string matching."
        ),
    }


def builder_source_boundary():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden_source_mentions = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        function_name = node.func.id if isinstance(node.func, ast.Name) else ""
        if function_name not in {"load_json", "open"}:
            continue
        source = node.args[0]
        if not isinstance(source, ast.Constant) or not isinstance(source.value, str):
            continue
        if "public_persona_observations" in source.value or "public_persona_source_registry" in source.value:
            forbidden_source_mentions.append(source.value)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden_model_calls = sorted(called_attributes & {"chat", "generate", "fit", "backward", "train"})
    return {
        "passed": not forbidden_source_mentions and not forbidden_model_calls,
        "public_persona_raw_source_references": forbidden_source_mentions,
        "model_or_training_calls": forbidden_model_calls,
    }


def build_report(preregistration=None, specs=None):
    preregistration = preregistration or load_json(DEFAULT_PREREGISTRATION)
    specs = specs or load_json(DEFAULT_SPECS)
    frozen = validate_frozen_inputs(preregistration)
    rows, payload_rows = build_curriculum(specs)
    pilot_cases = load_json(ROOT / preregistration["frozen_inputs"]["excluded_development_sets"][0]["path"])["cases"]
    persona_cases = load_json(ROOT / preregistration["frozen_inputs"]["excluded_development_sets"][1]["path"])["cases"]
    current_reference_rows = _runtime_case_payloads(pilot_cases)
    development_rows = current_reference_rows + _runtime_case_payloads(persona_cases)
    balance = audit_balance(rows, preregistration)
    quality = audit_quality(
        rows,
        payload_rows,
        preregistration,
        current_reference_rows,
        specs,
    )
    separation = audit_separation(
        rows,
        payload_rows,
        preregistration,
        specs,
        development_rows,
    )
    source_boundary = builder_source_boundary()
    passed = all(
        (
            frozen["passed"],
            balance["passed"],
            quality["passed"],
            separation["passed"],
            source_boundary["passed"],
        )
    )
    return rows, {
        "schema": "uruha_rightbrain_role_specialization_curriculum_report_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "construction_passed" if passed else "construction_failed",
        "inputs": {
            "preregistration": file_binding(DEFAULT_PREREGISTRATION),
            "specs": file_binding(DEFAULT_SPECS),
        },
        "frozen_input_validation": frozen,
        "accounting": {
            "base_case_count": len(specs["cases"]),
            "curriculum_row_count": len(rows),
            "unique_payload_count": len(payload_rows),
            "actual_model_generation_call_count": 0,
            "model_training_run_count": 0,
            "production_runtime_file_change_count": 0,
            "production_memory_write_count": 0,
        },
        "balance": balance,
        "quality": quality,
        "separation": separation,
        "builder_source_boundary": source_boundary,
        "decision": {
            "outcome": (
                "authorize_matched_local_training_pilot_preregistration_only"
                if passed
                else "reject_or_revise_curriculum"
            ),
            "authorize_training_pilot_preregistration": passed,
            "authorize_model_training": False,
            "authorize_production_change": False,
            "authorize_persona_similarity_claim": False,
            "authorize_generalization_claim": False,
            "causal_claim_supported": False,
        },
        "evidence_boundary": (
            "This result proves only that the synthetic curriculum satisfies the frozen structural, balance, "
            "surface, memory-policy, and separation gates. A preregistered matched training comparison is still "
            "required to learn whether it improves fresh local-model generation."
        ),
    }


def render_markdown(report):
    quality = report["quality"]
    separation = report["separation"]
    decision = report["decision"]
    return "\n".join(
        [
            "# 右腦角色專業化課程 V1",
            "",
            "## 結論",
            "",
            (
                "課程建構與稽核通過。它只授權下一輪先登記公平的本機訓練對照實驗，"
                "尚未授權訓練、上線或宣稱人格更相似。"
                if report["status"] == "construction_passed"
                else "課程未通過凍結門檻，不能進入訓練。"
            ),
            "",
            "## 課程構造",
            "",
            "| 項目 | 結果 |",
            "|---|---:|",
            f"| 全新通用情境 | {report['accounting']['base_case_count']} |",
            f"| 現行聯合契約 payload | {report['accounting']['unique_payload_count']} |",
            f"| 訓練列 | {report['accounting']['curriculum_row_count']} |",
            f"| 目標政策／中性政策 | {report['balance']['provider_counts'][persona_policy.TARGET_PROVIDER]} / {report['balance']['provider_counts'][persona_policy.NEUTRAL_PROVIDER]} |",
            "| 四種記憶模式 | 每種 20 筆 |",
            f"| 有／無程序指引 | {report['balance']['rows_with_procedural_guidance']} / {report['balance']['rows_without_procedural_guidance']} |",
            "",
            "每個認知計畫都同時提供目標政策與中性政策，各有兩種不同說法。這些句子是訓練範例，",
            "不是正式聊天時可以查表輸出的固定回覆。",
            "",
            "## 品質門檻",
            "",
            "| 檢查 | 結果 |",
            "|---|---:|",
            f"| 現行聯合契約覆蓋 | {quality['rates']['joint_contract_coverage']:.1%} |",
            f"| 人格政策路徑覆蓋 | {quality['rates']['current_persona_policy_path_coverage']:.1%} |",
            f"| 人格政策值覆蓋 | {quality['rates']['current_persona_policy_value_coverage']:.1%} |",
            f"| 必要語意通過 | {quality['rates']['semantic_contract_pass_rate']:.1%} |",
            f"| 記憶可說性通過 | {quality['rates']['memory_policy_pass_rate']:.1%} |",
            f"| 正式候選驗證器接受 | {quality['rates']['runtime_candidate_gate_pass_rate']:.1%} |",
            f"| 禁用內容與長度通過 | {quality['rates']['forbidden_marker_pass_rate']:.1%} / {quality['rates']['maximum_length_pass_rate']:.1%} |",
            f"| 80 筆回答的正規化唯一數 | {quality['counts']['unique_normalized_target_count']} |",
            f"| 同計畫兩種政策輸出不同 | {quality['rates']['provider_pair_output_difference_rate']:.1%} |",
            "",
            "## 資料邊界",
            "",
            "| 洩漏檢查 | 數量 |",
            "|---|---:|",
            *[
                f"| {key} | {value} |"
                for key, value in separation["checks"].items()
            ],
            "",
            "教材範例由 Codex 協助合成；建構程式沒有讀取公開人物原始逐字稿，也沒有呼叫本機生成或訓練。人物原句不存在於專案證據庫，",
            "因此本輪可證明的是來源治理、字串分離與建構程序，不把『沒有找到相同字串』誤稱為人格原創性的完整證明。",
            "",
            "## 決策",
            "",
            f"- 結果：`{decision['outcome']}`",
            "- 下一輪可做：先凍結同模型、同初始 adapter、同訓練預算與同評測的 matched pilot。",
            "- 本輪不可做：直接訓練、切換正式模型、宣稱人格更像或正式上線。",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=DEFAULT_DATASET)
    parser.add_argument("--report-json", default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", default=DEFAULT_REPORT_MD)
    args = parser.parse_args()
    rows, report = build_report()
    atomic_json(args.output, rows)
    atomic_json(args.report_json, report)
    atomic_text(args.report_md, render_markdown(report))
    if report["status"] != "construction_passed":
        raise SystemExit("curriculum construction failed frozen gates")


if __name__ == "__main__":
    main()
