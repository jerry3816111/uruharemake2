#!/usr/bin/env python3
"""Run the frozen four-condition V44 semantic isolation experiment."""

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from action_ontology_grounding_v38 import _anchor_scope_reasons
from commitment_carrier_v44 import SCHEMAS, parse_carrier_response
from grounded_commitment_classifier_v42 import ground_supported_targets
from grounded_frame_isolation_v39 import load_v39_anchor_ontology
from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
)


ROOT = Path(__file__).resolve().parent
LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
PREREG_PATH = ROOT / "configs" / "commitment_carrier_target_isolation_v44_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
AUDIT_PATH = ROOT / "reports" / "grounded_action_candidate_audit_v42.json"
CARRIER_ANALYSIS_PATH = ROOT / "reports" / "commitment_carrier_v44_probe_analysis.json"
DEFAULT_OUTPUT = ROOT / "reports" / "commitment_target_isolation_v44_development_raw.json"
TZ = ZoneInfo("Asia/Tokyo")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def _git_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _validate_inputs(lock, prereg, dataset, audit, carrier_analysis):
    for section in ("selection_provenance", "frozen_semantic_inputs"):
        values = lock[section]
        for key, expected in values.items():
            if not key.endswith("_sha256"):
                continue
            path = ROOT / values[key.removesuffix("_sha256")]
            if _sha256(path) != expected:
                raise ValueError(f"V44 semantic frozen hash mismatch: {path.name}")
    selected = lock["selection_provenance"]["selected_carrier"]
    if selected != carrier_analysis.get("selected_carrier"):
        raise ValueError("V44 selected carrier mismatch")
    if not carrier_analysis.get("semantic_development_authorized"):
        raise ValueError("V44 carrier probe did not authorize semantic development")
    if selected != "two_field_object_schema":
        raise ValueError("V44 semantic lock expects the mechanically selected two-field carrier")
    frozen = lock["frozen_semantic_inputs"]
    if dataset["case_count"] != frozen["development_case_count"]:
        raise ValueError("V44 semantic development case count mismatch")
    if audit["summary"]["supported_expected_target_count"] != frozen["supported_target_count"]:
        raise ValueError("V44 semantic supported target count mismatch")
    if audit["summary"]["supported_target_recall"] != 1.0 or audit["summary"]["candidate_precision"] != 1.0:
        raise ValueError("V44 semantic experiment requires exact frozen candidate grounding")
    if tuple(lock["conditions"]) != tuple(prereg["stage_2_semantic_conditions"]["conditions"]):
        raise ValueError("V44 semantic condition order mismatch")
    if any(
        lock[key] or prereg[key]
        for key in (
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
        )
    ):
        raise ValueError("V44 semantic development cannot authorize integration or execution")


def _model_snapshot(prereg):
    frozen = prereg["frozen_environment"]
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=30) as response:
        inventory = {row["name"]: row for row in json.load(response).get("models") or []}
    actual = inventory.get(frozen["model"])
    if not actual or actual.get("digest") != frozen["model_digest"]:
        raise ValueError("V44 semantic fixed model missing or digest mismatch")
    return {
        "model_tag": frozen["model"],
        "digest": actual.get("digest"),
        "size": actual.get("size"),
        "details": actual.get("details") or {},
        "thinking": frozen["thinking"],
    }


def _selected_schema(lock):
    return SCHEMAS[lock["selection_provenance"]["selected_carrier"]]


def build_system_prompts(lock):
    schema_text = json.dumps(_selected_schema(lock), ensure_ascii=False, sort_keys=True)
    output_instruction = (
        "判定結果を次の JSON Schema どおりに返してください。commitment には判定した一値、"
        "contract_ack には v44 を入れ、説明文、Markdown、指定外のキーを出力しないでください。"
        f"\nExact output schema:\n{schema_text}"
    )
    blocks = {
        "base_instruction": lock["base_instruction"],
        "relational_instruction": lock["relational_instruction"],
        "target_isolation_instruction": lock["target_isolation_instruction"],
        "scope_signal_instruction": lock["scope_signal_instruction"],
        "exact_selected_carrier_schema": output_instruction,
    }
    return {
        condition: "\n\n".join(blocks[name] for name in lock["prompt_composition"][condition])
        for condition in lock["conditions"]
    }


def _candidate_rows(dataset, ontology):
    return [
        {
            "case_id": case["id"],
            "family": case["family"],
            "user_input": case["user_input"],
            "candidates": ground_supported_targets(case["user_input"], ontology),
        }
        for case in dataset["cases"]
    ]


def _target_payload(candidate):
    return {"domain": candidate["domain"], "value": candidate["value"]}


def _evidence_payload(candidate):
    return [
        {"index": index, "text": anchor["text"]}
        for index, anchor in enumerate(candidate["anchors"])
    ]


def _context_target_payload(candidate):
    return {
        "domain": candidate["domain"],
        "value": candidate["value"],
        "anchors": [
            {"text": anchor["text"], "start": anchor["start"], "end": anchor["end"]}
            for anchor in candidate["anchors"]
        ],
    }


def _scope_signal_payload(user_input, candidate):
    return [
        {
            "text": anchor["text"],
            "start": anchor["start"],
            "end": anchor["end"],
            "scope_reasons": _anchor_scope_reasons(user_input, anchor),
        }
        for anchor in candidate["anchors"]
    ]


