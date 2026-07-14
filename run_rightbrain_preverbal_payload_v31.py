#!/usr/bin/env python3
"""Run one preregistered V31 RightBrain payload condition."""

import argparse
import hashlib
import json
import os
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from eval_rightbrain_model_surface_holdout import (
    TZ,
    _adapter_ref,
    _evaluate_surface_quality,
    _quality_pass,
    _selection_gap,
    _set_model_env,
    _summarize,
    write_markdown,
)
from rightbrain_on_policy_dev_cases_v29 import case_inputs, validate_cases
from rightbrain_preverbal_payload_v31 import CONDITION_FACTORS, build_payload_variant


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_preverbal_payload_v31_preregistration.json"
AMENDMENT_PATH = ROOT / "configs/rightbrain_preverbal_payload_v31_amendment.json"
CONTROL_BINDING_PATH = (
    ROOT / "configs/rightbrain_preverbal_payload_v31_control_binding.json"
)
ADAPTER_PATH = ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
SERIALIZER_PATH = ROOT / "rightbrain_preverbal_payload_v31.py"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_preregistration(path=PREREG_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_control_binding(path=CONTROL_BINDING_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cached_base_revision():
    ref = (
        Path.home()
        / ".cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/refs/main"
    )
    return ref.read_text(encoding="utf-8").strip() if ref.is_file() else ""


def verify_frozen_sources(preregistration, control_binding, root=ROOT):
    frozen = preregistration["frozen_inputs"]
    checks = {}
    for name in ("runtime", "evaluator", "case_module"):
        entry = frozen[name]
        path = Path(root) / entry["path"]
        checks[f"{name}_exists"] = path.is_file()
        checks[f"{name}_sha256_matches"] = (
            path.is_file() and sha256_file(path) == entry["sha256"]
        )
    adapter_config = Path(root) / frozen["adapter_ref"] / "adapter_config.json"
    adapter_model = Path(root) / frozen["adapter_ref"] / "adapter_model.safetensors"
    checks["adapter_config_sha256_matches"] = (
        adapter_config.is_file()
        and sha256_file(adapter_config) == frozen["adapter_config_sha256"]
    )
    checks["adapter_model_sha256_matches"] = (
        adapter_model.is_file()
        and sha256_file(adapter_model) == frozen["adapter_model_sha256"]
    )
    for entry in control_binding["frozen_v30_control_reports"]:
        path = Path(root) / entry["path"]
        checks[f"v30_control_seed_{entry['seed']}_sha256_matches"] = (
            path.is_file() and sha256_file(path) == entry["sha256"]
        )
    return checks


def _ordered_raw_candidates(case_row, candidate_count):
    ordered = [None] * candidate_count
    for rejected in case_row.get("model_initial_rejected_candidates") or []:
        index = int(rejected["candidate_index"])
        ordered[index] = str(rejected.get("raw_candidate") or "")
    accepted = [
        str(row.get("raw_candidate") or "")
        for row in case_row.get("model_accepted_candidates") or []
        if row.get("source") == "initial"
    ]
    accepted_iter = iter(accepted)
    for index, value in enumerate(ordered):
        if value is None:
            ordered[index] = next(accepted_iter, None)
    if any(value is None for value in ordered) or next(accepted_iter, None) is not None:
        raise ValueError(f"Cannot reconstruct candidate order for {case_row.get('id')}")
    return ordered


def compare_control_to_v30(report, control_binding, root=ROOT):
    seed = int(report["seed"])
    entry = next(
        row
        for row in control_binding["frozen_v30_control_reports"]
        if int(row["seed"]) == seed
    )
    frozen = json.loads((Path(root) / entry["path"]).read_text(encoding="utf-8"))
    candidate_count = int(report["candidate_count_per_case"])
    observed_rows = {row["id"]: row for row in report["cases"]}
    frozen_rows = {row["id"]: row for row in frozen["cases"]}
    mismatches = []
    if list(observed_rows) != list(frozen_rows):
        mismatches.append("case_ids_or_order")
    for case_id in sorted(set(observed_rows) & set(frozen_rows)):
        observed = _ordered_raw_candidates(observed_rows[case_id], candidate_count)
        expected = _ordered_raw_candidates(frozen_rows[case_id], candidate_count)
        if observed != expected:
            mismatches.append(case_id)
    return {
        "frozen_report_path": entry["path"],
        "frozen_report_sha256": entry["sha256"],
        "raw_candidate_sequences_match": not mismatches,
        "mismatches": mismatches,
    }


def _build_v31_rightbrain_class(base_class, condition):
    class V31PayloadRightBrain(base_class):
        def _build_model_surface_payload(
            self,
            logic_data,
            current_psyche,
            max_chars,
            memory_data=None,
        ):
            control_payload = super()._build_model_surface_payload(
                logic_data,
                current_psyche,
                max_chars,
                memory_data=memory_data,
            )
            variant = build_payload_variant(control_payload, condition)
            metadata = dict(variant.metadata)
            metadata["control_exact_text_matches"] = (
                variant.text == control_payload
                if condition == "mixed_json_control"
                else None
            )
            tokenized = self.tokenizer(
                variant.text,
                add_special_tokens=False,
            )["input_ids"]
            metadata["rendered_token_count"] = len(tokenized)
            metadata["representation_integrity_pass"] = bool(
                metadata["representation_integrity_pass"]
                and (
                    metadata["control_exact_text_matches"] is not False
                )
            )
            logic_data.setdefault("model_surface_candidate_trace", {})[
                "preverbal_payload_v31"
            ] = metadata
            return variant.text

    V31PayloadRightBrain.__name__ = f"V31PayloadRightBrain_{condition}"
    return V31PayloadRightBrain


def _summarize_payload(rows):
    missing_case_ids = [
        row["id"] for row in rows if not row.get("preverbal_payload_v31")
    ]
    traces = [
        row["preverbal_payload_v31"]
        for row in rows
        if row.get("preverbal_payload_v31")
    ]
    if not traces:
        return {
            "case_count": len(rows),
            "trace_count": 0,
            "missing_case_ids": missing_case_ids,
            "representation_integrity_pass_count": 0,
            "canonical_payload_unique_count": 0,
            "mean_character_count": None,
            "mean_token_count": None,
            "mean_ascii_letter_count": None,
        }
    return {
        "case_count": len(rows),
        "trace_count": len(traces),
        "missing_case_ids": missing_case_ids,
        "representation_integrity_pass_count": sum(
            bool(row["representation_integrity_pass"]) for row in traces
        ),
        "canonical_payload_unique_count": len(
            {row["canonical_payload_sha256"] for row in traces}
        ),
        "mean_character_count": round(
            sum(row["rendered_character_count"] for row in traces) / len(traces),
            2,
        ),
        "mean_token_count": round(
            sum(row["rendered_token_count"] for row in traces) / len(traces),
            2,
        ),
        "mean_ascii_letter_count": round(
            sum(row["rendered_ascii_letter_count"] for row in traces) / len(traces),
            2,
        ),
    }


def build_condition_report(condition, seed, preregistration=None, control_binding=None):
    if condition not in CONDITION_FACTORS:
        raise ValueError(f"Unknown V31 condition: {condition}")
    preregistration = preregistration or load_preregistration()
    control_binding = control_binding or load_control_binding()
    frozen = preregistration["frozen_inputs"]
    _set_model_env(
        adapter_path=str(ADAPTER_PATH),
        base_only=False,
        candidate_count=frozen["candidate_count_per_case"],
        repair_enabled=False,
    )
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    import torch

    torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)

    from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RightBrain

    V31RightBrain = _build_v31_rightbrain_class(RightBrain, condition)
    started_at = time.time()
    cases = case_inputs()
    deterministic_right = RightBrain(load_model=False)
    model_right = V31RightBrain(load_model=True)
    model_right.model_blend_enabled = True
    model_right.model_candidate_count = int(frozen["candidate_count_per_case"])
    model_right.model_repair_enabled = False
    model_ready_at = time.time()

    rows = []
    for case in cases:
        deterministic_right.history = []
        model_right.history = []
        deterministic_logic = deepcopy(case["logic"])
        model_logic = deepcopy(case["logic"])
        deterministic_reply = deterministic_right.speak(
            case["user_input"],
            deterministic_logic,
            deepcopy(case["memory_data"]),
            deepcopy(case["psyche"]),
        )
        final_reply = model_right.speak(
            case["user_input"],
            model_logic,
            deepcopy(case["memory_data"]),
            deepcopy(case["psyche"]),
        )
        trace = model_logic.get("model_surface_candidate_trace") or {}
        selection = model_logic.get("model_surface_selection") or {}
        rejection_reasons = [
            reason
            for item in trace.get("rejected") or []
            for reason in item.get("rejection_reasons") or []
        ]
        deterministic_quality = _evaluate_surface_quality(deterministic_reply, case)
        final_quality = _evaluate_surface_quality(final_reply, case)
        rows.append(
            {
                "id": case["id"],
                "source_family": case.get("source_family", ""),
                "category": case["category"],
                "user_input": case["user_input"],
                "preverbal_payload_v31": trace.get("preverbal_payload_v31") or {},
                "deterministic_reply": deterministic_reply,
                "final_reply": final_reply,
                "selected_source": selection.get("selected_source") or "deterministic",
                "model_surface_selection": selection,
                "model_selection_score_gap": _selection_gap(selection),
                "model_disabled_reason": trace.get("disabled_reason") or "",
                "generated_candidate_count": trace.get("initial_generated_count", 0),
                "initial_accepted_candidate_count": trace.get("initial_accepted_count", 0),
                "accepted_candidate_count": len(trace.get("accepted") or []),
                "repair_attempt_count": trace.get("repair_attempt_count", 0),
                "repair_accepted_count": trace.get("repair_accepted_count", 0),
                "model_accepted_candidates": trace.get("accepted") or [],
                "model_rejected_candidates": trace.get("rejected") or [],
                "model_initial_rejected_candidates": trace.get("initial_rejected") or [],
                "model_repair_attempts": trace.get("repairs") or [],
                "model_rejection_reasons": rejection_reasons,
                "deterministic_quality": deterministic_quality,
                "deterministic_quality_pass": _quality_pass(deterministic_quality),
                "final_quality": final_quality,
                "final_quality_pass": _quality_pass(final_quality),
            }
        )

    completed_at = time.time()
    summary = _summarize(rows, model_loaded=True)
    summary["payload"] = _summarize_payload(rows)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_preverbal_payload_v31",
        "condition": condition,
        "factors": CONDITION_FACTORS[condition],
        "research_boundary": preregistration["research_boundary"],
        "adapter_ref": _adapter_ref(str(ADAPTER_PATH)),
        "base_model": frozen["base_model"],
        "base_model_revision": _cached_base_revision(),
        "load_model": True,
        "seed": seed,
        "candidate_count_per_case": int(frozen["candidate_count_per_case"]),
        "repair_enabled": False,
        "runtime_contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "duration_seconds": round(completed_at - started_at, 3),
        "model_load_duration_seconds": round(model_ready_at - started_at, 3),
        "case_eval_duration_seconds": round(completed_at - model_ready_at, 3),
        "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
        "preregistration_sha256": sha256_file(PREREG_PATH),
        "amendment_path": str(AMENDMENT_PATH.relative_to(ROOT)),
        "amendment_sha256": sha256_file(AMENDMENT_PATH),
        "control_binding_path": str(CONTROL_BINDING_PATH.relative_to(ROOT)),
        "control_binding_sha256": sha256_file(CONTROL_BINDING_PATH),
        "runner_sha256": sha256_file(Path(__file__)),
        "serializer_sha256": sha256_file(SERIALIZER_PATH),
        "source_verification": verify_frozen_sources(
            preregistration,
            control_binding,
        ),
        "dev_case_validation": validate_cases(cases),
        "summary": summary,
        "cases": rows,
    }
    if condition == "mixed_json_control":
        report["control_reproduction"] = compare_control_to_v30(
            report,
            control_binding,
        )
    else:
        report["control_reproduction"] = {
            "not_applicable": True,
            "raw_candidate_sequences_match": True,
            "mismatches": [],
        }
    generated_counts = [row["generated_candidate_count"] for row in rows]
    payload_traces = [row["preverbal_payload_v31"] for row in rows]
    report["formal_run_gates"] = {
        "all_frozen_sources_match": all(report["source_verification"].values()),
        "base_model_revision_matches": report["base_model_revision"]
        == frozen["base_model_revision"],
        "adapter_matches": report["adapter_ref"] == frozen["adapter_ref"],
        "seed_is_preregistered": seed in frozen["seeds"],
        "case_validation_passes": report["dev_case_validation"]["valid"],
        "case_shape_matches": (
            len(rows) == frozen["case_count"]
            and all(
                count == frozen["candidate_count_per_case"]
                for count in generated_counts
            )
        ),
        "repair_disabled": report["repair_enabled"] is False,
        "all_representation_integrity_checks_pass": (
            len(payload_traces) == frozen["case_count"]
            and all(
                row.get("representation_integrity_pass") for row in payload_traces
            )
        ),
        "all_payloads_tokenized": all(
            int(row.get("rendered_token_count") or 0) > 0 for row in payload_traces
        ),
        "control_reproduces_v30": report["control_reproduction"][
            "raw_candidate_sequences_match"
        ],
    }
    report["formal_run_complete"] = all(report["formal_run_gates"].values())
    report["conclusion_zh"] = (
        f"{condition} 已依 V31 預註冊完成單一條件資料產生；"
        "本報告不單獨宣稱優劣，必須等四條件配對分析。"
    )
    return report


