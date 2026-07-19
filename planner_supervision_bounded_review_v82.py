"""Bounded matched proxy review for full and executable planner views."""

from __future__ import annotations

import copy
import json
import subprocess
import time
from collections import Counter, defaultdict

import planner_supervision_executable_view_v81 as v81
import planner_supervision_pilot_review_v79 as v79
import planner_supervision_v76 as v76


OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
C0 = v81.C0
T1 = v81.T1
VARIANT_ORIGINAL = v81.VARIANT_ORIGINAL
VARIANT_MUTATION = v81.VARIANT_MUTATION


def installed_model_digests():
    return v81.installed_model_digests()


def _pilot_binding(unit):
    return {
        "candidate_binding_sha256": unit["candidate_binding_sha256"],
        "session_binding_sha256": unit["session_binding_sha256"],
        "scenario_family": unit["scenario_family"],
    }


def build_packets(candidates, manifest_rows, frozen_v79_units, v81_packets, contract):
    selection = contract["selection"]
    eligible, current_v79_units = v79.select_pilot(
        candidates,
        manifest_rows,
        budget=int(selection["v79_count"]),
        seed=selection["v79_validation_seed"],
    )
    if [_pilot_binding(row) for row in current_v79_units] != [_pilot_binding(row) for row in frozen_v79_units]:
        raise ValueError("V82 source validation does not preserve the frozen V79 pilot")
    if len(v81_packets) != int(selection["v81_count"]):
        raise ValueError("V82 exclusion source does not contain the frozen V81 packet count")
    eligible_ids = {row["id"] for row in eligible}
    v79_ids = {row["candidate_id"] for row in frozen_v79_units}
    v81_ids = {row["candidate_id"] for row in v81_packets}
    if v79_ids.intersection(v81_ids):
        raise ValueError("V82 exclusion sources overlap")
    if not (v79_ids | v81_ids).issubset(eligible_ids):
        raise ValueError("V82 exclusion source contains an ineligible candidate")
    fresh_candidates = v81.select_disjoint_holdout(
        eligible,
        v79_ids | v81_ids,
        budget=int(selection["fresh_count"]),
        seed=selection["fresh_selection_seed"],
    )
    if len(fresh_candidates) != int(selection["fresh_count"]):
        raise ValueError("V82 fresh selection is incomplete")
    if (v79_ids | v81_ids).intersection(row["id"] for row in fresh_candidates):
        raise ValueError("V82 fresh selection overlaps an earlier holdout")

    packets = []
    mutation_count = int(selection["mutation_calibration_count"])
    for index, candidate in enumerate(fresh_candidates, start=1):
        target_plan = candidate.get("target_plan")
        if candidate.get("target_plan_sha256") != v76.canonical_sha256(target_plan):
            raise ValueError("V82 candidate target plan hash mismatch")
        context = copy.deepcopy(candidate.get("input") or {})
        views = {
            C0: {"input_context": context, "plan": copy.deepcopy(target_plan)},
            T1: {"input_context": context, "plan": v81.executable_view(target_plan)},
        }
        packets.append(
            {
                "schema": "uruha_planner_bounded_review_packet_v82",
                "fresh_index": index,
                "candidate_id": candidate["id"],
                "scenario_family": candidate["scenario_family"],
                "mutation_calibration": index <= mutation_count,
                "views": views,
                "view_sha256": {condition: v76.canonical_sha256(view) for condition, view in views.items()},
            }
        )
    return packets


def build_request(packet, contract, model, condition, variant):
    view = packet["views"][condition]
    if variant == VARIANT_MUTATION:
        view = v81.apply_known_defect(view, condition)
    elif variant != VARIANT_ORIGINAL:
        raise ValueError(f"unknown V82 variant: {variant}")
    user_payload = {
        "task": "Audit whether the current plan is executable for one user-facing reply.",
        "allowed_failure_codes": contract["rubric"]["failure_codes"],
        "scenario_family": packet["scenario_family"],
        **view,
    }
    inference = contract["inference"]
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": contract["rubric"]["system_prompt"]},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
        ],
        "stream": False,
        "think": bool(inference["think"]),
        "options": {
            "temperature": inference["temperature"],
            "seed": inference["seed"],
            "num_ctx": inference["num_ctx"],
            "num_predict": inference["num_predict"],
        },
    }


