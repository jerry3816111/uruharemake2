#!/usr/bin/env python3
"""Matched baseline/system harness for V2.14 pragmatic-understanding research.

This module is deliberately evaluation-only.  It never opens UruhaBrain's
production memory database, never writes dialogue memories, and never treats
automatic proxies as evidence that a person felt understood.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
import urllib.error
import urllib.request
from copy import deepcopy
from pathlib import Path

import uruha_functional_understanding as ufu
import uruha_personhood_loop as upl
import rightbrain_language_quality as rblq


ROOT = Path(__file__).resolve().parent
DEVELOPMENT_CONFIG = ROOT / "configs/v2_13_human_pragmatic_comparison_preregistration.json"
DEFAULT_HOLDOUT = ROOT / "datasets/v2_14_human_pragmatic_holdout.json"
DEFAULT_LOCK = ROOT / "configs/v2_14_human_pragmatic_holdout_lock.json"
DEFAULT_RAW = ROOT / "analysis/v2_14_human_pragmatic_comparison_raw.json"
DEFAULT_BLIND_PACKET = ROOT / "analysis/v2_14_human_pragmatic_blind_packet.json"
DEFAULT_BLIND_KEY = ROOT / "analysis/v2_14_human_pragmatic_blind_key.json"
HUMAN_EVAL_SOURCE = ROOT / "human_pragmatic_human_eval_v2_14.py"

CONDITIONS = ("baseline", "system")
HUMAN_RATING_DIMENSIONS = (
    "implicit_need_caught_without_overclaiming",
    "overinterpretation_or_fabrication_reverse_scored",
    "quality_of_revision_after_user_denial",
    "cross_turn_consistency",
    "felt_understanding",
    "public_uruha_persona_naturalness_secondary",
)
FINAL_REPLY_RULE = "最終返答規則: 日本語だけ。一文か二文。です・ます、私、引用符、接客口調、内部分析は禁止。返事だけを書く。"
SHARED_SYSTEM_PROMPT = """あなたは研究用の対話AIで、公開情報だけに基づくうるは風の表現契約を使う。本人ではなく、私生活や未公開の経験を作らない。入力言語に関係なく、返事は自然で短い日本語だけにする。中国語や英語を混ぜず、です・ます調、接客口調、引用符、説明口調を使わない。一人称が必要なら「うち」を使い、「私」は使わない。返事は一文か二文にする。相手の字面だけでなく、文脈上あり得る目的や言外の必要も考えるが、証拠が弱い時は断定しない。十分な根拠があれば核心を一つだけ控えめに拾い、違う可能性を残す。訂正されたら言い訳せず更新する。入力 packet に reply_plan.core_message_jp がある場合は、その意味を変えず自然な会話として返す。内部ラベル、信頼度、JSON、分析手順は見せず、返事だけを出す。"""

PERSONA_CONTRACT = {
    "positioning": "public-evidence-grounded development persona instance; not the real person",
    "evidence_refs": [
        "datasets/public_persona_evidence_v1.json#persona_dev_v1_002",
        "datasets/public_persona_evidence_v1.json#persona_dev_v1_003",
    ],
    "authorization_scope": "development_hypothesis_only_not_persona_fidelity",
    "unknown_space": [
        "childhood_and_unpublished_experience",
        "private_relationships_and_memories",
        "unobserved_current_mental_state",
    ],
}


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
    return {
        "path": str(resolved.relative_to(ROOT)),
        "sha256": sha256_file(resolved),
    }


def load_local_tokenizer(model_id="Qwen/Qwen3-4B-Instruct-2507"):
    from transformers import AutoTokenizer

    cache_root = (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / ("models--" + model_id.replace("/", "--"))
        / "snapshots"
    )
    snapshots = [
        path
        for path in sorted(cache_root.glob("*"))
        if (path / "tokenizer.json").is_file() and (path / "config.json").is_file()
    ]
    if not snapshots:
        raise FileNotFoundError(
            f"local tokenizer snapshot unavailable for {model_id}; network fallback is forbidden"
        )
    return AutoTokenizer.from_pretrained(str(snapshots[-1]), local_files_only=True)


def token_count(tokenizer, text):
    return len(tokenizer.encode(str(text or ""), add_special_tokens=False))


def _pad_to_exact_tokens(text, target_tokens, tokenizer):
    text = str(text)
    current = token_count(tokenizer, text)
    if current > int(target_tokens):
        raise ValueError(f"prompt exceeds token budget: {current}>{target_tokens}")
    # Qwen tokenizers encode each appended ' 0' as one token after the first.
    # Verify on every step and fail closed if a tokenizer revision behaves
    # differently; do not silently truncate semantic content.
    while current < int(target_tokens):
        candidate = text + " 0"
        after = token_count(tokenizer, candidate)
        if after <= current:
            raise ValueError("token padding did not advance")
        if after > int(target_tokens):
            # Try single visible-neutral characters for the final token.
            matched = None
            for unit in ("・", "。", "_", " 1", "\n"):
                probe = text + unit
                if token_count(tokenizer, probe) == int(target_tokens):
                    matched = probe
                    break
            if matched is None:
                raise ValueError(
                    f"cannot reach exact token budget from {current} to {target_tokens}"
                )
            text = matched
            current = int(target_tokens)
            break
        text = candidate
        current = after
    return text


def _base_plan():
    return {
        "intent": "chat",
        "scene": "casual",
        "reply_goal": "自然に返す",
        "core_message_jp": "今の話に自然に返す。",
        "response_mode": "direct_answer",
        "surface_act": "plain_reply",
        "payload_level": "medium",
        "constraints": {"max_chars": 96},
    }


def build_research_state(user_turns):
    """Build V2.13 state only from user signals available at this turn."""
    model = upl.empty_longitudinal_model()
    previous_hypothesis = None
    previous_pragmatic = None
    last = None
    for turn_index, user_text in enumerate(user_turns, start=1):
        actual_signal = {
            "actual_intent": (
                "correction_followup"
                if "correction" in set(ufu.semantic_features(user_text))
                else "chat"
            )
        }
        verification = ufu.verify_previous_hypothesis(
            previous_hypothesis,
            user_text,
            current_actual_signal=actual_signal,
            turn_index=turn_index,
        )
        hypothesis = ufu.build_user_mental_state_hypothesis(
            user_text,
            actual_signal=actual_signal,
            turn_index=turn_index,
        )
        pragmatic = upl.build_human_pragmatic_understanding(
            user_text,
            hypothesis=hypothesis,
            input_mode="text",
            turn_index=turn_index,
        )
        pragmatic["linked_hypothesis_id"] = hypothesis["hypothesis_id"]
        hypothesis["pragmatic_understanding_v2_13"] = pragmatic
        pragmatic_verification = upl.verify_previous_pragmatic_understanding(
            previous_pragmatic,
            user_text,
            pragmatic,
            turn_index=turn_index,
        )
        model, update = upl.update_longitudinal_user_model(
            model,
            hypothesis,
            verification,
            pragmatic_verification,
            user_text,
            turn_index=turn_index,
        )
        plan = upl.apply_pragmatic_attunement_to_plan(
            _base_plan(),
            pragmatic,
            hypothesis=hypothesis,
            pragmatic_verification=pragmatic_verification,
            hypothesis_verification=verification,
        )
        plan, model, validation = upl.apply_longitudinal_model_to_plan(
            plan,
            model,
            hypothesis,
            turn_index,
        )
        plan, persona_appraisal = upl.apply_public_persona_appraisal_to_plan(
            plan,
            pragmatic,
            model,
            {"mood": 0, "trust": 55},
        )
        last = {
            "hypothesis": hypothesis,
            "verification": verification,
            "pragmatic": pragmatic,
            "pragmatic_verification": pragmatic_verification,
            "model": model,
            "model_update": update,
            "plan": plan,
            "validation": validation,
            "persona_appraisal": persona_appraisal,
        }
        previous_hypothesis = hypothesis
        previous_pragmatic = pragmatic
    return last or {
        "hypothesis": {},
        "verification": {"status": "not_available"},
        "pragmatic": {},
        "pragmatic_verification": {"status": "not_available"},
        "model": model,
        "model_update": {},
        "plan": _base_plan(),
        "validation": {},
        "persona_appraisal": {},
    }


def _compact_inference(payload):
    payload = payload or {}
    return {
        "value": payload.get("value"),
        "confidence": payload.get("confidence"),
        "alternatives": [row.get("value") for row in (payload.get("alternatives") or [])[:2]],
    }


def system_state_packet(state):
    pragmatic = state.get("pragmatic") or {}
    model = state.get("model") or {}
    plan = state.get("plan") or {}
    return {
        "schema": "uruha_v2_14_system_condition_packet",
        "condition": "auditable_cross_turn_pragmatic_loop",
        "literal": (pragmatic.get("literal_content") or {}).get("value"),
        "pragmatic_label": pragmatic.get("pragmatic_label"),
        "communicative_intent": _compact_inference(
            (pragmatic.get("inferences") or {}).get("communicative_intent")
        ),
        "emotion_or_stance": _compact_inference(
            (pragmatic.get("inferences") or {}).get("emotion_or_stance")
        ),
        "relationship_signal": _compact_inference(
            (pragmatic.get("inferences") or {}).get("relationship_signal")
        ),
        "implicit_need": _compact_inference(
            (pragmatic.get("inferences") or {}).get("implicit_need")
        ),
        "action_tendency": _compact_inference(
            (pragmatic.get("inferences") or {}).get("action_tendency")
        ),
        "unknown": [row.get("field") for row in (pragmatic.get("unknown") or [])],
        "previous_outcome": {
            "general": (state.get("verification") or {}).get("status"),
            "pragmatic": (state.get("pragmatic_verification") or {}).get("status"),
        },
        "persistent_other_model": upl.model_summary(model),
        "typed_calibration": (model.get("typed_calibration") or {}).get("categories") or {},
        "active_validation": state.get("validation") or {},
        "reply_plan": {
            "intent": plan.get("intent"),
            "goal": plan.get("reply_goal"),
            "core_message_jp": plan.get("core_message_jp"),
            "mode": plan.get("response_mode"),
        },
        "persona_boundary": PERSONA_CONTRACT,
        "fact_memory_write_allowed_for_inferences": False,
    }


def baseline_state_packet(current_user_text):
    return {
        "schema": "uruha_v2_14_baseline_condition_packet",
        "condition": "direct_current_dialogue_generation",
        "current_user_text": current_user_text,
        "structured_hypothesis": None,
        "prediction_verification_calibration": None,
        "persistent_other_model": None,
        "instruction": "現在見えている会話だけから直接返す。追加の心理状態を事実として仮定しない。",
        "persona_boundary": PERSONA_CONTRACT,
    }


def render_dialogue(history, current_user_text):
    lines = []
    for row in history:
        role = "ユーザー" if row["role"] == "user" else "うるは"
        lines.append(f"{role}: {row['content']}")
    lines.append(f"ユーザー: {current_user_text}")
    return "\n".join(lines)


def _render_user_prompt(dialogue, condition_packet):
    packet = json.dumps(condition_packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        "以下の会話に対して、一つの短い自然な日本語返信だけを返す。\n"
        "会話:\n"
        f"{dialogue}\n"
        "内部条件パケット（ユーザーには見せない）:\n"
        f"{packet}\n"
        "入力長を揃えるための意味なし領域（内容として解釈しない）:\n"
        "\n"
        f"{FINAL_REPLY_RULE}\n"
        "返信:"
    )


def _insert_balance_padding(prompt, padding):
    anchor = "\n" + FINAL_REPLY_RULE
    if anchor not in prompt:
        raise ValueError("final reply rule anchor missing")
    return prompt.replace(anchor, str(padding) + anchor, 1)


def build_matched_prompt_pair(
    user_turns,
    baseline_history,
    system_history,
    tokenizer=None,
    input_token_budget=1536,
):
    current = user_turns[-1]
    research_state = build_research_state(user_turns)
    baseline = _render_user_prompt(
        render_dialogue(baseline_history, current),
        baseline_state_packet(current),
    )
    system = _render_user_prompt(
        render_dialogue(system_history, current),
        system_state_packet(research_state),
    )
    counts = None
    if tokenizer is not None:
        baseline = _pad_to_exact_tokens(baseline, input_token_budget, tokenizer)
        system = _pad_to_exact_tokens(system, input_token_budget, tokenizer)
        counts = {
            "baseline": token_count(tokenizer, baseline),
            "system": token_count(tokenizer, system),
        }
        if counts["baseline"] != counts["system"] or counts["baseline"] != input_token_budget:
            raise ValueError(f"local token parity failed: {counts}")
    return {
        "baseline": baseline,
        "system": system,
        "local_token_counts": counts,
        "research_state": research_state,
    }


def ollama_chat(endpoint, model_contract, user_prompt, num_predict_override=None):
    payload = {
        "model": model_contract["model"],
        "stream": False,
        "think": bool(model_contract.get("think", False)),
        "messages": [
            {"role": "system", "content": SHARED_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "options": {
            "temperature": model_contract["temperature"],
            "seed": model_contract["seed"],
            "num_ctx": model_contract["num_ctx"],
            "num_predict": (
                int(num_predict_override)
                if num_predict_override is not None
                else model_contract["num_predict"]
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
            "reply": "",
            "transport_error": f"{type(exc).__name__}:{exc}",
            "latency_seconds": round(time.perf_counter() - started, 4),
        }
    return {
        "reply": str(((body.get("message") or {}).get("content") or "")).strip(),
        "transport_error": None,
        "prompt_eval_count": body.get("prompt_eval_count"),
        "eval_count": body.get("eval_count"),
        "total_duration_ns": body.get("total_duration"),
        "load_duration_ns": body.get("load_duration"),
        "latency_seconds": round(time.perf_counter() - started, 4),
    }


def balance_prompt_pair_with_ollama(
    prompts,
    endpoint,
    model_contract,
    max_rounds=4,
):
    """Balance with Ollama's real prompt tokenizer before scored generation.

    Both conditions receive exactly the same fixed number of one-token
    preflight calls.  Generated preflight text is discarded.  Only
    ``prompt_eval_count`` is retained, so no future-turn or gold information is
    used to tune the mechanism after the holdout is frozen.
    """
    balanced = {condition: str(prompts[condition]) for condition in CONDITIONS}
    rounds = []
    gate = int(model_contract["paired_prompt_eval_token_delta_gate"])
    budget = int(model_contract.get("input_token_budget", 1536))
    for round_index in range(1, int(max_rounds) + 1):
        measured = {
            condition: ollama_chat(
                endpoint,
                model_contract,
                balanced[condition],
                num_predict_override=1,
            )
            for condition in CONDITIONS
        }
        counts = {
            condition: measured[condition].get("prompt_eval_count")
            for condition in CONDITIONS
        }
        if any(value is None for value in counts.values()):
            raise RuntimeError(f"prompt token preflight failed: {measured}")
        if any(int(value) > budget for value in counts.values()):
            raise RuntimeError(f"prompt token budget exceeded: {counts}>{budget}")
        delta = int(counts["system"]) - int(counts["baseline"])
        rounds.append(
            {
                "round": round_index,
                "counts": counts,
                "delta_system_minus_baseline": delta,
                "within_gate": abs(delta) <= gate,
                "preflight_calls_each_condition": 1,
                "preflight_output_discarded": True,
            }
        )
        if abs(delta) > gate:
            shorter = "baseline" if delta > 0 else "system"
            # Development preflight established that a spaced zero contributes
            # two Qwen3.5/Ollama prompt tokens here, while a Japanese full stop
            # contributes one.  Every following real-token preflight verifies
            # the construction; the final scored gate still uses Ollama's own
            # prompt_eval_count rather than trusting this arithmetic.
            magnitude = abs(delta)
            padding = " 0" * (magnitude // 2)
            if magnitude % 2:
                padding += "。"
            balanced[shorter] = _insert_balance_padding(
                balanced[shorter],
                padding,
            )
    final = rounds[-1]
    return {
        "baseline": balanced["baseline"],
        "system": balanced["system"],
        "rounds": rounds,
        "final_prompt_eval_counts": final["counts"],
        "final_delta": final["delta_system_minus_baseline"],
        "gate_passed": final["within_gate"],
        "preflight_call_count": int(max_rounds) * len(CONDITIONS),
    }


def visible_reply_contract(reply):
    text = str(reply or "").strip()
    internal_markers = [
        "confidence",
        "pragmatic_label",
        "structured_hypothesis",
        "内部条件",
        "JSON",
    ]
    return {
        "nonempty": bool(text),
        "has_japanese": rblq.has_japanese(text),
        "no_foreign_or_nonstandard_language": not rblq.has_bad_language(
            text,
            reject_latin=True,
            include_audited_residue=True,
        ),
        "no_polite_register": not bool(rblq.POLITE_RE.search(text)),
        "no_watashi_first_person": "私" not in text,
        "no_quote_wrapper": not bool(re.search(r"[\"'“”‘’「」『』]", text)),
        "no_service_tone": not any(
            marker in text
            for marker in ["お手伝い", "サポート", "お気軽", "ご相談", "お聞かせ"]
        ),
        "no_analysis_dump": not any(marker.lower() in text.lower() for marker in internal_markers),
        "no_private_person_claim": not any(
            marker in text
            for marker in ["子供の頃", "幼い頃", "家族との思い出", "本当の記憶"]
        ),
        "no_mind_reading_claim": not any(
            marker in text for marker in ["全部分かる", "心が読める", "絶対そう"]
        ),
    }


def normalize_visible_reply(reply):
    """Apply the same non-semantic surface cleanup to both conditions."""
    text = str(reply or "").strip()
    wrappers = [("\"", "\""), ("'", "'"), ("“", "”"), ("‘", "’"), ("「", "」"), ("『", "』")]
    changed = True
    while changed and len(text) >= 2:
        changed = False
        for left, right in wrappers:
            if text.startswith(left) and text.endswith(right):
                text = text[len(left) : len(text) - len(right)].strip()
                changed = True
                break
    return re.sub(r"[ \t]+", " ", text).strip()


def proxy_score(reply, proxy, turn_index):
    text = str(reply or "")
    if int(turn_index) == 1:
        expected = list(proxy.get("turn_1_expected_japanese_anchors_any") or [])
    else:
        expected = list(proxy.get("later_turn_expected_japanese_anchors_any") or [])
        if not expected:
            expected = list(proxy.get("turn_2_revision_anchors_any") or [])
    forbidden = list(proxy.get("forbidden_overclaim_anchors") or [])
    contract = visible_reply_contract(text)
    return {
        "expected_anchor_available": bool(expected),
        "expected_anchor_hit": bool(not expected or any(anchor in text for anchor in expected)),
        "forbidden_overclaim_hit": any(anchor in text for anchor in forbidden),
        "visible_contract": contract,
        "proxy_pass": bool(
            all(contract.values())
            and (not expected or any(anchor in text for anchor in expected))
            and not any(anchor in text for anchor in forbidden)
        ),
    }


def validate_case_bundle(bundle, expected_count=None):
    cases = list(bundle.get("cases") or bundle.get("development_cases") or [])
    errors = []
    if expected_count is not None and len(cases) != int(expected_count):
        errors.append(f"case_count:{len(cases)}!={expected_count}")
    ids = [case.get("case_id") for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_case_id")
    for case in cases:
        if len(case.get("turns") or []) < 2:
            errors.append(f"too_few_turns:{case.get('case_id')}")
        if not case.get("language") or not case.get("phenomenon"):
            errors.append(f"missing_case_metadata:{case.get('case_id')}")
        if any(not str(turn).strip() for turn in case.get("turns") or []):
            errors.append(f"empty_turn:{case.get('case_id')}")
    return {"passed": not errors, "errors": errors, "case_count": len(cases), "cases": cases}


def validate_holdout_design(bundle, expected_count=18):
    base = validate_case_bundle(bundle, expected_count=expected_count)
    errors = list(base["errors"])
    cases = base["cases"]
    languages = {language: 0 for language in ("zh", "en", "ja")}
    seen_turns = set()
    forbidden_gold_keys = {"expected_reply", "gold_reply", "reference_reply"}
    for case in cases:
        case_id = str(case.get("case_id") or "")
        language = case.get("language")
        if language in languages:
            languages[language] += 1
        else:
            errors.append(f"unsupported_language:{case_id}:{language}")
        turns = list(case.get("turns") or [])
        if len(turns) != 3:
            errors.append(f"holdout_requires_three_turns:{case_id}:{len(turns)}")
        normalized_turns = [re.sub(r"\s+", " ", str(turn)).strip().lower() for turn in turns]
        for turn in normalized_turns:
            if turn in seen_turns:
                errors.append(f"duplicate_holdout_turn:{case_id}")
            seen_turns.add(turn)
        if forbidden_gold_keys.intersection(case):
            errors.append(f"exact_gold_reply_forbidden:{case_id}")
        expected_sequence = list(case.get("expected_trace_outcome_sequence") or [])
        if len(expected_sequence) != 3:
            errors.append(f"trace_sequence_length:{case_id}:{len(expected_sequence)}")
        focus = list(case.get("evaluation_focus_by_turn") or [])
        if len(focus) != 3:
            errors.append(f"evaluation_focus_length:{case_id}:{len(focus)}")
    if languages != {"zh": 6, "en": 6, "ja": 6}:
        errors.append(f"language_balance:{languages}")
    if not bool(bundle.get("source_disjoint_from_development_cases")):
        errors.append("source_disjoint_flag_missing")
    return {
        **base,
        "passed": not errors,
        "errors": errors,
        "language_counts": languages,
        "exact_gold_replies_present": any(
            forbidden_gold_keys.intersection(case) for case in cases
        ),
    }


def run_bundle(bundle, preregistration, tokenizer=None, endpoint="http://127.0.0.1:11434"):
    validation = validate_case_bundle(bundle)
    if not validation["passed"]:
        raise ValueError(validation["errors"])
    model_contract = deepcopy(preregistration["model_contract"])
    input_budget = int(model_contract.get("input_token_budget", 1536))
    order_seed = int(preregistration.get("blind_rating", {}).get("pair_order_seed", 20260811))
    rows = []
    for case_index, case in enumerate(validation["cases"]):
        histories = {condition: [] for condition in CONDITIONS}
        user_turns = []
        for turn_index, user_text in enumerate(case["turns"], start=1):
            user_turns.append(user_text)
            prompts = build_matched_prompt_pair(
                user_turns,
                histories["baseline"],
                histories["system"],
                tokenizer,
                input_budget,
            )
            balance = balance_prompt_pair_with_ollama(
                prompts,
                endpoint,
                model_contract,
                max_rounds=int(model_contract.get("token_balance_preflight_rounds", 4)),
            )
            order = list(CONDITIONS)
            random.Random(order_seed + case_index * 101 + turn_index).shuffle(order)
            generated = {}
            for condition in order:
                result = ollama_chat(endpoint, model_contract, balance[condition])
                raw_reply = result.get("reply") or ""
                result["raw_reply"] = raw_reply
                result["reply"] = normalize_visible_reply(raw_reply)
                research_state = prompts.get("research_state") or {}
                system_trace = None
                if condition == "system":
                    system_trace = {
                        "hypothesis_id": (research_state.get("hypothesis") or {}).get(
                            "hypothesis_id"
                        ),
                        "pragmatic_label": (research_state.get("pragmatic") or {}).get(
                            "pragmatic_label"
                        ),
                        "general_verification": (
                            research_state.get("verification") or {}
                        ).get("status"),
                        "pragmatic_verification": (
                            research_state.get("pragmatic_verification") or {}
                        ).get("status"),
                        "model_summary": upl.model_summary(
                            research_state.get("model") or {}
                        ),
                        "reply_plan": {
                            "intent": (research_state.get("plan") or {}).get("intent"),
                            "mode": (research_state.get("plan") or {}).get(
                                "response_mode"
                            ),
                            "core_message_jp": (research_state.get("plan") or {}).get(
                                "core_message_jp"
                            ),
                        },
                        "fact_memory_write_allowed_for_inferences": False,
                    }
                result.update(
                    {
                        "case_id": case["case_id"],
                        "phenomenon": case["phenomenon"],
                        "language": case["language"],
                        "turn_index": turn_index,
                        "evaluation_focus": list(
                            (case.get("evaluation_focus_by_turn") or [[], [], []])[
                                turn_index - 1
                            ]
                        ),
                        "condition": condition,
                        "execution_position": order.index(condition) + 1,
                        "dialogue_context": render_dialogue(
                            histories[condition], user_text
                        ),
                        "system_trace": system_trace,
                        "input_sha256": hashlib.sha256(user_text.encode("utf-8")).hexdigest(),
                        "prompt_sha256": hashlib.sha256(balance[condition].encode("utf-8")).hexdigest(),
                        "local_prompt_token_count": (
                            (prompts.get("local_token_counts") or {}).get(condition)
                        ),
                        "token_balance_preflight": deepcopy(balance["rounds"]),
                        "token_balance_preflight_call_count": balance["preflight_call_count"],
                        "preflight_token_gate_passed": balance["gate_passed"],
                        "proxy": proxy_score(result.get("reply"), case.get("proxy") or {}, turn_index),
                        "production_memory_write_count": 0,
                    }
                )
                rows.append(result)
                generated[condition] = result
            for condition in CONDITIONS:
                histories[condition].append({"role": "user", "content": user_text})
                histories[condition].append(
                    {"role": "assistant", "content": generated[condition].get("reply") or ""}
                )
    return rows


def summarize_rows(rows, preregistration):
    pair_map = {}
    for row in rows:
        pair_map.setdefault((row["case_id"], row["turn_index"]), {})[row["condition"]] = row
    pairs = []
    gate = int(preregistration["model_contract"]["paired_prompt_eval_token_delta_gate"])
    for (case_id, turn_index), pair in sorted(pair_map.items()):
        baseline = pair.get("baseline") or {}
        system = pair.get("system") or {}
        left = baseline.get("prompt_eval_count")
        right = system.get("prompt_eval_count")
        delta = abs(int(left) - int(right)) if left is not None and right is not None else None
        pairs.append(
            {
                "case_id": case_id,
                "turn_index": turn_index,
                "both_present": set(pair) == set(CONDITIONS),
                "prompt_eval_token_delta": delta,
                "prompt_eval_gate_passed": delta is not None and delta <= gate,
                "baseline_proxy_pass": bool((baseline.get("proxy") or {}).get("proxy_pass")),
                "system_proxy_pass": bool((system.get("proxy") or {}).get("proxy_pass")),
            }
        )
    return {
        "generation_count": len(rows),
        "pair_count": len(pairs),
        "transport_error_count": sum(bool(row.get("transport_error")) for row in rows),
        "all_visible_contract_pass_count": sum(
            all((row.get("proxy") or {}).get("visible_contract", {}).values()) for row in rows
        ),
        "baseline_visible_contract_pass_count": sum(
            row.get("condition") == "baseline"
            and all((row.get("proxy") or {}).get("visible_contract", {}).values())
            for row in rows
        ),
        "system_visible_contract_pass_count": sum(
            row.get("condition") == "system"
            and all((row.get("proxy") or {}).get("visible_contract", {}).values())
            for row in rows
        ),
        "baseline_proxy_pass_count": sum(
            row["baseline_proxy_pass"] for row in pairs
        ),
        "system_proxy_pass_count": sum(row["system_proxy_pass"] for row in pairs),
        "token_parity_pair_count": sum(row["prompt_eval_gate_passed"] for row in pairs),
        "all_pairs_token_parity": bool(pairs and all(row["prompt_eval_gate_passed"] for row in pairs)),
        "pairs": pairs,
        "evidence_boundary": "Automatic proxies validate transport, language, obvious overclaim and harness behavior only; they are not human felt-understanding evidence.",
    }


def build_blind_packet(rows, seed=20260811):
    grouped = {}
    for row in rows:
        grouped.setdefault((row["case_id"], row["turn_index"]), {})[row["condition"]] = row
    rng = random.Random(seed)
    items = []
    key = []
    for index, ((case_id, turn_index), pair) in enumerate(sorted(grouped.items()), start=1):
        if set(pair) != set(CONDITIONS):
            continue
        conditions = list(CONDITIONS)
        rng.shuffle(conditions)
        mapping = {"A": conditions[0], "B": conditions[1]}
        focus = set(pair[mapping["A"]].get("evaluation_focus") or [])
        rating_dimensions = [
            "implicit_need_caught_without_overclaiming",
            "overinterpretation_or_fabrication_reverse_scored",
            "felt_understanding",
            "public_uruha_persona_naturalness_secondary",
        ]
        if int(turn_index) > 1:
            rating_dimensions.append("cross_turn_consistency")
        if focus.intersection({"revision_after_denial", "revision_after_misread"}):
            rating_dimensions.append("quality_of_revision_after_user_denial")
        rating_dimensions = [
            dimension for dimension in HUMAN_RATING_DIMENSIONS if dimension in rating_dimensions
        ]
        item_id = f"blind-{index:03d}"
        items.append(
            {
                "item_id": item_id,
                "case_id": case_id,
                "turn_index": turn_index,
                "context_A": pair[mapping["A"]].get("dialogue_context") or "",
                "context_B": pair[mapping["B"]].get("dialogue_context") or "",
                "reply_A": pair[mapping["A"]]["reply"],
                "reply_B": pair[mapping["B"]]["reply"],
                "rating_dimensions": rating_dimensions,
                "rating_scale": "1-5 each; preference A/B/tie/both_bad",
            }
        )
        key.append({"item_id": item_id, "A": mapping["A"], "B": mapping["B"]})
    return (
        {
            "schema": "uruha_v2_14_blind_human_rating_packet",
            "condition_labels_hidden": True,
            "minimum_independent_raters_for_claim": 3,
            "items": items,
            "evidence_boundary": "A packet is an evaluation instrument, not a human preference result.",
        },
        {"schema": "uruha_v2_14_blind_key", "items": key},
    )


def validate_lock(lock_path, holdout_path, preregistration_path):
    lock = load_json(lock_path)
    checks = {
        "holdout_sha256": sha256_file(holdout_path) == lock["artifacts"]["holdout"]["sha256"],
        "preregistration_sha256": (
            sha256_file(preregistration_path)
            == lock["artifacts"]["preregistration"]["sha256"]
        ),
        "mechanism_source_sha256": (
            sha256_file(ROOT / "uruha_personhood_loop.py")
            == lock["artifacts"]["mechanism_source"]["sha256"]
        ),
        "functional_source_sha256": (
            sha256_file(ROOT / "uruha_functional_understanding.py")
            == lock["artifacts"]["functional_source"]["sha256"]
        ),
        "harness_sha256": (
            sha256_file(Path(__file__)) == lock["artifacts"]["harness"]["sha256"]
        ),
        "human_eval_source_sha256": (
            sha256_file(HUMAN_EVAL_SOURCE)
            == lock["artifacts"]["human_eval_source"]["sha256"]
        ),
    }
    return {"passed": all(checks.values()), "checks": checks, "lock": lock}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate-development", "validate-holdout", "run-holdout"), required=True)
    parser.add_argument("--development-config", default=str(DEVELOPMENT_CONFIG))
    parser.add_argument("--holdout", default=str(DEFAULT_HOLDOUT))
    parser.add_argument("--lock", default=str(DEFAULT_LOCK))
    parser.add_argument("--output", default=str(DEFAULT_RAW))
    parser.add_argument("--blind-packet", default=str(DEFAULT_BLIND_PACKET))
    parser.add_argument("--blind-key", default=str(DEFAULT_BLIND_KEY))
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    preregistration = load_json(args.development_config)
    if args.mode == "validate-development":
        result = validate_case_bundle(preregistration)
        result["tokenizer"] = "ollama_prompt_eval_count_at_execution"
        result["preregistration_sha256"] = sha256_file(args.development_config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    holdout = load_json(args.holdout)
    lock_validation = validate_lock(args.lock, args.holdout, args.development_config)
    bundle_validation = validate_holdout_design(holdout, expected_count=18)
    if args.mode == "validate-holdout":
        print(
            json.dumps(
                {"lock": lock_validation, "bundle": bundle_validation},
                ensure_ascii=False,
                indent=2,
            )
        )
        if not lock_validation["passed"] or not bundle_validation["passed"]:
            raise SystemExit(1)
        return

    if not lock_validation["passed"] or not bundle_validation["passed"]:
        raise SystemExit("holdout or harness lock failed")
    rows = run_bundle(holdout, preregistration, None, endpoint=args.endpoint)
    summary = summarize_rows(rows, preregistration)
    report = {
        "schema": "uruha_v2_14_human_pragmatic_comparison_raw",
        "status": "fresh_generation_complete_human_ratings_pending",
        "inputs": {
            "holdout": relative_binding(args.holdout),
            "preregistration": relative_binding(args.development_config),
            "lock": relative_binding(args.lock),
            "model": preregistration["model_contract"],
            "shared_system_prompt_sha256": hashlib.sha256(
                SHARED_SYSTEM_PROMPT.encode("utf-8")
            ).hexdigest(),
        },
        "summary": summary,
        "rows": rows,
        "claims": {
            "human_preference_supported": False,
            "system_better_than_baseline": False,
            "reason": "blind human ratings from at least three independent raters are not yet present",
        },
    }
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    packet, key = build_blind_packet(rows, seed=preregistration["blind_rating"]["pair_order_seed"])
    Path(args.blind_packet).write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    Path(args.blind_key).write_text(
        json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": args.output, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
