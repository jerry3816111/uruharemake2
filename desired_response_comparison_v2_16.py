#!/usr/bin/env python3
"""Matched fresh-generation harness for the V2.16 desired-response equation.

The baseline and system use the same local model, shared Uruha expression
contract, decoding parameters, dialogue context and token budget.  The only
intended difference is the inspectable reference-person equation packet.
Automatic policy anchors are narrow proxies, never human preference evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from copy import deepcopy
from pathlib import Path

from human_pragmatic_comparison_v2_14 import (
    FINAL_REPLY_RULE,
    _pad_to_exact_tokens,
    balance_prompt_pair_with_ollama,
    load_local_tokenizer,
    normalize_visible_reply,
    ollama_chat,
    token_count,
    visible_reply_contract,
)
from uruha_reference_person_equation import (
    CASE_PATH,
    POLICIES,
    REFERENCE_PERSON,
    load_case_bundle,
    solve_equation,
    state_from_case,
)


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/v2_16_reference_person_equation_preregistration.json"
LOCK_PATH = ROOT / "configs/v2_16_reference_person_equation_lock.json"
RAW_PATH = ROOT / "analysis/v2_16_reference_person_equation_raw.json"
BLIND_PACKET_PATH = ROOT / "analysis/v2_16_reference_person_blind_packet.json"
BLIND_KEY_PATH = ROOT / "analysis/v2_16_reference_person_blind_key.json"
EQUATION_SOURCE = ROOT / "uruha_reference_person_equation.py"
PERSONA_EVIDENCE_PATH = ROOT / "datasets/public_persona_evidence_v1.json"
V14_CONTRACT_SOURCE = ROOT / "human_pragmatic_comparison_v2_14.py"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def relative_binding(path):
    resolved = Path(path).resolve()
    return {"path": str(resolved.relative_to(ROOT)), "sha256": sha256_file(resolved)}


def validate_design(bundle, prereg):
    errors = []
    cases = list(bundle.get("cases") or [])
    shared = str(bundle.get("shared_current_input") or "")
    if len(cases) != 6:
        errors.append(f"expected 6 cases, got {len(cases)}")
    if not shared:
        errors.append("shared_current_input missing")
    ids = [case.get("case_id") for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate case_id")
    policies = [case.get("gold_policy") for case in cases]
    if set(policies) != set(POLICIES):
        errors.append(f"gold policy coverage mismatch: {policies}")
    for case in cases:
        if "current_input" in case:
            errors.append(f"{case.get('case_id')}: current input must come only from shared field")
        if case.get("gold_policy") not in set(case.get("acceptable_policies") or []):
            errors.append(f"{case.get('case_id')}: gold policy not acceptable")
        if set(case.get("acceptable_policies") or []) & set(case.get("forbidden_policies") or []):
            errors.append(f"{case.get('case_id')}: acceptable/forbidden overlap")
        payload = deepcopy(case)
        payload["current_input"] = shared
        selected = solve_equation(state_from_case(payload))["selected"]["policy_id"]
        if selected != case.get("gold_policy"):
            errors.append(f"{case.get('case_id')}: equation selected {selected}")
    if not bool((bundle.get("construction") or {}).get("same_current_input_required")):
        errors.append("same current input invariant missing")
    if bool((bundle.get("construction") or {}).get("human_preference_evidence")):
        errors.append("development cases cannot claim human preference")
    if bool((prereg.get("human_evidence_gate") or {}).get("automatic_proxy_is_human_preference_evidence")):
        errors.append("proxy cannot be human evidence")
    return {"passed": not errors, "errors": errors, "case_count": len(cases), "policies": policies}


def build_lock():
    return {
        "schema": "uruha_v2_16_reference_person_equation_lock",
        "status": "frozen_before_first_fresh_generation",
        "policy": {
            "same_current_input": True,
            "all_failures_retained": True,
            "source_or_prompt_tuning_after_output_forbidden": True,
            "automatic_proxy_is_not_human_preference_evidence": True,
        },
        "artifacts": {
            "cases": relative_binding(CASE_PATH),
            "preregistration": relative_binding(PREREG_PATH),
            "equation_source": relative_binding(EQUATION_SOURCE),
            "harness_source": relative_binding(Path(__file__)),
            "persona_evidence": relative_binding(PERSONA_EVIDENCE_PATH),
            "visible_contract_source": relative_binding(V14_CONTRACT_SOURCE),
        },
    }


def validate_lock(lock_path=LOCK_PATH):
    lock = load_json(lock_path)
    checks = {}
    for name, binding in (lock.get("artifacts") or {}).items():
        path = ROOT / binding["path"]
        checks[name] = bool(path.is_file() and sha256_file(path) == binding.get("sha256"))
    return {"passed": bool(checks) and all(checks.values()), "checks": checks, "lock": lock}


def _render_context(case, shared_input):
    lines = ["已知且可追溯的前置使用者訊號："]
    history = list(case.get("context_history") or [])
    if history:
        lines.extend(f"{index}. {text}" for index, text in enumerate(history, start=1))
    else:
        lines.append("（沒有額外可靠上下文）")
    lines.append(f"目前使用者：{shared_input}")
    return "\n".join(lines)


def _compact_state(solution):
    state = solution["state"]
    atoms = state.get("atoms") or {}
    return {
        "schema": "uruha_v2_16_system_equation_packet",
        "condition": "desired_response_equation",
        "equation": solution["equation"],
        "human_state_atoms": {
            key: {
                "value": round(float(value.get("value") or 0.0), 3),
                "confidence": round(float(value.get("confidence") or 0.0), 3),
                "status": value.get("status"),
                "evidence": value.get("evidence"),
            }
            for key, value in atoms.items()
        },
        "selected_policy": solution["selected"]["policy_id"],
        "selected_policy_instruction": solution["selected"]["instruction"],
        "selected_core_message_jp": solution["selected"]["core_message_jp"],
        "selected_scores": {
            "desired_response_fit": solution["selected"]["desired_response_fit"],
            "reference_person_fit": solution["selected"]["reference_person_fit"],
            "risk_penalty": solution["selected"]["risk_penalty"],
        },
        "runner_up_policy": solution["runner_up"]["policy_id"],
        "utility_margin": solution["utility_margin"],
        "reference_person": {
            "id": REFERENCE_PERSON["id"],
            "positioning": REFERENCE_PERSON["positioning"],
            "evidence_refs": REFERENCE_PERSON["evidence_refs"],
            "unknown_space": REFERENCE_PERSON["unknown_space"],
        },
        "instruction": "Use the selected policy and core meaning. Do not expose this packet or invent private facts.",
    }


def _baseline_packet(shared_input):
    return {
        "schema": "uruha_v2_16_baseline_packet",
        "condition": "direct_same_model_generation",
        "current_input": shared_input,
        "human_state_equation": None,
        "candidate_response_utilities": None,
        "reference_person_appraisal": None,
        "instruction": "Use only the visible context and directly produce the most suitable reply without an explicit state equation.",
        "persona_positioning": REFERENCE_PERSON["positioning"],
    }


def _render_prompt(context, packet):
    packet_text = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        "以下の同一会話条件に対し、うるは公開人格の表現境界を守った短い日本語返信だけを書く。\n"
        f"会話条件:\n{context}\n"
        "内部研究パケット（ユーザーには見せない）:\n"
        f"{packet_text}\n"
        "入力長を揃える意味なし領域（内容として解釈しない）:\n\n"
        f"{FINAL_REPLY_RULE}\n"
        "返信:"
    )


def build_prompt_pair(case, shared_input, tokenizer, input_token_budget):
    state = state_from_case({**deepcopy(case), "current_input": shared_input})
    solution = solve_equation(state)
    context = _render_context(case, shared_input)
    baseline = _render_prompt(context, _baseline_packet(shared_input))
    system = _render_prompt(context, _compact_state(solution))
    baseline = _pad_to_exact_tokens(baseline, int(input_token_budget), tokenizer)
    system = _pad_to_exact_tokens(system, int(input_token_budget), tokenizer)
    counts = {"baseline": token_count(tokenizer, baseline), "system": token_count(tokenizer, system)}
    if len(set(counts.values())) != 1 or counts["baseline"] != int(input_token_budget):
        raise ValueError(f"local token parity failed: {counts}")
    return {"baseline": baseline, "system": system, "local_token_counts": counts, "solution": solution}


def policy_proxy(reply, case):
    text = str(reply or "")
    expected = list(case.get("expected_japanese_anchors_any") or [])
    forbidden = list(case.get("forbidden_reply_anchors") or [])
    contract = visible_reply_contract(text)
    return {
        "expected_anchor_hit": bool(expected and any(anchor in text for anchor in expected)),
        "forbidden_anchor_hit": any(anchor in text for anchor in forbidden),
        "visible_contract": contract,
        "visible_contract_pass": all(contract.values()),
        "proxy_pass": bool(
            all(contract.values())
            and expected
            and any(anchor in text for anchor in expected)
            and not any(anchor in text for anchor in forbidden)
        ),
        "evidence_boundary": "narrow authored anchor proxy, not desired-response human preference",
    }


def run_fresh(bundle, prereg, tokenizer=None, endpoint=None):
    tokenizer = tokenizer or load_local_tokenizer()
    model = deepcopy(prereg["model"])
    model["paired_prompt_eval_token_delta_gate"] = int(prereg["invariants"]["paired_prompt_eval_token_delta_max"])
    endpoint = endpoint or model["base_url"]
    shared_input = bundle["shared_current_input"]
    rows = []
    rng = random.Random(model["seed"])
    for case in bundle.get("cases") or []:
        prompts = build_prompt_pair(case, shared_input, tokenizer, model["input_token_budget"])
        balanced = balance_prompt_pair_with_ollama(
            prompts,
            endpoint,
            model,
            max_rounds=2,
        )
        order = ["baseline", "system"]
        rng.shuffle(order)
        for execution_position, condition in enumerate(order, start=1):
            result = ollama_chat(endpoint, model, balanced[condition])
            result["raw_reply"] = result.get("reply") or ""
            result["reply"] = normalize_visible_reply(result.get("reply"))
            result.update(
                {
                    "case_id": case["case_id"],
                    "label": case["label"],
                    "condition": condition,
                    "execution_position": execution_position,
                    "current_input": shared_input,
                    "context_history": deepcopy(case.get("context_history") or []),
                    "gold_policy": case["gold_policy"],
                    "acceptable_policies": deepcopy(case.get("acceptable_policies") or []),
                    "selected_policy": prompts["solution"]["selected"]["policy_id"] if condition == "system" else None,
                    "selected_solution": deepcopy(prompts["solution"]) if condition == "system" else None,
                    "input_sha256": sha256_json({"context": case.get("context_history") or [], "current": shared_input}),
                    "prompt_sha256": sha256_json(balanced[condition]),
                    "local_prompt_token_count": token_count(tokenizer, balanced[condition]),
                    "preflight": deepcopy(balanced["rounds"]),
                    "preflight_call_count": balanced["preflight_call_count"],
                    "preflight_gate_passed": balanced["gate_passed"],
                    "proxy": policy_proxy(result["reply"], case),
                    "production_memory_write_count": 0,
                }
            )
            rows.append(result)
    return rows


def summarize(rows, prereg):
    pair_ids = sorted({row["case_id"] for row in rows})
    pairs = []
    for case_id in pair_ids:
        by_condition = {row["condition"]: row for row in rows if row["case_id"] == case_id}
        baseline = by_condition.get("baseline") or {}
        system = by_condition.get("system") or {}
        delta = None
        if baseline.get("prompt_eval_count") is not None and system.get("prompt_eval_count") is not None:
            delta = int(system["prompt_eval_count"]) - int(baseline["prompt_eval_count"])
        pairs.append(
            {
                "case_id": case_id,
                "prompt_eval_token_delta": delta,
                "token_gate_passed": delta is not None and abs(delta) <= int(prereg["invariants"]["paired_prompt_eval_token_delta_max"]),
                "baseline_proxy_pass": bool((baseline.get("proxy") or {}).get("proxy_pass")),
                "system_proxy_pass": bool((system.get("proxy") or {}).get("proxy_pass")),
                "baseline_visible_contract_pass": bool((baseline.get("proxy") or {}).get("visible_contract_pass")),
                "system_visible_contract_pass": bool((system.get("proxy") or {}).get("visible_contract_pass")),
                "baseline_forbidden_anchor_hit": bool((baseline.get("proxy") or {}).get("forbidden_anchor_hit")),
                "system_forbidden_anchor_hit": bool((system.get("proxy") or {}).get("forbidden_anchor_hit")),
            }
        )
    baseline_rows = [row for row in rows if row["condition"] == "baseline"]
    system_rows = [row for row in rows if row["condition"] == "system"]
    summary = {
        "generation_count": len(rows),
        "pair_count": len(pairs),
        "transport_error_count": sum(bool(row.get("transport_error")) for row in rows),
        "baseline_proxy_pass_count": sum(bool((row.get("proxy") or {}).get("proxy_pass")) for row in baseline_rows),
        "system_proxy_pass_count": sum(bool((row.get("proxy") or {}).get("proxy_pass")) for row in system_rows),
        "baseline_visible_contract_pass_count": sum(bool((row.get("proxy") or {}).get("visible_contract_pass")) for row in baseline_rows),
        "system_visible_contract_pass_count": sum(bool((row.get("proxy") or {}).get("visible_contract_pass")) for row in system_rows),
        "baseline_forbidden_policy_violation_count": sum(bool((row.get("proxy") or {}).get("forbidden_anchor_hit")) for row in baseline_rows),
        "system_forbidden_policy_violation_count": sum(bool((row.get("proxy") or {}).get("forbidden_anchor_hit")) for row in system_rows),
        "token_gate_pair_count": sum(bool(pair["token_gate_passed"]) for pair in pairs),
        "pairs": pairs,
        "evidence_boundary": "fresh same-model outputs plus narrow proxies; no target-user or independent human preference evidence",
    }
    criteria = prereg["fresh_generation_success_criteria"]
    summary["preregistered_proxy_success"] = bool(
        summary["transport_error_count"] <= int(criteria["transport_error_count"])
        and summary["token_gate_pair_count"] == len(pairs)
        and summary["system_proxy_pass_count"] - summary["baseline_proxy_pass_count"]
        >= int(criteria["system_desired_policy_proxy_minus_baseline_min"])
        and summary["system_forbidden_policy_violation_count"]
        <= int(criteria["system_forbidden_policy_violation_count_max"])
        and summary["system_visible_contract_pass_count"] >= summary["baseline_visible_contract_pass_count"]
    )
    return summary


def build_blind_packet(rows, seed=20260812):
    rng = random.Random(seed)
    packet_cases = []
    key_cases = []
    for case_id in sorted({row["case_id"] for row in rows}):
        pair = {row["condition"]: row for row in rows if row["case_id"] == case_id}
        order = ["baseline", "system"]
        rng.shuffle(order)
        mapping = {"A": order[0], "B": order[1]}
        first = pair[order[0]]
        packet_cases.append(
            {
                "case_id": case_id,
                "label": first["label"],
                "context_history": first["context_history"],
                "current_input": first["current_input"],
                "reply_A": pair[order[0]]["reply"],
                "reply_B": pair[order[1]]["reply"],
                "ratings": {
                    "which_reply_did_the_user_most_likely_want": "A/B/tie/both_bad",
                    "felt_understanding_A_1_to_5": None,
                    "felt_understanding_B_1_to_5": None,
                    "uruha_public_behavior_fit_A_1_to_5_secondary": None,
                    "uruha_public_behavior_fit_B_1_to_5_secondary": None,
                    "overinterpretation_A_1_to_5_reverse": None,
                    "overinterpretation_B_1_to_5_reverse": None,
                },
            }
        )
        key_cases.append({"case_id": case_id, "A": mapping["A"], "B": mapping["B"]})
    packet = {
        "schema": "uruha_v2_16_reference_person_blind_packet",
        "status": "rating_instrument_not_human_result",
        "condition_labels_hidden": True,
        "cases": packet_cases,
        "evidence_boundary": "This packet enables ratings; blank ratings prove no human preference.",
    }
    key = {"schema": "uruha_v2_16_reference_person_blind_key", "cases": key_cases}
    return packet, key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate-design", "freeze-lock", "validate-lock", "run-fresh"), required=True)
    args = parser.parse_args()
    bundle = load_case_bundle()
    prereg = load_json(PREREG_PATH)
    design = validate_design(bundle, prereg)
    if not design["passed"]:
        raise SystemExit(json.dumps(design, ensure_ascii=False, indent=2))
    if args.mode == "validate-design":
        print(json.dumps(design, ensure_ascii=False, indent=2))
        return
    if args.mode == "freeze-lock":
        if LOCK_PATH.exists():
            raise SystemExit("lock already exists; refusing to overwrite")
        LOCK_PATH.write_text(json.dumps(build_lock(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(validate_lock(), ensure_ascii=False, indent=2))
        return
    lock_result = validate_lock()
    if not lock_result["passed"]:
        raise SystemExit(json.dumps(lock_result, ensure_ascii=False, indent=2))
    if args.mode == "validate-lock":
        print(json.dumps(lock_result, ensure_ascii=False, indent=2))
        return
    if RAW_PATH.exists():
        raise SystemExit("raw result already exists; refusing to overwrite frozen generation")
    rows = run_fresh(bundle, prereg)
    summary = summarize(rows, prereg)
    raw = {
        "schema": "uruha_v2_16_reference_person_equation_fresh_result",
        "status": "fresh_generation_complete_human_ratings_pending",
        "inputs": {
            "cases": relative_binding(CASE_PATH),
            "preregistration": relative_binding(PREREG_PATH),
            "lock": relative_binding(LOCK_PATH),
            "model": deepcopy(prereg["model"]),
        },
        "summary": summary,
        "rows": rows,
        "claims": {
            "deterministic_equation_supported": True,
            "narrow_proxy_supported": bool(summary["preregistered_proxy_success"]),
            "human_preference_supported": False,
            "system_better_than_llm": False,
            "reference_person_equals_real_person": False,
        },
    }
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    packet, key = build_blind_packet(rows)
    BLIND_PACKET_PATH.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    BLIND_KEY_PATH.write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