def parse_line(content, contract):
    if not isinstance(content, str) or content != content.strip() or "\n" in content or "\r" in content:
        raise ValueError("V82 judgment must be exactly one stripped line")
    parts = content.split("|")
    if len(parts) != 2:
        raise ValueError("V82 judgment must contain one separator")
    decision, code = parts
    if decision not in {"ACCEPT", "REJECT", "UNCERTAIN"}:
        raise ValueError("V82 judgment has invalid decision")
    allowed = set(contract["rubric"]["failure_codes"])
    if decision == "ACCEPT":
        if code != "none":
            raise ValueError("accepted V82 judgment must use none")
    elif code not in allowed:
        raise ValueError("non-accept V82 judgment requires one allowed failure code")
    return {"decision": decision.lower(), "failure_code": code}


def parse_stored_judgment(value, contract):
    if not isinstance(value, dict) or set(value) != {"decision", "failure_code"}:
        raise ValueError("V82 stored judgment has invalid keys")
    return parse_line(
        f"{str(value['decision']).upper()}|{str(value['failure_code'])}",
        contract,
    )


def _post_json_bounded(payload, *, curl_max_time_seconds, hard_deadline_seconds):
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--max-time",
        str(curl_max_time_seconds),
        "--header",
        "Content-Type: application/json",
        "--data-binary",
        encoded,
        OLLAMA_CHAT_URL,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=hard_deadline_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("hard_deadline") from exc
    if completed.returncode != 0:
        category = "curl_timeout" if completed.returncode == 28 else "curl_failure"
        raise RuntimeError(category)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("transport_json_failure") from exc


def expected_run_sequence(packets, contract):
    rows = []
    for judge in contract["judges"]:
        for packet in packets:
            for condition in contract["conditions"]:
                rows.append((judge, packet, condition, VARIANT_ORIGINAL))
            if packet["mutation_calibration"]:
                for condition in contract["conditions"]:
                    rows.append((judge, packet, condition, VARIANT_MUTATION))
    return rows


