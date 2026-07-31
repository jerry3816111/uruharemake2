"""Fresh-generation V88 holdout for the RightBrain forbidden-conflict projection."""

from __future__ import annotations

import copy
import hashlib
import json

import planner_supervision_executable_view_v81 as v81
import planner_supervision_pilot_review_v79 as v79
import planner_supervision_v76 as v76
import rightbrain_length_contract_v85_1 as v851
from rightbrain_language_quality import has_bad_language
from uruha_brain_mac import MEMORY_TRANSCRIPT_LABEL_RE


C0 = "c0_projection_disabled"
T1 = "t1_projection_enabled"
CONDITIONS = (C0, T1)
STRATUM_CONFLICT = "stale_opening_conflict"
STRATUM_NONCONFLICT = "nonconflict_safety"


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sources(contract, root):
    checks = {}
    for section in ("private_sources", "prior_evidence"):
        for name, artifact in contract[section].items():
            path = root / artifact["path"]
            checks[f"{section}.{name}"] = path.is_file() and file_sha256(path) == artifact["sha256"]
    if not all(checks.values()):
        raise ValueError(f"V88 source drift: {checks}")
    return checks


def _normalized(values):
    return list(
        dict.fromkeys(
            str(value or "").strip()
            for value in values or []
            if str(value or "").strip()
        )
    )


def _payload_and_prompt(right_brain, logic, psyche, memory_data, max_chars, projection_enabled):
    previous = (
        right_brain.memory_cue_canonicalization_enabled,
        right_brain.explicit_length_contract_enabled,
        right_brain.forbidden_conflict_projection_enabled,
    )
    right_brain.memory_cue_canonicalization_enabled = True
    right_brain.explicit_length_contract_enabled = True
    right_brain.forbidden_conflict_projection_enabled = projection_enabled
    logic_copy = copy.deepcopy(logic)
    try:
        payload = json.loads(
            right_brain._build_model_surface_payload(
                logic_copy,
                copy.deepcopy(psyche),
                max_chars,
                memory_data=copy.deepcopy(memory_data),
            )
        )
        prompt = right_brain._model_surface_system_instruction()
        trace = copy.deepcopy(logic_copy.get("model_surface_forbidden_projection") or {})
    finally:
        (
            right_brain.memory_cue_canonicalization_enabled,
            right_brain.explicit_length_contract_enabled,
            right_brain.forbidden_conflict_projection_enabled,
        ) = previous
    return payload, prompt, trace


def _without_forbidden(payload):
    normalized = copy.deepcopy(payload)
    normalized.pop("forbidden_markers", None)
    return normalized


def build_packet(right_brain, candidate):
    logic = copy.deepcopy(candidate["target_plan"])
    if candidate.get("target_plan_sha256") != v76.canonical_sha256(logic):
        raise ValueError("V88 target plan hash mismatch")
    context = candidate["input"]
    psyche = copy.deepcopy(context.get("psyche_state") or {})
    memory_data = copy.deepcopy(context.get("working_memory") or [])
    max_chars = max(24, min(int((logic.get("constraints") or {}).get("max_chars") or 72), 96))
    control, control_prompt, control_trace = _payload_and_prompt(
        right_brain, logic, psyche, memory_data, max_chars, False
    )
    treatment, treatment_prompt, treatment_trace = _payload_and_prompt(
        right_brain, logic, psyche, memory_data, max_chars, True
    )
    if control_prompt != treatment_prompt:
        raise ValueError("V88 system prompt drift")
    if _without_forbidden(control) != _without_forbidden(treatment):
        raise ValueError("V88 payload differs outside forbidden projection")
    original = _normalized(logic.get("must_avoid") or [])
    if control.get("forbidden_markers") != original:
        raise ValueError("V88 control forbidden contract drift")
    effective = _normalized(treatment.get("forbidden_markers") or [])
    dropped = [marker for marker in original if marker not in effective]
    if int(treatment_trace.get("dropped_stale_recent_opening_count") or 0) != len(dropped):
        raise ValueError("V88 projection trace mismatch")
    if control_trace:
        raise ValueError("V88 disabled control unexpectedly recorded a projection trace")
    groups = copy.deepcopy(treatment.get("required_marker_groups") or [])
    if not groups or groups != control.get("required_marker_groups"):
        raise ValueError("V88 semantic contract mismatch")
    outcome_contract = {
        "required_semantic_groups": groups,
        "forbidden_markers": effective,
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
        "schema": "uruha_rightbrain_forbidden_projection_packet_v88",
        "candidate_id": candidate["id"],
        "source_session_id": candidate["source_session_id"],
        "scenario_family": candidate["scenario_family"],
        "stratum": STRATUM_CONFLICT if dropped else STRATUM_NONCONFLICT,
        "dropped_marker_count": len(dropped),
        "outcome_contract": outcome_contract,
        "payloads": {C0: control, T1: treatment},
        "system_prompts": {C0: control_prompt, T1: treatment_prompt},
    }
    packet["payload_sha256"] = {
        condition: v76.canonical_sha256(packet["payloads"][condition]) for condition in CONDITIONS
    }
    packet["packet_sha256"] = v76.canonical_sha256(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )
    return packet


