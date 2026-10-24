#!/usr/bin/env python3
"""One-shot P4-BD local model comparison after the 26fb898 freeze.

The sole scoring change from P4-BC is the prospectively enumerated role-aware
evidence boundary. The P4-BC prompt, dynamic schema, model call, normalizer,
P4-BB compiler, non-span gates, model options, and 20-second gate are reused.
The result is an offline developer-authored proxy, never a product integration.
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

import p4_bd_role_aware_scoring as scoring
import rightbrain_language_quality as language
import run_p4_bc_raw_dialogue_typed_spec as bc
import uruha_typed_action_compiler_p4 as compiler


ROOT = Path(__file__).resolve().parent
FREEZE_SHA = "26fb898"
DEFAULT_CONTRACT = ROOT / "configs/p4_bd_role_aware_evidence_v1.json"
DEFAULT_OUTPUT = ROOT / "analysis/p4_bd_role_aware_evidence_2026-09-29.json"
FROZEN_PATHS = (
    "configs/p4_bd_role_aware_evidence_v1.json",
    "datasets/p4_bd_role_aware_evidence_v1.json",
    "datasets/p4_bd_span_annotation_candidates_v1.json",
    "analysis/p4_bd_annotation_proxy_pre_freeze_2026-09-29.json",
    "p4_bd_role_aware_scoring.py",
    "test_p4_bd_role_aware_freeze.py",
    "test_p4_bd_role_aware_scoring.py",
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.load(response)


def preflight(contract_path: Path, output_path: Path) -> tuple[dict, dict, str]:
    """Reject changed frozen inputs, wrong model/hardware, or an existing run."""
    if output_path.exists():
        raise RuntimeError(f"P4-BD output already exists; no rerun or overwrite: {output_path}")
    if output_path != DEFAULT_OUTPUT:
        raise RuntimeError("P4-BD formal run requires the single frozen output path")
    if contract_path != DEFAULT_CONTRACT:
        raise RuntimeError("P4-BD formal run requires the frozen default contract")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["status"] != "prospectively_frozen_before_model_execution":
        raise RuntimeError("P4-BD contract is not frozen")
    freeze_full_sha = _git("rev-parse", FREEZE_SHA)
    subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_SHA, "HEAD"], cwd=ROOT, check=True)
    _git("diff", "--exit-code", FREEZE_SHA, "--", *FROZEN_PATHS)
    _git("ls-files", "--error-unmatch", "run_p4_bd_role_aware_evidence.py")
    _git("ls-files", "--error-unmatch", "test_p4_bd_role_aware_runner.py")
    _git("diff", "--exit-code", "HEAD", "--", "run_p4_bd_role_aware_evidence.py", "test_p4_bd_role_aware_runner.py")
    for label in (
        "dataset", "annotation_candidate_projection", "annotation_proxy_decisions",
        "span_scorer", "prompt", "downstream_compiler", "read_only_p4_bc_runner",
    ):
        record = contract[label]
        path = ROOT / record["path"]
        if _hash(path) != record["sha256"]:
            raise RuntimeError(f"P4-BD frozen {label} hash mismatch")
    dataset = json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))
    if dataset["status"] != "sealed_before_model_execution":
        raise RuntimeError("P4-BD dataset is not sealed")
    if len(dataset["positive_cases"]) != 6 or len(dataset["control_cases"]) != 8:
        raise RuntimeError("P4-BD scored case count changed")
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("P4-BD formal hardware changed")
    cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    memory_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    if cpu != "Apple M2 Pro" or memory_bytes != 34359738368:
        raise RuntimeError("P4-BD M2 Pro 32GB hardware gate mismatch")
    if not _get_json("http://127.0.0.1:11434/api/version").get("version"):
        raise RuntimeError("P4-BD Ollama version unavailable")
    tags = _get_json("http://127.0.0.1:11434/api/tags")
    observed_models = {model["name"]: model["digest"] for model in tags["models"]}
    for model, expected_digest in contract["model_digests"].items():
        if observed_models.get(model) != expected_digest:
            raise RuntimeError(f"P4-BD model digest mismatch: {model}")
    return contract, dataset, freeze_full_sha


def _source_violation(parsed: object, source: dict) -> bool:
    """Conservative observed identity check; bounded dynamic enums remain in force."""
    if source.get("kind") != "current_user":
        return True
    if not isinstance(parsed, dict):
        return False  # JSON/normalization gates fail independently
    return parsed.get("source_id") != source["id"] or parsed.get("source_span") != source["text"]


def positive_record(case: dict, model: str, prompt: str, contract: dict, dataset: dict) -> dict:
    source = deepcopy(case["source"])
    call = bc.model_json_call(
        model=model, prompt=prompt, source=source,
        schema=bc.output_schema(source, contract, dataset),
        contract=contract, call_id=f"positive:{model}:{case['case_id']}",
    )
    parsed = call.get("parsed") if isinstance(call.get("parsed"), dict) else None
    spec, normalization = (
        bc.normalize_output(parsed, source) if parsed is not None
        else (None, {"status": "invalid", "reason": "json_unavailable"})
    )
    expected = case["expected_spec"]
    plan = trace = None
    if spec is not None:
        plan, trace = compiler.compile_typed_action_p4_bb(source, spec)
    raw_atoms = parsed.get("evidence_atoms") if parsed else None
    span = scoring.score_packet(case, spec, raw_atoms)
    return {
        "kind": "positive", "case_id": case["case_id"], "language": case["language"],
        "model": model, "source_digest": bc.digest(source["text"]),
        "call": {key: value for key, value in call.items() if key != "parsed"},
        "raw_model_output": parsed,
        "normalization": normalization,
        "observed_status": parsed.get("status") if parsed else None,
        "observed_template_id": parsed.get("template_id") if parsed else None,
        "observed_unavailable_reason": parsed.get("unavailable_reason") if parsed else None,
        "typed_spec": spec is not None,
        "exact_spec": spec == expected,
        "template_exact": bool(spec and spec.get("template_id") == expected["template_id"]),
        "evidence_exact": bool(spec and spec.get("evidence_atoms") == expected["evidence_atoms"]),
        "slots_exact": bool(spec and spec.get("slots") == expected["slots"]),
        "non_span_exact": span["non_span_exact"],
        "role_aware_evidence": span["role_aware_evidence"],
        "role_aware_packet_exact": span["role_aware_packet_exact"],
        "role_aware_accepted_atom_count": span["accepted_atom_count"],
        "raw_role_aware_evidence": span["raw_role_aware_evidence"],
        "raw_role_aware_accepted_atom_count": span["raw_accepted_atom_count"],
        "role_aware_per_role": span["per_role"],
        "downstream_compiled": bool(plan and trace and trace.get("status") == "compiled"),
        "downstream_mechanism_exact": bool(
            plan and plan.get("progress_mechanism")
            == compiler.TEMPLATE_CONTRACTS[expected["template_id"]]["progress_mechanism"]
        ),
        "natural_japanese": bool(
            plan and language.has_japanese(plan.get("instruction_jp"))
            and not language.has_bad_language(plan.get("instruction_jp"))
        ),
        "instruction_jp": plan.get("instruction_jp") if plan else None,
        "plan_digest": trace.get("plan_digest") if isinstance(trace, dict) else None,
        "assistant_or_private_source": _source_violation(parsed, source),
    }


def control_record(case: dict, model: str, prompt: str, contract: dict, dataset: dict) -> dict:
    source = deepcopy(case["source"])
    call = bc.model_json_call(
        model=model, prompt=prompt, source=source,
        schema=bc.output_schema(source, contract, dataset),
        contract=contract, call_id=f"control:{model}:{case['case_id']}",
    )
    parsed = call.get("parsed") if isinstance(call.get("parsed"), dict) else None
    spec, normalization = (
        bc.normalize_output(parsed, source) if parsed is not None
        else (None, {"status": "invalid", "reason": "json_unavailable"})
    )
    observed_reason = parsed.get("unavailable_reason") if parsed else None
    return {
        "kind": "control", "case_id": case["case_id"], "language": case["language"],
        "model": model, "source_digest": bc.digest(source["text"]),
        "call": {key: value for key, value in call.items() if key != "parsed"},
        "raw_model_output": parsed, "normalization": normalization,
        "observed_status": parsed.get("status") if parsed else None,
        "observed_template_id": parsed.get("template_id") if parsed else None,
        "expected_unavailable_reason": case["expected_unavailable_reason"],
        "observed_unavailable_reason": observed_reason,
        "unavailable": normalization.get("status") == "unavailable",
        "reason_exact": observed_reason == case["expected_unavailable_reason"],
        "false_spec": spec is not None or bool(parsed and parsed.get("status") == "typed_spec"),
        "assistant_or_private_source": _source_violation(parsed, source),
    }


def summarize_model(model: str, rows: list[dict], contract: dict) -> dict:
    expected = contract["formal_gates_per_model"]
    current = [row for row in rows if row["model"] == model]
    positives = [row for row in current if row["kind"] == "positive"]
    controls = [row for row in current if row["kind"] == "control"]
    calls = [row["call"] for row in current]
    times = [row["wall_seconds"] for row in calls if row.get("completed")]
    token_complete = len(calls) == expected["case_count"] and all(
        call.get("completed")
        and isinstance(call.get("prompt_tokens"), int)
        and isinstance(call.get("completion_tokens"), int)
        for call in calls
    )
    metrics = {
        "case_count": len(current),
        "json_parse_success_count": sum(row["call"].get("json_parse_success") is True for row in current),
        "positive_typed_spec_count": sum(row["typed_spec"] is True for row in positives),
        "positive_non_span_exact_count": sum(row["non_span_exact"] is True for row in positives),
        "positive_exact_spec_count": sum(row["exact_spec"] is True for row in positives),
        "positive_template_exact_count": sum(row["template_exact"] is True for row in positives),
        "positive_evidence_exact_count": sum(row["evidence_exact"] is True for row in positives),
        "positive_role_aware_evidence_count": sum(row["role_aware_evidence"] is True for row in positives),
        "positive_role_aware_packet_count": sum(row["role_aware_packet_exact"] is True for row in positives),
        "positive_role_aware_atom_count": sum(row["role_aware_accepted_atom_count"] for row in positives),
        "raw_role_aware_evidence_count": sum(row["raw_role_aware_evidence"] is True for row in positives),
        "positive_slots_exact_count": sum(row["slots_exact"] is True for row in positives),
        "positive_downstream_compiled_count": sum(row["downstream_compiled"] is True for row in positives),
        "positive_downstream_mechanism_exact_count": sum(row["downstream_mechanism_exact"] is True for row in positives),
        "positive_natural_japanese_count": sum(row["natural_japanese"] is True for row in positives),
        "control_unavailable_count": sum(row["unavailable"] is True for row in controls),
        "control_reason_exact_count": sum(row["reason_exact"] is True for row in controls),
        "control_false_spec_count": sum(row["false_spec"] is True for row in controls),
        "assistant_or_private_source_count": sum(row["assistant_or_private_source"] is True for row in current),
        "token_accounting_complete": token_complete,
        "maximum_call_seconds": max(times) if times else None,
        "median_call_seconds": round(statistics.median(times), 5) if times else None,
        "prompt_tokens": sum(int(call.get("prompt_tokens") or 0) for call in calls),
        "completion_tokens": sum(int(call.get("completion_tokens") or 0) for call in calls),
    }
    failures = []
    for key, value in expected.items():
        if key == "maximum_call_seconds":
            if metrics[key] is None or metrics[key] > value:
                failures.append(key)
        elif metrics[key] != value:
            failures.append(key)
    return {"model": model, "metrics": metrics, "failed_gates": failures, "eligible": not failures}


def select_model(summaries: list[dict]) -> str | None:
    eligible = [row for row in summaries if row["eligible"]]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda row: (row["metrics"]["median_call_seconds"], row["metrics"]["completion_tokens"]),
    )["model"]


def _checkpoint(path: Path, evidence: dict, *, first: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
    if first:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".p4_bd_", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def run(contract_path: Path = DEFAULT_CONTRACT, output_path: Path = DEFAULT_OUTPUT) -> dict:
    contract_path = contract_path.resolve()
    output_path = output_path.resolve()
    contract, dataset, freeze_sha = preflight(contract_path, output_path)
    prompt = (ROOT / contract["prompt"]["path"]).read_text(encoding="utf-8")
    evidence = {
        "schema": "uruha_p4_bd_role_aware_evidence_v1",
        "status": "running_not_reusable",
        "freeze_sha": freeze_sha,
        "runner_sha256": _hash(Path(__file__)),
        "contract": {"path": str(contract_path.relative_to(ROOT)), "sha256": _hash(contract_path)},
        "dataset_sha256": contract["dataset"]["sha256"],
        "annotation_proxy_sha256": contract["annotation_proxy_decisions"]["sha256"],
        "executed_exactly_once_per_model_case": False,
        "retry_count": 0, "prewarm": [], "rows": [], "models": [], "selected_model": None,
        "product_runtime_changed": False, "claim_boundary": contract["claim_boundary"],
    }
    _checkpoint(output_path, evidence, first=True)
    for model in contract["controlled_constants"]["prewarm_models_once_in_fixed_order"]:
        record = bc.prewarm_model(model, contract["controlled_constants"]["keep_alive"])
        evidence["prewarm"].append(record)
        _checkpoint(output_path, evidence)
        if not record.get("completed"):
            evidence["status"] = "prewarm_failed_no_scored_calls"
            _checkpoint(output_path, evidence)
            return evidence
    for model in contract["models"]:
        for case in dataset["positive_cases"]:
            evidence["rows"].append(positive_record(case, model, prompt, contract, dataset))
            _checkpoint(output_path, evidence)
        for case in dataset["control_cases"]:
            evidence["rows"].append(control_record(case, model, prompt, contract, dataset))
            _checkpoint(output_path, evidence)
    evidence["models"] = [summarize_model(model, evidence["rows"], contract) for model in contract["models"]]
    evidence["selected_model"] = select_model(evidence["models"])
    evidence["status"] = "pass" if evidence["selected_model"] else "fail"
    evidence["executed_exactly_once_per_model_case"] = len(evidence["rows"]) == contract["execution"]["max_scored_calls"]
    _checkpoint(output_path, evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    evidence = run(args.contract, args.output)
    print(json.dumps({
        "status": evidence["status"], "selected_model": evidence["selected_model"],
        "models": evidence["models"], "rows": len(evidence["rows"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
