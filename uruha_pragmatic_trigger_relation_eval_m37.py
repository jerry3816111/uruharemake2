#!/usr/bin/env python3
"""M37 same-model evaluation of verified trigger-to-response relations.

The formal reserve is isolated from production memory.  It compares a
current-turn-only model against the same model after the runtime has selected
one support-verified, raw-free trigger relation.  Surface checks are automatic
proxies and are not evidence of human felt-understanding preference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import uruha_adaptive_person_model as uapm
import uruha_same_model_longitudinal_eval_m35 as m35
from test_personhood_loop_v2_13 import _IsolatedContractBrain


ROOT = Path(__file__).resolve().parent
RESERVE_PATH = ROOT / "datasets/m37_pragmatic_trigger_relation_reserve_v1_1.json"
PROTOCOL_PATH = ROOT / "research/m37_pragmatic_trigger_relation_protocol_v1_1.json"
FREEZE_PATH = ROOT / "research/m37_implementation_freeze_2026-08-26.json"
OUTPUT_PATH = ROOT / "analysis/m37_pragmatic_trigger_relation_reserve_raw_2026-08-26.json"
PREVIOUS_RESERVES = (
    ROOT / "datasets/m35_same_model_longitudinal_pragmatic_reserve_v1.json",
    ROOT / "datasets/m36_compositional_multilingual_pragmatic_reserve_v1.json",
)
M37_SURFACE_VALIDATION_RULE = (
    "\n表面行為の共通検証規則: selected_policy をラベルだけで答えず、reply で実行する。"
    "playful_tease は軽いツッコミの言い切り、solve_regulation は『まず／一個／メモ／決める』等の具体動作、"
    "listen_presence は『話して／続き／聞く／そのまま』等で続きを受け止め、"
    "share_arousal は『一緒／ここにいる／そばにいる』等で同席を表す。"
    "説明文をそのまま reply にコピーせず、相手に直接返す自然なため口に言い換える。"
    "この規則は baseline と system の両方に同じく与えられる。\n"
)
M37_REQUIRED_SURFACE_ACT = {
    "playful_tease": "相手へ軽いツッコミを一つ返し、疑問形にしない。短い casual な punchline にする",
    "solve_regulation": "相手へ今すぐできる具体動作を一つ casual に提案する",
    "listen_presence": "助言せず、相手へ『そのまま話して』等の自然な言葉で続きを促す",
    "share_arousal": "質問や助言をせず、相手へ一緒にいることを自然に伝える",
}


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _rate(numerator, denominator):
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def _ratio(numerator, denominator):
    if not denominator:
        return 0.0 if not numerator else 999.0
    return round(float(numerator) / float(denominator), 4)


def validate_reserve(dataset, protocol):
    cases = list(dataset.get("cases") or [])
    errors = []
    expected_status = (
        "sealed_after_independent_response_policy_validation_before_m37_runtime_implementation"
    )
    if dataset.get("status") != expected_status:
        errors.append("dataset_not_pre_runtime_sealed")
    if protocol.get("status") != expected_status:
        errors.append("protocol_not_pre_runtime_sealed")
    reserve = protocol.get("reserve") or {}
    if len(cases) != int(reserve.get("case_count") or 0):
        errors.append("case_count_mismatch")
    if _sha256(RESERVE_PATH) != reserve.get("sha256"):
        errors.append("dataset_hash_mismatch")
    ids = [str(row.get("case_id") or "") for row in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_case_id")
    language_counts = {
        language: sum(row.get("language") == language for row in cases)
        for language in ("zh", "en", "ja")
    }
    if language_counts != {"zh": 4, "en": 4, "ja": 4}:
        errors.append(f"language_balance:{language_counts}")
    allowed_predicates = set(reserve.get("trigger_predicates") or [])
    pairs = {}
    annotation_audits = []
    for row in cases:
        case_id = str(row.get("case_id") or "")
        pairs.setdefault(row.get("pair_id"), []).append(row)
        expected_policy = str(row.get("expected_current_policy") or "")
        expected_predicate = str(row.get("expected_trigger_predicate") or "")
        if expected_policy not in m35.ALLOWED_POLICIES - {"not_applicable", "calibrate_need"}:
            errors.append(f"invalid_policy:{case_id}")
        if expected_predicate not in allowed_predicates:
            errors.append(f"invalid_trigger_predicate:{case_id}")
        independent = uapm.classify_explicit_desired_response_m25(
            row.get("seed_input") or ""
        )
        candidate = uapm.classify_trigger_relation_candidate_m37(
            row.get("seed_input") or ""
        )
        audit = {
            "case_id": case_id,
            "expected_policy": expected_policy,
            "independent_pre_m37_policy": independent.get("selected_policy"),
            "candidate_trigger_predicate": candidate.get("trigger_predicate"),
            "candidate_status": candidate.get("status"),
        }
        annotation_audits.append(audit)
        if independent.get("selected_policy") != expected_policy:
            errors.append(f"pre_m37_policy_mismatch:{case_id}")
        if candidate.get("trigger_predicate") != expected_predicate:
            errors.append(f"candidate_predicate_mismatch:{case_id}")
        if candidate.get("status") != "candidate_ready":
            errors.append(f"candidate_not_ready:{case_id}")
    for pair_id, group in pairs.items():
        if len(group) != 2:
            errors.append(f"pair_size:{pair_id}:{len(group)}")
            continue
        if len({row.get("current_input") for row in group}) != 1:
            errors.append(f"pair_current_not_identical:{pair_id}")
        if len({row.get("language") for row in group}) != 1:
            errors.append(f"pair_language_not_identical:{pair_id}")
        if len({row.get("expected_trigger_predicate") for row in group}) != 1:
            errors.append(f"pair_trigger_not_identical:{pair_id}")
        if len({row.get("expected_current_policy") for row in group}) != 2:
            errors.append(f"pair_policy_not_divergent:{pair_id}")

    previous_values = set()
    for path in PREVIOUS_RESERVES:
        if not path.exists():
            continue
        previous = json.loads(path.read_text(encoding="utf-8"))
        previous_values.update(
            str(row.get(field) or "")
            for row in (previous.get("cases") or [])
            for field in ("seed_input", "seed_feedback", "current_input", "feedback_input")
            if row.get(field)
        )
    for row in cases:
        for field in ("seed_input", "seed_feedback", "current_input"):
            if row.get(field) and str(row[field]) in previous_values:
                errors.append(f"previous_exact_source_reuse:{row.get('case_id')}:{field}")
    return {
        "passed": not errors,
        "errors": errors,
        "error_count": len(errors),
        "case_count": len(cases),
        "pair_count": len(pairs),
        "language_counts": language_counts,
        "annotation_audits": annotation_audits,
    }


def _system_packet(relation_trace):
    relation_trace = relation_trace if isinstance(relation_trace, dict) else {}
    match = relation_trace.get("match") or {}
    policy = str(match.get("response_policy") or "not_applicable")
    authoritative = bool(
        relation_trace.get("authoritative")
        and match.get("status") == "matched_verified_trigger_relation"
        and policy in m35.ALLOWED_POLICIES
        and policy != "not_applicable"
    )
    return {
        "schema": "uruha_m37_verified_trigger_relation_packet_v1",
        "condition": "verified_trigger_relation_system",
        "stage": "current",
        "trigger_predicate": match.get("trigger_predicate"),
        "match_kind": match.get("match_kind"),
        "relation_id": match.get("relation_id"),
        "verification_status": "supported_previous_seed",
        "must_execute_policy": authoritative,
        "authoritative_policy": policy if authoritative else None,
        "required_surface_act": (
            M37_REQUIRED_SURFACE_ACT.get(policy) if authoritative else None
        ),
        "instruction": "execute the verified typed relation without exposing fields",
        "private_mental_state_truth_available": False,
        "fact_memory_write_allowed": False,
        "raw_history_available": False,
    }


def build_prompt_m37(latest_input, dialogue, packet):
    prompt = m35.build_prompt(
        latest_input,
        dialogue,
        packet,
        "current",
    )
    anchor = m35.FINAL_OUTPUT_ANCHOR
    if anchor not in prompt:
        raise ValueError("M37 shared final-output anchor missing")
    return prompt.replace(anchor, M37_SURFACE_VALIDATION_RULE + anchor, 1)


def _run_case(case, protocol, tokenizer, case_index):
    contract = protocol["model_contract"]
    endpoint = contract["base_url"]
    brain = _IsolatedContractBrain()
    seed_runtime = brain.run_turn_debug(case["seed_input"])
    feedback_runtime = brain.run_turn_debug(case["seed_feedback"])
    current_runtime = brain.run_turn_debug(case["current_input"])
    seed_trace = seed_runtime["runtime_trace"]["pragmatic_trigger_relation_m37"]
    feedback_trace = feedback_runtime["runtime_trace"]["pragmatic_trigger_relation_m37"]
    current_trace = current_runtime["runtime_trace"]["pragmatic_trigger_relation_m37"]
    prompts = {
        "baseline": build_prompt_m37(
            case["current_input"],
            m35._dialogue_current(case["current_input"]),
            m35._baseline_packet("current"),
        ),
        "system": build_prompt_m37(
            case["current_input"],
            m35._dialogue_current(case["current_input"]),
            _system_packet(current_trace),
        ),
    }
    model_results, balance = m35._run_scored_pair(
        prompts,
        endpoint,
        contract,
        tokenizer,
        int(contract["seed"]) + case_index * 131,
    )
    adaptive_serialized = json.dumps(
        brain.runtime.adaptive_person_model,
        ensure_ascii=False,
        sort_keys=True,
    )
    raw_dialogue_persisted = any(
        raw and raw in adaptive_serialized
        for raw in (
            case["seed_input"],
            case["seed_feedback"],
            case["current_input"],
            *[model_results[c].get("reply") or "" for c in m35.CONDITIONS],
        )
    )
    candidate = seed_trace.get("candidate") or {}
    update = feedback_trace.get("verification_update") or {}
    match = current_trace.get("match") or {}
    return {
        "case_id": case["case_id"],
        "pair_id": case["pair_id"],
        "language": case["language"],
        "current_input_digest": _digest(case["current_input"]),
        "expected_trigger_predicate": case["expected_trigger_predicate"],
        "expected_current_policy": case["expected_current_policy"],
        "relation_candidate": {
            "status": candidate.get("status"),
            "trigger_predicate": candidate.get("trigger_predicate"),
            "response_policy": candidate.get("response_policy"),
        },
        "relation_persistence": {
            "status": update.get("status"),
            "trigger_predicate": update.get("trigger_predicate"),
            "response_policy": update.get("response_policy"),
        },
        "relation_current_match": {
            "status": match.get("status"),
            "trigger_predicate": match.get("trigger_predicate"),
            "response_policy": match.get("response_policy"),
            "match_kind": match.get("match_kind"),
        },
        "mechanism_selected_policy": current_trace.get("selected_policy"),
        "mechanism_authoritative": bool(current_trace.get("authoritative")),
        "current": {
            condition: {
                **model_results[condition],
                "surface_proxy_match": m35.policy_surface_proxy(
                    case["expected_current_policy"],
                    model_results[condition].get("reply"),
                ),
                "visible_japanese": m35._visible_japanese(
                    model_results[condition].get("reply")
                ),
            }
            for condition in m35.CONDITIONS
        },
        "current_token_balance": {
            "gate_passed": balance["gate_passed"],
            "rounds": balance["rounds"],
            "final_counts": balance["final_counts"],
        },
        "unverified_mental_fact_write_count": sum(
            bool(trace.get("private_state_truth_claimed"))
            for trace in (candidate, update, match)
        ),
        "raw_dialogue_persisted": raw_dialogue_persisted,
    }


def summarize(rows, gates, reserve_validation_error_count=0):
    count = len(rows)
    pairs = {}
    for row in rows:
        pairs.setdefault(row["pair_id"], []).append(row)
    baseline_accuracy = _rate(
        sum(
            row["current"]["baseline"]["selected_policy"]
            == row["expected_current_policy"]
            for row in rows
        ),
        count,
    )
    system_accuracy = _rate(
        sum(
            row["current"]["system"]["selected_policy"]
            == row["expected_current_policy"]
            for row in rows
        ),
        count,
    )
    prompt_tokens = {
        condition: sum(
            int(row["current"][condition].get("prompt_eval_count") or 0)
            for row in rows
        )
        for condition in m35.CONDITIONS
    }
    completion_tokens = {
        condition: sum(
            int(row["current"][condition].get("eval_count") or 0)
            for row in rows
        )
        for condition in m35.CONDITIONS
    }
    latencies = {
        condition: sum(
            float(row["current"][condition].get("latency_seconds") or 0.0)
            for row in rows
        )
        for condition in m35.CONDITIONS
    }
    visible_rates = {
        condition: _rate(
            sum(row["current"][condition]["visible_japanese"] for row in rows),
            count,
        )
        for condition in m35.CONDITIONS
    }
    metrics = {
        "case_count": count,
        "pair_count": len(pairs),
        "reserve_validation_error_count": int(reserve_validation_error_count),
        "transport_error_count": sum(
            bool(row["current"][condition].get("transport_error"))
            for row in rows
            for condition in m35.CONDITIONS
        ),
        "json_parse_error_count": sum(
            not row["current"][condition].get("parsed")
            for row in rows
            for condition in m35.CONDITIONS
        ),
        "paired_prompt_token_gate_rate": _rate(
            sum(row["current_token_balance"]["gate_passed"] for row in rows),
            count,
        ),
        "system_relation_candidate_accuracy": _rate(
            sum(
                row["relation_candidate"]["status"] == "candidate_ready"
                and row["relation_candidate"]["trigger_predicate"]
                == row["expected_trigger_predicate"]
                and row["relation_candidate"]["response_policy"]
                == row["expected_current_policy"]
                for row in rows
            ),
            count,
        ),
        "system_relation_persistence_accuracy": _rate(
            sum(
                row["relation_persistence"]["status"]
                == "verified_relation_persisted"
                and row["relation_persistence"]["trigger_predicate"]
                == row["expected_trigger_predicate"]
                and row["relation_persistence"]["response_policy"]
                == row["expected_current_policy"]
                for row in rows
            ),
            count,
        ),
        "system_relation_current_match_accuracy": _rate(
            sum(
                row["relation_current_match"]["status"]
                == "matched_verified_trigger_relation"
                and row["relation_current_match"]["trigger_predicate"]
                == row["expected_trigger_predicate"]
                and row["relation_current_match"]["response_policy"]
                == row["expected_current_policy"]
                for row in rows
            ),
            count,
        ),
        "system_mechanism_current_policy_accuracy": _rate(
            sum(
                row["mechanism_selected_policy"] == row["expected_current_policy"]
                and row["mechanism_authoritative"]
                for row in rows
            ),
            count,
        ),
        "baseline_current_policy_accuracy": baseline_accuracy,
        "system_current_policy_accuracy": system_accuracy,
        "system_minus_baseline_current_policy_accuracy": round(
            system_accuracy - baseline_accuracy,
            4,
        ),
        "system_pair_divergence_rate": _rate(
            sum(
                len(group) == 2
                and len(
                    {row["current"]["system"]["selected_policy"] for row in group}
                )
                == 2
                for group in pairs.values()
            ),
            len(pairs),
        ),
        "baseline_pair_policy_invariance_rate": _rate(
            sum(
                len(group) == 2
                and len(
                    {row["current"]["baseline"]["selected_policy"] for row in group}
                )
                == 1
                for group in pairs.values()
            ),
            len(pairs),
        ),
        "baseline_current_surface_proxy_match_rate": _rate(
            sum(row["current"]["baseline"]["surface_proxy_match"] for row in rows),
            count,
        ),
        "system_current_surface_proxy_match_rate": _rate(
            sum(row["current"]["system"]["surface_proxy_match"] for row in rows),
            count,
        ),
        "visible_japanese_rate": visible_rates,
        "unverified_mental_fact_write_count": sum(
            row["unverified_mental_fact_write_count"] for row in rows
        ),
        "raw_dialogue_persisted_count": sum(
            row["raw_dialogue_persisted"] for row in rows
        ),
        "scored_prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_seconds": {
            key: round(value, 4) for key, value in latencies.items()
        },
        "system_to_baseline_scored_prompt_token_ratio": _ratio(
            prompt_tokens["system"], prompt_tokens["baseline"]
        ),
        "system_to_baseline_completion_token_ratio": _ratio(
            completion_tokens["system"], completion_tokens["baseline"]
        ),
        "system_to_baseline_latency_ratio": _ratio(
            latencies["system"], latencies["baseline"]
        ),
        "median_scored_call_seconds": (
            round(
                statistics.median(
                    float(row["current"][condition].get("latency_seconds") or 0.0)
                    for row in rows
                    for condition in m35.CONDITIONS
                ),
                4,
            )
            if rows
            else 0.0
        ),
    }
    gate_results = {}
    for gate_name, threshold in gates.items():
        if gate_name == "visible_japanese_rate_each_condition_min":
            for condition in m35.CONDITIONS:
                gate_results[f"visible_japanese_rate_{condition}_min"] = (
                    visible_rates[condition] >= threshold
                )
            continue
        metric_name = (
            gate_name.removesuffix("_min")
            if gate_name.endswith("_min")
            else gate_name.removesuffix("_max")
        )
        if metric_name not in metrics:
            gate_results[gate_name] = False
        elif gate_name.endswith("_min"):
            gate_results[gate_name] = metrics[metric_name] >= threshold
        else:
            gate_results[gate_name] = metrics[metric_name] <= threshold
    return metrics, gate_results


def run_reserve(output_path=OUTPUT_PATH):
    dataset = json.loads(RESERVE_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    validation = validate_reserve(dataset, protocol)
    if not validation["passed"]:
        raise ValueError(validation["errors"])
    if not FREEZE_PATH.exists():
        raise FileNotFoundError("M37 implementation freeze is required before reserve run")
    rows = [
        _run_case(case, protocol, None, index)
        for index, case in enumerate(dataset["cases"], start=1)
    ]
    metrics, gate_results = summarize(
        rows,
        protocol["frozen_success_gates"],
        validation["error_count"],
    )
    payload = {
        "schema": "uruha_pragmatic_trigger_relation_evaluation_m37_v1",
        "mode": "reserve",
        "dataset_path": str(RESERVE_PATH.relative_to(ROOT)),
        "dataset_sha256": _sha256(RESERVE_PATH),
        "protocol_path": str(PROTOCOL_PATH.relative_to(ROOT)),
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": _sha256(FREEZE_PATH),
        "reserve_validation": validation,
        "model_contract": protocol["model_contract"],
        "decision": (
            "pass_all_frozen_gates"
            if gate_results and all(gate_results.values())
            else "fail_one_or_more_frozen_gates"
        ),
        "metrics": metrics,
        "gate_results": gate_results,
        "rows": rows,
        "claim_boundary": protocol["claim_boundary"],
        "human_felt_understanding_evidence_available": False,
    }
    Path(output_path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reserve",), required=True)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()
    payload = run_reserve(args.output)
    print(
        json.dumps(
            {"decision": payload["decision"], **payload["metrics"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