def _fresh_eligible(candidates, manifest_rows, exclusion_rows, contract, right_brain):
    selection = contract["selection"]
    eligible, current_v79 = v79.select_pilot(
        candidates,
        manifest_rows,
        budget=int(selection["v79_count"]),
        seed=selection["v79_validation_seed"],
    )
    frozen_v79 = exclusion_rows["v79"]
    if [row["candidate_binding_sha256"] for row in current_v79] != [
        row["candidate_binding_sha256"] for row in frozen_v79
    ]:
        raise ValueError("V88 source validation does not preserve the frozen V79 pilot")
    expected_counts = selection["exclusion_counts"]
    for name, expected in expected_counts.items():
        if len(exclusion_rows[name]) != int(expected):
            raise ValueError(f"V88 {name} exclusion count mismatch")
    excluded = {
        str(row.get("candidate_id") or row.get("id") or "")
        for rows in exclusion_rows.values()
        for row in rows
    }
    excluded.discard("")
    if len(excluded) != sum(int(value) for value in expected_counts.values()):
        raise ValueError("V88 exclusion sources overlap")

    fresh = []
    for row in eligible:
        plan = row.get("target_plan") or {}
        anchor = plan.get("memory_anchor") or {}
        if row["id"] in excluded or row.get("scenario_family") != "memory_recall_update":
            continue
        if not plan.get("memory_use_expected") or not anchor:
            continue
        raw_terms = [
            str(anchor.get("jp_anchor") or ""),
            *[str(value or "") for value in anchor.get("terms") or []],
        ]
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
        fresh.append((row, build_packet(right_brain, row)))
    return fresh


def select_fresh_candidates(candidates, manifest_rows, exclusion_rows, contract, right_brain):
    selection = contract["selection"]
    fresh = _fresh_eligible(candidates, manifest_rows, exclusion_rows, contract, right_brain)
    by_stratum = {
        stratum: [candidate for candidate, packet in fresh if packet["stratum"] == stratum]
        for stratum in (STRATUM_CONFLICT, STRATUM_NONCONFLICT)
    }
    selected = []
    for stratum, seed_key, count_key in (
        (STRATUM_CONFLICT, "conflict_selection_seed", "conflict_count"),
        (STRATUM_NONCONFLICT, "nonconflict_selection_seed", "nonconflict_count"),
    ):
        budget = int(selection[count_key])
        rows = v81.select_disjoint_holdout(
            by_stratum[stratum],
            set(),
            budget=budget,
            seed=selection[seed_key],
        )
        if len(rows) != budget:
            raise ValueError(f"V88 {stratum} selection is incomplete")
        if len({row["source_session_id"] for row in rows}) < int(selection["minimum_sessions_per_stratum"]):
            raise ValueError(f"V88 {stratum} lacks session coverage")
        selected.extend(rows)
    if len({row["id"] for row in selected}) != len(selected):
        raise ValueError("V88 selected identities overlap")
    return sorted(
        selected,
        key=lambda row: v76.canonical_sha256(
            {"seed": selection["combined_order_seed"], "candidate_id": row["id"]}
        ),
    )


def sample_seed(packet, contract, sample_index):
    base = int(contract["generation"]["seed"])
    offset = int(
        v76.canonical_sha256(
            {"candidate_id": packet["candidate_id"], "sample_index": sample_index}
        )[:8],
        16,
    )
    return (base + offset) % 2_147_483_647


