#!/usr/bin/env python3
"""Build and audit the matched RightBrain role-curriculum training pilot."""

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

from transformers import AutoTokenizer

import build_rightbrain_role_specialization_curriculum_v1 as curriculum
import public_persona_scorer_contract_v4 as persona_scorer
import public_persona_specificity_scorer_v7 as specificity_scorer
import uruha_persona_policy as persona_policy
from train_uruha_rightbrain_contract_v1 import tokenize_row


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_role_curriculum_training_pilot_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_preregistration.json"
DEFAULT_TREATMENT = ROOT / "datasets/rightbrain_role_specialization_curriculum_v1.json"
DEFAULT_CONTROL = ROOT / "datasets/rightbrain_role_specialization_curriculum_v1_policy_permuted_control.json"
DEFAULT_HOLDOUT = ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_holdout.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_role_curriculum_training_pilot_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_role_curriculum_training_pilot_v1_construction.md"
PROVIDERS = (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER)
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
JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶー一-龠]")
LATIN_RE = re.compile(r"[A-Za-z]")
POLITE_MARKERS = ("です", "ます", "ください", "ございます")


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


def assistant_target(row):
    return str(row["messages"][-1]["content"]).strip()


def role_message(row, role):
    return next(message["content"] for message in row["messages"] if message["role"] == role)


