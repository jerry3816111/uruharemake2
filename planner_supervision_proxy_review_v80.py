"""Hash-bound local proxy review for the V79 planner pilot."""

from __future__ import annotations

import json
import time
import urllib.request
from collections import Counter, defaultdict

import planner_supervision_pilot_review_v79 as v79
import planner_supervision_v76 as v76


OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OUTPUT_KEYS = {"decision", "failure_codes", "rationale", "confidence"}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["accept", "reject", "uncertain"]},
        "failure_codes": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
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


def build_packets(candidates, manifest_rows, pilot_units, v79_contract):
    eligible, canonical_units = v79.select_pilot(
        candidates,
        manifest_rows,
        budget=int(v79_contract["selection"]["budget"]),
        seed=v79_contract["selection"]["seed"],
    )
    if canonical_units != pilot_units:
        raise ValueError("current V79 pilot differs from the frozen local queue")
    candidates_by_id = {row["id"]: row for row in eligible}
    packets = []
    for unit in canonical_units:
        candidate = candidates_by_id.get(unit["candidate_id"])
        if not candidate:
            raise ValueError("pilot candidate is not currently eligible")
        if unit["candidate_binding_sha256"] != v76.canonical_sha256(unit["candidate_binding"]):
            raise ValueError("pilot candidate binding hash mismatch")
        packet_payload = {
            "input_context": candidate["input"],
            "target_plan": candidate["target_plan"],
        }
        packets.append(
            {
                "schema": "uruha_planner_proxy_review_packet_v80",
                "pilot_index": unit["pilot_index"],
                "candidate_id": candidate["id"],
                "candidate_binding_sha256": unit["candidate_binding_sha256"],
                "scenario_family": candidate["scenario_family"],
                "packet_payload": packet_payload,
                "packet_sha256": v76.canonical_sha256(packet_payload),
            }
        )
    return packets


def build_request(packet, contract, model):
    rubric = contract["rubric"]
    user_payload = {
        "task": "Audit whether this internal speech plan is a reliable target for general dialogue planning.",
        "failure_code_definitions": rubric["failure_codes"],
        "scenario_family": packet["scenario_family"],
        **packet["packet_payload"],
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": rubric["system_prompt"]},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
        ],
        "format": OUTPUT_SCHEMA,
        "stream": False,
        "options": {
            "temperature": contract["inference"]["temperature"],
            "seed": contract["inference"]["seed"],
            "num_ctx": contract["inference"]["num_ctx"],
        },
    }
    return payload


def parse_judgment(content, contract):
    value = json.loads(content) if isinstance(content, str) else content
    if not isinstance(value, dict) or set(value) != OUTPUT_KEYS:
        raise ValueError("proxy judgment has invalid keys")
    if value["decision"] not in {"accept", "reject", "uncertain"}:
        raise ValueError("proxy judgment has invalid decision")
    codes = value["failure_codes"]
    allowed = set(contract["rubric"]["failure_codes"])
    if not isinstance(codes, list) or len(codes) != len(set(codes)) or any(code not in allowed for code in codes):
        raise ValueError("proxy judgment has invalid failure codes")
    if value["decision"] == "accept" and codes:
        raise ValueError("accepted proxy judgment cannot have failure codes")
    if value["decision"] == "reject" and not codes:
        raise ValueError("rejected proxy judgment requires a failure code")
    rationale = str(value["rationale"] or "").strip()
    if not rationale:
        raise ValueError("proxy judgment requires rationale")
    confidence = float(value["confidence"])
    if not 0 <= confidence <= 1:
        raise ValueError("proxy judgment confidence is out of range")
    return {
        "decision": value["decision"],
        "failure_codes": codes,
        "rationale": rationale,
        "confidence": confidence,
    }


def run_judgment(packet, contract, judge, digest):
    request_payload = build_request(packet, contract, judge["model"])
    request_sha256 = v76.canonical_sha256(request_payload)
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
        "schema": "uruha_planner_proxy_review_raw_v80",
        "pilot_index": packet["pilot_index"],
        "candidate_id": packet["candidate_id"],
        "packet_sha256": packet["packet_sha256"],
        "candidate_binding_sha256": packet["candidate_binding_sha256"],
        "model": judge["model"],
        "model_digest": digest,
        "request_sha256": request_sha256,
        "response_model": response.get("model"),
        "done": response.get("done") is True,
        "parsed": parsed,
        "parse_error": parse_error,
        "elapsed_seconds": round(elapsed, 6),
        "ollama_total_duration_ns": response.get("total_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
    }


def expected_run_sequence(packets, contract):
    return [
        (judge, packet)
        for judge in contract["judges"]
        for packet in packets
    ]


def validate_resume_prefix(packets, raw_rows, contract, installed_digests):
    sequence = expected_run_sequence(packets, contract)
    if len(raw_rows) > len(sequence):
        raise ValueError("resume rows exceed the frozen run length")
    for index, row in enumerate(raw_rows):
        judge, packet = sequence[index]
        model = judge["model"]
        if row.get("model") != model or row.get("candidate_id") != packet["candidate_id"]:
            raise ValueError("resume rows do not follow the frozen run order")
        if installed_digests.get(model) != judge["digest"] or row.get("model_digest") != judge["digest"]:
            raise ValueError("resume model digest mismatch")
        if row.get("packet_sha256") != packet["packet_sha256"]:
            raise ValueError("resume packet hash mismatch")
        request = build_request(packet, contract, model)
        if row.get("request_sha256") != v76.canonical_sha256(request):
            raise ValueError("resume request hash mismatch")
        parse_judgment(row.get("parsed"), contract)
    return sequence


