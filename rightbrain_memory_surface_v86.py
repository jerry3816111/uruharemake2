"""Fresh disjoint V86 holdout utilities for RightBrain memory surface contracts."""

from __future__ import annotations

import copy
import json

import memory_cue_canonicalization_v85 as v85
import planner_memory_causality_v84 as v84
import planner_supervision_executable_view_v81 as v81
import planner_supervision_pilot_review_v79 as v79
import planner_supervision_v76 as v76
import rightbrain_length_contract_v85_1 as v851
from rightbrain_language_quality import has_bad_language
from uruha_brain_mac import MEMORY_TRANSCRIPT_LABEL_RE, RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE


C0 = "c0_legacy_cue_implicit_length"
C1 = "c1_canonical_cue_implicit_length"
T2 = "t2_canonical_cue_explicit_length"
CONDITIONS = (C0, C1, T2)


file_sha256 = v85.file_sha256
verify_private_sources = v85.verify_private_sources


def select_fresh_candidates(
    candidates,
    manifest_rows,
    v79_units,
    v81_packets,
    v82_packets,
    v84_packets,
    contract,
    right_brain,
):
    selection = contract["selection"]
    eligible, current_v79 = v79.select_pilot(
        candidates,
        manifest_rows,
        budget=int(selection["v79_count"]),
        seed=selection["v79_validation_seed"],
    )
    if [v84._pilot_binding(row) for row in current_v79] != [v84._pilot_binding(row) for row in v79_units]:
        raise ValueError("V86 source validation does not preserve the frozen V79 pilot")
    expected_counts = {
        "v79": (len(v79_units), int(selection["v79_count"])),
        "v81": (len(v81_packets), int(selection["v81_count"])),
        "v82": (len(v82_packets), int(selection["v82_count"])),
        "v84": (len(v84_packets), int(selection["v84_count"])),
    }
    if any(observed != expected for observed, expected in expected_counts.values()):
        raise ValueError(f"V86 exclusion source count mismatch: {expected_counts}")
    excluded = {
        *[row["candidate_id"] for row in v79_units],
        *[row["candidate_id"] for row in v81_packets],
        *[row["candidate_id"] for row in v82_packets],
        *[row["candidate_id"] for row in v84_packets],
    }
    if len(excluded) != sum(expected for _, expected in expected_counts.values()):
        raise ValueError("V86 exclusion sources overlap")
    memory_eligible = []
    for row in eligible:
        plan = row.get("target_plan") or {}
        anchor = plan.get("memory_anchor") or {}
        if row["id"] in excluded or row.get("scenario_family") != "memory_recall_update":
            continue
        if not plan.get("memory_use_expected") or not anchor:
            continue
        raw_terms = [str(anchor.get("jp_anchor") or ""), *[str(value or "") for value in anchor.get("terms") or []]]
        if not any(MEMORY_TRANSCRIPT_LABEL_RE.search(term) for term in raw_terms):
            continue
        cue, _ = right_brain._canonical_memory_expression_cue(copy.deepcopy(plan))
        canonical_terms = [
            str(value or "")
            for value in [cue.get("jp_anchor"), *(cue.get("terms") or [])]
            if str(value or "")
        ]
        if not canonical_terms:
            continue
        if any(
            MEMORY_TRANSCRIPT_LABEL_RE.search(term) or has_bad_language(term, reject_latin=True)
            for term in canonical_terms
        ):
            continue
        memory_eligible.append(row)
    selected = v81.select_disjoint_holdout(
        memory_eligible,
        set(),
        budget=int(selection["fresh_count"]),
        seed=selection["fresh_selection_seed"],
    )
    if len(selected) != int(selection["fresh_count"]):
        raise ValueError("V86 fresh selection is incomplete")
    if excluded.intersection(row["id"] for row in selected):
        raise ValueError("V86 fresh selection overlaps an earlier holdout")
    session_count = len({row["source_session_id"] for row in selected})
    if session_count < int(selection["minimum_session_count"]):
        raise ValueError("V86 fresh selection lacks session coverage")
    return selected


