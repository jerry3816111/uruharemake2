import argparse
import hashlib
import json
import os
import time
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_MODEL_GATE_DATASET_PATH,
    RIGHTBRAIN_MODEL_GATE_REPORT_JSON_PATH,
)


TZ = ZoneInfo("Asia/Tokyo")
MEMORY = {
    "wisdom": "",
    "episodes": "",
    "profile": "",
    "recent_dialogue": "",
    "working_memory_summary": "",
    "working_memory_items": [],
    "recent_turns": [],
    "profile_structured": {},
}
PSYCHE = {"mood": 0, "trust": 50}


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _summarize(rows):
    enabled_rows = [row for row in rows if row["actual_model_policy"] == "allow"]
    generated = sum(row["generated_candidate_count"] for row in enabled_rows)
    accepted = sum(row["accepted_candidate_count"] for row in enabled_rows)
    rejected_rows = [row for row in enabled_rows if row["generated_candidate_count"] and not row["accepted_candidate_count"]]
    protected_rows = [row for row in rejected_rows if row["final_contract_pass"] and row["final_language_clean"]]
    return {
        "case_count": len(rows),
        "model_enabled_case_count": len(enabled_rows),
        "policy_match_rate": _safe_rate(sum(row["policy_match"] for row in rows), len(rows)),
        "generated_candidate_count": generated,
        "accepted_candidate_count": accepted,
        "raw_candidate_acceptance_rate": _safe_rate(accepted, generated),
        "model_selected_case_count": sum(row["selected_source"] == "model" for row in rows),
        "model_selected_case_rate": _safe_rate(sum(row["selected_source"] == "model" for row in rows), len(enabled_rows)),
        "final_contract_pass_rate": _safe_rate(sum(row["final_contract_pass"] for row in rows), len(rows)),
        "final_language_clean_rate": _safe_rate(sum(row["final_language_clean"] for row in rows), len(rows)),
        "fallback_protection_rate": _safe_rate(len(protected_rows), len(rejected_rows)),
        "deterministic_contract_pass_rate": _safe_rate(sum(row["deterministic_contract_pass"] for row in rows), len(rows)),
        "rejection_reason_counts": dict(
            Counter(reason for row in rows for reason in row["rejection_reasons"])
        ),
        "disabled_reason_counts": dict(Counter(row["disabled_reason"] for row in rows if row["disabled_reason"])),
    }


