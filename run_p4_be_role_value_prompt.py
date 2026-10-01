#!/usr/bin/env python3
"""One-shot paired P4-BE prompt study; offline evidence, never product runtime.

Both arms use the frozen P4-BC schema, normalizer, and P4-BB compiler on the
same 14 new source cases. The only producer intervention is the system prompt's
evidence-role guidance. This runner must be committed before formal model calls.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import urllib.request

import p4_be_role_value_scoring as scoring
import rightbrain_language_quality as language
import run_p4_bc_raw_dialogue_typed_spec as bc
import uruha_typed_action_compiler_p4 as compiler


ROOT = Path(__file__).resolve().parent
FREEZE_SHA = "90b4c4a"
DEFAULT_CONTRACT = ROOT / "configs/p4_be_role_value_prompt_v1.json"
DEFAULT_OUTPUT = ROOT / "analysis/p4_be_role_value_prompt_evidence_2026-09-29.json"
FROZEN_PATHS = (
    "analysis/p4_be_source_bound_role_prompt_design_review_2026-09-29.md",
    "configs/p4_be_role_value_prompt_v1.json",
    "configs/p4_be_role_value_prompt_v1.txt",
    "datasets/p4_be_role_value_prompt_v1.json",
    "p4_be_role_value_scoring.py",
    "test_p4_be_role_value_freeze.py",
    "test_p4_be_role_value_scoring.py",
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.load(response)


def preflight(contract_path: Path, output_path: Path) -> tuple[dict, dict, str]:
    """No scored request before all frozen-input, host, and one-shot checks."""
    if output_path.exists():
        raise RuntimeError(f"P4-BE output already exists; no rerun or overwrite: {output_path}")
    if output_path != DEFAULT_OUTPUT:
        raise RuntimeError("P4-BE formal run requires the single frozen output path")
    if contract_path != DEFAULT_CONTRACT:
        raise RuntimeError("P4-BE formal run requires the frozen default contract")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["status"] != "prospectively_frozen_before_model_execution":
        raise RuntimeError("P4-BE contract is not frozen")
    freeze_sha = _git("rev-parse", FREEZE_SHA)
    subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_SHA, "HEAD"], cwd=ROOT, check=True)
    _git("diff", "--exit-code", FREEZE_SHA, "--", *FROZEN_PATHS)
    _git("ls-files", "--error-unmatch", "run_p4_be_role_value_prompt.py")
    _git("ls-files", "--error-unmatch", "test_p4_be_role_value_runner.py")
    _git("diff", "--exit-code", "HEAD", "--", "run_p4_be_role_value_prompt.py", "test_p4_be_role_value_runner.py")
    for label in (
        "dataset", "baseline_prompt", "intervention_prompt", "role_value_scorer",
        "downstream_compiler", "read_only_p4_bc_runner",
    ):
        record = contract[label]
        if _hash(ROOT / record["path"]) != record["sha256"]:
            raise RuntimeError(f"P4-BE frozen {label} hash mismatch")
    dataset = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    if dataset["status"] != "sealed_before_model_execution":
        raise RuntimeError("P4-BE dataset is not sealed")
    if len(dataset["positive_cases"]) != 6 or len(dataset["control_cases"]) != 8:
        raise RuntimeError("P4-BE case count changed")
    if contract["model"] != "qwen3.5:9b" or contract["arms"] != ["bc_frozen_prompt", "be_role_value_prompt"]:
        raise RuntimeError("P4-BE model or arm changed")
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("P4-BE formal hardware changed")
    cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    memory_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    if cpu != "Apple M2 Pro" or memory_bytes != 34359738368:
        raise RuntimeError("P4-BE M2 Pro 32GB hardware gate mismatch")
    if not _get_json("http://127.0.0.1:11434/api/version").get("version"):
        raise RuntimeError("P4-BE Ollama version unavailable")
    tags = _get_json("http://127.0.0.1:11434/api/tags")
    digests = {row["name"]: row["digest"] for row in tags["models"]}
    if digests.get(contract["model"]) != contract["model_digest"]:
        raise RuntimeError("P4-BE model digest mismatch")
    return contract, dataset, freeze_sha


def _source_identity_valid(parsed: object, source: dict) -> bool:
    return bool(
        source.get("kind") == "current_user"
        and isinstance(parsed, dict)
        and parsed.get("source_id") == source.get("id")
        and parsed.get("source_span") == source.get("text")
    )


def _positive(case: dict, arm: str, prompt: str, contract: dict, dataset: dict) -> dict:
    source = deepcopy(case["source"])
    call = bc.model_json_call(
        model=contract["model"], prompt=prompt, source=source,
        schema=bc.output_schema(source, contract, dataset),
        contract=contract, call_id=f"positive:{arm}:{case['case_id']}",
    )
    parsed = call.get("parsed") if isinstance(call.get("parsed"), dict) else None
    spec, normalization = (
        bc.normalize_output(parsed, source) if parsed is not None
        else (None, {"status": "invalid", "reason": "json_unavailable"})
    )
    plan = trace = None
    if spec is not None:
        plan, trace = compiler.compile_typed_action_p4_bb(source, spec)
    expected = case["expected_spec"]
    raw_atoms = parsed.get("evidence_atoms") if parsed else None
    score = scoring.score_packet(case, spec, raw_atoms)
    identity_valid = _source_identity_valid(parsed, source)
    downstream_compiled = bool(plan and trace and trace.get("status") == "compiled")
    mechanism_exact = bool(
        plan and plan.get("progress_mechanism")
        == compiler.TEMPLATE_CONTRACTS[expected["template_id"]]["progress_mechanism"]
    )
    natural_japanese = bool(
        plan and language.has_japanese(plan.get("instruction_jp"))
        and not language.has_bad_language(plan.get("instruction_jp"))
    )
    full_accept = bool(
        spec is not None and identity_valid and spec.get("template_id") == expected["template_id"]
        and score["role_value_packet_exact"] and downstream_compiled
        and mechanism_exact and natural_japanese
    )
    return {
        "kind": "positive", "case_id": case["case_id"], "language": case["language"],
        "arm": arm, "model": contract["model"], "source_digest": bc.digest(source["text"]),
        "call": {key: value for key, value in call.items() if key != "parsed"},
        "raw_model_output": parsed, "normalization": normalization,
        "source_identity_valid": identity_valid,
        "observed_status": parsed.get("status") if parsed else None,
        "observed_template_id": parsed.get("template_id") if parsed else None,
        "observed_unavailable_reason": parsed.get("unavailable_reason") if parsed else None,
        "typed_spec": spec is not None,
        "exact_spec": spec == expected,
        "template_exact": bool(spec and spec.get("template_id") == expected["template_id"]),
        "evidence_exact": bool(spec and spec.get("evidence_atoms") == expected["evidence_atoms"]),
        "slots_exact": bool(spec and spec.get("slots") == expected["slots"]),
        "non_span_exact": score["non_span_exact"],
        "role_value_evidence": score["role_value_evidence"],
        "role_value_packet_exact": score["role_value_packet_exact"],
        "accepted_atom_count": score["accepted_atom_count"],
        "raw_role_value_evidence": score["raw_role_value_evidence"],
        "raw_accepted_atom_count": score["raw_accepted_atom_count"],
        "role_value_per_role": score["per_role"],
        "quote_boundary_diagnostic_count": sum(
            bool(detail.get("boundary_valid")) for detail in score["per_role"].values()
        ),
        "downstream_compiled": downstream_compiled,
        "downstream_mechanism_exact": mechanism_exact,
        "natural_japanese": natural_japanese,
        "full_accept": full_accept,
        "instruction_jp": plan.get("instruction_jp") if plan else None,
        "plan_digest": trace.get("plan_digest") if isinstance(trace, dict) else None,
        "assistant_or_private_source": bool(parsed and not identity_valid),
    }


def _control(case: dict, arm: str, prompt: str, contract: dict, dataset: dict) -> dict:
    source = deepcopy(case["source"])
    call = bc.model_json_call(
        model=contract["model"], prompt=prompt, source=source,
        schema=bc.output_schema(source, contract, dataset),
        contract=contract, call_id=f"control:{arm}:{case['case_id']}",
    )
    parsed = call.get("parsed") if isinstance(call.get("parsed"), dict) else None
    spec, normalization = (
        bc.normalize_output(parsed, source) if parsed is not None
        else (None, {"status": "invalid", "reason": "json_unavailable"})
    )
    reason = parsed.get("unavailable_reason") if parsed else None
    identity_valid = _source_identity_valid(parsed, source)
    return {
        "kind": "control", "case_id": case["case_id"], "language": case["language"],
        "arm": arm, "model": contract["model"], "source_digest": bc.digest(source["text"]),
        "call": {key: value for key, value in call.items() if key != "parsed"},
        "raw_model_output": parsed, "normalization": normalization,
        "source_identity_valid": identity_valid,
        "observed_status": parsed.get("status") if parsed else None,
        "observed_template_id": parsed.get("template_id") if parsed else None,
        "expected_unavailable_reason": case["expected_unavailable_reason"],
        "observed_unavailable_reason": reason,
        "unavailable": normalization.get("status") == "unavailable",
        "reason_exact": reason == case["expected_unavailable_reason"],
        "false_spec": spec is not None or bool(parsed and parsed.get("status") == "typed_spec"),
        "assistant_or_private_source": bool(parsed and not identity_valid),
    }


def summarize_arm(arm: str, rows: list[dict], contract: dict) -> dict:
    current = [row for row in rows if row["arm"] == arm]
    positives = [row for row in current if row["kind"] == "positive"]
    controls = [row for row in current if row["kind"] == "control"]
    calls = [row["call"] for row in current]
    times = [row["wall_seconds"] for row in calls if row.get("completed")]
    expected = contract["formal_gates_for_intervention"]
    token_complete = len(calls) == expected["case_count"] and all(
        call.get("completed")
        and isinstance(call.get("prompt_tokens"), int)
        and call["prompt_tokens"] > 0
        and isinstance(call.get("completion_tokens"), int)
        and call["completion_tokens"] > 0
        for call in calls
    )
    metrics = {
        "case_count": len(current),
        "json_parse_success_count": sum(row["call"].get("json_parse_success") is True for row in current),
        "positive_typed_spec_count": sum(row["typed_spec"] is True for row in positives),
        "positive_non_span_exact_count": sum(row["non_span_exact"] is True for row in positives),
        "positive_template_exact_count": sum(row["template_exact"] is True for row in positives),
        "positive_role_value_evidence_count": sum(row["role_value_evidence"] is True for row in positives),
        "positive_role_value_packet_count": sum(row["role_value_packet_exact"] is True for row in positives),
        "positive_accepted_atom_count": sum(row["accepted_atom_count"] for row in positives),
        "positive_slots_exact_count": sum(row["slots_exact"] is True for row in positives),
        "positive_downstream_compiled_count": sum(row["downstream_compiled"] is True for row in positives),
        "positive_downstream_mechanism_exact_count": sum(row["downstream_mechanism_exact"] is True for row in positives),
        "positive_natural_japanese_count": sum(row["natural_japanese"] is True for row in positives),
        "positive_full_accept_count": sum(row["full_accept"] is True for row in positives),
        "control_unavailable_count": sum(row["unavailable"] is True for row in controls),
        "control_reason_exact_count": sum(row["reason_exact"] is True for row in controls),
        "control_false_spec_count": sum(row["false_spec"] is True for row in controls),
        "assistant_or_private_source_count": sum(row["assistant_or_private_source"] is True for row in current),
        "token_accounting_complete": token_complete,
        "maximum_call_seconds": max(times) if times else None,
        "median_call_seconds": round(statistics.median(times), 5) if times else None,
        "prompt_tokens": sum(int(call.get("prompt_tokens") or 0) for call in calls),
        "completion_tokens": sum(int(call.get("completion_tokens") or 0) for call in calls),
        "strict_exact_spec_count": sum(row["exact_spec"] is True for row in positives),
        "strict_evidence_exact_count": sum(row["evidence_exact"] is True for row in positives),
        "raw_role_value_evidence_count": sum(row["raw_role_value_evidence"] is True for row in positives),
        "raw_accepted_atom_count": sum(row["raw_accepted_atom_count"] for row in positives),
        "quote_boundary_diagnostic_count": sum(row["quote_boundary_diagnostic_count"] for row in positives),
    }
    failed = []
    for key, value in expected.items():
        if key == "maximum_call_seconds":
            if metrics[key] is None or metrics[key] > value:
                failed.append(key)
        elif metrics[key] != value:
            failed.append(key)
    return {"arm": arm, "metrics": metrics, "failed_absolute_gates": failed, "absolute_eligible": not failed}


def compare_pairs(rows: list[dict], contract: dict) -> dict:
    cases = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    positives = [case["case_id"] for case in cases["positive_cases"]]
    by_key = {(row["arm"], row["case_id"]): row for row in rows if row["kind"] == "positive"}
    paired = []
    for case_id in positives:
        baseline = by_key.get(("bc_frozen_prompt", case_id))
        intervention = by_key.get(("be_role_value_prompt", case_id))
        if baseline is None or intervention is None:
            continue
        bc_full = baseline["full_accept"] is True
        be_full = intervention["full_accept"] is True
        both_identity_valid = baseline["source_identity_valid"] is True and intervention["source_identity_valid"] is True
        raw_role_uplift = bool(
            both_identity_valid
            and baseline["raw_role_value_evidence"] is False
            and intervention["raw_role_value_evidence"] is True
        )
        paired.append({
            "case_id": case_id, "bc_full_accept": bc_full, "be_full_accept": be_full,
            "bc_raw_role_value_evidence": baseline["raw_role_value_evidence"],
            "be_raw_role_value_evidence": intervention["raw_role_value_evidence"],
            "both_source_identities_valid": both_identity_valid,
            "be_only_raw_role_value_uplift": raw_role_uplift,
        })
    all_rows = [row for row in rows if row["arm"] in contract["arms"]]
    all_calls_interpretable = bool(
        len(all_rows) == contract["execution"]["max_scored_calls"]
        and all(row["call"].get("completed") is True and row["call"].get("json_parse_success") is True for row in all_rows)
    )
    metrics = {
        "bc_and_be_all_calls_completed_and_json_parseable": all_calls_interpretable,
        "be_only_full_accept": sum(item["be_full_accept"] and not item["bc_full_accept"] for item in paired),
        "bc_only_full_accept": sum(item["bc_full_accept"] and not item["be_full_accept"] for item in paired),
        "both_full_accept": sum(item["bc_full_accept"] and item["be_full_accept"] for item in paired),
        "both_full_fail": sum(not item["bc_full_accept"] and not item["be_full_accept"] for item in paired),
        "be_only_raw_role_value_evidence_with_both_source_identities_valid": sum(
            item["be_only_raw_role_value_uplift"] for item in paired
        ),
    }
    gates = contract["paired_advantage_gates"]
    failed = []
    if metrics["bc_and_be_all_calls_completed_and_json_parseable"] != gates["bc_and_be_all_calls_completed_and_json_parseable"]:
        failed.append("bc_and_be_all_calls_completed_and_json_parseable")
    if metrics["be_only_full_accept"] < gates["be_only_full_accept_minimum"]:
        failed.append("be_only_full_accept_minimum")
    if metrics["bc_only_full_accept"] > gates["bc_only_full_accept_maximum"]:
        failed.append("bc_only_full_accept_maximum")
    if (
        metrics["be_only_raw_role_value_evidence_with_both_source_identities_valid"]
        < gates["be_only_raw_role_value_evidence_with_both_source_identities_valid_minimum"]
    ):
        failed.append("be_only_raw_role_value_evidence_with_both_source_identities_valid_minimum")
    return {"pairs": paired, "metrics": metrics, "failed_paired_gates": failed, "paired_advantage": not failed}


def _checkpoint(path: Path, evidence: dict, *, first: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    if first:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".p4_be_", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def run(contract_path: Path = DEFAULT_CONTRACT, output_path: Path = DEFAULT_OUTPUT) -> dict:
    contract_path = contract_path.resolve()
    output_path = output_path.resolve()
    contract, dataset, freeze_sha = preflight(contract_path, output_path)
    prompts = {
        "bc_frozen_prompt": (ROOT / contract["baseline_prompt"]["path"]).read_text(encoding="utf-8"),
        "be_role_value_prompt": (ROOT / contract["intervention_prompt"]["path"]).read_text(encoding="utf-8"),
    }
    evidence = {
        "schema": "uruha_p4_be_role_value_prompt_evidence_v1",
        "status": "running_not_reusable",
        "freeze_sha": freeze_sha,
        "runner_sha256": _hash(Path(__file__)),
        "contract": {"path": str(contract_path.relative_to(ROOT)), "sha256": _hash(contract_path)},
        "dataset_sha256": contract["dataset"]["sha256"],
        "prompt_sha256_by_arm": {
            arm: hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            for arm, prompt in prompts.items()
        },
        "executed_exactly_once_per_arm_case": False,
        "retry_count": 0, "prewarm": [], "rows": [], "arms": [], "comparison": None,
        "selected_prompt": None, "product_runtime_changed": False,
        "claim_boundary": contract["claim_boundary"],
    }
    _checkpoint(output_path, evidence, first=True)
    prewarm = bc.prewarm_model(contract["model"], contract["controlled_constants"]["keep_alive"])
    evidence["prewarm"].append(prewarm)
    _checkpoint(output_path, evidence)
    if not prewarm.get("completed"):
        evidence["status"] = "prewarm_failed_no_scored_calls"
        _checkpoint(output_path, evidence)
        return evidence
    cases = [("positive", case) for case in dataset["positive_cases"]] + [
        ("control", case) for case in dataset["control_cases"]
    ]
    for index, (kind, case) in enumerate(cases):
        order = contract["arms"] if index % 2 == 0 else list(reversed(contract["arms"]))
        for arm in order:
            row = (
                _positive(case, arm, prompts[arm], contract, dataset)
                if kind == "positive"
                else _control(case, arm, prompts[arm], contract, dataset)
            )
            row["case_order_index"] = index
            row["arm_order_index"] = order.index(arm)
            evidence["rows"].append(row)
            _checkpoint(output_path, evidence)
    evidence["arms"] = [summarize_arm(arm, evidence["rows"], contract) for arm in contract["arms"]]
    evidence["comparison"] = compare_pairs(evidence["rows"], contract)
    candidate = next(item for item in evidence["arms"] if item["arm"] == "be_role_value_prompt")
    evidence["executed_exactly_once_per_arm_case"] = bool(
        len(evidence["rows"]) == contract["execution"]["max_scored_calls"]
        and len({row["call"]["call_id"] for row in evidence["rows"]}) == contract["execution"]["max_scored_calls"]
    )
    passed = bool(
        candidate["absolute_eligible"]
        and evidence["comparison"]["paired_advantage"]
        and evidence["executed_exactly_once_per_arm_case"]
    )
    evidence["selected_prompt"] = "be_role_value_prompt" if passed else None
    evidence["status"] = "pass_bounded_offline" if passed else "fail"
    evidence["next_state_if_failed"] = None if passed else contract["failure_policy"]["if_intervention_fails_next_state"]
    _checkpoint(output_path, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    evidence = run(args.contract, args.output)
    print(json.dumps({
        "status": evidence["status"], "selected_prompt": evidence["selected_prompt"],
        "arms": evidence["arms"], "comparison": evidence["comparison"],
        "rows": len(evidence["rows"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
