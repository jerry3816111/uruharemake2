#!/usr/bin/env python3
"""Run the preregistered V52 precise-target-mention development comparison."""

import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from commitment_carrier_v44 import SCHEMAS, parse_carrier_response
from precise_target_mentions_v52 import (
    audit_precise_event_maps,
    build_precise_target_event_map,
)
from run_discourse_state_perception_v45 import (
    _user_payload as v45_user_payload,
    build_system_prompts as build_v45_system_prompts,
)
from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
)
from run_target_event_map_v51 import build_candidate_rows
from target_event_map_v51 import build_target_event_map


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"
V51_CONFIG_PATH = ROOT / "configs" / "target_event_map_v51_preregistration.json"
V45_CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
V44_LOCK_PATH = ROOT / "configs" / "commitment_target_isolation_v44_semantic_lock.json"
DATASET_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
DEFAULT_OUTPUT = ROOT / "reports" / "precise_target_mentions_v52_development_raw.json"
CONDITIONS = ("v51_event_map_control", "precise_target_mentions_candidate")
TZ = ZoneInfo("Asia/Tokyo")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now():
    return datetime.now(TZ).isoformat(timespec="seconds")


def _git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _validate_inputs(config, dataset):
    frozen = config["frozen_inputs"]
    for key, expected in frozen.items():
        if key.endswith("_sha256"):
            path = ROOT / frozen[key.removesuffix("_sha256")]
            if _sha256(path) != expected:
                raise ValueError(f"V52 frozen input hash mismatch: {path.name}")
    if list(config["conditions"]) != list(CONDITIONS):
        raise ValueError("V52 condition order mismatch")
    if dataset["case_count"] != frozen["case_count"]:
        raise ValueError("V52 retired development case count mismatch")
    if config["expected_judgment_count"] != (
        len(CONDITIONS) * frozen["grounded_target_count"]
    ):
        raise ValueError("V52 expected judgment count mismatch")
    if any(
        config[key]
        for key in (
            "prompt_or_map_tuning_after_run_authorized",
            "fresh_holdout_claim_authorized",
            "runtime_change_authorized",
            "shadow_integration_authorized",
            "physical_vrm_execution_enabled",
            "human_likeness_claim_authorized",
        )
    ):
        raise ValueError("V52 development cannot start with advancement authorized")


def _model_snapshot(config):
    frozen = config["fixed_model"]
    with urllib.request.urlopen(
        "http://127.0.0.1:11434/api/tags", timeout=30
    ) as response:
        inventory = {
            row["name"]: row for row in json.load(response).get("models") or []
        }
    actual = inventory.get(frozen["ollama_tag"])
    if not actual or actual.get("digest") != frozen["digest"]:
        raise ValueError("V52 fixed Qwen3.5 4B model missing or digest mismatch")
    if actual.get("size") != frozen["blob_bytes"]:
        raise ValueError("V52 fixed model blob size mismatch")
    return {
        "model_tag": frozen["ollama_tag"],
        "digest": actual.get("digest"),
        "size": actual.get("size"),
        "details": actual.get("details") or {},
        "thinking": frozen["thinking"],
    }


def build_prompts(config, v51_config, v45_config, v44_lock):
    base = build_v45_system_prompts(v45_config, v44_lock)[
        "taxonomy_plus_discourse_signals_candidate"
    ]
    return {
        "v51_event_map_control": "\n\n".join(
            [base, v51_config["causal_change"]["candidate_instruction"]]
        ),
        "precise_target_mentions_candidate": "\n\n".join(
            [base, config["causal_change"]["candidate_instruction"]]
        ),
    }


def build_user_payload(condition, candidate_row, candidate, config, v45_config):
    payload = v45_user_payload(
        "taxonomy_plus_discourse_signals_candidate",
        candidate_row,
        candidate,
        v45_config,
    )
    if condition == "v51_event_map_control":
        payload["target_event_map"] = build_target_event_map(
            candidate_row["user_input"],
            candidate_row["candidates"],
            candidate["target_id"],
        )
    elif condition == "precise_target_mentions_candidate":
        payload["target_event_map"] = build_precise_target_event_map(
            candidate_row["user_input"],
            candidate_row["candidates"],
            candidate["target_id"],
            config["causal_change"]["target_mention_patterns"],
        )
    else:
        raise ValueError(f"Unknown V52 condition: {condition}")
    forbidden = set(config["causal_change"]["forbidden_fields"])
    if forbidden.intersection(payload) or forbidden.intersection(
        payload["target_event_map"]
    ):
        raise ValueError("V52 payload contains a forbidden answer field")
    return payload