def analyze(packets, raw_rows, contract, *, strict_human_rows_created, production_runtime_files_changed):
    packet_map = {row["candidate_id"]: row for row in packets}
    judges = {row["model"]: row for row in contract["judges"]}
    grouped = defaultdict(dict)
    model_digest_match_count = 0
    packet_hash_match_count = 0
    request_hash_match_count = 0
    parsed_count = 0
    failure_counts = Counter()
    model_decisions = {model: Counter() for model in judges}
    elapsed_by_model = {model: [] for model in judges}

    for row in raw_rows:
        candidate_id = str(row.get("candidate_id") or "")
        model = str(row.get("model") or "")
        packet = packet_map.get(candidate_id)
        judge = judges.get(model)
        if not packet or not judge or model in grouped[candidate_id]:
            continue
        grouped[candidate_id][model] = row
        if row.get("model_digest") == judge["digest"]:
            model_digest_match_count += 1
        if row.get("packet_sha256") == packet["packet_sha256"]:
            packet_hash_match_count += 1
        expected_request = build_request(packet, contract, model)
        if row.get("request_sha256") == v76.canonical_sha256(expected_request):
            request_hash_match_count += 1
        parsed = row.get("parsed")
        if isinstance(parsed, dict):
            try:
                parsed = parse_judgment(parsed, contract)
                parsed_count += 1
                model_decisions[model][parsed["decision"]] += 1
                failure_counts.update(parsed["failure_codes"])
            except Exception:
                pass
        if isinstance(row.get("elapsed_seconds"), (int, float)):
            elapsed_by_model[model].append(float(row["elapsed_seconds"]))

    minimum_confidence = float(contract["rubric"]["minimum_confidence_for_consensus"])
    consensus = Counter()
    for packet in packets:
        rows = grouped.get(packet["candidate_id"], {})
        if set(rows) != set(judges):
            consensus["incomplete"] += 1
            continue
        judgments = [rows[model].get("parsed") for model in judges]
        if not all(isinstance(value, dict) for value in judgments):
            consensus["unparsed"] += 1
            continue
        decisions = [value["decision"] for value in judgments]
        confidences = [float(value["confidence"]) for value in judgments]
        if all(decision == "accept" for decision in decisions) and min(confidences) >= minimum_confidence:
            consensus["accept"] += 1
        elif all(decision == "reject" for decision in decisions):
            consensus["reject"] += 1
        elif len(set(decisions)) > 1:
            consensus["disagreement"] += 1
        else:
            consensus["uncertain"] += 1

    packet_count = len(packets)
    attempt_count = len(raw_rows)
    accept_rate = consensus["accept"] / packet_count if packet_count else 0.0
    disagreement_rate = consensus["disagreement"] / packet_count if packet_count else 0.0
    observed_integrity = {
        "packet_count": packet_count,
        "attempt_count": attempt_count,
        "parsed_count": parsed_count,
        "model_digest_match_count": model_digest_match_count,
        "packet_hash_match_count": packet_hash_match_count,
        "request_hash_match_count": request_hash_match_count,
        "strict_human_rows_created": strict_human_rows_created,
        "production_runtime_files_changed": production_runtime_files_changed,
    }
    expected_integrity = contract["integrity_gates"]
    integrity_checks = {key: observed_integrity[key] == expected_integrity[key] for key in expected_integrity}
    integrity_passed = all(integrity_checks.values())
    viability = contract["viability_gates"]
    viability_checks = {
        "minimum_consensus_accept_rate": accept_rate >= viability["minimum_consensus_accept_rate"],
        "maximum_disagreement_rate": disagreement_rate <= viability["maximum_disagreement_rate"],
    }
    viability_passed = integrity_passed and all(viability_checks.values())
    return {
        "schema": "uruha_planner_proxy_review_analysis_v80",
        "contract_sha256": v76.canonical_sha256(contract),
        "integrity": {"passed": integrity_passed, "observed": observed_integrity, "checks": integrity_checks},
        "consensus_counts": dict(sorted(consensus.items())),
        "consensus_accept_rate": accept_rate,
        "disagreement_rate": disagreement_rate,
        "model_decision_counts": {model: dict(sorted(counts.items())) for model, counts in model_decisions.items()},
        "failure_code_counts": dict(sorted(failure_counts.items())),
        "elapsed_seconds_by_model": {
            model: {
                "count": len(values),
                "total": sum(values),
                "mean": (sum(values) / len(values)) if values else None,
            }
            for model, values in elapsed_by_model.items()
        },
        "viability": {"passed": viability_passed, "checks": viability_checks},
        "proxy_approved_weak_supervision_count": consensus["accept"] if integrity_passed else 0,
        "strict_human_training_authorized": False,
        "decision": (
            "proxy_viable_but_training_not_authorized"
            if viability_passed
            else "do_not_train_fix_collection_or_review_method"
        ),
        "evidence_boundary": contract["evidence_boundary"],
    }