def _user_payload(condition, candidate_row, candidate):
    payload = {
        "user_input": candidate_row["user_input"],
        "target": _target_payload(candidate),
        "evidence_candidates": _evidence_payload(candidate),
    }
    if condition == "all_targets_relational":
        payload["all_grounded_targets"] = [
            _context_target_payload(row) for row in candidate_row["candidates"]
        ]
    if condition in {"isolated_other_targets", "isolated_scope_signals_candidate"}:
        payload["context_only_other_targets"] = [
            _context_target_payload(row)
            for row in candidate_row["candidates"]
            if row["target_id"] != candidate["target_id"]
        ]
    if condition == "isolated_scope_signals_candidate":
        payload["focus_anchor_scope_signals"] = _scope_signal_payload(
            candidate_row["user_input"], candidate
        )
    return payload


def _run_judgment(condition, candidate_row, candidate, prompts, lock, prereg, snapshot):
    payload = _user_payload(condition, candidate_row, candidate)
    messages = [
        {"role": "system", "content": prompts[condition]},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]
    frozen = prereg["frozen_environment"]
    options = {
        "temperature": frozen["temperature"],
        "top_p": frozen["top_p"],
        "seed": frozen["seed"],
        "num_ctx": frozen["context_tokens"],
        "num_predict": frozen["maximum_output_tokens"],
    }
    model_info = {
        "condition": "qwen3_5_4b_v44_semantic",
        "model_tag": snapshot["model_tag"],
        "blob_bytes": snapshot["size"],
        "thinking": snapshot["thinking"],
    }
    body = _chat_body(model_info, messages, options=options)
    body["format"] = _selected_schema(lock)
    response, elapsed, attempts, errors = _call_ollama(body)
    return {
        "response_message": response.get("message") or {},
        "parsed": parse_carrier_response(
            lock["selection_provenance"]["selected_carrier"], response
        ),
        "response_metrics": _response_metrics(response, elapsed),
        "transport_attempts": attempts,
        "prior_transport_errors": errors,
    }


def _report_checks(prompts):
    return {
        "runner_commit": _git_head(),
        "semantic_lock_sha256": _sha256(LOCK_PATH),
        "preregistration_sha256": _sha256(PREREG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "audit_sha256": _sha256(AUDIT_PATH),
        "carrier_analysis_sha256": _sha256(CARRIER_ANALYSIS_PATH),
        "condition_prompt_sha256": {
            condition: hashlib.sha256(prompt.encode()).hexdigest()
            for condition, prompt in prompts.items()
        },
    }


def _load_or_create(output, prompts, snapshot, candidate_rows, lock):
    checks = _report_checks(prompts)
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        for field, expected in checks.items():
            if report.get(field) != expected:
                raise ValueError(f"Existing V44 semantic report {field} mismatch")
        return report
    return {
        "schema": "uruha_commitment_target_isolation_development_raw_v44",
        "evidence_status": "causal_ablation_on_retired_v42_development_targets",
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "selected_carrier": lock["selection_provenance"]["selected_carrier"],
        "model_snapshot": snapshot,
        "candidate_rows": candidate_rows,
        "judgment_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    carrier_analysis = json.loads(CARRIER_ANALYSIS_PATH.read_text(encoding="utf-8"))
    _validate_inputs(lock, prereg, dataset, audit, carrier_analysis)
    snapshot = _model_snapshot(prereg)
    prompts = build_system_prompts(lock)
    candidate_rows = _candidate_rows(dataset, load_v39_anchor_ontology())
    target_count = sum(len(row["candidates"]) for row in candidate_rows)
    if target_count != lock["frozen_semantic_inputs"]["supported_target_count"]:
        raise ValueError("V44 runtime grounded target count mismatch")
    report = _load_or_create(output, prompts, snapshot, candidate_rows, lock)
    completed = {
        (row["condition"], row["case_id"], row["target_id"])
        for row in report["judgment_rows"]
    }
    total = len(lock["conditions"]) * target_count
    for condition in lock["conditions"]:
        for candidate_row in candidate_rows:
            for candidate in candidate_row["candidates"]:
                key = (condition, candidate_row["case_id"], candidate["target_id"])
                if key in completed:
                    continue
                report["judgment_rows"].append(
                    {
                        "condition": condition,
                        "case_id": candidate_row["case_id"],
                        "target_id": candidate["target_id"],
                        "result": _run_judgment(
                            condition,
                            candidate_row,
                            candidate,
                            prompts,
                            lock,
                            prereg,
                            snapshot,
                        ),
                    }
                )
                _atomic_write(output, report)
                print(
                    f"[v44 semantic {len(report['judgment_rows'])}/{total}] "
                    f"{condition} {candidate_row['case_id']} {candidate['target_id']}",
                    flush=True,
                )
    if len(report["judgment_rows"]) == total:
        report["completed_at"] = _now()
    _atomic_write(output, report)
    _unload_model(snapshot["model_tag"])
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps({"rows": len(report["judgment_rows"]), "completed_at": report["completed_at"]}, indent=2))


if __name__ == "__main__":
    main()
