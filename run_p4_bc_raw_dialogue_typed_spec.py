#!/usr/bin/env python3
"""Execute the prospectively frozen P4-BC raw-dialogue typed-spec study once.

Each model/case pair is called exactly once with the same prompt and dynamic
schema.  The runner records both model arms, never retries, never installs the
compiler into the product runtime, and preserves a negative result.
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

import rightbrain_language_quality as language
import uruha_typed_action_compiler_p4 as compiler


ROOT = Path(__file__).resolve().parent
DEFAULT_CONTRACT = ROOT / "configs" / "p4_bc_raw_dialogue_typed_spec_v1.json"
DEFAULT_OUTPUT = ROOT / "analysis" / "p4_bc_raw_dialogue_typed_spec_evidence_2026-09-27.json"
OLLAMA_CHAT = "http://127.0.0.1:11434/api/chat"
OLLAMA_GENERATE = "http://127.0.0.1:11434/api/generate"
SLOT_KEYS = (
    "work_object_jp", "scaffold_unit_jp", "count_word_jp",
    "items_jp", "left_label_jp", "right_label_jp",
    "collection_jp", "selected_item_jp", "target_jp", "condition_jp",
    "obstacle_jp", "atomic_object_jp", "unknown_constraint_jp",
)
EVIDENCE_ROLES = sorted({
    role
    for row in compiler.TEMPLATE_CONTRACTS.values()
    for role in row["evidence_roles"]
})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _object(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def output_schema(source: dict, contract: dict, dataset: dict) -> dict:
    values = contract["output_contract"]
    return _object({
        "status": {"type": "string", "enum": values["status"]},
        "source_id": {"type": "string", "enum": [source["id"]]},
        "source_span": {"type": "string", "enum": [source["text"]]},
        "template_id": {"type": "string", "enum": values["template_id"]},
        "safety_class": {"type": "string", "enum": values["safety_class"]},
        "evidence_atoms": {
            "type": "array",
            "items": _object({
                "role": {"type": "string", "enum": EVIDENCE_ROLES},
                "text": {"type": "string"},
            }),
            "minItems": 0,
            "maxItems": 3,
        },
        "slots": _object({key: {"type": "string"} for key in SLOT_KEYS}),
        "unavailable_reason": {
            "type": "string",
            "enum": ["none", *dataset["reason_vocabulary"]],
        },
    })


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
    except Exception as exc:  # one-shot evidence; never retry
        record.update(error_type=type(exc).__name__, error=str(exc)[:300])
    record["wall_seconds"] = round(time.monotonic() - started, 5)
    return record


def model_json_call(*, model: str, prompt: str, source: dict, schema: dict,
                    contract: dict, call_id: str) -> dict:
    started = time.monotonic()
    record = {
        "call_id": call_id,
        "model": model,
        "attempted": True,
        "completed": False,
        "json_parse_success": False,
        "system_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "schema_sha256": hashlib.sha256(
            json.dumps(schema, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "payload_digest": digest({"source": source}),
    }
    constants = contract["controlled_constants"]
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps({"source": source}, ensure_ascii=False)},
        ],
        "format": schema,
        "stream": constants["stream"],
        "think": constants["think"],
        "keep_alive": constants["keep_alive"],
        "options": {
            "temperature": constants["temperature"],
            "seed": constants["seed"],
            "num_ctx": constants["num_ctx"],
            "num_predict": constants["num_predict"],
        },
    }
    try:
        data = _post_json(OLLAMA_CHAT, body, contract["execution"]["call_timeout_seconds"])
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
    except Exception as exc:  # one-shot evidence; never retry
        record.update(error_type=type(exc).__name__, error=str(exc)[:300])
    record["wall_seconds"] = round(time.monotonic() - started, 5)
    return record


def normalize_output(parsed: dict, source: dict) -> tuple[dict | None, dict]:
    """Normalize the fixed wide schema into either one P4-BB spec or unavailable."""
    if not isinstance(parsed, dict):
        return None, {"status": "invalid", "reason": "not_an_object"}
    status = parsed.get("status")
    slots = parsed.get("slots")
    atoms = parsed.get("evidence_atoms")
    if not isinstance(slots, dict) or set(slots) != set(SLOT_KEYS):
        return None, {"status": "invalid", "reason": "wide_slot_contract_mismatch"}
    if parsed.get("source_id") != source.get("id") or parsed.get("source_span") != source.get("text"):
        return None, {"status": "invalid", "reason": "source_identity_mismatch"}
    if status == "unavailable":
        valid = (
            parsed.get("template_id") == "unavailable"
            and parsed.get("safety_class") == "unavailable"
            and atoms == []
            and all(value == "" for value in slots.values())
            and parsed.get("unavailable_reason") != "none"
        )
        return None, {
            "status": "unavailable" if valid else "invalid",
            "reason": parsed.get("unavailable_reason"),
            "unavailable_contract_valid": valid,
        }
    if status != "typed_spec":
        return None, {"status": "invalid", "reason": "invalid_status"}
    template_id = parsed.get("template_id")
    template = compiler.TEMPLATE_CONTRACTS.get(template_id)
    if not template:
        return None, {"status": "invalid", "reason": "unsupported_template"}
    used = {key: value for key, value in slots.items() if value != ""}
    valid = (
        parsed.get("safety_class") == "low_risk_reversible"
        and parsed.get("unavailable_reason") == "none"
        and isinstance(atoms, list)
        and len(atoms) == 3
        and set(used) == template["slots"]
        and all(key in template["slots"] or value == "" for key, value in slots.items())
    )
    if not valid:
        return None, {"status": "invalid", "reason": "typed_spec_contract_mismatch"}
    spec = {
        "schema": compiler.TASK_SPEC_SCHEMA,
        "source_id": source["id"],
        "source_span": source["text"],
        "template_id": template_id,
        "safety_class": "low_risk_reversible",
        "evidence_atoms": deepcopy(atoms),
        "slots": used,
    }
    return spec, {"status": "typed_spec", "reason": "normalized"}


def positive_record(case: dict, model: str, prompt: str, contract: dict, dataset: dict) -> dict:
    source = deepcopy(case["source"])
    call = model_json_call(
        model=model,
        prompt=prompt,
        source=source,
        schema=output_schema(source, contract, dataset),
        contract=contract,
        call_id=f"positive:{model}:{case['case_id']}",
    )
    spec, normalization = normalize_output(call.get("parsed"), source) if call.get("json_parse_success") else (None, {"status": "invalid", "reason": "json_unavailable"})
    expected = case["expected_spec"]
    plan = None
    compile_trace = None
    if spec is not None:
        plan, compile_trace = compiler.compile_typed_action_p4_bb(source, spec)
    row = {
        "kind": "positive",
        "case_id": case["case_id"],
        "language": case["language"],
        "model": model,
        "source_digest": digest(source["text"]),
        "call": {key: value for key, value in call.items() if key != "parsed"},
        "normalization": normalization,
        "observed_status": (call.get("parsed") or {}).get("status") if isinstance(call.get("parsed"), dict) else None,
        "observed_template_id": (call.get("parsed") or {}).get("template_id") if isinstance(call.get("parsed"), dict) else None,
        "observed_unavailable_reason": (call.get("parsed") or {}).get("unavailable_reason") if isinstance(call.get("parsed"), dict) else None,
        "typed_spec": spec is not None,
        "exact_spec": spec == expected,
        "template_exact": bool(spec and spec.get("template_id") == expected["template_id"]),
        "evidence_exact": bool(spec and spec.get("evidence_atoms") == expected["evidence_atoms"]),
        "slots_exact": bool(spec and spec.get("slots") == expected["slots"]),
        "downstream_compiled": bool(plan and compile_trace and compile_trace.get("status") == "compiled"),
        "downstream_mechanism_exact": bool(
            plan and plan.get("progress_mechanism")
            == compiler.TEMPLATE_CONTRACTS[expected["template_id"]]["progress_mechanism"]
        ),
        "natural_japanese": bool(
            plan and language.has_japanese(plan.get("instruction_jp"))
            and not language.has_bad_language(plan.get("instruction_jp"))
        ),
        "instruction_jp": plan.get("instruction_jp") if plan else None,
        "plan_digest": compile_trace.get("plan_digest") if isinstance(compile_trace, dict) else None,
        "assistant_or_private_source": False,
    }
    if isinstance(call.get("parsed"), dict):
        row["observed_evidence_atoms"] = call["parsed"].get("evidence_atoms")
        row["observed_nonempty_slots"] = {
            key: value for key, value in (call["parsed"].get("slots") or {}).items() if value
        }
    return row


def control_record(case: dict, model: str, prompt: str, contract: dict, dataset: dict) -> dict:
    source = deepcopy(case["source"])
    call = model_json_call(
        model=model,
        prompt=prompt,
        source=source,
        schema=output_schema(source, contract, dataset),
        contract=contract,
        call_id=f"control:{model}:{case['case_id']}",
    )
    spec, normalization = normalize_output(call.get("parsed"), source) if call.get("json_parse_success") else (None, {"status": "invalid", "reason": "json_unavailable"})
    parsed = call.get("parsed") if isinstance(call.get("parsed"), dict) else {}
    observed_reason = parsed.get("unavailable_reason")
    return {
        "kind": "control",
        "case_id": case["case_id"],
        "language": case["language"],
        "model": model,
        "source_digest": digest(source["text"]),
        "call": {key: value for key, value in call.items() if key != "parsed"},
        "normalization": normalization,
        "observed_status": parsed.get("status"),
        "observed_template_id": parsed.get("template_id"),
        "expected_unavailable_reason": case["expected_unavailable_reason"],
        "observed_unavailable_reason": observed_reason,
        "unavailable": normalization.get("status") == "unavailable",
        "reason_exact": observed_reason == case["expected_unavailable_reason"],
        "false_spec": spec is not None or parsed.get("status") == "typed_spec",
        "assistant_or_private_source": False,
    }


def summarize_model(model: str, rows: list[dict], contract: dict) -> dict:
    expected = contract["formal_gates_per_model"]
    current = [row for row in rows if row["model"] == model]
    positives = [row for row in current if row["kind"] == "positive"]
    controls = [row for row in current if row["kind"] == "control"]
    calls = [row["call"] for row in current]
    completed_times = [row["wall_seconds"] for row in calls if row.get("completed")]
    token_complete = len(calls) == expected["case_count"] and all(
        row.get("completed")
        and isinstance(row.get("prompt_tokens"), int)
        and isinstance(row.get("completion_tokens"), int)
        for row in calls
    )
    metrics = {
        "case_count": len(current),
        "json_parse_success_count": sum(row["call"].get("json_parse_success") is True for row in current),
        "positive_typed_spec_count": sum(row["typed_spec"] is True for row in positives),
        "positive_exact_spec_count": sum(row["exact_spec"] is True for row in positives),
        "positive_template_exact_count": sum(row["template_exact"] is True for row in positives),
        "positive_evidence_exact_count": sum(row["evidence_exact"] is True for row in positives),
        "positive_slots_exact_count": sum(row["slots_exact"] is True for row in positives),
        "positive_downstream_compiled_count": sum(row["downstream_compiled"] is True for row in positives),
        "positive_downstream_mechanism_exact_count": sum(row["downstream_mechanism_exact"] is True for row in positives),
        "positive_natural_japanese_count": sum(row["natural_japanese"] is True for row in positives),
        "control_unavailable_count": sum(row["unavailable"] is True for row in controls),
        "control_reason_exact_count": sum(row["reason_exact"] is True for row in controls),
        "control_false_spec_count": sum(row["false_spec"] is True for row in controls),
        "assistant_or_private_source_count": sum(row["assistant_or_private_source"] is True for row in current),
        "token_accounting_complete": token_complete,
        "maximum_call_seconds": max(completed_times) if completed_times else None,
        "median_call_seconds": round(statistics.median(completed_times), 5) if completed_times else None,
        "prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in calls),
        "completion_tokens": sum(int(row.get("completion_tokens") or 0) for row in calls),
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
        key=lambda row: (
            row["metrics"]["median_call_seconds"],
            row["metrics"]["completion_tokens"],
        ),
    )["model"]


def run(contract_path: Path, output_path: Path) -> dict:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    dataset_path = ROOT / contract["dataset"]["path"]
    prompt_path = ROOT / contract["prompt"]["path"]
    compiler_path = ROOT / contract["downstream_compiler"]["path"]
    for path, expected, label in (
        (dataset_path, contract["dataset"]["sha256"], "dataset"),
        (prompt_path, contract["prompt"]["sha256"], "prompt"),
        (compiler_path, contract["downstream_compiler"]["sha256"], "compiler"),
    ):
        if sha256(path) != expected:
            raise RuntimeError(f"Frozen P4-BC {label} hash mismatch")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    prompt = prompt_path.read_text(encoding="utf-8")

    prewarm = [
        prewarm_model(model, contract["controlled_constants"]["keep_alive"])
        for model in contract["controlled_constants"]["prewarm_models_once_in_fixed_order"]
    ]
    rows = []
    for model in contract["models"]:
        rows.extend(
            positive_record(case, model, prompt, contract, dataset)
            for case in dataset["positive_cases"]
        )
        rows.extend(
            control_record(case, model, prompt, contract, dataset)
            for case in dataset["control_cases"]
        )
    summaries = [summarize_model(model, rows, contract) for model in contract["models"]]
    selected = select_model(summaries)
    evidence = {
        "schema": "uruha_p4_bc_raw_dialogue_typed_spec_evidence_v1",
        "status": "pass" if selected else "fail",
        "executed_exactly_once_per_model_case": True,
        "retry_count": 0,
        "contract": {
            "path": str(contract_path.relative_to(ROOT)),
            "sha256": sha256(contract_path),
            "dataset_path": str(dataset_path.relative_to(ROOT)),
            "dataset_sha256": sha256(dataset_path),
            "prompt_path": str(prompt_path.relative_to(ROOT)),
            "prompt_sha256": sha256(prompt_path),
            "compiler_path": str(compiler_path.relative_to(ROOT)),
            "compiler_sha256": sha256(compiler_path),
        },
        "prewarm": prewarm,
        "rows": rows,
        "models": summaries,
        "selected_model": selected,
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
        "selected_model": evidence["selected_model"],
        "models": evidence["models"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