def _contains_forbidden_key(value):
    if isinstance(value, dict):
        return sum(
            int(str(key).lower() in BENCHMARK_ANSWER_KEYS) + _contains_forbidden_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return sum(_contains_forbidden_key(item) for item in value)
    return 0


def build_policy_permuted_control(treatment_rows):
    """Keep variant 1 aligned and exchange variant 2 within each matched provider pair."""
    indexed = {
        (row["source_id"], row["provider_id"], int(row["variant_index"])): row
        for row in treatment_rows
    }
    if len(indexed) != len(treatment_rows):
        raise ValueError("Treatment rows do not have unique source/provider/variant keys")
    control = []
    for treatment_row in treatment_rows:
        row = copy.deepcopy(treatment_row)
        row["id"] = str(row["id"]).replace(
            "rb_role_specialization_v1_",
            "rb_role_specialization_v1_policy_permuted_control_",
        )
        provider_id = row["provider_id"]
        variant_index = int(row["variant_index"])
        aligned = variant_index == 1
        source_provider = provider_id
        if not aligned:
            source_provider = next(provider for provider in PROVIDERS if provider != provider_id)
            source = indexed[(row["source_id"], source_provider, variant_index)]
            row["messages"][-1]["content"] = assistant_target(source)
        row["training_role"] = "policy_permuted_surface_realization_control"
        row["control_assignment"] = {
            "prompt_provider_id": provider_id,
            "surface_source_provider_id": source_provider,
            "policy_aligned": aligned,
            "variant_index_not_present_in_model_prompt": True,
        }
        control.append(row)
    return control


def _multiset(values):
    return Counter(str(value) for value in values)


def _token_profile(rows, tokenizer, max_length):
    lengths = []
    prompt_tokens = completion_tokens = combined_tokens = 0
    truncated = []
    for row in rows:
        prompt = tokenizer.apply_chat_template(
            row["messages"][:-1], tokenize=False, add_generation_prompt=True
        )
        answer = f"{assistant_target(row)}<|im_end|>"
        prompt_count = len(tokenizer(prompt, add_special_tokens=False).input_ids)
        completion_count = len(tokenizer(answer, add_special_tokens=False).input_ids)
        tokenized = tokenize_row(row, tokenizer, max_length)
        combined_count = prompt_count + completion_count
        prompt_tokens += prompt_count
        completion_tokens += completion_count
        combined_tokens += combined_count
        lengths.append(combined_count)
        if combined_count > max_length or len(tokenized["input_ids"]) != combined_count:
            truncated.append(row["id"])
    return {
        "row_count": len(rows),
        "total_prompt_tokens": prompt_tokens,
        "total_completion_tokens": completion_tokens,
        "total_combined_tokens": combined_tokens,
        "minimum_active_token_length": min(lengths),
        "maximum_active_token_length": max(lengths),
        "allocated_token_length_each": max_length,
        "maximum_token_length": max_length,
        "mean_token_length": round(sum(lengths) / len(lengths), 3),
        "truncated_row_ids": truncated,
    }


def audit_matched_training_data(treatment, control, tokenizer, preregistration):
    max_length = int(preregistration["training_schedule"]["maximum_sequence_length"])
    treatment_tokens = _token_profile(treatment, tokenizer, max_length)
    control_tokens = _token_profile(control, tokenizer, max_length)
    treatment_keys = {
        (row["source_id"], row["provider_id"], int(row["variant_index"])): row
        for row in treatment
    }
    control_keys = {
        (row["source_id"], row["provider_id"], int(row["variant_index"])): row
        for row in control
    }
    assignment_checks = []
    for key, control_row in control_keys.items():
        source_id, provider_id, variant_index = key
        expected_provider = provider_id if variant_index == 1 else next(
            provider for provider in PROVIDERS if provider != provider_id
        )
        expected_target = assistant_target(
            treatment_keys[(source_id, expected_provider, variant_index)]
        )
        assignment_checks.append(
            assistant_target(control_row) == expected_target
            and control_row["control_assignment"]["policy_aligned"] == (variant_index == 1)
        )

    fields = {
        "row_count": len(treatment) == len(control) == 80,
        "system_message_multiset": _multiset(role_message(row, "system") for row in treatment)
        == _multiset(role_message(row, "system") for row in control),
        "user_payload_multiset": _multiset(role_message(row, "user") for row in treatment)
        == _multiset(role_message(row, "user") for row in control),
        "assistant_target_multiset": _multiset(assistant_target(row) for row in treatment)
        == _multiset(assistant_target(row) for row in control),
        "source_case_multiset": _multiset(row["source_id"] for row in treatment)
        == _multiset(row["source_id"] for row in control),
        "provider_multiset": _multiset(row["provider_id"] for row in treatment)
        == _multiset(row["provider_id"] for row in control),
        "memory_mode_multiset": _multiset(row["memory_mode"] for row in treatment)
        == _multiset(row["memory_mode"] for row in control),
        "total_prompt_tokens": treatment_tokens["total_prompt_tokens"]
        == control_tokens["total_prompt_tokens"],
        "total_completion_tokens": treatment_tokens["total_completion_tokens"]
        == control_tokens["total_completion_tokens"],
        "total_combined_tokens": treatment_tokens["total_combined_tokens"]
        == control_tokens["total_combined_tokens"],
        "maximum_token_length": treatment_tokens["maximum_token_length"]
        == control_tokens["maximum_token_length"],
        "no_truncation": not treatment_tokens["truncated_row_ids"]
        and not control_tokens["truncated_row_ids"],
        "control_pairing_rule": all(assignment_checks),
    }
    treatment_alignment = 1.0 if all(row["provider_id"] in PROVIDERS for row in treatment) else 0.0
    control_alignment = sum(
        row["control_assignment"]["policy_aligned"] for row in control
    ) / len(control)
    return {
        "passed": all(fields.values()) and treatment_alignment == 1.0 and control_alignment == 0.5,
        "checks": fields,
        "policy_target_alignment_rate": {
            "treatment": treatment_alignment,
            "control": control_alignment,
        },
        "treatment_token_profile": treatment_tokens,
        "control_token_profile": control_tokens,
    }


def _memory_policy_pass(spec, reference):
    memory = spec.get("memory") or {}
    terms = [str(term) for term in memory.get("terms") or [] if str(term)]
    if spec["memory_mode"] == "explicit_allowed":
        return any(term in reference for term in terms)
    if spec["memory_mode"] in {"background_only", "do_not_mention"}:
        return not any(term in reference for term in terms)
    return spec["memory_mode"] == "no_memory"


def _collect_strings_by_key(value, keys):
    output = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, str) and item.strip():
                output.append(item.strip())
            output.extend(_collect_strings_by_key(item, keys))
    elif isinstance(value, list):
        for item in value:
            output.extend(_collect_strings_by_key(item, keys))
    return output


