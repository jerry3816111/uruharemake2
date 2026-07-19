"""Matched memory-plan intervention utilities for the V84 causal pilot."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter

import planner_outcome_evaluator_v83 as v83
import planner_supervision_executable_view_v81 as v81
import planner_supervision_pilot_review_v79 as v79
import planner_supervision_v76 as v76
import run_rightbrain_pipeline_shadow_v61 as v61


C0 = "c0_intact_memory_integrated_plan"
T1 = "t1_memory_integration_removed"
CONDITIONS = (C0, T1)
ABLATION_PATHS = (
    "memory_use_expected",
    "memory_speakability",
    "memory_anchor",
    "working_memory_used",
    "reply_goal",
    "core_message_jp",
    "human_speech_plan.content_units",
    "human_speech_plan.speech_moves",
    "human_speech_plan.grounding_terms",
)


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
        raise ValueError(f"V84 private source drift: {checks}")
    return checks


def _pilot_binding(row):
    return {
        "candidate_binding_sha256": row["candidate_binding_sha256"],
        "session_binding_sha256": row["session_binding_sha256"],
        "scenario_family": row["scenario_family"],
    }


def select_fresh_candidates(candidates, manifest_rows, v79_units, v81_packets, v82_packets, contract):
    selection = contract["selection"]
    eligible, current_v79 = v79.select_pilot(
        candidates,
        manifest_rows,
        budget=int(selection["v79_count"]),
        seed=selection["v79_validation_seed"],
    )
    if [_pilot_binding(row) for row in current_v79] != [_pilot_binding(row) for row in v79_units]:
        raise ValueError("V84 source validation does not preserve the frozen V79 pilot")
    if len(v81_packets) != int(selection["v81_count"]) or len(v82_packets) != int(selection["v82_count"]):
        raise ValueError("V84 exclusion source count mismatch")
    excluded = {
        *[row["candidate_id"] for row in v79_units],
        *[row["candidate_id"] for row in v81_packets],
        *[row["candidate_id"] for row in v82_packets],
    }
    if len(excluded) != int(selection["v79_count"]) + int(selection["v81_count"]) + int(selection["v82_count"]):
        raise ValueError("V84 exclusion sources overlap")
    memory_eligible = [
        row
        for row in eligible
        if row["id"] not in excluded and row.get("scenario_family") == "memory_recall_update"
    ]
    selected = v81.select_disjoint_holdout(
        memory_eligible,
        set(),
        budget=int(selection["fresh_count"]),
        seed=selection["fresh_selection_seed"],
    )
    if len(selected) != int(selection["fresh_count"]):
        raise ValueError("V84 fresh selection is incomplete")
    if excluded.intersection(row["id"] for row in selected):
        raise ValueError("V84 fresh selection overlaps an earlier holdout")
    return selected


def ablate_memory_integration(logic):
    ablated = copy.deepcopy(logic)
    ablated["memory_use_expected"] = False
    ablated["memory_speakability"] = "no_memory"
    ablated["memory_anchor"] = {}
    ablated["working_memory_used"] = []
    ablated["reply_goal"] = ""
    ablated["core_message_jp"] = ""
    speech = ablated.get("human_speech_plan")
    if not isinstance(speech, dict):
        raise ValueError("V84 source plan is missing human_speech_plan")
    speech["content_units"] = []
    speech["speech_moves"] = []
    speech["grounding_terms"] = []
    return ablated


def _payload_dict(right_brain, logic, psyche, max_chars, memory_data):
    payload = right_brain._build_model_surface_payload(
        copy.deepcopy(logic),
        copy.deepcopy(psyche),
        max_chars,
        memory_data=copy.deepcopy(memory_data),
    )
    parsed = json.loads(payload)
    forbidden_keys = {"outcome_contract", "target_failure_code", "benchmark_answer", "gold"}

    def keys(value):
        found = set()
        if isinstance(value, dict):
            found.update(value)
            for item in value.values():
                found.update(keys(item))
        elif isinstance(value, list):
            for item in value:
                found.update(keys(item))
        return found

    leaked = forbidden_keys.intersection(keys(parsed))
    if leaked:
        raise ValueError(f"V84 scorer-only fields leaked into payload: {sorted(leaked)}")
    return parsed


def build_packet(right_brain, candidate):
    original = copy.deepcopy(candidate["target_plan"])
    if candidate.get("target_plan_sha256") != v76.canonical_sha256(original):
        raise ValueError("V84 target plan hash mismatch")
    if not original.get("memory_use_expected") or not original.get("memory_anchor"):
        raise ValueError("V84 source plan lacks explicit memory integration")
    required_groups = [list(group) for group in right_brain._model_required_semantic_groups(original)]
    if not required_groups:
        raise ValueError("V84 source plan has no runtime semantic contract")
    input_context = candidate["input"]
    psyche = copy.deepcopy(input_context.get("psyche_state") or {})
    memory_data = copy.deepcopy(input_context.get("working_memory") or [])
    max_chars = int((original.get("constraints") or {}).get("max_chars") or 72)
    max_chars = max(24, min(max_chars, 96))
    outcome_contract = {
        "required_semantic_groups": required_groups,
        "forbidden_markers": list(original.get("must_avoid") or []),
        "private_memory_terms": list(right_brain._audited_memory_forbidden_surface_terms(original)),
        "maximum_reply_chars": max_chars,
        "action_contract": {
            "allowed_action_names": [],
            "required_action_names": [],
            "forbidden_action_names": [],
            "maximum_action_count": 0,
        },
    }
    ablated = ablate_memory_integration(original)
    payloads = {
        C0: _payload_dict(right_brain, original, psyche, max_chars, memory_data),
        T1: _payload_dict(right_brain, ablated, psyche, max_chars, memory_data),
    }
    intact_brief = payloads[C0]["context"]["audited_memory_brief"]
    removed_brief = payloads[T1]["context"]["audited_memory_brief"]
    if intact_brief.get("policy") != "explicit_allowed" or not intact_brief.get("allowed_memory_cues"):
        raise ValueError("V84 intact payload lacks explicit memory cue")
    if removed_brief.get("policy") != "no_memory" or removed_brief.get("allowed_memory_cues"):
        raise ValueError("V84 ablated payload retained memory authorization")
    if not payloads[C0].get("required_marker_groups") or payloads[T1].get("required_marker_groups"):
        raise ValueError("V84 payload semantic-contract intervention shape mismatch")
    removed_plan = payloads[T1].get("leftbrain_plan") or {}
    if removed_plan.get("meaning") or removed_plan.get("content_units") or removed_plan.get("grounding_terms"):
        raise ValueError("V84 ablated payload retained executable memory meaning")
    packet = {
        "schema": "uruha_planner_memory_causality_packet_v84",
        "candidate_id": candidate["id"],
        "scenario_family": candidate["scenario_family"],
        "source_session_id": candidate["source_session_id"],
        "source_binding_sha256": v76.canonical_sha256(
            {
                "candidate_id": candidate["id"],
                "target_plan_sha256": candidate["target_plan_sha256"],
                "source_session_id": candidate["source_session_id"],
            }
        ),
        "outcome_contract": outcome_contract,
        "ablation_paths": list(ABLATION_PATHS),
        "payloads": payloads,
        "payload_sha256": {condition: v76.canonical_sha256(payload) for condition, payload in payloads.items()},
    }
    packet["packet_sha256"] = v76.canonical_sha256({key: value for key, value in packet.items() if key != "packet_sha256"})
    return packet


def build_request(packet, contract, condition, seed):
    model = contract["model"]
    generation = contract["generation"]
    body = {
        "model": model["ollama_tag"],
        "messages": [
            {"role": "system", "content": v61.brain_module.RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(packet["payloads"][condition], ensure_ascii=False, separators=(",", ":")),
            },
        ],
        "stream": False,
        "think": bool(model["thinking"]),
        "keep_alive": "20m",
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "top_k": generation["top_k"],
            "repeat_penalty": generation["repeat_penalty"],
            "seed": int(seed),
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
        },
    }
    encoded = json.dumps(body, ensure_ascii=False)
    if "outcome_contract" in encoded or "target_failure_code" in encoded:
        raise ValueError("V84 scorer-only contract leaked into model request")
    return body


def expected_sequence(packets, contract):
    pairs = [
        (int(seed), packet)
        for seed in contract["generation"]["replicate_seeds"]
        for packet in packets
    ]
    pairs.sort(key=lambda pair: v76.canonical_sha256({"seed": pair[0], "candidate_id": pair[1]["candidate_id"]}))
    sequence = []
    for index, (seed, packet) in enumerate(pairs):
        order = CONDITIONS if index % 2 == 0 else tuple(reversed(CONDITIONS))
        for condition in order:
            sequence.append((seed, packet, condition))
    return sequence


def score_reply(packet, reply):
    result = v83.evaluate_outcome(packet, {"reply": reply, "actions": []})
    missing = len(result["details"].get("missing_required_group_indexes", []))
    total = len(packet["outcome_contract"]["required_semantic_groups"])
    language_failures = {
        "empty_reply",
        "missing_japanese_surface",
        "cjk_language_leak",
        "foreign_script_leak",
        "unexpected_ascii_leak",
        "ascii_symbol_artifact",
        "unicode_replacement_character",
        "over_max_chars",
    }
    return {
        "outcome_pass": result["passed"],
        "failure_codes": result["failure_codes"],
        "required_group_hit_count": total - missing,
        "required_group_count": total,
        "required_group_recall": (total - missing) / total,
        "semantic_complete": "required_semantic_missing" not in result["failure_codes"],
        "surface_pass": not language_failures.intersection(result["failure_codes"]),
        "forbidden_violation": "forbidden_semantic_present" in result["failure_codes"],
        "private_memory_intrusion": "private_memory_intrusion" in result["failure_codes"],
        "reply_chars": result["reply_chars"],
        "normalized_reply": re.sub(r"[\s\u3000。．，,、！？?!…~～ー\-_/'\"`]+", "", str(reply or "").lower()),
    }


def validate_resume_prefix(packets, rows, contract):
    sequence = expected_sequence(packets, contract)
    if len(rows) > len(sequence):
        raise ValueError("V84 resume rows exceed frozen call count")
    for index, row in enumerate(rows):
        seed, packet, condition = sequence[index]
        if (row.get("candidate_id"), row.get("seed"), row.get("condition")) != (
            packet["candidate_id"], seed, condition
        ):
            raise ValueError("V84 resume order mismatch")
        if row.get("packet_sha256") != packet["packet_sha256"]:
            raise ValueError("V84 resume packet hash mismatch")
        request = build_request(packet, contract, condition, seed)
        if row.get("request_sha256") != v76.canonical_sha256(request):
            raise ValueError("V84 resume request hash mismatch")
    return sequence