def _payload_and_prompt(right_brain, logic, psyche, memory_data, max_chars, canonical, explicit_length):
    previous_memory = right_brain.memory_cue_canonicalization_enabled
    previous_length = right_brain.explicit_length_contract_enabled
    right_brain.memory_cue_canonicalization_enabled = canonical
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
        prompt = right_brain._model_surface_system_instruction()
    finally:
        right_brain.memory_cue_canonicalization_enabled = previous_memory
        right_brain.explicit_length_contract_enabled = previous_length
    return payload, prompt


def build_packet(right_brain, candidate):
    logic = copy.deepcopy(candidate["target_plan"])
    if candidate.get("target_plan_sha256") != v76.canonical_sha256(logic):
        raise ValueError("V86 target plan hash mismatch")
    context = candidate["input"]
    psyche = copy.deepcopy(context.get("psyche_state") or {})
    memory_data = copy.deepcopy(context.get("working_memory") or [])
    max_chars = max(24, min(int((logic.get("constraints") or {}).get("max_chars") or 72), 96))
    payloads = {}
    prompts = {}
    payloads[C0], prompts[C0] = _payload_and_prompt(right_brain, logic, psyche, memory_data, max_chars, False, False)
    payloads[C1], prompts[C1] = _payload_and_prompt(right_brain, logic, psyche, memory_data, max_chars, True, False)
    payloads[T2], prompts[T2] = _payload_and_prompt(right_brain, logic, psyche, memory_data, max_chars, True, True)
    if payloads[C1] != v851._without_length_contract(payloads[T2]):
        raise ValueError("V86 length comparison differs outside explicit contract")
    if prompts[C0] != prompts[C1] or prompts[T2] != prompts[C1] + RIGHT_BRAIN_EXPLICIT_LENGTH_SYSTEM_RULE:
        raise ValueError("V86 prompt comparison drift")
    if not any(MEMORY_TRANSCRIPT_LABEL_RE.search(term) for term in v85._surface_terms(payloads[C0])):
        raise ValueError("V86 legacy condition lacks transcript-shaped cue")
    for condition in (C1, T2):
        terms = v85._surface_terms(payloads[condition])
        if any(MEMORY_TRANSCRIPT_LABEL_RE.search(term) or has_bad_language(term, reject_latin=True) for term in terms):
            raise ValueError("V86 canonical condition retained unsafe memory cue")
    clean_groups = copy.deepcopy(payloads[C1].get("required_marker_groups") or [])
    if not clean_groups or clean_groups != payloads[T2].get("required_marker_groups"):
        raise ValueError("V86 clean semantic contract mismatch")
    outcome_contract = {
        "required_semantic_groups": clean_groups,
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
        "schema": "uruha_rightbrain_memory_surface_packet_v86",
        "candidate_id": candidate["id"],
        "scenario_family": candidate["scenario_family"],
        "source_session_id": candidate["source_session_id"],
        "outcome_contract": outcome_contract,
        "payloads": payloads,
        "system_prompts": prompts,
    }
    packet["payload_sha256"] = {
        condition: v76.canonical_sha256(payloads[condition]) for condition in CONDITIONS
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
    if "outcome_contract" in encoded or "candidate_id" in encoded or "source_session_id" in encoded:
        raise ValueError("V86 scorer-only data leaked into model request")
    return body


def expected_sequence(packets, contract):
    ranked = sorted(
        packets,
        key=lambda packet: v76.canonical_sha256({"seed": contract["generation"]["seed"], "candidate_id": packet["candidate_id"]}),
    )
    sequence = []
    for index, packet in enumerate(ranked):
        offset = index % len(CONDITIONS)
        order = CONDITIONS[offset:] + CONDITIONS[:offset]
        for condition in order:
            sequence.append((packet, condition))
    return sequence


def score_reply(packet, reply):
    return v851.score_reply(packet, reply)


def validate_resume_prefix(packets, rows, contract):
    sequence = expected_sequence(packets, contract)
    if len(rows) > len(sequence):
        raise ValueError("V86 resume rows exceed frozen sequence")
    for index, row in enumerate(rows):
        packet, condition = sequence[index]
        if (row.get("candidate_id"), row.get("condition")) != (packet["candidate_id"], condition):
            raise ValueError("V86 resume order mismatch")
        if row.get("request_sha256") != v76.canonical_sha256(build_request(packet, contract, condition)):
            raise ValueError("V86 resume request hash mismatch")
        if row.get("packet_sha256") != packet["packet_sha256"]:
            raise ValueError("V86 resume packet hash mismatch")
    return sequence