def _separation_sources(treatment):
    prior_inputs = set()
    prior_payloads = {role_message(row, "user") for row in treatment}
    prior_targets = {assistant_target(row) for row in treatment}

    curriculum_specs = load_json(curriculum.DEFAULT_SPECS)
    prior_inputs.update(str(case["user_input"]) for case in curriculum_specs["cases"])
    development_paths = (
        ROOT / "configs/persona_policy_local_model_pilot_v1_cases.json",
        ROOT / "datasets/public_persona_contract_v3_development.json",
    )
    for path in development_paths:
        value = load_json(path)
        prior_inputs.update(_collect_strings_by_key(value, {"user_input"}))
        prior_targets.update(
            _collect_strings_by_key(
                value,
                {"reply", "response", "target_reply", "assistant_reply"},
            )
        )
    result_path = ROOT / "reports/persona_policy_local_model_pilot_v1_result.json"
    prior_targets.update(
        _collect_strings_by_key(
            load_json(result_path),
            {"raw_generation", "visible_reply"},
        )
    )
    curriculum_preregistration = load_json(curriculum.DEFAULT_PREREGISTRATION)
    historical_training_targets, historical_training_rows = curriculum._old_training_targets(
        curriculum_preregistration
    )
    prior_model_outputs, prior_model_output_bindings = curriculum._existing_development_outputs()
    prior_targets.update(historical_training_targets)
    prior_targets.update(prior_model_outputs)
    separation_bindings = [
        curriculum.file_binding(curriculum.DEFAULT_PREREGISTRATION),
        *[
            curriculum.file_binding(ROOT / source["path"])
            for source in curriculum_preregistration["frozen_inputs"]["excluded_training_targets"]
        ],
        *prior_model_output_bindings,
    ]
    return (
        prior_inputs,
        prior_payloads,
        prior_targets,
        historical_training_rows,
        separation_bindings,
    )


