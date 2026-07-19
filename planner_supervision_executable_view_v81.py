"""Matched proxy-review experiment for full versus executable planner views."""

from __future__ import annotations

import copy
import json
import math
import time
import urllib.request
from collections import Counter, defaultdict

import planner_supervision_pilot_review_v79 as v79
import planner_supervision_v76 as v76


OLLAMA_BASE_URL = "http://127.0.0.1:11434"
C0 = "c0_full_internal_target"
T1 = "t1_executable_decision_view"
VARIANT_ORIGINAL = "original"
VARIANT_MUTATION = "known_defect"
OUTPUT_KEYS = {"decision", "failure_codes", "reason_summary", "confidence"}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["accept", "reject", "uncertain"]},
        "failure_codes": {"type": "array", "items": {"type": "string"}},
        "reason_summary": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": sorted(OUTPUT_KEYS),
    "additionalProperties": False,
}


def _post_json(path, payload, timeout=600):
    request = urllib.request.Request(
        OLLAMA_BASE_URL + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def installed_model_digests():
    with urllib.request.urlopen(OLLAMA_BASE_URL + "/api/tags", timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {row["name"]: row["digest"] for row in payload.get("models", [])}


def _pilot_binding(unit):
    return {
        "candidate_binding_sha256": unit["candidate_binding_sha256"],
        "session_binding_sha256": unit["session_binding_sha256"],
        "scenario_family": unit["scenario_family"],
    }


def _selection_rank(candidate_id, seed):
    return v76.canonical_sha256({"seed": seed, "candidate_id": candidate_id})


def _distribution_distance(counts, total, population_counts, population_total):
    families = set(population_counts) | set(counts)
    return sum(
        abs((counts.get(family, 0) / total) - (population_counts.get(family, 0) / population_total))
        for family in families
    )


def select_disjoint_holdout(eligible, excluded_ids, *, budget, seed):
    remaining = [row for row in eligible if row.get("id") not in excluded_ids]
    available_families = {str(row.get("scenario_family") or "") for row in remaining}
    available_sessions = {str(row.get("source_session_id") or "") for row in remaining}
    if "" in available_families or "" in available_sessions:
        raise ValueError("V81 remaining candidate is missing family or session")
    if budget < max(len(available_families), len(available_sessions)):
        raise ValueError("V81 budget cannot cover all remaining families and sessions")
    ranked = sorted(remaining, key=lambda row: _selection_rank(row["id"], seed))
    selected = []
    selected_ids = set()
    covered_families = set()
    covered_sessions = set()
    while (covered_families != available_families or covered_sessions != available_sessions) and len(selected) < budget:
        choices = [row for row in ranked if row["id"] not in selected_ids]
        if not choices:
            break
        row = min(
            choices,
            key=lambda item: (
                -int(item["scenario_family"] not in covered_families)
                - int(item["source_session_id"] not in covered_sessions),
                _selection_rank(item["id"], seed),
            ),
        )
        selected.append(row)
        selected_ids.add(row["id"])
        covered_families.add(row["scenario_family"])
        covered_sessions.add(row["source_session_id"])
    if covered_families != available_families or covered_sessions != available_sessions:
        raise ValueError("V81 selection failed remaining family/session coverage")

    population_counts = Counter(row["scenario_family"] for row in remaining)
    selected_counts = Counter(row["scenario_family"] for row in selected)
    while len(selected) < min(budget, len(remaining)):
        choices = [row for row in ranked if row["id"] not in selected_ids]
        if not choices:
            break

        def fill_key(item):
            proposed = selected_counts.copy()
            proposed[item["scenario_family"]] += 1
            return (
                _distribution_distance(proposed, len(selected) + 1, population_counts, len(remaining)),
                _selection_rank(item["id"], seed),
            )

        row = min(choices, key=fill_key)
        selected.append(row)
        selected_ids.add(row["id"])
        selected_counts[row["scenario_family"]] += 1
    return selected


def _safe_memory_anchor(anchor):
    anchor = anchor if isinstance(anchor, dict) else {}
    return {
        key: copy.deepcopy(anchor[key])
        for key in ("kind", "jp_anchor", "terms")
        if anchor.get(key) not in (None, "", [])
    }


def executable_view(target_plan):
    plan = target_plan if isinstance(target_plan, dict) else {}
    speech = plan.get("human_speech_plan") if isinstance(plan.get("human_speech_plan"), dict) else {}
    constraints = plan.get("constraints") if isinstance(plan.get("constraints"), dict) else {}
    return {
        "decision": {
            key: copy.deepcopy(plan.get(key))
            for key in ("intent", "hidden_intent", "scene", "response_mode", "premise_check", "dialogue_act")
        },
        "response_intent": {
            key: copy.deepcopy(plan.get(key))
            for key in ("reply_goal", "core_message_jp", "listener_state", "uncertainty")
        },
        "social_model": {
            key: copy.deepcopy(plan.get(key))
            for key in ("user_belief", "user_expectation", "stance")
        },
        "memory_policy": {
            "memory_use_expected": bool(plan.get("memory_use_expected")),
            "memory_speakability": str(plan.get("memory_speakability") or "no_memory"),
            "memory_anchor": _safe_memory_anchor(plan.get("memory_anchor")),
        },
        "surface_brief": {
            key: copy.deepcopy(speech.get(key))
            for key in ("content_units", "speech_moves", "style_operators", "target_length", "grounding_terms")
        },
        "constraints": {
            key: copy.deepcopy(constraints.get(key))
            for key in ("sentence_count", "max_chars", "casual_japanese_only", "forbid_polite")
        }
        | {"must_avoid": list(plan.get("must_avoid") or [])},
    }


def apply_known_defect(plan_view, condition):
    mutated = copy.deepcopy(plan_view)
    plan = mutated["plan"]
    if condition == C0:
        plan["reply_goal"] = ""
        plan["core_message_jp"] = ""
        speech = plan.get("human_speech_plan")
        if isinstance(speech, dict):
            speech["content_units"] = []
            speech["speech_moves"] = []
            speech["grounding_terms"] = []
    elif condition == T1:
        plan["response_intent"]["reply_goal"] = ""
        plan["response_intent"]["core_message_jp"] = ""
        plan["surface_brief"]["content_units"] = []
        plan["surface_brief"]["speech_moves"] = []
        plan["surface_brief"]["grounding_terms"] = []
    else:
        raise ValueError(f"unknown V81 condition: {condition}")
    return mutated


def build_packets(candidates, manifest_rows, frozen_v79_units, contract):
    selection = contract["selection"]
    eligible, current_v79_units = v79.select_pilot(
        candidates,
        manifest_rows,
        budget=int(selection["frozen_v79_prefix_count"]),
        seed=selection["v79_validation_seed"],
    )
    expected_prefix = [_pilot_binding(row) for row in frozen_v79_units]
    actual_prefix = [_pilot_binding(row) for row in current_v79_units]
    if actual_prefix != expected_prefix:
        raise ValueError("V81 source validation does not preserve the frozen V79 pilot")
    count = int(selection["fresh_count"])
    frozen_ids = {row["candidate_id"] for row in frozen_v79_units}
    fresh_candidates = select_disjoint_holdout(
        eligible,
        frozen_ids,
        budget=count,
        seed=selection["fresh_selection_seed"],
    )
    if len(fresh_candidates) != count:
        raise ValueError("V81 fresh selection is incomplete")
    if frozen_ids.intersection(row["id"] for row in fresh_candidates):
        raise ValueError("V81 fresh selection overlaps the V79 pilot")
    mutation_count = int(selection["mutation_calibration_count"])
    packets = []
    for index, candidate in enumerate(fresh_candidates, start=1):
        target_plan = candidate.get("target_plan")
        if candidate.get("target_plan_sha256") != v76.canonical_sha256(target_plan):
            raise ValueError("V81 candidate target plan hash mismatch")
        context = copy.deepcopy(candidate.get("input") or {})
        views = {
            C0: {"input_context": context, "plan": copy.deepcopy(target_plan)},
            T1: {"input_context": context, "plan": executable_view(target_plan)},
        }
        packets.append(
            {
                "schema": "uruha_planner_executable_view_packet_v81",
                "fresh_index": index,
                "candidate_id": candidate["id"],
                "candidate_binding_sha256": v76.canonical_sha256(
                    {
                        "id": candidate["id"],
                        "source_sha256": (candidate.get("provenance") or {}).get("source_sha256"),
                        "target_plan_sha256": candidate.get("target_plan_sha256"),
                    }
                ),
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
        view = apply_known_defect(view, condition)
    elif variant != VARIANT_ORIGINAL:
        raise ValueError(f"unknown V81 variant: {variant}")
    user_payload = {
        "task": "Audit whether the current plan is executable for one user-facing reply.",
        "failure_code_definitions": contract["rubric"]["failure_codes"],
        "scenario_family": packet["scenario_family"],
        **view,
    }
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": contract["rubric"]["system_prompt"]},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
        ],
        "format": OUTPUT_SCHEMA,
        "stream": False,
        "think": bool(contract["inference"]["think"]),
        "options": {
            "temperature": contract["inference"]["temperature"],
            "seed": contract["inference"]["seed"],
            "num_ctx": contract["inference"]["num_ctx"],
        },
    }


def parse_judgment(value, contract):
    value = json.loads(value) if isinstance(value, str) else value
    if not isinstance(value, dict) or set(value) != OUTPUT_KEYS:
        raise ValueError("V81 judgment has invalid keys")
    decision = value.get("decision")
    if decision not in {"accept", "reject", "uncertain"}:
        raise ValueError("V81 judgment has invalid decision")
    codes = value.get("failure_codes")
    allowed = set(contract["rubric"]["failure_codes"])
    if not isinstance(codes, list) or len(codes) != len(set(codes)) or any(code not in allowed for code in codes):
        raise ValueError("V81 judgment has invalid failure codes")
    if decision == "accept" and codes:
        raise ValueError("accepted V81 judgment cannot have failure codes")
    if decision == "reject" and not codes:
        raise ValueError("rejected V81 judgment requires a failure code")
    reason = value.get("reason_summary")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("V81 judgment requires a reason summary")
    confidence = value.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence):
        raise ValueError("V81 judgment confidence is invalid")
    if not 0 <= float(confidence) <= 1:
        raise ValueError("V81 judgment confidence is out of range")
    return {
        "decision": decision,
        "failure_codes": list(codes),
        "reason_summary": reason.strip(),
        "confidence": float(confidence),
    }


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
    request_payload = build_request(packet, contract, judge["model"], condition, variant)
    request_sha256 = v76.canonical_sha256(request_payload)
    request_bytes = len(json.dumps(request_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    started = time.monotonic()
    response = _post_json("/api/chat", request_payload)
    elapsed = time.monotonic() - started
    content = ((response.get("message") or {}).get("content") or "").strip()
    parsed = None
    parse_error = ""
    try:
        parsed = parse_judgment(content, contract)
    except Exception as exc:
        parse_error = str(exc)
    return {
        "schema": "uruha_planner_executable_view_raw_v81",
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
        "elapsed_seconds": round(elapsed, 6),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
    }


def validate_resume_prefix(packets, raw_rows, contract, installed_digests):
    sequence = expected_run_sequence(packets, contract)
    if len(raw_rows) > len(sequence):
        raise ValueError("V81 resume rows exceed the frozen run length")
    for index, row in enumerate(raw_rows):
        judge, packet, condition, variant = sequence[index]
        model = judge["model"]
        expected = (packet["candidate_id"], condition, variant, model)
        observed = (row.get("candidate_id"), row.get("condition"), row.get("variant"), row.get("model"))
        if observed != expected:
            raise ValueError("V81 resume rows do not follow the frozen run order")
        if installed_digests.get(model) != judge["digest"] or row.get("model_digest") != judge["digest"]:
            raise ValueError("V81 resume model digest mismatch")
        if row.get("packet_view_sha256") != packet["view_sha256"][condition]:
            raise ValueError("V81 resume view hash mismatch")
        request = build_request(packet, contract, model, condition, variant)
        if row.get("request_sha256") != v76.canonical_sha256(request):
            raise ValueError("V81 resume request hash mismatch")
        parse_judgment(row.get("parsed"), contract)
    return sequence


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def analyze(packets, raw_rows, contract, *, production_runtime_files_changed):
    judges = {row["model"]: row for row in contract["judges"]}
    expected_attempts = int(contract["inference"]["expected_attempt_count"])
    parsed_count = 0
    digest_match_count = 0
    request_hash_match_count = 0
    view_hash_match_count = 0
    done_count = 0
    response_model_match_count = 0
    grouped = defaultdict(dict)
    parsed_grouped = defaultdict(dict)
    aggregates = {
        condition: {
            "original_decisions": Counter(),
            "mutation_decisions": Counter(),
            "original_agreement_count": 0,
            "original_packet_count": len(packets),
            "mutation_unanimous_reject_count": 0,
            "mutation_packet_count": sum(1 for packet in packets if packet["mutation_calibration"]),
            "mutation_expected_code_count": 0,
            "mutation_judgment_count": 0,
            "request_bytes": [],
            "elapsed_seconds": [],
            "prompt_eval_count": [],
        }
        for condition in contract["conditions"]
    }
    packet_by_id = {packet["candidate_id"]: packet for packet in packets}

    for row in raw_rows:
        candidate_id = str(row.get("candidate_id") or "")
        condition = str(row.get("condition") or "")
        variant = str(row.get("variant") or "")
        model = str(row.get("model") or "")
        packet = packet_by_id.get(candidate_id)
        judge = judges.get(model)
        if not packet or condition not in aggregates or variant not in {VARIANT_ORIGINAL, VARIANT_MUTATION} or not judge:
            continue
        key = (candidate_id, condition, variant)
        if model in grouped[key]:
            continue
        grouped[key][model] = row
        if row.get("model_digest") == judge["digest"]:
            digest_match_count += 1
        if row.get("packet_view_sha256") == packet["view_sha256"][condition]:
            view_hash_match_count += 1
        expected_request = build_request(packet, contract, model, condition, variant)
        if row.get("request_sha256") == v76.canonical_sha256(expected_request):
            request_hash_match_count += 1
        if row.get("done") is True:
            done_count += 1
        if row.get("response_model") == model:
            response_model_match_count += 1
        try:
            parsed = parse_judgment(row.get("parsed"), contract)
        except Exception:
            continue
        parsed_grouped[key][model] = parsed
        parsed_count += 1
        bucket = aggregates[condition]
        decision_key = "original_decisions" if variant == VARIANT_ORIGINAL else "mutation_decisions"
        bucket[decision_key][parsed["decision"]] += 1
        if variant == VARIANT_MUTATION:
            bucket["mutation_judgment_count"] += 1
            if contract["known_defect"]["expected_failure_code"] in parsed["failure_codes"]:
                bucket["mutation_expected_code_count"] += 1
        for metric in ("request_bytes", "elapsed_seconds", "prompt_eval_count"):
            if isinstance(row.get(metric), (int, float)) and not isinstance(row.get(metric), bool):
                bucket[metric].append(float(row[metric]))

    for condition in contract["conditions"]:
        for packet in packets:
            original_rows = parsed_grouped.get((packet["candidate_id"], condition, VARIANT_ORIGINAL), {})
            if set(original_rows) == set(judges):
                decisions = [original_rows[model]["decision"] for model in judges]
                if len(set(decisions)) == 1:
                    aggregates[condition]["original_agreement_count"] += 1
            if packet["mutation_calibration"]:
                mutation_rows = parsed_grouped.get((packet["candidate_id"], condition, VARIANT_MUTATION), {})
                if set(mutation_rows) == set(judges):
                    decisions = [mutation_rows[model]["decision"] for model in judges]
                    if all(decision == "reject" for decision in decisions):
                        aggregates[condition]["mutation_unanimous_reject_count"] += 1

    condition_reports = {}
    for condition, bucket in aggregates.items():
        condition_reports[condition] = {
            "original_decision_counts": dict(sorted(bucket["original_decisions"].items())),
            "mutation_decision_counts": dict(sorted(bucket["mutation_decisions"].items())),
            "original_interjudge_agreement": _ratio(bucket["original_agreement_count"], bucket["original_packet_count"]),
            "mutation_unanimous_rejection_rate": _ratio(
                bucket["mutation_unanimous_reject_count"], bucket["mutation_packet_count"]
            ),
            "mutation_expected_code_rate": _ratio(
                bucket["mutation_expected_code_count"], bucket["mutation_judgment_count"]
            ),
            "mean_request_bytes": sum(bucket["request_bytes"]) / len(bucket["request_bytes"]) if bucket["request_bytes"] else None,
            "mean_elapsed_seconds": sum(bucket["elapsed_seconds"]) / len(bucket["elapsed_seconds"]) if bucket["elapsed_seconds"] else None,
            "mean_prompt_eval_count": sum(bucket["prompt_eval_count"]) / len(bucket["prompt_eval_count"]) if bucket["prompt_eval_count"] else None,
        }

    c0 = condition_reports[C0]
    t1 = condition_reports[T1]
    comparisons = {
        "original_agreement_delta_t1_minus_c0": t1["original_interjudge_agreement"] - c0["original_interjudge_agreement"],
        "request_bytes_ratio_t1_vs_c0": _ratio(t1["mean_request_bytes"], c0["mean_request_bytes"]),
        "mean_latency_ratio_t1_vs_c0": _ratio(t1["mean_elapsed_seconds"], c0["mean_elapsed_seconds"]),
        "prompt_eval_count_ratio_t1_vs_c0": _ratio(t1["mean_prompt_eval_count"], c0["mean_prompt_eval_count"]),
    }
    integrity_observed = {
        "packet_count": len(packets),
        "attempt_count": len(raw_rows),
        "parsed_count": parsed_count,
        "model_digest_match_count": digest_match_count,
        "view_hash_match_count": view_hash_match_count,
        "request_hash_match_count": request_hash_match_count,
        "done_count": done_count,
        "response_model_match_count": response_model_match_count,
        "production_runtime_files_changed": production_runtime_files_changed,
    }
    integrity_checks = {
        "packet_count": integrity_observed["packet_count"] == int(contract["selection"]["fresh_count"]),
        "attempt_count": integrity_observed["attempt_count"] == expected_attempts,
        "parsed_count": integrity_observed["parsed_count"] == expected_attempts,
        "model_digest_match_count": integrity_observed["model_digest_match_count"] == expected_attempts,
        "view_hash_match_count": integrity_observed["view_hash_match_count"] == expected_attempts,
        "request_hash_match_count": integrity_observed["request_hash_match_count"] == expected_attempts,
        "done_count": integrity_observed["done_count"] == expected_attempts,
        "response_model_match_count": integrity_observed["response_model_match_count"] == expected_attempts,
        "production_runtime_files_changed": production_runtime_files_changed == 0,
    }
    integrity_passed = all(integrity_checks.values())
    gates = contract["success_gates"]
    success_checks = {
        "minimum_t1_original_interjudge_agreement": t1["original_interjudge_agreement"] >= gates["minimum_t1_original_interjudge_agreement"],
        "minimum_original_agreement_delta_vs_c0": comparisons["original_agreement_delta_t1_minus_c0"] >= gates["minimum_original_agreement_delta_vs_c0"],
        "minimum_t1_unanimous_mutation_rejection": t1["mutation_unanimous_rejection_rate"] >= gates["minimum_t1_unanimous_mutation_rejection"],
        "minimum_t1_mutation_expected_code_rate": t1["mutation_expected_code_rate"] >= gates["minimum_t1_mutation_expected_code_rate"],
        "maximum_t1_request_bytes_ratio_vs_c0": comparisons["request_bytes_ratio_t1_vs_c0"] <= gates["maximum_t1_request_bytes_ratio_vs_c0"],
        "maximum_t1_mean_latency_ratio_vs_c0": comparisons["mean_latency_ratio_t1_vs_c0"] <= gates["maximum_t1_mean_latency_ratio_vs_c0"],
        "maximum_production_runtime_files_changed": production_runtime_files_changed <= gates["maximum_production_runtime_files_changed"],
    }
    success_passed = integrity_passed and all(success_checks.values())
    return {
        "schema": "uruha_planner_executable_view_analysis_v81",
        "contract_sha256": v76.canonical_sha256(contract),
        "integrity": {"passed": integrity_passed, "observed": integrity_observed, "checks": integrity_checks},
        "conditions": condition_reports,
        "comparisons": comparisons,
        "success": {"passed": success_passed, "checks": success_checks},
        "planner_training_authorized": False,
        "production_runtime_change_authorized": False,
        "decision": (
            "executable_view_calibrated_for_proxy_triage_only"
            if success_passed
            else "stop_executable_view_proxy_review_hypothesis"
        ),
        "evidence_boundary": contract["evidence_boundary"],
    }
