"""Matched regression utilities for the V85.1 explicit length contract."""

from __future__ import annotations

import copy
import json

import memory_cue_canonicalization_v85 as v85
import planner_supervision_v76 as v76
import run_rightbrain_pipeline_shadow_v61 as v61
from rightbrain_language_quality import has_bad_language
from uruha_brain_mac import MEMORY_TRANSCRIPT_LABEL_RE, RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE


C0 = "c0_canonical_cue_implicit_length"
T1 = "t1_canonical_cue_explicit_length"
CONDITIONS = (C0, T1)


file_sha256 = v85.file_sha256
verify_private_sources = v85.verify_private_sources
regression_candidates = v85.regression_candidates


def _payload_and_prompt(right_brain, logic, psyche, memory_data, max_chars, explicit_length):
    previous_memory = right_brain.memory_cue_canonicalization_enabled
    previous_length = right_brain.explicit_length_contract_enabled
    right_brain.memory_cue_canonicalization_enabled = True
    right_brain.explicit_length_contract_enabled = explicit_length
    try:
        payload = json.loads(
            right_brain._build_model_surface_payload(
                copy.deepcopy(logic),
                copy.deepcopy(psyche),
                max_chars,
                memory_data=copy.deepcopy(memory_data),
            )
        )
        system_prompt = right_brain._model_surface_system_instruction()
    finally:
        right_brain.memory_cue_canonicalization_enabled = previous_memory
        right_brain.explicit_length_contract_enabled = previous_length
    return payload, system_prompt


def _without_length_contract(payload):
    normalized = copy.deepcopy(payload)
    normalized.pop("output_budget", None)
    requirements = normalized.get("reply_requirements") or []
    normalized["reply_requirements"] = [
        value for value in requirements if "visible characters including punctuation" not in str(value)
    ]
    return normalized


def build_packet(right_brain, candidate):
    logic = copy.deepcopy(candidate["target_plan"])
    if candidate.get("target_plan_sha256") != v76.canonical_sha256(logic):
        raise ValueError("V85.1 target plan hash mismatch")
    context = candidate["input"]
    psyche = copy.deepcopy(context.get("psyche_state") or {})
    memory_data = copy.deepcopy(context.get("working_memory") or [])
    max_chars = max(24, min(int((logic.get("constraints") or {}).get("max_chars") or 72), 96))
    control_payload, control_prompt = _payload_and_prompt(
        right_brain, logic, psyche, memory_data, max_chars, False
    )
    treatment_payload, treatment_prompt = _payload_and_prompt(
        right_brain, logic, psyche, memory_data, max_chars, True
    )
    if control_payload != _without_length_contract(treatment_payload):
        raise ValueError("V85.1 payload differs outside the explicit length contract")
    if treatment_prompt != control_prompt + RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE:
        raise ValueError("V85.1 system prompt intervention drift")
    if "output_budget" in control_payload:
        raise ValueError("V85.1 control unexpectedly contains output budget")
    if treatment_payload.get("output_budget", {}).get("maximum_characters") != max_chars:
        raise ValueError("V85.1 treatment output budget mismatch")
    groups = copy.deepcopy(control_payload.get("required_marker_groups") or [])
    if not groups or groups != treatment_payload.get("required_marker_groups"):
        raise ValueError("V85.1 semantic contract mismatch")
    for payload in (control_payload, treatment_payload):
        terms = v85._surface_terms(payload)
        if any(MEMORY_TRANSCRIPT_LABEL_RE.search(term) or has_bad_language(term, reject_latin=True) for term in terms):
            raise ValueError("V85.1 retained unsafe canonical memory terms")
    outcome_contract = {
        "required_semantic_groups": groups,
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
        "schema": "uruha_rightbrain_length_contract_packet_v85_1",
        "candidate_id": candidate["id"],
        "scenario_family": candidate["scenario_family"],
        "outcome_contract": outcome_contract,
        "payloads": {C0: control_payload, T1: treatment_payload},
        "system_prompts": {C0: control_prompt, T1: treatment_prompt},
    }
    packet["payload_sha256"] = {
        condition: v76.canonical_sha256(packet["payloads"][condition]) for condition in CONDITIONS
    }
    packet["packet_sha256"] = v76.canonical_sha256(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )
    return packet


def build_request(packet, contract, condition):
    generation = contract["generation"]
    body = {
        "model": contract["model"]["ollama_tag"],
        "messages": [
            {"role": "system", "content": packet["system_prompts"][condition]},
            {
                "role": "user",
                "content": json.dumps(packet["payloads"][condition], ensure_ascii=False, separators=(",", ":")),
            },
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
        raise ValueError("V85.1 scorer-only data leaked into model request")
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
    score = v85.score_reply(packet, reply)
    maximum = int(packet["outcome_contract"]["maximum_reply_chars"])
    reply_chars = len(str(reply or "").strip())
    return {
        **score,
        "reply_chars": reply_chars,
        "maximum_reply_chars": maximum,
        "over_by_chars": max(0, reply_chars - maximum),
    }


def validate_resume_prefix(packets, rows, contract):
    sequence = expected_sequence(packets, contract)
    if len(rows) > len(sequence):
        raise ValueError("V85.1 resume rows exceed frozen sequence")
    for index, row in enumerate(rows):
        packet, condition = sequence[index]
        if (row.get("candidate_id"), row.get("condition")) != (packet["candidate_id"], condition):
            raise ValueError("V85.1 resume order mismatch")
        request = build_request(packet, contract, condition)
        if row.get("request_sha256") != v76.canonical_sha256(request):
            raise ValueError("V85.1 resume request hash mismatch")
        if row.get("packet_sha256") != packet["packet_sha256"]:
            raise ValueError("V85.1 resume packet hash mismatch")
    return sequence