def evaluate_representation_audit(audit, config, candidate_rows):
    gates = config["representation_gates"]
    contrast_row = next(
        row for row in candidate_rows if row["case_id"] == "v45h_negation_02"
    )
    contrast = build_precise_target_event_map(
        contrast_row["user_input"],
        contrast_row["candidates"],
        "gaze.right",
        config["causal_change"]["target_mention_patterns"],
    )
    observed = {
        row["target_id"]: row["target_mentions"][0]["text"]
        for row in contrast["ordered_grounded_occurrences"]
        if row["target_id"] in {"gaze.left", "gaze.right"}
    }
    checks = {
        "grounded_occurrence_mention_coverage": audit[
            "grounded_occurrence_mention_coverage"
        ]
        == gates["grounded_occurrence_mention_coverage"],
        "fallback_occurrence_count": audit["fallback_occurrence_count"]
        == gates["fallback_occurrence_count"],
        "mention_inside_predicate_evidence_rate": audit[
            "mention_inside_predicate_evidence_rate"
        ]
        == gates["mention_inside_predicate_evidence_rate"],
        "cross_target_mention_overlap_count": audit[
            "cross_target_mention_overlap_count"
        ]
        == gates["cross_target_mention_overlap_count"],
        "contrast_probe_focus_mentions": observed
        == gates["contrast_probe_focus_mentions"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "contrast_probe_observed": observed,
    }


def _run_judgment(
    condition, candidate_row, candidate, config, v45_config, prompts, snapshot
):
    payload = build_user_payload(
        condition, candidate_row, candidate, config, v45_config
    )
    messages = [
        {"role": "system", "content": prompts[condition]},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]
    frozen = config["fixed_model"]
    options = {
        "temperature": frozen["temperature"],
        "top_p": frozen["top_p"],
        "seed": frozen["seed"],
        "num_ctx": frozen["context_tokens"],
        "num_predict": frozen["maximum_output_tokens"],
    }
    model_info = {
        "condition": condition,
        "model_tag": snapshot["model_tag"],
        "blob_bytes": snapshot["size"],
        "thinking": snapshot["thinking"],
    }
    body = _chat_body(model_info, messages, options=options)
    body["format"] = SCHEMAS[config["fixed_carrier"]]
    response, elapsed, attempts, errors = _call_ollama(body)
    return {
        "response_message": response.get("message") or {},
        "parsed": parse_carrier_response(config["fixed_carrier"], response),
        "response_metrics": _response_metrics(response, elapsed),
        "transport_attempts": attempts,
        "prior_transport_errors": errors,
    }


def _checks(prompts):
    return {
        "runner_commit": _git_head(),
        "preregistration_sha256": _sha256(CONFIG_PATH),
        "dataset_sha256": _sha256(DATASET_PATH),
        "prompt_sha256": {
            condition: hashlib.sha256(prompt.encode()).hexdigest()
            for condition, prompt in prompts.items()
        },
    }


def _load_or_create(
    output, config, prompts, snapshot, candidate_rows, audit, audit_gate
):
    checks = _checks(prompts)
    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        for field, expected in checks.items():
            if report.get(field) != expected:
                raise ValueError(f"Existing V52 report {field} mismatch")
        return report
    return {
        "schema": "uruha_precise_target_mentions_development_raw_v52",
        "evidence_status": "development_only_on_retired_v45_holdout",
        "started_at": _now(),
        "completed_at": None,
        **checks,
        "conditions": list(CONDITIONS),
        "selected_carrier": config["fixed_carrier"],
        "model_snapshot": snapshot,
        "representation_audit": audit,
        "representation_gate": audit_gate,
        "candidate_rows": candidate_rows,
        "judgment_rows": [],
    }


def run(output=DEFAULT_OUTPUT):
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    config = load(CONFIG_PATH)
    v51_config = load(V51_CONFIG_PATH)
    v45_config = load(V45_CONFIG_PATH)
    v44_lock = load(V44_LOCK_PATH)
    dataset = load(DATASET_PATH)
    _validate_inputs(config, dataset)
    candidate_rows = build_candidate_rows(dataset)
    target_count = sum(len(row["candidates"]) for row in candidate_rows)
    if target_count != config["frozen_inputs"]["grounded_target_count"]:
        raise ValueError("V52 grounded candidate count drift")
    audit = audit_precise_event_maps(
        candidate_rows, config["causal_change"]["target_mention_patterns"]
    )
    audit_gate = evaluate_representation_audit(audit, config, candidate_rows)
    if not audit_gate["passed"]:
        raise ValueError(
            f"V52 representation gate failed before inference: "
            f"{audit_gate['failed_checks']}"
        )
    snapshot = _model_snapshot(config)
    prompts = build_prompts(config, v51_config, v45_config, v44_lock)
    report = _load_or_create(
        output, config, prompts, snapshot, candidate_rows, audit, audit_gate
    )
    completed = {
        (row["condition"], row["case_id"], row["target_id"])
        for row in report["judgment_rows"]
    }
    total = config["expected_judgment_count"]
    for condition in CONDITIONS:
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
                            config,
                            v45_config,
                            prompts,
                            snapshot,
                        ),
                    }
                )
                _atomic_write(output, report)
                print(
                    f"[v52 {len(report['judgment_rows'])}/{total}] "
                    f"{condition} {candidate_row['case_id']} {candidate['target_id']}",
                    flush=True,
                )
        _unload_model(snapshot["model_tag"])
    if len(report["judgment_rows"]) == total:
        report["completed_at"] = _now()
    _atomic_write(output, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(
        json.dumps(
            {
                "rows": len(report["judgment_rows"]),
                "representation_gate_passed": report["representation_gate"]["passed"],
                "completed_at": report["completed_at"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
