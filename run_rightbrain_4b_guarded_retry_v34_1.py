#!/usr/bin/env python3
"""Run a single guarded retry for failed V34 4B development rows."""

import argparse
import hashlib
import json
import os
import subprocess
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from run_rightbrain_qwen35_migration_v33 import (
    _call_ollama,
    _chat_body,
    _response_metrics,
    _unload_model,
    score_rightbrain_output,
)


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "rightbrain_4b_guarded_retry_v34_1_preregistration.json"
SOURCE_RAW_PATH = ROOT / "reports" / "rightbrain_role_ladder_v34_pilot_raw.json"
DATASET_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"
DEFAULT_OUTPUT = ROOT / "reports" / "rightbrain_4b_guarded_retry_v34_1_raw.json"
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
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _selection_key(score):
    return (
        int(score["semantic_group_hit_count"]),
        int(not score["private_memory_intrusion"]),
        int(not score["hard_surface_failure"]),
        -len(score["current_gate_rejection_reasons"]),
    )


def _select_attempt(first, retry=None):
    if first["score"]["current_gate_raw_pass"]:
        return "first", first
    if retry and retry["score"]["current_gate_raw_pass"]:
        return "retry", retry
    candidates = [("first", first)]
    if retry:
        candidates.append(("retry", retry))
    return max(candidates, key=lambda item: _selection_key(item[1]["score"]))


def run(output=DEFAULT_OUTPUT):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if _sha256(SOURCE_RAW_PATH) != config["source_raw_report_sha256"]:
        raise ValueError("V34 source raw report hash mismatch")
    source = json.loads(SOURCE_RAW_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in dataset["rightbrain_cases"]}
    condition = config["known_result"]["condition"]
    first_rows = [row for row in source["rows"] if row["condition"] == condition]
    if len(first_rows) != config["known_result"]["row_count"]:
        raise ValueError("Unexpected V34 4B source row count")

    if output.exists():
        report = json.loads(output.read_text(encoding="utf-8"))
        if report["preregistration_sha256"] != _sha256(CONFIG_PATH):
            raise ValueError("Existing guarded retry preregistration hash mismatch")
        if report["runner_commit"] != _git_head():
            raise ValueError("Existing guarded retry runner commit mismatch")
    else:
        report = {
            "schema": "uruha_rightbrain_4b_guarded_retry_raw_v34_1",
            "evidence_status": "post_pilot_development_not_confirmation",
            "started_at": _now(),
            "completed_at": None,
            "runner_commit": _git_head(),
            "preregistration_sha256": _sha256(CONFIG_PATH),
            "source_raw_report_sha256": _sha256(SOURCE_RAW_PATH),
            "rows": [],
        }

    existing = {(row["case_id"], row["seed"]) for row in report["rows"]}
    os.environ["URUHA_SKIP_AUTO_VENV"] = "1"
    from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain

    brain = RightBrain(load_model=False)
    model = config["intervention"]["model"]
    retry_sampling = config["intervention"]["retry_sampling"]
    model_info = {
        "condition": condition,
        "model_tag": model["ollama_tag"],
        "blob_bytes": model["blob_bytes"],
        "thinking": model.get("thinking"),
    }

    for index, first in enumerate(first_rows, start=1):
        key = (first["case_id"], first["seed"])
        if key in existing:
            continue
        case = cases[first["case_id"]]
        retry = None
        if not first["score"]["current_gate_raw_pass"]:
            logic = deepcopy(case["logic"])
            max_chars = int((logic.get("constraints") or {}).get("max_chars") or 48)
            payload = brain._build_model_surface_payload(
                logic,
                deepcopy(case.get("psyche") or {}),
                max_chars,
                memory_data=deepcopy(case.get("memory_data") or {}),
            )
            messages = [
                {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
                {"role": "user", "content": payload},
            ]
            options = {
                "temperature": retry_sampling["temperature"],
                "top_p": retry_sampling["top_p"],
                "top_k": retry_sampling["top_k"],
                "repeat_penalty": retry_sampling["repeat_penalty"],
                "seed": first["seed"] + retry_sampling["seed_offset"],
                "num_ctx": retry_sampling["context_tokens"],
                "num_predict": retry_sampling["maximum_output_tokens"],
            }
            response, elapsed, attempts, errors = _call_ollama(
                _chat_body(model_info, messages, options=options)
            )
            raw_reply = str((response.get("message") or {}).get("content") or "").strip()
            retry = {
                "raw_reply": raw_reply,
                "sampling": options,
                "score": score_rightbrain_output(brain, case, logic, raw_reply),
                "response_metrics": _response_metrics(response, elapsed),
                "transport_attempts": attempts,
                "prior_transport_errors": errors,
            }
        selected_source, selected = _select_attempt(first, retry)
        report["rows"].append(
            {
                "case_id": first["case_id"],
                "category": first["category"],
                "seed": first["seed"],
                "first": first,
                "retry": retry,
                "selected_source": selected_source,
                "selected_raw_reply": selected["raw_reply"],
                "selected_score": selected["score"],
                "total_wall_seconds": round(
                    first["response_metrics"]["wall_seconds"]
                    + (retry["response_metrics"]["wall_seconds"] if retry else 0.0),
                    6,
                ),
            }
        )
        _atomic_write(output, report)
        print(
            f"[{index}/{len(first_rows)}] {first['case_id']} retry={retry is not None} selected={selected_source}",
            flush=True,
        )

    if len(report["rows"]) == len(first_rows):
        report["completed_at"] = _now()
    _atomic_write(output, report)
    _unload_model(model["ollama_tag"])
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps({"rows": len(report["rows"]), "completed_at": report["completed_at"]}, indent=2))


if __name__ == "__main__":
    main()
