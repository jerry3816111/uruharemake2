"""Matched regression utilities for V85 memory-cue canonicalization."""

from __future__ import annotations

import copy
import hashlib
import json
import re

import planner_memory_causality_v84 as v84
import planner_outcome_evaluator_v83 as v83
import planner_supervision_v76 as v76
import run_rightbrain_pipeline_shadow_v61 as v61
from rightbrain_language_quality import has_bad_language
from uruha_brain_mac import MEMORY_TRANSCRIPT_LABEL_RE


C0 = "c0_legacy_raw_memory_cue"
T1 = "t1_canonical_memory_cue"
CONDITIONS = (C0, T1)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_private_sources(contract, root):
    checks = {}
    for name, artifact in contract["private_sources"].items():
        path = root / artifact["path"]
        checks[name] = path.is_file() and file_sha256(path) == artifact["sha256"]
    if not all(checks.values()):
        raise ValueError(f"V85 private source drift: {checks}")
    return checks


def regression_candidates(candidates, v84_packets, contract):
    expected_count = int(contract["scope"]["case_count"])
    if len(v84_packets) != expected_count:
        raise ValueError("V85 V84 packet count mismatch")
    ids = [packet["candidate_id"] for packet in v84_packets]
    if len(set(ids)) != expected_count:
        raise ValueError("V85 V84 packet identities are not unique")
    by_id = {candidate["id"]: candidate for candidate in candidates}
    selected = [by_id.get(candidate_id) for candidate_id in ids]
    if any(candidate is None for candidate in selected):
        raise ValueError("V85 regression candidate missing from frozen queue")
    return selected


def _payload(right_brain, logic, psyche, memory_data, max_chars, enabled):
    previous = right_brain.memory_cue_canonicalization_enabled
    right_brain.memory_cue_canonicalization_enabled = enabled
    try:
        parsed = json.loads(
            right_brain._build_model_surface_payload(
                copy.deepcopy(logic),
                copy.deepcopy(psyche),
                max_chars,
                memory_data=copy.deepcopy(memory_data),
            )
        )
    finally:
        right_brain.memory_cue_canonicalization_enabled = previous
    return parsed


def _surface_terms(payload):
    cues = payload["context"]["audited_memory_brief"].get("allowed_memory_cues") or []
    cue_terms = [
        str(term or "")
        for cue in cues
        for term in [cue.get("jp_anchor"), *(cue.get("terms") or [])]
        if str(term or "")
    ]
    group_terms = [str(term or "") for group in payload.get("required_marker_groups") or [] for term in group]
    return cue_terms + group_terms


def build_packet(right_brain, candidate):
    logic = copy.deepcopy(candidate["target_plan"])
    if candidate.get("target_plan_sha256") != v76.canonical_sha256(logic):
        raise ValueError("V85 target plan hash mismatch")
    context = candidate["input"]
    psyche = copy.deepcopy(context.get("psyche_state") or {})
    memory_data = copy.deepcopy(context.get("working_memory") or [])
    max_chars = max(24, min(int((logic.get("constraints") or {}).get("max_chars") or 72), 96))
    payloads = {
        C0: _payload(right_brain, logic, psyche, memory_data, max_chars, False),
        T1: _payload(right_brain, logic, psyche, memory_data, max_chars, True),
    }
    canonical_groups = copy.deepcopy(payloads[T1].get("required_marker_groups") or [])
    if not canonical_groups:
        raise ValueError("V85 treatment has no clean semantic contract")
    control_terms = _surface_terms(payloads[C0])
    treatment_terms = _surface_terms(payloads[T1])
    if not any(MEMORY_TRANSCRIPT_LABEL_RE.search(term) for term in control_terms):
        raise ValueError("V85 legacy control no longer reproduces the known transcript-shaped cue")
    if any(MEMORY_TRANSCRIPT_LABEL_RE.search(term) or has_bad_language(term, reject_latin=True) for term in treatment_terms):
        raise ValueError("V85 treatment retained an unsafe memory surface term")
    outcome_contract = {
        "required_semantic_groups": canonical_groups,
        "forbidden_markers": list(logic.get("must_avoid") or []),
        "private_memory_terms": list(right_brain._audited_memory_forbidden_surface_terms(logic)),
        "maximum_reply_chars": max_chars,
        "action_contract": {
            "allowed_action_names": [],
            "required_action_names": [],
            "forbidden_action_names": [],
            "maximum_action_count": 0,
        },
    }
    packet = {
        "schema": "uruha_memory_cue_canonicalization_packet_v85",
        "candidate_id": candidate["id"],
        "scenario_family": candidate["scenario_family"],
        "outcome_contract": outcome_contract,
        "payloads": payloads,
        "payload_sha256": {condition: v76.canonical_sha256(payload) for condition, payload in payloads.items()},
    }
    packet["packet_sha256"] = v76.canonical_sha256({key: value for key, value in packet.items() if key != "packet_sha256"})
    return packet