def run_judgment(packet, contract, judge, digest, condition, variant):
    request = build_request(packet, contract, judge["model"], condition, variant)
    request_sha256 = v76.canonical_sha256(request)
    request_bytes = len(json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    started = time.monotonic()
    response = None
    transport_error = ""
    try:
        response = _post_json_bounded(
            request,
            curl_max_time_seconds=contract["inference"]["curl_max_time_seconds"],
            hard_deadline_seconds=contract["inference"]["hard_deadline_seconds"],
        )
    except Exception as exc:
        transport_error = str(exc) or type(exc).__name__
    elapsed = time.monotonic() - started
    response = response if isinstance(response, dict) else {}
    content = ((response.get("message") or {}).get("content") or "")
    parsed = None
    parse_error = ""
    if not transport_error:
        try:
            parsed = parse_line(content, contract)
        except Exception as exc:
            parse_error = str(exc)
    return {
        "schema": "uruha_planner_bounded_review_raw_v82",
        "fresh_index": packet["fresh_index"],
        "candidate_id": packet["candidate_id"],
        "condition": condition,
        "variant": variant,
        "packet_view_sha256": packet["view_sha256"][condition],
        "model": judge["model"],
        "model_digest": digest,
        "request_sha256": request_sha256,
        "request_bytes": request_bytes,
        "response_model": response.get("model"),
        "done": response.get("done") is True,
        "parsed": parsed,
        "parse_error": parse_error,
        "transport_error": transport_error,
        "elapsed_seconds": round(elapsed, 6),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
    }


def validate_resume_prefix(packets, raw_rows, contract, installed_digests):
    sequence = expected_run_sequence(packets, contract)
    if len(raw_rows) > len(sequence):
        raise ValueError("V82 resume rows exceed the frozen run length")
    for index, row in enumerate(raw_rows):
        judge, packet, condition, variant = sequence[index]
        model = judge["model"]
        if (row.get("candidate_id"), row.get("condition"), row.get("variant"), row.get("model")) != (
            packet["candidate_id"],
            condition,
            variant,
            model,
        ):
            raise ValueError("V82 resume rows do not follow the frozen run order")
        if installed_digests.get(model) != judge["digest"] or row.get("model_digest") != judge["digest"]:
            raise ValueError("V82 resume model digest mismatch")
        if row.get("packet_view_sha256") != packet["view_sha256"][condition]:
            raise ValueError("V82 resume view hash mismatch")
        request = build_request(packet, contract, model, condition, variant)
        if row.get("request_sha256") != v76.canonical_sha256(request):
            raise ValueError("V82 resume request hash mismatch")
    return sequence


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def analyze(packets, raw_rows, contract, *, production_runtime_files_changed):
    judges = {row["model"]: row for row in contract["judges"]}
    packet_by_id = {row["candidate_id"]: row for row in packets}
    grouped = defaultdict(dict)
    parsed_grouped = defaultdict(dict)
    integrity_counts = Counter()
    transport_failures_by_condition = Counter()
    transport_failures_by_model = Counter()
    parse_failures_by_condition = Counter()
    parse_failures_by_model = Counter()
    condition_data = {
        condition: {
            "original_decisions": Counter(),
            "mutation_decisions": Counter(),
            "request_bytes": [],
            "elapsed_seconds": [],
            "prompt_eval_count": [],
            "eval_count": [],
            "mutation_expected_code_count": 0,
            "mutation_judgment_count": 0,
        }
        for condition in contract["conditions"]
    }
    model_decisions = {model: Counter() for model in judges}
    for row in raw_rows:
        candidate_id = str(row.get("candidate_id") or "")
        condition = str(row.get("condition") or "")
        variant = str(row.get("variant") or "")
        model = str(row.get("model") or "")
        packet = packet_by_id.get(candidate_id)
        judge = judges.get(model)
        if not packet or condition not in condition_data or variant not in {VARIANT_ORIGINAL, VARIANT_MUTATION} or not judge:
            continue
        key = (candidate_id, condition, variant)
        if model in grouped[key]:
            continue
        grouped[key][model] = row
        if row.get("model_digest") == judge["digest"]:
            integrity_counts["model_digest"] += 1
        if row.get("packet_view_sha256") == packet["view_sha256"][condition]:
            integrity_counts["view_hash"] += 1
        request = build_request(packet, contract, model, condition, variant)
        if row.get("request_sha256") == v76.canonical_sha256(request):
            integrity_counts["request_hash"] += 1
        if row.get("done") is True:
            integrity_counts["done"] += 1
        if row.get("response_model") == model:
            integrity_counts["response_model"] += 1
        if row.get("transport_error"):
            integrity_counts["transport_failure"] += 1
            transport_failures_by_condition[condition] += 1
            transport_failures_by_model[model] += 1
        bucket = condition_data[condition]
        for metric in ("request_bytes", "elapsed_seconds", "prompt_eval_count", "eval_count"):
            value = row.get(metric)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                bucket[metric].append(float(value))
        if row.get("transport_error"):
            continue
        try:
            parsed = parse_stored_judgment(row.get("parsed"), contract)
        except Exception:
            integrity_counts["parse_failure"] += 1
            parse_failures_by_condition[condition] += 1
            parse_failures_by_model[model] += 1
            continue
        integrity_counts["parsed"] += 1
        parsed_grouped[key][model] = parsed
        decision_bucket = "original_decisions" if variant == VARIANT_ORIGINAL else "mutation_decisions"
        bucket[decision_bucket][parsed["decision"]] += 1
        model_decisions[model][parsed["decision"]] += 1
        if variant == VARIANT_MUTATION:
            bucket["mutation_judgment_count"] += 1
            if parsed["failure_code"] == contract["known_defect"]["expected_failure_code"]:
                bucket["mutation_expected_code_count"] += 1

    condition_reports = {}
    mutation_packet_count = sum(1 for packet in packets if packet["mutation_calibration"])
    for condition, bucket in condition_data.items():
        agreement = 0
        mutation_reject = 0
        for packet in packets:
            original = parsed_grouped.get((packet["candidate_id"], condition, VARIANT_ORIGINAL), {})
            if set(original) == set(judges) and len({original[model]["decision"] for model in judges}) == 1:
                agreement += 1
            if packet["mutation_calibration"]:
                mutation = parsed_grouped.get((packet["candidate_id"], condition, VARIANT_MUTATION), {})
                if set(mutation) == set(judges) and all(mutation[model]["decision"] == "reject" for model in judges):
                    mutation_reject += 1
        condition_reports[condition] = {
            "original_decision_counts": dict(sorted(bucket["original_decisions"].items())),
            "mutation_decision_counts": dict(sorted(bucket["mutation_decisions"].items())),
            "original_interjudge_agreement": _ratio(agreement, len(packets)),
            "mutation_unanimous_rejection_rate": _ratio(mutation_reject, mutation_packet_count),
            "mutation_expected_code_rate": _ratio(
                bucket["mutation_expected_code_count"], bucket["mutation_judgment_count"]
            ),
            **{
                f"mean_{metric}": (sum(bucket[metric]) / len(bucket[metric]) if bucket[metric] else None)
                for metric in ("request_bytes", "elapsed_seconds", "prompt_eval_count", "eval_count")
            },
        }
    c0 = condition_reports[C0]
    t1 = condition_reports[T1]
    comparisons = {
        "original_agreement_delta_t1_minus_c0": t1["original_interjudge_agreement"] - c0["original_interjudge_agreement"],
        "request_bytes_ratio_t1_vs_c0": _ratio(t1["mean_request_bytes"], c0["mean_request_bytes"]),
        "mean_latency_ratio_t1_vs_c0": _ratio(t1["mean_elapsed_seconds"], c0["mean_elapsed_seconds"]),
        "prompt_eval_count_ratio_t1_vs_c0": _ratio(t1["mean_prompt_eval_count"], c0["mean_prompt_eval_count"]),
    }
    expected = int(contract["inference"]["expected_attempt_count"])
    observed = {
        "packet_count": len(packets),
        "attempt_count": len(raw_rows),
        "parsed_count": integrity_counts["parsed"],
        "transport_failure_count": integrity_counts["transport_failure"],
        "parse_failure_count": integrity_counts["parse_failure"],
        "model_digest_match_count": integrity_counts["model_digest"],
        "view_hash_match_count": integrity_counts["view_hash"],
        "request_hash_match_count": integrity_counts["request_hash"],
        "done_count": integrity_counts["done"],
        "response_model_match_count": integrity_counts["response_model"],
        "production_runtime_files_changed": production_runtime_files_changed,
    }
    checks = {
        "packet_count": observed["packet_count"] == int(contract["selection"]["fresh_count"]),
        "attempt_count": observed["attempt_count"] == expected,
        "parsed_count": observed["parsed_count"] == expected,
        "transport_failure_count": observed["transport_failure_count"] == 0,
        "parse_failure_count": observed["parse_failure_count"] == 0,
        "model_digest_match_count": observed["model_digest_match_count"] == expected,
        "view_hash_match_count": observed["view_hash_match_count"] == expected,
        "request_hash_match_count": observed["request_hash_match_count"] == expected,
        "done_count": observed["done_count"] == expected,
        "response_model_match_count": observed["response_model_match_count"] == expected,
        "production_runtime_files_changed": production_runtime_files_changed == 0,
    }
    integrity_passed = all(checks.values())
    gates = contract["success_gates"]
    success_checks = {
        "minimum_t1_original_interjudge_agreement": t1["original_interjudge_agreement"] >= gates["minimum_t1_original_interjudge_agreement"],
        "minimum_original_agreement_delta_vs_c0": comparisons["original_agreement_delta_t1_minus_c0"] >= gates["minimum_original_agreement_delta_vs_c0"],
        "minimum_t1_unanimous_mutation_rejection": t1["mutation_unanimous_rejection_rate"] >= gates["minimum_t1_unanimous_mutation_rejection"],
        "minimum_t1_mutation_expected_code_rate": t1["mutation_expected_code_rate"] >= gates["minimum_t1_mutation_expected_code_rate"],
        "maximum_t1_request_bytes_ratio_vs_c0": comparisons["request_bytes_ratio_t1_vs_c0"] <= gates["maximum_t1_request_bytes_ratio_vs_c0"],
        "maximum_t1_mean_latency_ratio_vs_c0": comparisons["mean_latency_ratio_t1_vs_c0"] <= gates["maximum_t1_mean_latency_ratio_vs_c0"],
        "maximum_transport_failure_count": observed["transport_failure_count"] <= gates["maximum_transport_failure_count"],
        "maximum_parse_failure_count": observed["parse_failure_count"] <= gates["maximum_parse_failure_count"],
        "maximum_production_runtime_files_changed": production_runtime_files_changed <= gates["maximum_production_runtime_files_changed"],
    }
    success_passed = integrity_passed and all(success_checks.values())
    return {
        "schema": "uruha_planner_bounded_review_analysis_v82",
        "contract_sha256": v76.canonical_sha256(contract),
        "scenario_family_counts": dict(sorted(Counter(packet["scenario_family"] for packet in packets).items())),
        "integrity": {"passed": integrity_passed, "observed": observed, "checks": checks},
        "failure_distribution": {
            "transport_by_condition": dict(sorted(transport_failures_by_condition.items())),
            "transport_by_model": dict(sorted(transport_failures_by_model.items())),
            "parse_by_condition": dict(sorted(parse_failures_by_condition.items())),
            "parse_by_model": dict(sorted(parse_failures_by_model.items())),
        },
        "conditions": condition_reports,
        "comparisons": comparisons,
        "model_decision_counts": {model: dict(sorted(counts.items())) for model, counts in model_decisions.items()},
        "success": {"passed": success_passed, "checks": success_checks},
        "comparative_metrics_authorized": integrity_passed,
        "planner_training_authorized": False,
        "production_runtime_change_authorized": False,
        "decision": (
            "bounded_executable_view_calibrated_for_proxy_triage_only"
            if success_passed
            else "stop_bounded_executable_view_proxy_review_hypothesis"
        ),
        "evidence_boundary": contract["evidence_boundary"],
    }
