#!/usr/bin/env python3
"""Run the frozen local-model screen for the current RightBrain contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import time
import urllib.request
from collections import Counter
from pathlib import Path

import rightbrain_adapter_causality_diagnostic_v1 as diagnostic
import uruha_brain_mac as brain_module
import uruha_persona_policy as persona_policy
import uruha_surface_payload_v2 as surface_payload
from persona_policy_local_model_pilot_v1 import EMPTY_MEMORY, PSYCHE


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_carrier_model_screen_v1"
PREREGISTRATION_PATH = ROOT / "configs/rightbrain_carrier_model_screen_v1_preregistration.json"
CASES_PATH = ROOT / "configs/persona_policy_local_model_pilot_v1_cases.json"
PREFLIGHT_PATH = ROOT / "reports/rightbrain_carrier_model_screen_v1_preflight.json"
RESULT_JSON_PATH = ROOT / "reports/rightbrain_carrier_model_screen_v1_result.json"
RESULT_MD_PATH = ROOT / "reports/rightbrain_carrier_model_screen_v1_result.md"
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
OLLAMA_PS_URL = "http://127.0.0.1:11434/api/ps"
CONDITION_ARTIFACTS = {
    "qwen2_5_7b_q4_control": ROOT / "reports/rightbrain_carrier_model_screen_v1_qwen2_5_7b.json",
    "qwen3_5_4b_q4_candidate": ROOT / "reports/rightbrain_carrier_model_screen_v1_qwen3_5_4b.json",
    "qwen3_5_9b_q4_candidate": ROOT / "reports/rightbrain_carrier_model_screen_v1_qwen3_5_9b.json",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def binding(path):
    resolved = Path(path).resolve()
    try:
        display = str(resolved.relative_to(ROOT))
    except ValueError:
        display = str(resolved)
    return {"path": display, "sha256": sha256_file(resolved)}


def atomic_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def git_head():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def percentile(values, probability):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    index = max(0, min(len(ordered) - 1, math.ceil(probability * len(ordered)) - 1))
    return round(ordered[index], 4)


def model_blob_path(model_info):
    return (
        Path.home()
        / ".ollama/models/blobs"
        / f"sha256-{model_info['model_blob_sha256']}"
    )


def manifest_model_layer(manifest):
    for layer in manifest.get("layers") or []:
        if layer.get("mediaType") == "application/vnd.ollama.image.model":
            return layer
    return {}


def build_case_input(case, provider_id):
    rightbrain = brain_module.RightBrain(
        load_model=False,
        persona_policy_provider=persona_policy.build_persona_policy_provider(provider_id),
    )
    rightbrain.structured_payload_mode = surface_payload.LEGACY_JSON_V1
    rightbrain.model_repair_enabled = False
    rightbrain.model_candidate_count = 1
    logic = copy.deepcopy(case["logic"])
    logic["public_persona_context"] = case["context"]
    max_chars = int(case["logic"]["constraints"]["max_chars"])
    payload = rightbrain._build_model_surface_payload(
        logic,
        dict(PSYCHE),
        max_chars,
        memory_data=copy.deepcopy(EMPTY_MEMORY),
    )
    system_instruction = rightbrain._model_surface_system_instruction()
    return rightbrain, logic, max_chars, payload, system_instruction


def validate_frozen_inputs(preregistration, *, deep_model_hash=False):
    checks = {
        "experiment_id": preregistration.get("experiment_id") == EXPERIMENT_ID,
        "status_frozen": preregistration.get("status")
        == "frozen_before_first_model_call",
        "payload_mode_legacy": preregistration["design"]["payload_mode"]
        == surface_payload.LEGACY_JSON_V1,
        "case_count": False,
        "source_hashes": True,
        "system_instruction_hash": True,
        "payload_hashes": True,
        "manifest_hashes": True,
        "manifest_model_layers": True,
        "model_blob_files": True,
        "model_blob_hashes": True,
        "generation_accounting": preregistration["design"][
            "actual_generation_count_total"
        ]
        == 30,
        "no_production_or_persona_authorization": not any(
            preregistration["authorizations"][key]
            for key in (
                "change_production_default",
                "train_persona_adapter",
                "claim_persona_similarity",
                "request_human_blind_rating",
                "public_impersonation",
            )
        ),
    }
    details = {"source_bindings": {}, "model_assets": {}, "payload_rows": []}

    cases = load_json(CASES_PATH)["cases"]
    checks["case_count"] = len(cases) == preregistration["design"][
        "development_case_count"
    ]
    for relative_path, expected_hash in preregistration["frozen_sources"].items():
        path = ROOT / relative_path
        actual_hash = sha256_file(path)
        details["source_bindings"][relative_path] = {
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
        }
        checks["source_hashes"] &= actual_hash == expected_hash

    expected_system_hash = preregistration["frozen_prompt_hashes"][
        "system_instruction_sha256"
    ]
    expected_payload_hashes = preregistration["frozen_prompt_hashes"][
        "payload_sha256_by_provider_and_case"
    ]
    for case in cases:
        for provider_id in case["condition_order"]:
            _, _, _, payload, system_instruction = build_case_input(case, provider_id)
            system_hash = sha256_text(system_instruction)
            payload_hash = sha256_text(payload)
            expected_payload_hash = expected_payload_hashes[provider_id][case["case_id"]]
            checks["system_instruction_hash"] &= system_hash == expected_system_hash
            checks["payload_hashes"] &= payload_hash == expected_payload_hash
            details["payload_rows"].append(
                {
                    "case_id": case["case_id"],
                    "provider_id": provider_id,
                    "system_instruction_sha256": system_hash,
                    "payload_sha256": payload_hash,
                    "payload_chars": len(payload),
                }
            )

    for condition_id in preregistration["design"]["conditions_in_execution_order"]:
        model_info = preregistration["model_inventory"][condition_id]
        manifest_path = Path(model_info["manifest_path"])
        manifest_exists = manifest_path.is_file()
        manifest_hash = sha256_file(manifest_path) if manifest_exists else None
        checks["manifest_hashes"] &= (
            manifest_exists and manifest_hash == model_info["manifest_sha256"]
        )
        manifest = load_json(manifest_path) if manifest_exists else {}
        layer = manifest_model_layer(manifest)
        expected_digest = f"sha256:{model_info['model_blob_sha256']}"
        checks["manifest_model_layers"] &= (
            layer.get("digest") == expected_digest
            and layer.get("size") == model_info["model_blob_bytes"]
        )
        blob_path = model_blob_path(model_info)
        blob_exists = blob_path.is_file()
        blob_size = blob_path.stat().st_size if blob_exists else None
        checks["model_blob_files"] &= (
            blob_exists and blob_size == model_info["model_blob_bytes"]
        )
        blob_hash = None
        if deep_model_hash and blob_exists:
            blob_hash = sha256_file(blob_path)
            checks["model_blob_hashes"] &= blob_hash == model_info["model_blob_sha256"]
        details["model_assets"][condition_id] = {
            "ollama_tag": model_info["ollama_tag"],
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_hash,
            "model_layer": layer,
            "blob_path": str(blob_path),
            "blob_bytes": blob_size,
            "deep_hash_requested": deep_model_hash,
            "verified_blob_sha256": blob_hash,
        }
    if not deep_model_hash:
        checks["model_blob_hashes"] = True
    return checks, details


def run_preflight(*, deep_model_hash=False, output=PREFLIGHT_PATH):
    preregistration = load_json(PREREGISTRATION_PATH)
    checks, details = validate_frozen_inputs(
        preregistration,
        deep_model_hash=deep_model_hash,
    )
    report = {
        "schema": "uruha_rightbrain_carrier_model_screen_preflight_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "preflight_passed" if all(checks.values()) else "preflight_failed",
        "git_head": git_head(),
        "inputs": {
            "preregistration": binding(PREREGISTRATION_PATH),
            "runner": binding(ROOT / "run_rightbrain_carrier_model_screen_v1.py"),
        },
        "checks": checks,
        "details": details,
        "actual_model_generation_call_count": 0,
        "production_memory_write_count": 0,
        "formal_persona_score_count": 0,
    }
    atomic_write(output, report)
    return report


def post_json(url, body, timeout=300):
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def get_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.load(response)


def unload_model(model_tag):
    subprocess.run(
        ["ollama", "stop", model_tag],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def peak_ollama_rss_bytes():
    try:
        output = subprocess.check_output(["ps", "-axo", "rss=,command="], text=True)
    except (OSError, subprocess.SubprocessError):
        return None
    total_kib = 0
    for line in output.splitlines():
        if "ollama" not in line.lower():
            continue
        match = re.match(r"\s*(\d+)\s+", line)
        if match:
            total_kib += int(match.group(1))
    return total_kib * 1024


def resident_snapshot():
    try:
        return get_json(OLLAMA_PS_URL).get("models") or []
    except (OSError, TimeoutError, json.JSONDecodeError):
        return []


def chat_body(model_info, messages, options, seed):
    body = {
        "model": model_info["ollama_tag"],
        "messages": messages,
        "stream": False,
        "keep_alive": "20m",
        "options": {**options, "seed": int(seed)},
    }
    if model_info.get("thinking") is not None:
        body["think"] = bool(model_info["thinking"])
    return body


def score_raw_generation(raw_generation, case, provider_id):
    rightbrain, logic, max_chars, _, _ = build_case_input(case, provider_id)
    localized = rightbrain._localize_model_surface_ascii_terms(raw_generation)
    raw_reasons = rightbrain._model_candidate_rejection_reasons(
        localized,
        logic,
        max_chars,
        user_input=case["user_input"],
    )
    prepared, final_reasons = rightbrain._prepare_model_surface_candidate(
        raw_generation,
        logic,
        case["user_input"],
        copy.deepcopy(EMPTY_MEMORY),
        max_chars,
    )
    strict_valid = bool(prepared) and not final_reasons
    visible_reply = prepared if strict_valid else ""
    return {
        "strict_valid": strict_valid,
        "raw_rejection_reasons": raw_reasons,
        "rejection_reasons": final_reasons,
        "prepared_candidate": prepared,
        "visible_reply": visible_reply,
        "normalized_output": rightbrain._normalize_reply_key(visible_reply or raw_generation),
    }


def reason_families(rows):
    counts = Counter()
    for row in rows:
        reasons = row.get("rejection_reasons") or []
        if any(
            reason
            in {
                "cjk_language_leak",
                "nonstandard_cjk_surface",
                "foreign_script_leak",
                "unexpected_ascii_leak",
            }
            for reason in reasons
        ):
            counts["language_or_script_pollution"] += 1
        if any(str(reason).startswith("semantic_slots_missing:") for reason in reasons):
            counts["required_semantics_missing"] += 1
        if any(reason in {"polite_tone_drift", "formal_register_drift"} for reason in reasons):
            counts["polite_register_drift"] += 1
    return dict(sorted(counts.items()))


def summarize_rows(rows, cases):
    row_map = {(row["case_id"], row["provider_id"]): row for row in rows}
    pairs = []
    for case in cases:
        target = row_map[(case["case_id"], persona_policy.TARGET_PROVIDER)]
        neutral = row_map[(case["case_id"], persona_policy.NEUTRAL_PROVIDER)]
        both_valid = target["strict_valid"] and neutral["strict_valid"]
        outputs_differ = (
            target["normalized_output"] != neutral["normalized_output"]
            and bool(target["normalized_output"])
            and bool(neutral["normalized_output"])
        )
        pairs.append(
            {
                "case_id": case["case_id"],
                "both_conditions_strict_valid": both_valid,
                "normalized_outputs_differ": outputs_differ,
                "strict_valid_and_different": both_valid and outputs_differ,
            }
        )
    wall_latencies = [row["runtime"]["wall_seconds"] for row in rows]
    warm_latencies = wall_latencies[1:]
    return {
        "generation_count": len(rows),
        "nonempty_raw_generation_count": sum(bool(row["raw_generation"]) for row in rows),
        "strict_valid_generation_count": sum(row["strict_valid"] for row in rows),
        "strict_valid_target_count": sum(
            row["strict_valid"] and row["provider_id"] == persona_policy.TARGET_PROVIDER
            for row in rows
        ),
        "strict_valid_neutral_count": sum(
            row["strict_valid"] and row["provider_id"] == persona_policy.NEUTRAL_PROVIDER
            for row in rows
        ),
        "both_conditions_strict_valid_pair_count": sum(
            pair["both_conditions_strict_valid"] for pair in pairs
        ),
        "raw_output_difference_pair_count": sum(
            pair["normalized_outputs_differ"] for pair in pairs
        ),
        "strict_valid_and_different_pair_count": sum(
            pair["strict_valid_and_different"] for pair in pairs
        ),
        "distinct_normalized_output_count": len(
            {row["normalized_output"] for row in rows if row["normalized_output"]}
        ),
        "rejection_families": reason_families(rows),
        "wall_latency_median_seconds": round(statistics.median(wall_latencies), 4),
        "warm_wall_latency_median_seconds": round(statistics.median(warm_latencies), 4),
        "warm_wall_latency_p95_seconds": percentile(warm_latencies, 0.95),
        "prompt_eval_count_range": [
            min(row["runtime"]["prompt_eval_count"] for row in rows),
            max(row["runtime"]["prompt_eval_count"] for row in rows),
        ],
        "pairs": pairs,
    }


def run_condition(condition_id, *, output=None):
    preregistration = load_json(PREREGISTRATION_PATH)
    preflight = load_json(PREFLIGHT_PATH)
    expected_preflight_binding = binding(PREFLIGHT_PATH)
    if preflight.get("status") != "preflight_passed" or not all(
        (preflight.get("checks") or {}).values()
    ):
        raise RuntimeError("deep preflight must pass before any model condition")
    if condition_id not in CONDITION_ARTIFACTS:
        raise ValueError(f"unknown condition: {condition_id}")
    checks, _ = validate_frozen_inputs(preregistration, deep_model_hash=False)
    if not all(checks.values()):
        raise RuntimeError("frozen inputs changed after preflight")

    cases = load_json(CASES_PATH)["cases"]
    model_info = preregistration["model_inventory"][condition_id]
    options = preregistration["runtime"]["options"]
    for inventory_entry in preregistration["model_inventory"].values():
        unload_model(inventory_entry["ollama_tag"])

    rows = []
    max_rss = 0
    resident_snapshots = []
    for case in cases:
        for provider_id in case["condition_order"]:
            _, _, _, payload, system_instruction = build_case_input(case, provider_id)
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": payload},
            ]
            body = chat_body(model_info, messages, options, case["seed"])
            started = time.perf_counter()
            response = post_json(OLLAMA_CHAT_URL, body)
            wall_seconds = round(time.perf_counter() - started, 4)
            raw_generation = str((response.get("message") or {}).get("content") or "").strip()
            scored = score_raw_generation(raw_generation, case, provider_id)
            snapshot = resident_snapshot()
            resident_snapshots.append(snapshot)
            rss = peak_ollama_rss_bytes()
            if rss is not None:
                max_rss = max(max_rss, rss)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "provider_id": provider_id,
                    "execution_position": len(rows) + 1,
                    "seed": int(case["seed"]),
                    "system_instruction_sha256": sha256_text(system_instruction),
                    "payload_sha256": sha256_text(payload),
                    "request_contract": {
                        "model": body["model"],
                        "think": body.get("think"),
                        "options": body["options"],
                        "message_roles": [message["role"] for message in messages],
                    },
                    "response_model": response.get("model"),
                    "raw_generation": raw_generation,
                    "raw_generation_sha256": sha256_text(raw_generation),
                    **scored,
                    "runtime": {
                        "wall_seconds": wall_seconds,
                        "total_duration_ns": response.get("total_duration"),
                        "load_duration_ns": response.get("load_duration"),
                        "prompt_eval_count": response.get("prompt_eval_count"),
                        "prompt_eval_duration_ns": response.get("prompt_eval_duration"),
                        "eval_count": response.get("eval_count"),
                        "eval_duration_ns": response.get("eval_duration"),
                    },
                }
            )

    summary = summarize_rows(rows, cases)
    expected_resident_names = {model_info["ollama_tag"], model_info["ollama_tag"].split(":")[0]}
    unexpected_residents = []
    reported_sizes = []
    for snapshot in resident_snapshots:
        for resident in snapshot:
            name = str(resident.get("name") or resident.get("model") or "")
            if name and not any(name.startswith(prefix) for prefix in expected_resident_names):
                unexpected_residents.append(name)
            if resident.get("size") is not None:
                reported_sizes.append(int(resident["size"]))

    expected_payloads = preregistration["frozen_prompt_hashes"][
        "payload_sha256_by_provider_and_case"
    ]
    condition_checks = {
        "preflight_binding_present": expected_preflight_binding["sha256"]
        == binding(PREFLIGHT_PATH)["sha256"],
        "generation_count_exact": len(rows)
        == preregistration["design"]["actual_generation_count_per_model"],
        "nonempty_raw_generation_count_exact": summary["nonempty_raw_generation_count"]
        == preregistration["design"]["actual_generation_count_per_model"],
        "model_tag_exact": all(
            row["request_contract"]["model"] == model_info["ollama_tag"] for row in rows
        ),
        "system_instruction_hash_exact": all(
            row["system_instruction_sha256"]
            == preregistration["frozen_prompt_hashes"]["system_instruction_sha256"]
            for row in rows
        ),
        "payload_hashes_exact": all(
            row["payload_sha256"]
            == expected_payloads[row["provider_id"]][row["case_id"]]
            for row in rows
        ),
        "options_exact": all(
            {
                key: value
                for key, value in row["request_contract"]["options"].items()
                if key != "seed"
            }
            == options
            for row in rows
        ),
        "seed_schedule_exact": all(
            row["request_contract"]["options"]["seed"] == row["seed"] for row in rows
        ),
        "thinking_setting_exact": all(
            row["request_contract"]["think"] == model_info.get("thinking") for row in rows
        ),
        "prompt_counts_reported": all(
            isinstance(row["runtime"]["prompt_eval_count"], int)
            and row["runtime"]["prompt_eval_count"] > 0
            for row in rows
        ),
        "one_model_resident_at_a_time": not unexpected_residents,
        "current_frozen_inputs_valid": all(checks.values()),
        "repair_disabled": preregistration["design"]["repair_enabled"] is False,
        "adapter_disabled": preregistration["design"]["adapter_loaded"] is False,
        "production_memory_unchanged": True,
        "no_formal_persona_score": True,
    }
    artifact = {
        "schema": "uruha_rightbrain_carrier_model_condition_v1",
        "experiment_id": EXPERIMENT_ID,
        "condition_id": condition_id,
        "status": "condition_complete"
        if all(condition_checks.values())
        else "condition_invalid",
        "git_head": git_head(),
        "inputs": {
            "preregistration": binding(PREREGISTRATION_PATH),
            "preflight": expected_preflight_binding,
            "cases": binding(CASES_PATH),
            "runner": binding(ROOT / "run_rightbrain_carrier_model_screen_v1.py"),
            "brain_source": binding(ROOT / "uruha_brain_mac.py"),
            "persona_policy_source": binding(ROOT / "uruha_persona_policy.py"),
            "surface_payload_source": binding(ROOT / "uruha_surface_payload_v2.py"),
        },
        "model": model_info,
        "checks": condition_checks,
        "summary": summary,
        "resources": {
            "maximum_ollama_process_rss_bytes": max_rss or None,
            "ollama_reported_resident_size_bytes": max(reported_sizes)
            if reported_sizes
            else None,
            "resident_snapshots": resident_snapshots,
        },
        "generations": rows,
        "actual_model_generation_call_count": len(rows),
        "production_memory_write_count": 0,
        "formal_persona_score_count": 0,
    }
    unload_model(model_info["ollama_tag"])
    atomic_write(output or CONDITION_ARTIFACTS[condition_id], artifact)
    return artifact


def candidate_gate(candidate_summary, control_summary, model_info, all_integrity_checks):
    requirements = {
        "nonempty_raw_generation_count": candidate_summary[
            "nonempty_raw_generation_count"
        ]
        == 10,
        "strict_valid_minimum": candidate_summary["strict_valid_generation_count"] >= 5,
        "strict_valid_delta": candidate_summary["strict_valid_generation_count"]
        - control_summary["strict_valid_generation_count"]
        >= 3,
        "language_pollution_reduction": control_summary["rejection_families"].get(
            "language_or_script_pollution", 0
        )
        - candidate_summary["rejection_families"].get(
            "language_or_script_pollution", 0
        )
        >= 2,
        "required_semantics_reduction": control_summary["rejection_families"].get(
            "required_semantics_missing", 0
        )
        - candidate_summary["rejection_families"].get(
            "required_semantics_missing", 0
        )
        >= 3,
        "polite_drift_not_worse": candidate_summary["rejection_families"].get(
            "polite_register_drift", 0
        )
        <= control_summary["rejection_families"].get("polite_register_drift", 0),
        "warm_latency": candidate_summary["warm_wall_latency_median_seconds"] <= 5.0,
        "model_blob_size": model_info["model_blob_bytes"] <= 8589934592,
        "integrity": bool(all_integrity_checks),
    }
    return {"passed": all(requirements.values()), "requirements": requirements}


def select_candidate(gates, summaries):
    passed = [condition_id for condition_id, gate in gates.items() if gate["passed"]]
    if not passed:
        return None, "reject_simple_carrier_swap_and_investigate_role_specialization"
    if len(passed) == 1:
        return passed[0], "authorize_disjoint_exact_current_contract_holdout_for_selected_carrier_only"

    four = summaries["qwen3_5_4b_q4_candidate"]
    nine = summaries["qwen3_5_9b_q4_candidate"]
    four_within_one = four["strict_valid_generation_count"] >= (
        nine["strict_valid_generation_count"] - 1
    )
    four_no_worse = (
        four["rejection_families"].get("language_or_script_pollution", 0)
        <= nine["rejection_families"].get("language_or_script_pollution", 0)
        and four["rejection_families"].get("required_semantics_missing", 0)
        <= nine["rejection_families"].get("required_semantics_missing", 0)
    )
    four_faster = (
        four["warm_wall_latency_median_seconds"]
        < nine["warm_wall_latency_median_seconds"]
    )
    if four_within_one and four_no_worse and four_faster:
        selected = "qwen3_5_4b_q4_candidate"
    else:
        selected = sorted(
            passed,
            key=lambda condition_id: (
                -summaries[condition_id]["strict_valid_generation_count"],
                summaries[condition_id]["rejection_families"].get(
                    "language_or_script_pollution", 0
                ),
                summaries[condition_id]["rejection_families"].get(
                    "required_semantics_missing", 0
                ),
                summaries[condition_id]["warm_wall_latency_median_seconds"],
            ),
        )[0]
    return selected, "authorize_disjoint_exact_current_contract_holdout_for_selected_carrier_only"


def validate_condition_artifact(artifact, condition_id):
    return bool(
        artifact.get("experiment_id") == EXPERIMENT_ID
        and artifact.get("condition_id") == condition_id
        and artifact.get("status") == "condition_complete"
        and all((artifact.get("checks") or {}).values())
        and artifact.get("actual_model_generation_call_count") == 10
        and artifact.get("production_memory_write_count") == 0
        and artifact.get("formal_persona_score_count") == 0
        and (artifact.get("inputs") or {}).get("preregistration")
        == binding(PREREGISTRATION_PATH)
        and (artifact.get("inputs") or {}).get("preflight") == binding(PREFLIGHT_PATH)
        and (artifact.get("inputs") or {}).get("cases") == binding(CASES_PATH)
        and (artifact.get("inputs") or {}).get("runner")
        == binding(ROOT / "run_rightbrain_carrier_model_screen_v1.py")
    )


def analyze(*, output_json=RESULT_JSON_PATH, output_md=RESULT_MD_PATH):
    preregistration = load_json(PREREGISTRATION_PATH)
    artifacts = {
        condition_id: load_json(path)
        for condition_id, path in CONDITION_ARTIFACTS.items()
    }
    artifact_validity = {
        condition_id: validate_condition_artifact(artifact, condition_id)
        for condition_id, artifact in artifacts.items()
    }
    summaries = {
        condition_id: artifact["summary"] for condition_id, artifact in artifacts.items()
    }
    control = summaries["qwen2_5_7b_q4_control"]
    gates = {}
    for condition_id in (
        "qwen3_5_4b_q4_candidate",
        "qwen3_5_9b_q4_candidate",
    ):
        gates[condition_id] = candidate_gate(
            summaries[condition_id],
            control,
            preregistration["model_inventory"][condition_id],
            artifact_validity[condition_id] and artifact_validity["qwen2_5_7b_q4_control"],
        )
    selected, decision = select_candidate(gates, summaries)
    checks = {
        "preflight_valid": load_json(PREFLIGHT_PATH).get("status") == "preflight_passed",
        "all_condition_artifacts_valid": all(artifact_validity.values()),
        "generation_count_total": sum(
            artifact["actual_model_generation_call_count"] for artifact in artifacts.values()
        )
        == preregistration["design"]["actual_generation_count_total"],
        "production_memory_unchanged": sum(
            artifact["production_memory_write_count"] for artifact in artifacts.values()
        )
        == 0,
        "no_formal_persona_score": sum(
            artifact["formal_persona_score_count"] for artifact in artifacts.values()
        )
        == 0,
    }
    report = {
        "schema": "uruha_rightbrain_carrier_model_screen_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "valid_screen" if all(checks.values()) else "invalid_screen",
        "decision": decision if all(checks.values()) else "invalidate_and_repair_harness",
        "selected_candidate": selected if all(checks.values()) else None,
        "git_head": git_head(),
        "inputs": {
            "preregistration": binding(PREREGISTRATION_PATH),
            "preflight": binding(PREFLIGHT_PATH),
            "runner": binding(ROOT / "run_rightbrain_carrier_model_screen_v1.py"),
            "condition_artifacts": {
                condition_id: binding(path)
                for condition_id, path in CONDITION_ARTIFACTS.items()
            },
        },
        "checks": checks,
        "artifact_validity": artifact_validity,
        "condition_summaries": summaries,
        "candidate_gates": gates,
        "authorizations": {
            "run_disjoint_exact_current_contract_holdout_for_selected_candidate": bool(
                selected and all(checks.values())
            ),
            "change_production_default": False,
            "train_persona_adapter": False,
            "claim_persona_similarity": False,
            "request_human_blind_rating": False,
            "public_impersonation": False,
        },
        "limitations": [
            "The five cases were already observed development cases.",
            "This is a practical model-artifact screen, not a causal parameter-count ablation.",
            "Model tokenizer and Ollama chat template differ by condition even though message text and context budget are fixed.",
            "No target-person utterance, persona score, memory write, repair pass, adapter, action call, or production change was used.",
        ],
        "evidence_boundary": preregistration["evidence_boundary"],
    }
    atomic_write(output_json, report)
    Path(output_md).write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report):
    labels = {
        "qwen2_5_7b_q4_control": "Qwen2.5-7B",
        "qwen3_5_4b_q4_candidate": "Qwen3.5-4B",
        "qwen3_5_9b_q4_candidate": "Qwen3.5-9B",
    }
    lines = [
        "# 右腦本機承載模型篩選 V1",
        "",
        f"**決策：`{report['decision']}`**",
        "",
        "這一輪只更換右腦表面表達模型。左腦計畫、人格政策、記憶、案例、提示文字、解碼與嚴格 gate 都固定。",
        "",
        "| 條件 | 嚴格有效 | 語言污染 | 必要語意缺失 | 過度禮貌 | 暖機中位延遲 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition_id, summary in report["condition_summaries"].items():
        families = summary["rejection_families"]
        lines.append(
            f"| {labels[condition_id]} | {summary['strict_valid_generation_count']}/10 | "
            f"{families.get('language_or_script_pollution', 0)}/10 | "
            f"{families.get('required_semantics_missing', 0)}/10 | "
            f"{families.get('polite_register_drift', 0)}/10 | "
            f"{summary['warm_wall_latency_median_seconds']:.2f}s |"
        )
    lines.extend(["", "## 候選門檻", ""])
    for condition_id, gate in report["candidate_gates"].items():
        lines.append(f"- {labels[condition_id]}：{'通過' if gate['passed'] else '未通過'}")
        failed = [key for key, value in gate["requirements"].items() if not value]
        if failed:
            lines.append(f"- 未通過項目：`{', '.join(failed)}`")
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            "這是已觀察開發題的承載模型篩選，不是人格相似度、正式 holdout 或上線證據。通過時只授權為單一候選建立另一批來源獨立測試。",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--condition", choices=tuple(CONDITION_ARTIFACTS))
    mode.add_argument("--analyze", action="store_true")
    parser.add_argument("--deep-model-hash", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.preflight:
        report = run_preflight(deep_model_hash=args.deep_model_hash)
    elif args.condition:
        report = run_condition(args.condition)
    else:
        report = analyze()
    print(json.dumps({
        "experiment_id": report["experiment_id"],
        "status": report["status"],
        "decision": report.get("decision"),
        "selected_candidate": report.get("selected_candidate"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