def build_request(packet, contract, condition):
    generation = contract["generation"]
    body = {
        "model": contract["model"]["ollama_tag"],
        "messages": [
            {"role": "system", "content": v61.brain_module.RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(packet["payloads"][condition], ensure_ascii=False, separators=(",", ":"))},
        ],
        "stream": False,
        "think": bool(contract["model"]["thinking"]),
        "keep_alive": "20m",
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "top_k": generation["top_k"],
            "repeat_penalty": generation["repeat_penalty"],
            "seed": generation["seed"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
        },
    }
    encoded = json.dumps(body, ensure_ascii=False)
    if "outcome_contract" in encoded or "candidate_id" in encoded:
        raise ValueError("V85 scorer-only data leaked into model request")
    return body


def expected_sequence(packets, contract):
    ranked = sorted(
        packets,
        key=lambda packet: v76.canonical_sha256(
            {"seed": contract["generation"]["seed"], "candidate_id": packet["candidate_id"]}
        ),
    )
    sequence = []
    for index, packet in enumerate(ranked):
        order = CONDITIONS if index % 2 == 0 else tuple(reversed(CONDITIONS))
        for condition in order:
            sequence.append((packet, condition))
    return sequence


def score_reply(packet, reply):
    result = v83.evaluate_outcome(packet, {"reply": reply, "actions": []})
    missing = len(result["details"].get("missing_required_group_indexes", []))
    total = len(packet["outcome_contract"]["required_semantic_groups"])
    surface_failures = {
        "empty_reply", "missing_japanese_surface", "cjk_language_leak", "foreign_script_leak",
        "unexpected_ascii_leak", "ascii_symbol_artifact", "unicode_replacement_character", "over_max_chars",
    }
    failures = result["failure_codes"]
    return {
        "outcome_pass": result["passed"],
        "failure_codes": failures,
        "clean_required_hit_count": total - missing,
        "clean_required_count": total,
        "clean_semantic_recall": (total - missing) / total,
        "surface_pass": not surface_failures.intersection(failures),
        "transcript_label_leak": bool(MEMORY_TRANSCRIPT_LABEL_RE.search(str(reply or ""))),
        "over_max": "over_max_chars" in failures,
        "forbidden_violation": "forbidden_semantic_present" in failures,
        "private_memory_intrusion": "private_memory_intrusion" in failures,
        "normalized_reply": re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/'\"`]+", "", str(reply or "").lower()),
    }


def validate_resume_prefix(packets, rows, contract):
    sequence = expected_sequence(packets, contract)
    if len(rows) > len(sequence):
        raise ValueError("V85 resume rows exceed frozen sequence")
    for index, row in enumerate(rows):
        packet, condition = sequence[index]
        if (row.get("candidate_id"), row.get("condition")) != (packet["candidate_id"], condition):
            raise ValueError("V85 resume order mismatch")
        request = build_request(packet, contract, condition)
        if row.get("request_sha256") != v76.canonical_sha256(request):
            raise ValueError("V85 resume request hash mismatch")
        if row.get("packet_sha256") != packet["packet_sha256"]:
            raise ValueError("V85 resume packet hash mismatch")
    return sequence