def build_request(packet, contract, condition, sample_index):
    setting = contract["generation"]["sampling_settings"][sample_index]
    body = {
        "model": contract["model"]["ollama_tag"],
        "messages": [
            {"role": "system", "content": packet["system_prompts"][condition]},
            {
                "role": "user",
                "content": json.dumps(
                    packet["payloads"][condition], ensure_ascii=False, separators=(",", ":")
                ),
            },
        ],
        "stream": False,
        "think": bool(contract["model"]["thinking"]),
        "keep_alive": "20m",
        "options": {
            "temperature": setting["temperature"],
            "top_p": setting["top_p"],
            "top_k": setting["top_k"],
            "repeat_penalty": setting["repeat_penalty"],
            "seed": sample_seed(packet, contract, sample_index),
            "num_ctx": contract["generation"]["context_tokens"],
            "num_predict": contract["generation"]["maximum_output_tokens"],
        },
    }
    encoded = json.dumps(body, ensure_ascii=False)
    if "outcome_contract" in encoded or "candidate_id" in encoded or "source_session_id" in encoded:
        raise ValueError("V88 scorer-only data leaked into model request")
    return body


def expected_sequence(packets, contract):
    ranked = sorted(
        packets,
        key=lambda packet: v76.canonical_sha256(
            {"seed": contract["selection"]["combined_order_seed"], "candidate_id": packet["candidate_id"]}
        ),
    )
    sequence = []
    for packet_index, packet in enumerate(ranked):
        for sample_index in range(len(contract["generation"]["sampling_settings"])):
            order = CONDITIONS if (packet_index + sample_index) % 2 == 0 else tuple(reversed(CONDITIONS))
            for condition in order:
                sequence.append((packet, condition, sample_index))
    return sequence


def score_reply(packet, reply):
    return v851.score_reply(packet, reply)


def evaluate_production_gate(right_brain, candidate, packet, condition, raw_reply):
    logic = copy.deepcopy(candidate["target_plan"])
    context = candidate["input"]
    memory_data = copy.deepcopy(context.get("working_memory") or [])
    user_input = str(context.get("user_utterance") or "")
    max_chars = int(packet["outcome_contract"]["maximum_reply_chars"])
    previous = (
        right_brain.memory_cue_canonicalization_enabled,
        right_brain.explicit_length_contract_enabled,
        right_brain.forbidden_conflict_projection_enabled,
    )
    right_brain.memory_cue_canonicalization_enabled = True
    right_brain.explicit_length_contract_enabled = True
    right_brain.forbidden_conflict_projection_enabled = condition == T1
    try:
        prepared, reasons = right_brain._prepare_model_surface_candidate(
            raw_reply,
            logic,
            user_input,
            memory_data,
            max_chars,
        )
        effective = right_brain._model_surface_forbidden_markers(logic)
        trace = copy.deepcopy(logic.get("model_surface_forbidden_projection") or {})
        production_score = right_brain._score_candidate(prepared, logic) if prepared and not reasons else None
    finally:
        (
            right_brain.memory_cue_canonicalization_enabled,
            right_brain.explicit_length_contract_enabled,
            right_brain.forbidden_conflict_projection_enabled,
        ) = previous
    expected = packet["payloads"][condition]["forbidden_markers"]
    return {
        "prepared_reply": prepared,
        "gate_rejection_reasons": list(reasons),
        "gate_accepted": not reasons,
        "production_candidate_score": production_score,
        "effective_forbidden_sha256": v76.canonical_sha256(effective),
        "effective_forbidden_matches_payload": effective == expected,
        "dropped_marker_count": int(trace.get("dropped_stale_recent_opening_count") or 0),
        "prepared_score": score_reply(packet, prepared),
    }


def validate_resume_prefix(packets, rows, contract):
    sequence = expected_sequence(packets, contract)
    if len(rows) > len(sequence):
        raise ValueError("V88 resume rows exceed frozen sequence")
    for index, row in enumerate(rows):
        packet, condition, sample_index = sequence[index]
        if (row.get("candidate_id"), row.get("condition"), row.get("sample_index")) != (
            packet["candidate_id"],
            condition,
            sample_index,
        ):
            raise ValueError("V88 resume order mismatch")
        request = build_request(packet, contract, condition, sample_index)
        if row.get("request_sha256") != v76.canonical_sha256(request):
            raise ValueError("V88 resume request hash mismatch")
        if row.get("packet_sha256") != packet["packet_sha256"]:
            raise ValueError("V88 resume packet hash mismatch")
    return sequence