def audit_holdout(bundle, treatment):
    cases = list(bundle.get("cases") or [])
    (
        prior_inputs,
        prior_payloads,
        prior_targets,
        historical_training_rows,
        separation_bindings,
    ) = _separation_sources(treatment)
    prior_normalized_inputs = {normalized_text(value) for value in prior_inputs}
    prior_normalized_targets = {normalized_text(value) for value in prior_targets}
    exact_input_overlap = normalized_input_overlap = exact_payload_overlap = 0
    exact_reference_overlap = normalized_reference_overlap = 0
    target_identity_count = benchmark_key_count = 0
    reference_count = reference_gate_count = persona_v4_pass = specificity_pass = 0
    memory_policy_pass = semantic_pass = forbidden_pass = casual_japanese_pass = 0
    payloads = []
    matched_payload_pass_count = 0
    references = []
    failures = []
    matrix = Counter()

    for spec in cases:
        matrix[(spec["context"], spec["memory_mode"])] += 1
        exact_input_overlap += int(spec["user_input"] in prior_inputs)
        normalized_input_overlap += int(normalized_text(spec["user_input"]) in prior_normalized_inputs)
        logic = curriculum.logic_from_spec(spec)
        matched_payloads = {}
        matched_instructions = {}
        for provider_id in PROVIDERS:
            payload, instruction = curriculum.build_payload(logic, spec["context"], provider_id)
            matched_payloads[provider_id] = copy.deepcopy(payload)
            matched_instructions[provider_id] = instruction
            payload_text = canonical_json(payload)
            payloads.append(payload_text)
            exact_payload_overlap += int(payload_text in prior_payloads)
            reference = str(spec["policy_references"][provider_id]).strip()
            references.append(reference)
            reference_count += 1
            exact_reference_overlap += int(reference in prior_targets)
            normalized_reference_overlap += int(normalized_text(reference) in prior_normalized_targets)
            target_identity_count += sum(marker.lower() in reference.lower() for marker in TARGET_IDENTITY_MARKERS)

            missing = [
                group
                for group in spec["required_marker_groups"]
                if not any(marker in reference for marker in group)
            ]
            forbidden = [
                marker
                for marker in payload.get("forbidden_markers") or []
                if marker and marker in reference
            ]
            semantic_ok = not missing
            forbidden_ok = not forbidden
            memory_ok = _memory_policy_pass(spec, reference)
            casual_ok = bool(JAPANESE_RE.search(reference)) and not LATIN_RE.search(reference) and not any(
                marker in reference for marker in POLITE_MARKERS
            )
            rightbrain = curriculum.brain_module.RightBrain(
                load_model=False,
                persona_policy_provider=persona_policy.build_persona_policy_provider(provider_id),
            )
            rightbrain.structured_payload_mode = curriculum.surface_payload.LEGACY_JSON_V1
            rightbrain.surface_watchlist_enabled = False
            rightbrain.explicit_length_contract_enabled = False
            rightbrain.memory_cue_canonicalization_enabled = False
            rightbrain.forbidden_conflict_projection_enabled = False
            rejection_reasons = rightbrain._model_candidate_rejection_reasons(
                reference,
                logic,
                int(spec["max_chars"]),
                user_input=spec["user_input"],
            )
            gate_ok = not rejection_reasons
            v4 = persona_scorer.score_reply(
                reference,
                persona_scorer.compile_scorer_contract(spec["context"]),
            )
            specificity = specificity_scorer.score_specificity(
                reference,
                {"context": spec["context"], "logic": logic},
            )
            semantic_pass += semantic_ok
            forbidden_pass += forbidden_ok
            memory_policy_pass += memory_ok
            casual_japanese_pass += casual_ok
            reference_gate_count += gate_ok
            persona_v4_pass += bool(v4["passed"])
            specificity_pass += bool(specificity["passed"])
            if not all((semantic_ok, forbidden_ok, memory_ok, casual_ok, gate_ok, specificity["passed"])):
                failures.append(
                    {
                        "case_id": spec["case_id"],
                        "provider_id": provider_id,
                        "missing_groups": missing,
                        "forbidden_hits": forbidden,
                        "memory_policy_pass": memory_ok,
                        "casual_japanese_pass": casual_ok,
                        "runtime_rejection_reasons": rejection_reasons,
                        "specificity": specificity,
                    }
                )
        target_payload = matched_payloads[persona_policy.TARGET_PROVIDER]
        neutral_payload = matched_payloads[persona_policy.NEUTRAL_PROVIDER]
        target_brief = target_payload["context"].pop("persona_expression_brief")
        neutral_brief = neutral_payload["context"].pop("persona_expression_brief")
        matched_payload_pass_count += int(
            target_brief != neutral_brief
            and target_payload == neutral_payload
            and matched_instructions[persona_policy.TARGET_PROVIDER]
            == matched_instructions[persona_policy.NEUTRAL_PROVIDER]
        )

    benchmark_key_count = _contains_forbidden_key(bundle)
    context_counts = Counter(case["context"] for case in cases)
    memory_counts = Counter(case["memory_mode"] for case in cases)
    checks = {
        "case_count": len(cases) == 20,
        "unique_case_ids": len({case["case_id"] for case in cases}) == 20,
        "context_balance": len(context_counts) == 5 and set(context_counts.values()) == {4},
        "memory_mode_balance": len(memory_counts) == 4 and set(memory_counts.values()) == {5},
        "full_context_memory_matrix": len(matrix) == 20 and set(matrix.values()) == {1},
        "two_policy_references_per_case": reference_count == 40,
        "references_are_unique": len({normalized_text(value) for value in references}) == 40,
        "matched_provider_payloads_differ_only_by_persona_policy": matched_payload_pass_count
        == len(cases),
        "reference_semantic_contract": semantic_pass == reference_count,
        "reference_forbidden_contract": forbidden_pass == reference_count,
        "reference_memory_policy": memory_policy_pass == reference_count,
        "reference_casual_japanese": casual_japanese_pass == reference_count,
        "reference_runtime_candidate_gate": reference_gate_count == reference_count,
        "reference_specificity_gate": specificity_pass == reference_count,
        "exact_user_input_overlap": exact_input_overlap == 0,
        "normalized_user_input_overlap": normalized_input_overlap == 0,
        "exact_payload_overlap": exact_payload_overlap == 0,
        "exact_reference_overlap": exact_reference_overlap == 0,
        "normalized_reference_overlap": normalized_reference_overlap == 0,
        "target_identity_markers": target_identity_count == 0,
        "benchmark_or_answer_key_fields": benchmark_key_count == 0,
        "provenance": bundle.get("contains_target_person_utterances") is False
        and bundle.get("contains_official_benchmark_items") is False
        and bundle.get("contains_exact_expected_chat_reply") is False
        and bundle.get("training_authorized") is False,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "counts": {
            "case_count": len(cases),
            "reference_count": reference_count,
            "unique_normalized_reference_count": len({normalized_text(value) for value in references}),
            "runtime_candidate_gate_pass_count": reference_gate_count,
            "public_persona_v4_contract_pass_count_descriptive_only": persona_v4_pass,
            "specificity_pass_count": specificity_pass,
            "matched_provider_payload_pair_count": matched_payload_pass_count,
            "exact_user_input_overlap_count": exact_input_overlap,
            "normalized_user_input_overlap_count": normalized_input_overlap,
            "exact_payload_overlap_count": exact_payload_overlap,
            "exact_reference_overlap_count": exact_reference_overlap,
            "normalized_reference_overlap_count": normalized_reference_overlap,
            "target_identity_marker_count": target_identity_count,
            "benchmark_or_answer_key_field_count": benchmark_key_count,
            "historical_training_target_row_count_checked": historical_training_rows,
            "prior_target_or_model_output_count_checked": len(prior_targets),
        },
        "context_counts": dict(sorted(context_counts.items())),
        "memory_mode_counts": dict(sorted(memory_counts.items())),
        "failures": failures,
        "separation_source_bindings": separation_bindings,
    }