def default_output_path(condition, seed, suffix):
    return ROOT / "reports" / f"rightbrain_preverbal_payload_v31_{condition}_seed{seed}.{suffix}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=sorted(CONDITION_FACTORS), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args()
    preregistration = load_preregistration()
    if args.seed not in preregistration["frozen_inputs"]["seeds"]:
        raise SystemExit(f"Seed {args.seed} is not preregistered")
    report = build_condition_report(args.condition, args.seed, preregistration)
    output_json = (
        Path(args.output_json)
        if args.output_json
        else default_output_path(args.condition, args.seed, "json")
    )
    output_md = (
        Path(args.output_md)
        if args.output_md
        else default_output_path(args.condition, args.seed, "md")
    )
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, output_md)
    with output_md.open("a", encoding="utf-8") as handle:
        handle.write("\n## V31 condition\n\n")
        handle.write(f"- condition: `{args.condition}`\n")
        handle.write(f"- factors: `{json.dumps(report['factors'], ensure_ascii=False)}`\n")
        handle.write(
            f"- mean prompt tokens: `{report['summary']['payload']['mean_token_count']}`\n"
        )
        handle.write("\n## Formal gates\n\n")
        for name, value in report["formal_run_gates"].items():
            handle.write(f"- {name}: {value}\n")
    print(
        json.dumps(
            {
                "condition": args.condition,
                "seed": args.seed,
                "summary": report["summary"],
                "formal_run_complete": report["formal_run_complete"],
                "output_json": str(output_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["formal_run_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