def _write_markdown(report, output_path):
    summary = report["summary"]
    lines = [
        "# RightBrain Model Candidate Gate Report",
        "",
        "這份報告測真實 LoRA 候選是否遵守左腦語意契約，以及不合格時 deterministic 回覆能否保護最終輸出。它不等同真人自然度。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Cases", ""])
    for row in report["cases"]:
        lines.extend(
            [
                f"### {row['id']}",
                f"- input: {row['input']}",
                f"- policy: {row['actual_model_policy']} / expected {row['expected_model_policy']}",
                f"- model: generated={row['generated_candidate_count']} accepted={row['accepted_candidate_count']} selected={row['selected_source']}",
                f"- rejection_reasons: {row['rejection_reasons']}",
                f"- deterministic_reply: {row['deterministic_reply']}",
                f"- final_reply: {row['final_reply']}",
                "",
            ]
        )
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_MODEL_GATE_DATASET_PATH)
    parser.add_argument("--report", default=RIGHTBRAIN_MODEL_GATE_REPORT_JSON_PATH)
    parser.add_argument("--report-md", default="")
    parser.add_argument("--adapter-path", default=os.getenv("URUHA_RIGHT_BRAIN_ADAPTER_PATH", ""))
    parser.add_argument("--base-only", action="store_true", help="Evaluate the base model without a LoRA adapter.")
    parser.add_argument("--candidate-count", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260621)
    args = parser.parse_args()
    report_md_path = args.report_md or str(Path(args.report).with_suffix(".md"))

    if args.base_only:
        os.environ["URUHA_RIGHT_BRAIN_ADAPTER_PATH"] = "base-only"
    elif args.adapter_path:
        os.environ["URUHA_RIGHT_BRAIN_ADAPTER_PATH"] = os.path.abspath(args.adapter_path)
    os.environ["URUHA_RIGHT_BRAIN_MODEL_CANDIDATE_COUNT"] = str(max(1, args.candidate_count))
    os.environ["URUHA_RIGHT_BRAIN_MODEL_BLEND_ENABLED"] = "1"
    os.environ["URUHA_SKIP_AUTO_VENV"] = "1"

    import torch
    from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, LeftBrain, RightBrain

    torch.manual_seed(args.seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(args.seed)

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    started_at = time.time()
    left = LeftBrain(None)
    deterministic_right = RightBrain(load_model=False)
    model_right = RightBrain(load_model=True)
    rows = []
    for case in dataset.get("cases") or []:
        # Each item is an independent paired trial; previous generated replies must not leak across cases.
        deterministic_right.history = []
        model_right.history = []
        base_logic = left._rule_based_plan(case["input"], PSYCHE, MEMORY) or left._fallback_plan()
        deterministic_logic = deepcopy(base_logic)
        model_logic = deepcopy(base_logic)
        deterministic_reply = deterministic_right.speak(case["input"], deterministic_logic, MEMORY, PSYCHE)
        final_reply = model_right.speak(case["input"], model_logic, MEMORY, PSYCHE)
        trace = model_logic.get("model_surface_candidate_trace") or {}
        selection = model_logic.get("model_surface_selection") or {}
        disabled_reason = trace.get("disabled_reason") or ""
        actual_policy = "deny" if disabled_reason else "allow"
        expected_policy = case.get("expected_model_policy") or "allow"
        expected_reason = case.get("expected_disabled_reason") or ""
        policy_match = actual_policy == expected_policy and (
            expected_policy != "deny" or disabled_reason == expected_reason
        )
        model_groups = model_right._model_required_semantic_groups(model_logic)
        final_hits = [any(marker and marker in final_reply for marker in group) for group in model_groups]
        deterministic_hits = [any(marker and marker in deterministic_reply for marker in group) for group in model_groups]
        final_reasons = model_right._model_candidate_rejection_reasons(
            final_reply,
            model_logic,
            model_logic.get("constraints", {}).get("max_chars", 48),
            user_input=case["input"],
        )
        rejection_reasons = [
            reason for item in trace.get("rejected") or [] for reason in item.get("rejection_reasons") or []
        ]
        rows.append(
            {
                "id": case["id"],
                "input": case["input"],
                "intent": model_logic.get("intent"),
                "surface_act": model_logic.get("surface_act"),
                "expected_model_policy": expected_policy,
                "actual_model_policy": actual_policy,
                "disabled_reason": disabled_reason,
                "policy_match": policy_match,
                "contract_version": trace.get("contract_version"),
                "semantic_contract": [list(group) for group in model_groups],
                "generated_candidate_count": len(trace.get("accepted") or []) + len(trace.get("rejected") or []),
                "accepted_candidate_count": len(trace.get("accepted") or []),
                "accepted_candidates": trace.get("accepted") or [],
                "rejected_candidates": trace.get("rejected") or [],
                "rejection_reasons": rejection_reasons,
                "selected_source": selection.get("selected_source") or "deterministic",
                "deterministic_reply": deterministic_reply,
                "final_reply": final_reply,
                "deterministic_contract_pass": not model_groups or all(deterministic_hits),
                "final_contract_pass": not model_groups or all(final_hits),
                "final_language_clean": not any(
                    reason in {"cjk_language_leak", "unexpected_ascii_leak", "instruction_or_plan_leak"}
                    for reason in final_reasons
                ),
            }
        )

    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": dataset.get("scope"),
        "research_boundary": dataset.get("research_boundary"),
        "human_naturalness_claim_allowed": False,
        "dataset_version": dataset.get("version"),
        "dataset_sha256": _sha256(args.dataset),
        "adapter_ref": (
            "base_model_only"
            if args.base_only
            else os.path.basename(os.path.abspath(args.adapter_path)) if args.adapter_path else "configured_default"
        ),
        "adapter_config_sha256": (
            _sha256(os.path.join(args.adapter_path, "adapter_config.json"))
            if args.adapter_path and not args.base_only
            else None
        ),
        "case_state_reset": True,
        "runtime_contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "candidate_count_per_enabled_case": max(1, args.candidate_count),
        "seed": args.seed,
        "duration_seconds": round(time.time() - started_at, 3),
        "summary": _summarize(rows),
        "cases": rows,
    }
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, report_md_path)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    success = (
        report["summary"]["policy_match_rate"] == 1.0
        and report["summary"]["final_contract_pass_rate"] == 1.0
        and report["summary"]["final_language_clean_rate"] == 1.0
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