def validate_frozen_inputs(preregistration):
    reports = []

    def check(path, expected):
        actual = sha256_file(path) if Path(path).is_file() else None
        reports.append(
            {
                "path": str(Path(path)),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "match": actual == expected,
            }
        )

    prior = preregistration["prior_authorization"]
    check(ROOT / prior["path"], prior["sha256"])
    source = preregistration["matched_training_data_contract"]["treatment_source"]
    check(ROOT / source["path"], source["sha256"])
    model = preregistration["local_model_contract"]
    snapshot = Path(model["snapshot_root"])
    for name, expected in model["snapshot_files"].items():
        check(snapshot / name, expected)
    adapter = ROOT / model["initial_adapter"]["path"]
    check(adapter / "adapter_config.json", model["initial_adapter"]["adapter_config_sha256"])
    check(adapter / "adapter_model.safetensors", model["initial_adapter"]["adapter_model_sha256"])
    return {"passed": all(row["match"] for row in reports), "bindings": reports}


def builder_source_boundary():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden = sorted(calls.intersection({"backward", "fit", "generate", "train"}))
    return {"passed": not forbidden, "forbidden_calls": forbidden}


def build_report(preregistration, treatment, control, holdout, tokenizer):
    frozen = validate_frozen_inputs(preregistration)
    matched = audit_matched_training_data(treatment, control, tokenizer, preregistration)
    heldout = audit_holdout(holdout, treatment)
    source_boundary = builder_source_boundary()
    passed = frozen["passed"] and matched["passed"] and heldout["passed"] and source_boundary["passed"]
    return {
        "schema": "uruha_rightbrain_role_curriculum_training_pilot_construction_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "construction_passed" if passed else "construction_failed",
        "inputs": {
            "preregistration": file_binding(DEFAULT_PREREGISTRATION),
            "treatment": file_binding(DEFAULT_TREATMENT),
            "holdout": file_binding(DEFAULT_HOLDOUT),
        },
        "outputs": {"control": file_binding(DEFAULT_CONTROL)},
        "frozen_input_validation": frozen,
        "matched_training_data": matched,
        "heldout_evaluation": heldout,
        "builder_source_boundary": source_boundary,
        "decision": {
            "outcome": (
                "authorize_execution_harness_lock_construction_only"
                if passed
                else "reject_training_pilot_construction"
            ),
            "authorize_execution_harness_lock_construction": passed,
            "authorize_model_training": False,
            "authorize_production_change": False,
            "persona_similarity_claim": False,
            "causal_claim_supported": False,
            "reason_zh": (
                "控制組與處理組的資料量、文字集合及 token 預算完全相同，獨立 holdout 與既有資料零重疊；可鎖定執行器，但本輪尚未訓練。"
                if passed
                else "資料等量、來源隔離或候選契約未通過，禁止進入模型訓練。"
            ),
        },
    }


