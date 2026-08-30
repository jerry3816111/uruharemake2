#!/usr/bin/env python3
"""M35 same-model current-turn baseline vs longitudinal pragmatic system.

The evaluator is deliberately isolated from production memory.  It compares
the same local model and visible-persona contract while intervening on only the
typed M34 longitudinal packet.  Automatic surface checks remain proxies and
must not be reported as human felt-understanding evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import statistics
import time
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path

from human_pragmatic_comparison_v2_14 import (
    normalize_visible_reply,
    token_count,
    visible_reply_contract,
)
from test_personhood_loop_v2_13 import _IsolatedContractBrain


ROOT = Path(__file__).resolve().parent
RESERVE_PATH = ROOT / "datasets/m35_same_model_longitudinal_pragmatic_reserve_v1.json"
PROTOCOL_PATH = ROOT / "research/m35_same_model_longitudinal_pragmatic_protocol.json"
FREEZE_PATH = ROOT / "research/m35_implementation_freeze_2026-08-25.json"
OUTPUT_PATH = ROOT / "analysis/m35_same_model_longitudinal_pragmatic_reserve_raw_2026-08-25.json"

CONDITIONS = ("baseline", "system")
ALLOWED_POLICIES = {
    "playful_tease",
    "solve_regulation",
    "listen_presence",
    "share_arousal",
    "calibrate_need",
    "not_applicable",
}
FINAL_OUTPUT_ANCHOR = (
    "\n出力規則: JSON オブジェクト一つだけ。selected_policy と reply 以外を出さない。"
)
SHARED_SYSTEM_PROMPT = """あなたは同一モデル比較実験の会話生成器。実在人物本人ではなく、公開情報だけに基づくうるは風の表現契約を使う。私生活、未公開経験、相手の私的心理を事実として作らない。返事は入力言語に関係なく自然で短い日本語だけ、ため口、一文か二文。一人称が必要なら「うち」。です・ます、接客口調、引用符、内部分析、信頼度の説明は禁止。出力は必ず JSON 一個だけで、形式は {"selected_policy":"許可されたID","reply":"実際にユーザーへ見せる日本語"}。"""

POLICY_GUIDE = {
    "playful_tease": "軽いツッコミを一つ。共感質問や助言には変えず、疑問形を使わない。短い punchline を『かよ』『じゃん』などの casual な言い切りで終える",
    "solve_regulation": "今すぐ実行できる具体的な動作を一つ。深呼吸、メモ、離れる等を命令ではなく casual に提案し、抽象的な共感だけで終えない",
    "listen_presence": "直そうとせず続きを話せるよう受け止める",
    "share_arousal": "質問や助言をせず、ここにいる／一緒にいると伝える",
    "calibrate_need": "決めつけず短い低圧の確認を一つ",
    "not_applicable": "単純な確認への相づち、または新しい話題への普通の返事",
}
POLICY_SURFACE_ANCHORS = {
    "playful_tease": ("脳内", "かよ", "じゃん", "回りすぎ", "止まる気", "営業"),
    "solve_regulation": ("まず", "一個", "ひとつ", "メモ", "書", "離れ", "決め", "やって", "深呼吸", "して", "しよ"),
    "listen_presence": ("話して", "聞く", "聞いて", "そのまま", "続き", "言って"),
    "share_arousal": ("ここにいる", "そばにいる", "一緒", "付き合", "隣に"),
    "calibrate_need": ("どっち", "どうしてほしい", "どれ", "？", "?"),
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
    if dataset.get("status") != "sealed_before_m35_evaluator_implementation":
        errors.append("dataset_not_preimplementation_sealed")
    if protocol.get("status") != "sealed_before_m35_evaluator_implementation":
        errors.append("protocol_not_preimplementation_sealed")
    if len(cases) != int((protocol.get("reserve") or {}).get("case_count") or 0):
        errors.append("case_count_mismatch")
    if _sha256(RESERVE_PATH) != (protocol.get("reserve") or {}).get("sha256"):
        errors.append("dataset_hash_mismatch")
    ids = [row.get("case_id") for row in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_case_id")
    languages = {
        language: sum(row.get("language") == language for row in cases)
        for language in ("zh", "en", "ja")
    }
    if languages != {"zh": 4, "en": 4, "ja": 4}:
        errors.append(f"language_balance:{languages}")
    pairs = {}
    for row in cases:
        pairs.setdefault(row.get("pair_id"), []).append(row)
        if row.get("expected_current_policy") not in ALLOWED_POLICIES:
            errors.append(f"invalid_current_policy:{row.get('case_id')}")
        if row.get("expected_feedback_policy") not in ALLOWED_POLICIES:
            errors.append(f"invalid_feedback_policy:{row.get('case_id')}")
        if row.get("expected_feedback_outcome") not in {
            "supported",
            "contradicted",
            "uncertain",
        }:
            errors.append(f"invalid_feedback_outcome:{row.get('case_id')}")
    for pair_id, group in pairs.items():
        if len(group) != 2:
            errors.append(f"pair_size:{pair_id}:{len(group)}")
            continue
        if len({row.get("current_input") for row in group}) != 1:
            errors.append(f"pair_current_not_identical:{pair_id}")
        if len({row.get("language") for row in group}) != 1:
            errors.append(f"pair_language_not_identical:{pair_id}")
        if len({row.get("expected_current_policy") for row in group}) != 2:
            errors.append(f"pair_policy_not_divergent:{pair_id}")
    return {
        "passed": not errors,
        "errors": errors,
        "case_count": len(cases),
        "pair_count": len(pairs),
        "language_counts": languages,
    }


def _branch_packet(branch, stage):
    branch = branch if isinstance(branch, dict) else {}
    selected = branch.get("selected_branch") or {}
    alternative = branch.get("bounded_alternative") or {}
    evidence = branch.get("context_evidence") or {}
    prediction = branch.get("observable_prediction") or {}
    verification = branch.get("previous_branch_verification") or {}
    revision = branch.get("revision") or {}
    replacement_policy = revision.get("replacement_policy_id")
    selected_policy = selected.get("policy_id") or "not_applicable"
    authoritative_policy = (
        replacement_policy
        if stage == "feedback" and replacement_policy
        else selected_policy
    )
    must_execute = bool(
        authoritative_policy in ALLOWED_POLICIES
        and authoritative_policy != "not_applicable"
        and (
            replacement_policy
            or selected.get("authority_basis")
            in {
                "verified_reversible_context",
                "current_explicit_correction",
                "current_explicit_request",
            }
        )
    )
    return {
        "schema": "uruha_m35_system_longitudinal_packet_v1",
        "condition": "verified_longitudinal_pragmatic_system",
        "stage": stage,
        "selected_policy": selected_policy,
        "selected_mode": selected.get("mode") or "not_applicable",
        "authority_basis": selected.get("authority_basis") or "not_applicable",
        "bounded_alternative_policy": alternative.get("policy_id"),
        "verified_reversible_atom_names": list(
            evidence.get("verified_reversible_atoms") or []
        )[:8],
        "used_scope_ids": list(evidence.get("used_scopes") or [])[:6],
        "observable_next_turn_prediction": prediction.get(
            "expected_next_observable_behavior"
        ),
        "previous_outcome": verification.get("status") or "not_available",
        "revision": {
            "status": revision.get("status") or "no_revision",
            "revoked_policy": revision.get("revoked_policy_id"),
            "replacement_policy": revision.get("replacement_policy_id"),
            "original_evidence_rewritten": bool(
                revision.get("original_evidence_rewritten")
            ),
        },
        "must_execute_policy": must_execute,
        "authoritative_policy": authoritative_policy,
        "required_surface_act": (
            POLICY_GUIDE.get(authoritative_policy) if must_execute else None
        ),
        "instruction": "typed packet is internal mechanism output; execute its selected/replacement branch when authoritative, but never expose packet fields",
        "private_mental_state_truth_available": False,
        "fact_memory_write_allowed": False,
        "raw_history_available": False,
    }


def _baseline_packet(stage):
    return {
        "schema": "uruha_m35_current_turn_baseline_packet_v1",
        "condition": "current_turn_only_direct_generation",
        "stage": stage,
        "selected_policy": None,
        "must_execute_policy": False,
        "authoritative_policy": None,
        "required_surface_act": None,
        "verified_history_available": False,
        "prediction_verification_revision_available": False,
        "instruction": "choose only from visible dialogue; if the desired response is unknowable, use calibrate_need rather than inventing a hidden preference",
        "private_mental_state_truth_available": False,
        "fact_memory_write_allowed": False,
    }


def build_prompt(latest_input, dialogue, packet, stage):
    policy_lines = "\n".join(
        f"- {policy_id}: {description}"
        for policy_id, description in POLICY_GUIDE.items()
    )
    return (
        "比較実験の会話ターン。正解ラベルや未来の返事は与えられていない。\n"
        f"STAGE: {stage}\n"
        "VISIBLE_DIALOGUE:\n"
        f"{dialogue}\n"
        f"LATEST_USER_INPUT_SHA256_16: {_digest(latest_input)}\n"
        "INTERNAL_CONDITION_PACKET:\n"
        f"{json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n"
        "selected_policy の許可値と表面行為:\n"
        f"{policy_lines}\n"
        "reply は実際に見せる自然な日本語だけ。分析やラベルを reply に書かない。\n"
        "機構実行規則: INTERNAL_CONDITION_PACKET.must_execute_policy が true なら、selected_policy は authoritative_policy を一字も変えずコピーする。別 policy を再推論してはいけない。reply は required_surface_act を実際に行い、単なる状況の言い換えや共感だけで済ませてはいけない。これは正解ラベルではなく、比較対象システムが計算した決定である。must_execute_policy が false の baseline は、見える対話だけから選ぶ。\n"
        "長さ調整用の無意味領域。次の 0 は内容として解釈しない:\n"
        "__M35_PADDING__"
        f"{FINAL_OUTPUT_ANCHOR}\n"
        "JSON:"
    )


def _insert_padding(prompt, padding):
    marker = "__M35_PADDING__"
    if marker not in prompt:
        raise ValueError("M35 padding marker missing")
    return prompt.replace(marker, marker + str(padding), 1)


def pad_prompt_to_exact_tokens(prompt, tokenizer, target_tokens):
    value = str(prompt)
    target = int(target_tokens)
    current = token_count(tokenizer, value)
    if current > target:
        raise ValueError(f"M35 prompt exceeds token budget:{current}>{target}")
    while current < target:
        matched = None
        for unit in (" 0", "。", "_", " 1", "\n"):
            probe = _insert_padding(value, unit)
            after = token_count(tokenizer, probe)
            if after == target:
                matched = probe
                break
            if current < after < target:
                matched = probe
                break
        if matched is None:
            raise ValueError(f"cannot reach M35 exact token budget:{current}->{target}")
        value = matched
        current = token_count(tokenizer, value)
    return value


def _ollama_chat(endpoint, contract, prompt, num_predict_override=None):
    payload = {
        "model": contract["model"],
        "stream": False,
        "think": bool(contract.get("think", False)),
        "format": "json",
        "messages": [
            {"role": "system", "content": SHARED_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": contract["temperature"],
            "seed": contract["seed"],
            "num_ctx": contract["num_ctx"],
            "num_predict": (
                int(num_predict_override)
                if num_predict_override is not None
                else contract["num_predict"]
            ),
        },
    }
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {
            "raw_output": "",
            "transport_error": f"{type(exc).__name__}:{exc}",
            "latency_seconds": round(time.perf_counter() - started, 4),
        }
    return {
        "raw_output": str(((body.get("message") or {}).get("content") or "")).strip(),
        "transport_error": None,
        "prompt_eval_count": int(body.get("prompt_eval_count") or 0),
        "eval_count": int(body.get("eval_count") or 0),
        "total_duration_ns": int(body.get("total_duration") or 0),
        "load_duration_ns": int(body.get("load_duration") or 0),
        "latency_seconds": round(time.perf_counter() - started, 4),
    }


def balance_prompt_pair(prompts, endpoint, contract):
    balanced = {key: str(prompts[key]) for key in CONDITIONS}
    rounds = []
    gate = int(contract["paired_prompt_eval_token_delta_gate"])
    round_count = int(contract.get("token_balance_preflight_rounds") or 2)
    for round_index in range(1, round_count + 1):
        measured = {
            condition: _ollama_chat(
                endpoint,
                contract,
                balanced[condition],
                num_predict_override=1,
            )
            for condition in CONDITIONS
        }
        counts = {
            condition: measured[condition].get("prompt_eval_count")
            for condition in CONDITIONS
        }
        if any(measured[c].get("transport_error") for c in CONDITIONS):
            raise RuntimeError(f"M35 token preflight transport failed:{measured}")
        budget = int(contract.get("input_token_budget") or 0)
        if budget and any(int(counts[c] or 0) > budget for c in CONDITIONS):
            raise RuntimeError(f"M35 prompt token budget exceeded:{counts}>{budget}")
        delta = int(counts["system"] or 0) - int(counts["baseline"] or 0)
        rounds.append(
            {
                "round": round_index,
                "counts": counts,
                "delta_system_minus_baseline": delta,
                "within_gate": abs(delta) <= gate,
                "generated_output_discarded": True,
            }
        )
        if round_index < round_count and abs(delta) > gate:
            shorter = "baseline" if delta > 0 else "system"
            magnitude = abs(delta)
            padding = " 0" * (magnitude // 2)
            if magnitude % 2:
                padding += "。"
            balanced[shorter] = _insert_padding(balanced[shorter], padding)
    return {
        **balanced,
        "rounds": rounds,
        "gate_passed": bool(rounds and rounds[-1]["within_gate"]),
        "final_counts": deepcopy((rounds[-1] if rounds else {}).get("counts") or {}),
    }


def parse_model_output(raw_output):
    text = str(raw_output or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            "parsed": False,
            "parse_error": f"JSONDecodeError:{exc}",
            "selected_policy": "parse_error",
            "reply": "",
        }
    policy = str(payload.get("selected_policy") or "").strip()
    reply = normalize_visible_reply(payload.get("reply") or "")
    if policy not in ALLOWED_POLICIES:
        return {
            "parsed": False,
            "parse_error": f"invalid_policy:{policy}",
            "selected_policy": "parse_error",
            "reply": reply,
        }
    return {
        "parsed": bool(reply),
        "parse_error": None if reply else "empty_reply",
        "selected_policy": policy,
        "reply": reply,
    }


def policy_surface_proxy(policy, reply):
    anchors = POLICY_SURFACE_ANCHORS.get(str(policy), ())
    if not anchors:
        return None
    return any(anchor in str(reply or "") for anchor in anchors)


def _visible_japanese(reply):
    contract = visible_reply_contract(reply)
    return bool(
        contract.get("nonempty")
        and contract.get("has_japanese")
        and contract.get("no_foreign_or_nonstandard_language")
        and contract.get("no_analysis_dump")
        and contract.get("no_private_person_claim")
        and contract.get("no_mind_reading_claim")
    )


def _run_scored_pair(prompts, endpoint, contract, tokenizer, order_seed):
    # Ollama's own prompt_eval_count is the authoritative tokenizer.  A local
    # Qwen tokenizer snapshot is intentionally not required because its
    # serialized format can drift from the installed transformers runtime.
    locally_padded = {condition: str(prompts[condition]) for condition in CONDITIONS}
    balance = balance_prompt_pair(locally_padded, endpoint, contract)
    order = list(CONDITIONS)
    random.Random(order_seed).shuffle(order)
    results = {}
    for condition in order:
        raw = _ollama_chat(endpoint, contract, balance[condition])
        parsed = parse_model_output(raw.get("raw_output"))
        results[condition] = {
            **raw,
            **parsed,
            "execution_position": order.index(condition) + 1,
            "prompt_sha256": _digest(balance[condition]),
            "local_prompt_token_count": (
                token_count(tokenizer, balance[condition])
                if tokenizer is not None
                else None
            ),
        }
    return results, balance


def _dialogue_current(current_input):
    return f"ユーザー: {current_input}"


def _dialogue_feedback(current_input, prior_reply, feedback_input):
    return (
        f"ユーザー: {current_input}\n"
        f"うるは: {prior_reply}\n"
        f"ユーザー: {feedback_input}"
    )


def _run_case(case, protocol, tokenizer, case_index):
    contract = protocol["model_contract"]
    endpoint = contract["base_url"]
    brain = _IsolatedContractBrain()
    brain.run_turn_debug(case["seed_input"])
    brain.run_turn_debug(case["seed_feedback"])
    current_runtime = brain.run_turn_debug(case["current_input"])
    current_branch = (
        (current_runtime.get("runtime_trace") or {}).get(
            "counterfactual_pragmatic_branch_m34"
        )
        or {}
    )
    current_prompts = {
        "baseline": build_prompt(
            case["current_input"],
            _dialogue_current(case["current_input"]),
            _baseline_packet("current"),
            "current",
        ),
        "system": build_prompt(
            case["current_input"],
            _dialogue_current(case["current_input"]),
            _branch_packet(current_branch, "current"),
            "current",
        ),
    }
    current_results, current_balance = _run_scored_pair(
        current_prompts,
        endpoint,
        contract,
        tokenizer,
        int(contract["seed"]) + case_index * 101,
    )

    feedback_runtime = brain.run_turn_debug(case["feedback_input"])
    feedback_branch = (
        (feedback_runtime.get("runtime_trace") or {}).get(
            "counterfactual_pragmatic_branch_m34"
        )
        or {}
    )
    feedback_prompts = {
        condition: build_prompt(
            case["feedback_input"],
            _dialogue_feedback(
                case["current_input"],
                current_results[condition].get("reply") or "",
                case["feedback_input"],
            ),
            (
                _baseline_packet("feedback")
                if condition == "baseline"
                else _branch_packet(feedback_branch, "feedback")
            ),
            "feedback",
        )
        for condition in CONDITIONS
    }
    feedback_results, feedback_balance = _run_scored_pair(
        feedback_prompts,
        endpoint,
        contract,
        tokenizer,
        int(contract["seed"]) + case_index * 101 + 37,
    )

    current_selected = current_branch.get("selected_branch") or {}
    previous_verification = feedback_branch.get("previous_branch_verification") or {}
    revision = feedback_branch.get("revision") or {}
    adaptive_serialized = json.dumps(
        brain.runtime.adaptive_person_model,
        ensure_ascii=False,
        sort_keys=True,
    )
    forbidden_raw = [
        case["seed_input"],
        case["seed_feedback"],
        case["current_input"],
        case["feedback_input"],
        *[
            stage_results[condition].get("reply") or ""
            for stage_results in (current_results, feedback_results)
            for condition in CONDITIONS
        ],
    ]
    raw_persisted = any(value and value in adaptive_serialized for value in forbidden_raw)
    return {
        "case_id": case["case_id"],
        "pair_id": case["pair_id"],
        "language": case["language"],
        "current_input_digest": _digest(case["current_input"]),
        "expected_current_policy": case["expected_current_policy"],
        "expected_feedback_outcome": case["expected_feedback_outcome"],
        "expected_feedback_policy": case["expected_feedback_policy"],
        "m34_current_policy": current_selected.get("policy_id"),
        "m34_current_authority": current_selected.get("authority_basis"),
        "m34_feedback_outcome": previous_verification.get("status"),
        "m34_revision_replacement": revision.get("replacement_policy_id"),
        "m34_original_evidence_rewritten": bool(
            revision.get("original_evidence_rewritten")
        ),
        "current": {
            condition: {
                **current_results[condition],
                "surface_proxy_match": policy_surface_proxy(
                    case["expected_current_policy"],
                    current_results[condition].get("reply"),
                ),
                "visible_japanese": _visible_japanese(
                    current_results[condition].get("reply")
                ),
            }
            for condition in CONDITIONS
        },
        "feedback": {
            condition: {
                **feedback_results[condition],
                "visible_japanese": _visible_japanese(
                    feedback_results[condition].get("reply")
                ),
            }
            for condition in CONDITIONS
        },
        "current_token_balance": {
            "gate_passed": current_balance["gate_passed"],
            "rounds": current_balance["rounds"],
        },
        "feedback_token_balance": {
            "gate_passed": feedback_balance["gate_passed"],
            "rounds": feedback_balance["rounds"],
        },
        "unverified_mental_fact_write_count": int(
            current_branch.get("fact_memory_write_count") or 0
        )
        + int(feedback_branch.get("fact_memory_write_count") or 0),
        "raw_dialogue_persisted": raw_persisted,
    }


def summarize(rows, gates):
    count = len(rows)
    contradiction_rows = [
        row for row in rows if row["expected_feedback_outcome"] == "contradicted"
    ]
    pair_groups = {}
    for row in rows:
        pair_groups.setdefault(row["pair_id"], []).append(row)

    def policy_accuracy(stage, condition):
        expected_key = (
            "expected_current_policy" if stage == "current" else "expected_feedback_policy"
        )
        scored_rows = rows if stage == "current" else contradiction_rows
        return _rate(
            sum(
                row[stage][condition]["selected_policy"] == row[expected_key]
                for row in scored_rows
            ),
            len(scored_rows),
        )

    baseline_current = policy_accuracy("current", "baseline")
    system_current = policy_accuracy("current", "system")
    baseline_feedback = policy_accuracy("feedback", "baseline")
    system_feedback = policy_accuracy("feedback", "system")
    prompt_counts = {
        condition: sum(
            int(row[stage][condition].get("prompt_eval_count") or 0)
            for row in rows
            for stage in ("current", "feedback")
        )
        for condition in CONDITIONS
    }
    completion_counts = {
        condition: sum(
            int(row[stage][condition].get("eval_count") or 0)
            for row in rows
            for stage in ("current", "feedback")
        )
        for condition in CONDITIONS
    }
    latencies = {
        condition: sum(
            float(row[stage][condition].get("latency_seconds") or 0.0)
            for row in rows
            for stage in ("current", "feedback")
        )
        for condition in CONDITIONS
    }
    visible_rates = {
        condition: _rate(
            sum(
                row[stage][condition]["visible_japanese"]
                for row in rows
                for stage in ("current", "feedback")
            ),
            count * 2,
        )
        for condition in CONDITIONS
    }
    surface_rates = {
        condition: _rate(
            sum(row["current"][condition]["surface_proxy_match"] for row in rows),
            count,
        )
        for condition in CONDITIONS
    }
    metrics = {
        "case_count": count,
        "pair_count": len(pair_groups),
        "transport_error_count": sum(
            bool(row[stage][condition].get("transport_error"))
            for row in rows
            for stage in ("current", "feedback")
            for condition in CONDITIONS
        ),
        "json_parse_error_count": sum(
            not row[stage][condition].get("parsed")
            for row in rows
            for stage in ("current", "feedback")
            for condition in CONDITIONS
        ),
        "paired_prompt_token_gate_rate": _rate(
            sum(
                row[key]["gate_passed"]
                for row in rows
                for key in ("current_token_balance", "feedback_token_balance")
            ),
            count * 2,
        ),
        "system_mechanism_current_policy_accuracy": _rate(
            sum(row["m34_current_policy"] == row["expected_current_policy"] for row in rows),
            count,
        ),
        "system_mechanism_feedback_outcome_accuracy": _rate(
            sum(row["m34_feedback_outcome"] == row["expected_feedback_outcome"] for row in rows),
            count,
        ),
        "baseline_current_policy_accuracy": baseline_current,
        "system_current_policy_accuracy": system_current,
        "system_minus_baseline_current_policy_accuracy": round(
            system_current - baseline_current, 4
        ),
        "system_pair_divergence_rate": _rate(
            sum(
                len(group) == 2
                and len({row["current"]["system"]["selected_policy"] for row in group}) == 2
                for group in pair_groups.values()
            ),
            len(pair_groups),
        ),
        "baseline_pair_policy_invariance_rate": _rate(
            sum(
                len(group) == 2
                and len({row["current"]["baseline"]["selected_policy"] for row in group}) == 1
                for group in pair_groups.values()
            ),
            len(pair_groups),
        ),
        "baseline_current_surface_proxy_match_rate": surface_rates["baseline"],
        "system_current_surface_proxy_match_rate": surface_rates["system"],
        "baseline_feedback_policy_accuracy": baseline_feedback,
        "system_feedback_policy_accuracy": system_feedback,
        "system_minus_baseline_feedback_policy_accuracy": round(
            system_feedback - baseline_feedback, 4
        ),
        "system_contradiction_revision_accuracy": _rate(
            sum(
                row["feedback"]["system"]["selected_policy"]
                == row["expected_feedback_policy"]
                and row["m34_revision_replacement"]
                == row["expected_feedback_policy"]
                and not row["m34_original_evidence_rewritten"]
                for row in contradiction_rows
            ),
            len(contradiction_rows),
        ),
        "visible_japanese_rate": visible_rates,
        "unverified_mental_fact_write_count": sum(
            row["unverified_mental_fact_write_count"] for row in rows
        ),
        "raw_dialogue_persisted_count": sum(
            row["raw_dialogue_persisted"] for row in rows
        ),
        "scored_prompt_tokens": prompt_counts,
        "completion_tokens": completion_counts,
        "latency_seconds": {
            key: round(value, 4) for key, value in latencies.items()
        },
        "system_to_baseline_scored_prompt_token_ratio": _ratio(
            prompt_counts["system"], prompt_counts["baseline"]
        ),
        "system_to_baseline_completion_token_ratio": _ratio(
            completion_counts["system"], completion_counts["baseline"]
        ),
        "system_to_baseline_latency_ratio": _ratio(
            latencies["system"], latencies["baseline"]
        ),
        "median_scored_call_seconds": round(
            statistics.median(
                float(row[stage][condition].get("latency_seconds") or 0.0)
                for row in rows
                for stage in ("current", "feedback")
                for condition in CONDITIONS
            ),
            4,
        ) if rows else 0.0,
    }
    gate_results = {
        key: (
            metrics[key.removesuffix("_max")] <= threshold
            if key.endswith("_max")
            else metrics[key.removesuffix("_min")] >= threshold
        )
        for key, threshold in gates.items()
        if key.removesuffix("_max").removesuffix("_min") in metrics
    }
    for condition in CONDITIONS:
        gate_results[f"visible_japanese_rate_{condition}_min"] = (
            visible_rates[condition]
            >= gates["visible_japanese_rate_each_condition_min"]
        )
    gate_results.pop("visible_japanese_rate_each_condition_min", None)
    return metrics, gate_results


def run_reserve():
    dataset = json.loads(RESERVE_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    validation = validate_reserve(dataset, protocol)
    if not validation["passed"]:
        raise ValueError(validation["errors"])
    rows = [
        _run_case(case, protocol, None, index)
        for index, case in enumerate(dataset["cases"], start=1)
    ]
    metrics, gate_results = summarize(rows, protocol["frozen_success_gates"])
    payload = {
        "schema": "uruha_same_model_longitudinal_pragmatic_evaluation_m35_v1",
        "mode": "reserve",
        "dataset_path": str(RESERVE_PATH.relative_to(ROOT)),
        "dataset_sha256": _sha256(RESERVE_PATH),
        "protocol_path": str(PROTOCOL_PATH.relative_to(ROOT)),
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": (
            _sha256(FREEZE_PATH) if FREEZE_PATH.exists() else None
        ),
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
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reserve",), required=True)
    parser.parse_args()
    payload = run_reserve()
    print(json.dumps({"decision": payload["decision"], **payload["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
