#!/usr/bin/env python3
"""Execute the prospectively frozen P4-BA local-model allocation study once.

The runner never retries a model/case call. Candidate generation is reused
across reviewer arms exactly as frozen, while every arm retains its own result.
It does not install or mutate the product runtime.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import statistics
import time
import urllib.request

import uruha_actionable_help_delivery_m45 as m45
import uruha_goal_progress_delivery_m46 as m46
import uruha_state_changing_candidates_m51 as m51


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "configs" / "p4_ba_stage_model_allocation_v1.json"
DEFAULT_OUTPUT = ROOT / "analysis" / "p4_ba_stage_model_allocation_evidence_2026-09-26.json"
OLLAMA_CHAT = "http://127.0.0.1:11434/api/chat"
OLLAMA_GENERATE = "http://127.0.0.1:11434/api/generate"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _post_json(url: str, body: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def prewarm_model(model: str, keep_alive: str) -> dict:
    started = time.monotonic()
    record = {"model": model, "attempted": True, "completed": False}
    try:
        data = _post_json(
            OLLAMA_GENERATE,
            {"model": model, "prompt": "", "stream": False, "keep_alive": keep_alive},
            120,
        )
        record.update(
            completed=True,
            load_duration_ns=int(data.get("load_duration") or 0),
            total_duration_ns=int(data.get("total_duration") or 0),
        )
    except Exception as exc:  # preserve one-shot failure; never retry
        record.update(error_type=type(exc).__name__, error=str(exc)[:300])
    record["wall_seconds"] = round(time.monotonic() - started, 5)
    return record


def model_json_call(
    *,
    model: str,
    system: str,
    payload: dict,
    schema: dict,
    timeout: float,
    num_predict: int,
    constants: dict,
    call_id: str,
) -> dict:
    started = time.monotonic()
    record = {
        "call_id": call_id,
        "model": model,
        "attempted": True,
        "completed": False,
        "json_parse_success": False,
        "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(
            json.dumps(schema, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "payload_digest": digest(payload),
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "format": schema,
        "stream": False,
        "think": False,
        "keep_alive": constants["keep_alive"],
        "options": {
            "temperature": constants["temperature"],
            "seed": constants["seed"],
            "num_ctx": constants["num_ctx"],
            "num_predict": num_predict,
        },
    }
    try:
        data = _post_json(OLLAMA_CHAT, body, timeout)
        record.update(
            completed=True,
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            completion_tokens=int(data.get("eval_count") or 0),
            load_duration_ns=int(data.get("load_duration") or 0),
            prompt_eval_duration_ns=int(data.get("prompt_eval_duration") or 0),
            eval_duration_ns=int(data.get("eval_duration") or 0),
            total_duration_ns=int(data.get("total_duration") or 0),
        )
        content = (data.get("message") or {}).get("content", "")
        record["content_digest"] = digest(content)
        try:
            record["parsed"] = json.loads(content)
            record["json_parse_success"] = True
        except (json.JSONDecodeError, TypeError) as exc:
            record.update(
                error_type=type(exc).__name__,
                error=str(exc)[:300],
                raw_content_preview=str(content)[:1000],
            )
    except Exception as exc:  # preserve one-shot failure; never retry
        record.update(error_type=type(exc).__name__, error=str(exc)[:300])
    record["wall_seconds"] = round(time.monotonic() - started, 5)
    return record


def generation_record(case: dict, model: str, contract: dict) -> dict:
    source = deepcopy(case["source"])
    sources = [source]
    call = model_json_call(
        model=model,
        system=m51.CANDIDATE_SYSTEM,
        payload={"user_sources": sources},
        schema=m51._candidate_schema(sources),
        timeout=contract["execution"]["candidate_timeout_seconds"],
        num_predict=contract["controlled_constants"]["candidate_num_predict"],
        constants=contract["controlled_constants"],
        call_id=f"generate:{model}:{case['case_id']}",
    )
    row = {
        "case_id": case["case_id"],
        "model": model,
        "source_digest": digest(source["text"]),
        "call": {key: value for key, value in call.items() if key != "parsed"},
        "selected_plan": None,
        "candidate_state": None,
        "selected_structurally_valid": False,
        "selected_mechanism_allowed": False,
    }
    if call.get("json_parse_success"):
        try:
            plan, state = m51.select_candidate_batch(call["parsed"], sources)
            row.update(
                selected_plan=plan,
                candidate_state=state,
                selected_structurally_valid=state.get("selected_structurally_valid") is True,
                selected_mechanism_allowed=(
                    plan.get("progress_mechanism") in case["allowed_progress_mechanisms"]
                ),
            )
        except Exception as exc:
            row.update(selection_error_type=type(exc).__name__, selection_error=str(exc)[:300])
    row["generation_case_pass"] = bool(
        call.get("json_parse_success")
        and row["selected_structurally_valid"]
        and row["selected_mechanism_allowed"]
    )
    return row


def review_record(*, case_id: str, source: dict, plan: dict, model: str,
                  expected_accepted: bool | None, contract: dict, call_kind: str) -> dict:
    sources = [deepcopy(source)]
    audited_plan = {key: value for key, value in plan.items() if key != "progress_mechanism"}
    payload = {
        "sources": sources,
        "plan": audited_plan,
        "planned_payload_digest": m45.digest({"sources": sources, "plan": plan}),
    }
    call = model_json_call(
        model=model,
        system=m46.REVIEW_SYSTEM,
        payload=payload,
        schema=m46.review_schema(sources, plan),
        timeout=contract["execution"]["review_timeout_seconds"],
        num_predict=contract["controlled_constants"]["review_num_predict"],
        constants=contract["controlled_constants"],
        call_id=f"{call_kind}:{model}:{case_id}",
    )
    row = {
        "case_id": case_id,
        "model": model,
        "expected_accepted": expected_accepted,
        "source_digest": digest(source["text"]),
        "plan_digest": digest(plan),
        "call": {key: value for key, value in call.items() if key != "parsed"},
        "accepted": False,
        "source_exact": False,
        "content_passed": False,
        "surface_passed": False,
    }
    if call.get("json_parse_success"):
        review = call["parsed"]
        audit = m46.inspect_goal_progress(plan, sources, review)
        accepted = bool(audit["content_passed"] and audit["surface_passed"])
        row.update(
            accepted=accepted,
            source_exact=(
                review.get("source_id") == plan.get("goal_source_id")
                and review.get("source_span") == plan.get("goal_source_span")
            ),
            content_passed=audit["content_passed"],
            surface_passed=audit["surface_passed"],
            mechanism_exact_agreement=audit["mechanism_exact_agreement"],
            structural_violations=audit["structural_violations"],
            content_violations=audit["content_violations"],
            surface_violations=audit["surface_violations"],
            review_observed_mechanism=review.get("observed_progress_mechanism"),
        )
    row["correct"] = (row["accepted"] == expected_accepted) if expected_accepted is not None else None
    return row


def summarize_arms(contract: dict, generation: list[dict], fixtures: list[dict],
                   full_reviews: list[dict]) -> list[dict]:
    expected = contract["formal_gates"]
    rows = []
    for arm in contract["arms"]:
        gen = [row for row in generation if row["model"] == arm["generator"]]
        fixed = [row for row in fixtures if row["model"] == arm["reviewer"]]
        full = [row for row in full_reviews
                if row["generator_model"] == arm["generator"]
                and row["model"] == arm["reviewer"]]
        combined_latency = []
        for review in full:
            source_gen = next((row for row in gen if row["case_id"] == review["case_id"]), None)
            if source_gen and review["call"].get("completed"):
                combined_latency.append(round(
                    source_gen["call"]["wall_seconds"] + review["call"]["wall_seconds"], 5
                ))
        product_calls = [row["call"] for row in gen] + [row["call"] for row in full]
        token_complete = bool(product_calls) and all(
            row.get("completed")
            and isinstance(row.get("prompt_tokens"), int)
            and isinstance(row.get("completion_tokens"), int)
            for row in product_calls
        )
        metrics = {
            "generation_json_parse_success_count": sum(row["call"].get("json_parse_success") is True for row in gen),
            "generation_structurally_valid_count": sum(row["selected_structurally_valid"] is True for row in gen),
            "generation_allowed_mechanism_count": sum(row["selected_mechanism_allowed"] is True for row in gen),
            "review_fixture_correct_count": sum(row["correct"] is True for row in fixed),
            "review_fixture_accepted_count": sum(row["accepted"] is True for row in fixed),
            "full_pipeline_accepted_count": sum(row["accepted"] is True for row in full),
            "full_pipeline_source_exact_count": sum(row["source_exact"] is True for row in full),
            "full_pipeline_natural_japanese_count": sum(row.get("natural_japanese") is True for row in full),
            "full_pipeline_raw_dialogue_trace_count": 0,
            "full_pipeline_factual_memory_write_count": 0,
            "maximum_two_stage_seconds": max(combined_latency) if combined_latency else None,
            "median_two_stage_seconds": round(statistics.median(combined_latency), 5) if combined_latency else None,
            "product_prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in product_calls),
            "product_completion_tokens": sum(int(row.get("completion_tokens") or 0) for row in product_calls),
            "token_accounting_complete": token_complete,
        }
        failures = []
        for key in (
            "generation_json_parse_success_count",
            "generation_structurally_valid_count",
            "generation_allowed_mechanism_count",
            "review_fixture_correct_count",
            "full_pipeline_accepted_count",
            "full_pipeline_source_exact_count",
            "full_pipeline_natural_japanese_count",
            "full_pipeline_raw_dialogue_trace_count",
            "full_pipeline_factual_memory_write_count",
        ):
            if metrics[key] != expected[key]:
                failures.append(key)
        if metrics["maximum_two_stage_seconds"] is None or metrics["maximum_two_stage_seconds"] > expected["maximum_two_stage_seconds"]:
            failures.append("maximum_two_stage_seconds")
        if metrics["token_accounting_complete"] is not expected["token_accounting_complete"]:
            failures.append("token_accounting_complete")
        rows.append({**arm, "metrics": metrics, "failed_gates": failures, "eligible": not failures})
    return rows


def run(contract_path: Path, output_path: Path) -> dict:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    dataset_path = ROOT / contract["dataset"]["path"]
    if sha256(dataset_path) != contract["dataset"]["sha256"]:
        raise RuntimeError("Frozen P4-BA dataset hash mismatch")
    for _name, (relative, expected) in contract["implementation"].items():
        if sha256(ROOT / relative) != expected:
            raise RuntimeError(f"Frozen implementation hash mismatch: {relative}")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))

    prewarm = [
        prewarm_model(model, contract["controlled_constants"]["keep_alive"])
        for model in contract["controlled_constants"]["prewarm_models_once_in_fixed_order"]
    ]
    generation = [
        generation_record(case, model, contract)
        for model in contract["models"]["generator"]
        for case in dataset["generation_cases"]
    ]
    fixtures = [
        review_record(
            case_id=case["case_id"],
            source=case["source"],
            plan=case["plan"],
            model=model,
            expected_accepted=case["expected_accepted"],
            contract=contract,
            call_kind="fixture_review",
        )
        for model in contract["models"]["reviewer"]
        for case in dataset["review_fixtures"]
    ]
    generation_cases = {case["case_id"]: case for case in dataset["generation_cases"]}
    full_reviews = []
    for arm in contract["arms"]:
        for generated in generation:
            if generated["model"] != arm["generator"] or not isinstance(generated.get("selected_plan"), dict):
                continue
            case = generation_cases[generated["case_id"]]
            row = review_record(
                case_id=generated["case_id"],
                source=case["source"],
                plan=generated["selected_plan"],
                model=arm["reviewer"],
                expected_accepted=None,
                contract=contract,
                call_kind=f"full_review:{arm['generator']}",
            )
            row["generator_model"] = arm["generator"]
            row["natural_japanese"] = m45._japanese(generated["selected_plan"].get("instruction_jp"))
            full_reviews.append(row)

    arms = summarize_arms(contract, generation, fixtures, full_reviews)
    eligible = [row for row in arms if row["eligible"]]
    selected = None
    if eligible:
        selected = min(
            eligible,
            key=lambda row: (
                row["metrics"]["median_two_stage_seconds"],
                row["metrics"]["product_completion_tokens"],
            ),
        )["arm_id"]
    evidence = {
        "schema": "uruha_p4_ba_stage_model_allocation_evidence_v1",
        "status": "pass" if selected else "fail",
        "executed_exactly_once_per_unique_model_case": True,
        "retry_count": 0,
        "contract": {
            "path": str(contract_path.relative_to(ROOT)),
            "sha256": sha256(contract_path),
            "dataset_path": str(dataset_path.relative_to(ROOT)),
            "dataset_sha256": sha256(dataset_path),
        },
        "prewarm": prewarm,
        "generation": generation,
        "review_fixtures": fixtures,
        "full_pipeline_reviews": full_reviews,
        "arms": arms,
        "selected_arm": selected,
        "product_runtime_changed": False,
        "claim_boundary": contract["claim_boundary"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    evidence = run(args.contract.resolve(), args.output.resolve())
    print(json.dumps({
        "status": evidence["status"],
        "selected_arm": evidence["selected_arm"],
        "arms": [
            {
                "arm_id": row["arm_id"],
                "eligible": row["eligible"],
                "failed_gates": row["failed_gates"],
                "metrics": row["metrics"],
            }
            for row in evidence["arms"]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