def render_markdown(report):
    matched = report["matched_training_data"]
    heldout = report["heldout_evaluation"]
    lines = [
        "# RightBrain 角色課程公平訓練試驗：建構結果",
        "",
        f"- 狀態：`{report['status']}`",
        f"- 決策：`{report['decision']['outcome']}`",
        "- 本輪模型訓練：`0`",
        "- 正式 runtime 修改：`0`",
        "",
        "## 唯一變因",
        "",
        "兩個訓練組都看到同樣 80 筆輸入、同一組 80 個回答、相同 token 與相同訓練步數。唯一差別是人格政策與回答風格是否保持正確對應。",
        "",
        "| 條件 | 政策對應率 | 筆數 | prompt tokens | completion tokens |",
        "|---|---:|---:|---:|---:|",
        (
            "| 打散控制組 | 50% | {rows} | {prompt} | {completion} |".format(
                rows=matched["control_token_profile"]["row_count"],
                prompt=matched["control_token_profile"]["total_prompt_tokens"],
                completion=matched["control_token_profile"]["total_completion_tokens"],
            )
        ),
        (
            "| 正確處理組 | 100% | {rows} | {prompt} | {completion} |".format(
                rows=matched["treatment_token_profile"]["row_count"],
                prompt=matched["treatment_token_profile"]["total_prompt_tokens"],
                completion=matched["treatment_token_profile"]["total_completion_tokens"],
            )
        ),
        "",
        "## 獨立 Holdout",
        "",
        f"- 全新開放式案例：`{heldout['counts']['case_count']}`",
        f"- 政策判別參考回答：`{heldout['counts']['reference_count']}`",
        f"- 與訓練/既有開發輸入重疊：`{heldout['counts']['normalized_user_input_overlap_count']}`",
        f"- 與訓練/既有輸出重疊：`{heldout['counts']['normalized_reference_overlap_count']}`",
        f"- 正式候選閘門通過：`{heldout['counts']['runtime_candidate_gate_pass_count']}/{heldout['counts']['reference_count']}`",
        "",
        "## 證據邊界",
        "",
        report["decision"]["reason_zh"],
        "即使未來訓練通過，也只可進入小型盲評；不能宣稱已複製特定人物，也不能直接上線。",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--treatment", default=str(DEFAULT_TREATMENT))
    parser.add_argument("--control", default=str(DEFAULT_CONTROL))
    parser.add_argument("--holdout", default=str(DEFAULT_HOLDOUT))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    preregistration = load_json(args.preregistration)
    if preregistration["experiment_id"] != EXPERIMENT_ID:
        raise RuntimeError("Unexpected preregistration experiment id")
    treatment = load_json(args.treatment)
    control = build_policy_permuted_control(treatment)
    holdout = load_json(args.holdout)
    if not args.check:
        atomic_json(args.control, control)
    tokenizer = AutoTokenizer.from_pretrained(
        preregistration["local_model_contract"]["snapshot_root"],
        trust_remote_code=True,
        local_files_only=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    report = build_report(preregistration, treatment, control, holdout, tokenizer)
    rendered = render_markdown(report)
    if args.check:
        existing_control = load_json(args.control)
        existing_report = load_json(args.report_json)
        existing_markdown = Path(args.report_md).read_text(encoding="utf-8").rstrip()
        if (
            existing_control != control
            or existing_report != report
            or existing_markdown != rendered.rstrip()
        ):
            raise RuntimeError("Committed construction artifacts are stale")
    else:
        atomic_json(args.report_json, report)
        atomic_text(args.report_md, rendered)
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))
    if not report["decision"]["authorize_execution_harness_lock_construction"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
