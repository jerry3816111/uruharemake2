#!/usr/bin/env python3
"""Run the preregistered V2.18 50-turn memory comparison.

The primary comparison is an architecture-level rollout, not a token-parity
claim.  ``uruha_memory`` uses the actual UruhaBrain checkpoint runtime over an
isolated database. ``plain_recent`` and ``plain_full`` use the same local
qwen2.5:7b backbone and the same visible persona contract, but differ in the
amount of transcript supplied.  The full-context arm is diagnostic: if it
matches UruhaBrain, the supported value is persistence/compression/traceability
relative to a bounded window, not superior LLM reasoning.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import io
import json
import os
import random
import re
import tempfile
import time
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE_PATH = ROOT / "datasets/v2_18_fifty_turn_memory_comparison.json"
PREREG_PATH = ROOT / "configs/v2_18_fifty_turn_memory_comparison_preregistration.json"
LOCK_PATH = ROOT / "configs/v2_18_fifty_turn_memory_comparison_lock.json"
RAW_PATH = ROOT / "analysis/v2_18_fifty_turn_memory_comparison_raw.json"
BLIND_PACKET_PATH = ROOT / "analysis/v2_18_fifty_turn_memory_blind_packet.json"
BLIND_KEY_PATH = ROOT / "analysis/v2_18_fifty_turn_memory_blind_key.json"
PRODUCTION_DB_PATH = ROOT / "uruha_memory_mac_db"
RUNTIME_PATH = ROOT / "uruha_brain_mac.py"
VISIBLE_CONTRACT_PATH = ROOT / "human_pragmatic_comparison_v2_14.py"

CONDITIONS = ("uruha_memory", "plain_recent", "plain_full")
PRIMARY_RECALL_ROLES = {"delayed_recall", "corrected_recall"}
CHECKPOINT_ROLES = {
    "delayed_recall",
    "explicit_correction",
    "corrected_recall",
    "withdrawal_probe",
    "false_memory_control",
}

PLAIN_SYSTEM_PROMPT = """あなたは研究用の対話AIで、公開情報だけに基づくうるは風の表現契約を使う。本人ではなく、私生活や未公開の経験を作らない。入力言語に関係なく、返事は自然で短い日本語だけにする。中国語や英語を混ぜず、です・ます調、接客口調、引用符、説明口調を使わない。一人称が必要なら「うち」を使い、「私」は使わない。見えている会話だけを根拠に答える。記憶の根拠が見えない時は、知っているふりや具体値の推測をせず短く曖昧さを認める。訂正が見えている時は新しい情報を優先する。内部分析やJSONは出さず、一文か二文の返事だけを書く。"""

UNCERTAINTY_MARKERS = (
    "覚えてない",
    "覚えてねえ",
    "分から",
    "わから",
    "知らない",
    "知らん",
    "曖昧",
    "はっきり",
    "言ったっけ",
    "確認でき",
    "見えてない",
    "手掛かり",
)
NEGATION_MARKERS = (
    "じゃない",
    "ではない",
    "違う",
    "違って",
    "言ってない",
    "言った覚えはない",
    "飲めない",
    "やめた",
    "外して",
    "本命じゃ",
    "今の好みじゃ",
    "もう好きじゃ",
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(path):
    digest = hashlib.sha256()
    for child in sorted(Path(path).rglob("*")):
        if child.is_file():
            digest.update(str(child.relative_to(path)).encode("utf-8"))
            digest.update(child.read_bytes())
    return digest.hexdigest()


def relative_binding(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def build_lock():
    return {
        "schema": "uruha_v2_18_fifty_turn_memory_comparison_lock",
        "status": "frozen_before_first_comparison_generation",
        "policy": {
            "retain_first_generation_failures": True,
            "post_generation_case_or_scoring_tuning_forbidden": True,
            "automatic_metrics_are_not_human_preference": True,
            "full_system_comparison_is_not_token_parity": True,
        },
        "artifacts": {
            "case": relative_binding(CASE_PATH),
            "preregistration": relative_binding(PREREG_PATH),
            "runner": relative_binding(Path(__file__)),
            "runtime": relative_binding(RUNTIME_PATH),
            "visible_contract": relative_binding(VISIBLE_CONTRACT_PATH),
        },
    }


def validate_lock(lock_path=LOCK_PATH):
    lock = load_json(lock_path)
    checks = {}
    for name, binding in (lock.get("artifacts") or {}).items():
        path = ROOT / binding["path"]
        checks[name] = bool(path.is_file() and sha256_file(path) == binding.get("sha256"))
    return {"passed": bool(checks) and all(checks.values()), "checks": checks, "lock": lock}


def validate_design(case, prereg):
    errors = []
    turns = list(case.get("turns") or [])
    turn_ids = [row.get("turn") for row in turns]
    if turn_ids != list(range(1, 51)):
        errors.append("turns must be exactly 1..50")
    if int(case.get("recent_window_turns") or 0) != int(prereg["invariants"]["recent_window_turns"]):
        errors.append("recent-window mismatch")
    checkpoints = [row for row in turns if row.get("role") in CHECKPOINT_ROLES]
    if [row.get("turn") for row in checkpoints] != [25, 26, 48, 49, 50]:
        errors.append("checkpoint layout mismatch")
    for row in checkpoints:
        if row.get("execution") != "full_runtime_comparison":
            errors.append(f"turn {row.get('turn')} checkpoint execution mismatch")
        if row.get("reply"):
            errors.append(f"turn {row.get('turn')} checkpoint reply must not be frozen")
    for row in turns:
        if row.get("role") not in CHECKPOINT_ROLES and row.get("execution") != "replayed_writeback":
            errors.append(f"turn {row.get('turn')} replay execution mismatch")
        if row.get("execution") == "replayed_writeback" and not row.get("reply"):
            errors.append(f"turn {row.get('turn')} replay reply missing")
    source_turns = case.get("source_turns") or {}
    recent_window = int(case["recent_window_turns"])
    for probe_turn, source_key in ((25, "initial"), (48, "correction")):
        source_turn = int(source_turns[source_key])
        if source_turn >= probe_turn - recent_window:
            errors.append(f"turn {probe_turn} source is still inside recent window")
    relational = [row for row in turns if row.get("role") == "relational_distractor"]
    if len(relational) < 4:
        errors.append("insufficient relational distractors")
    if bool((prereg.get("claim_boundary") or {}).get("independent_semantic_holdout")):
        errors.append("this scaling case must not claim independent semantic holdout")
    if bool((prereg.get("human_evaluation") or {}).get("automatic_proxy_is_human_preference_evidence")):
        errors.append("automatic proxy cannot be human preference evidence")
    return {
        "passed": not errors,
        "errors": errors,
        "turn_count": len(turns),
        "checkpoint_turns": [row.get("turn") for row in checkpoints],
        "relational_distractor_count": len(relational),
    }


def _compact_trace_rows(rows):
    compact = []
    for row in rows or []:
        compact.append(
            {
                "trace_id": row.get("trace_id"),
                "memory_id": row.get("memory_id"),
                "source": row.get("source"),
                "channel": row.get("channel"),
                "text": str(row.get("text") or ""),
                "score": row.get("score"),
                "rank": row.get("rank"),
                "selected": row.get("selected"),
            }
        )
    return compact


def _target_rows(memory_data, probes):
    probes = [str(probe).lower() for probe in probes if str(probe).strip()]
    provenance = (memory_data.get("memory_provenance") or {})
    rows = []
    for row in provenance.get("passed_to_leftbrain") or []:
        text = str(row.get("text") or "").lower()
        if any(probe in text for probe in probes):
            rows.append(row)
    return _compact_trace_rows(rows)


def _ledger_cost(snapshot):
    calls = list((snapshot or {}).get("calls") or [])
    return {
        "model_call_count": len(calls),
        "prompt_tokens": sum(int((row.get("response") or {}).get("prompt_tokens") or 0) for row in calls),
        "completion_tokens": sum(int((row.get("response") or {}).get("completion_tokens") or 0) for row in calls),
        "model_latency_seconds": round(sum(float(row.get("latency_seconds") or 0.0) for row in calls), 4),
        "stages": [row.get("stage") for row in calls],
        "contains_raw_prompt_or_reply": bool((snapshot or {}).get("contains_raw_prompt_or_reply")),
    }


def _visible_contract(reply):
    from human_pragmatic_comparison_v2_14 import visible_reply_contract

    contract = visible_reply_contract(reply)
    return {**contract, "pass": all(contract.values())}


def _run_system_checkpoint(bot, ledger, turn, target_probes):
    ledger.reset()
    capture = io.StringIO()
    started = time.monotonic()
    with ledger.item_scope(f"turn_{turn['turn']}", "uruha_memory"):
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            result = bot.run_turn_debug(turn["user"])
    elapsed = round(time.monotonic() - started, 4)
    memory_data = result.get("memory_data") or {}
    provenance = memory_data.get("memory_provenance") or {}
    anchor = result.get("logic", {}).get("memory_anchor") or {}
    rows = _target_rows(memory_data, target_probes)
    if anchor.get("source") == "current_input":
        rows.insert(
            0,
            {
                "trace_id": anchor.get("trace_id"),
                "memory_id": None,
                "source": "current_input",
                "channel": "current_input",
                "text": turn["user"],
                "score": anchor.get("score"),
                "rank": None,
                "selected": True,
            },
        )
    snapshot = ledger.snapshot()
    return {
        "condition": "uruha_memory",
        "reply": str(result.get("reply") or "").strip(),
        "elapsed_seconds": elapsed,
        "visible_contract": _visible_contract(result.get("reply")),
        "memory_anchor": anchor,
        "passed_target_rows": rows,
        "passed_trace_ids": provenance.get("passed_to_leftbrain_trace_ids") or [],
        "selected_trace_ids": provenance.get("selected_working_memory_trace_ids") or [],
        "profile_before": memory_data.get("profile_structured") or {},
        "profile_after": (result.get("memory_runtime") or {}).get("profile") or {},
        "runtime_cycle_index": (result.get("runtime_trace") or {}).get("cycle_index"),
        "runtime_log_sha256": hashlib.sha256(capture.getvalue().encode("utf-8")).hexdigest(),
        "compute": _ledger_cost(snapshot),
    }


def _replay_turn(bot, turn):
    logic = {
        "intent": "chat",
        "scene": "casual",
        "jp_summary": "隔離五十輪比較的凍結對話回放",
        "cognitive_mode": "direct",
        "premise_check": "accept",
        "routing_path": "replayed_writeback",
    }
    bot.memory.save_episode(turn["user"], turn["reply"], bot.psyche.get_state(), logic)
    return {
        "turn": turn["turn"],
        "role": turn["role"],
        "execution": turn["execution"],
        "user": turn["user"],
        "reply": turn["reply"],
        "profile_after": bot.memory.get_runtime_snapshot().get("profile") or {},
    }


def _history_messages(history, current_user, window=None):
    rows = list(history)
    if window is not None:
        rows = rows[-int(window):]
    messages = [{"role": "system", "content": PLAIN_SYSTEM_PROMPT}]
    for row in rows:
        messages.append({"role": "user", "content": row["user"]})
        messages.append({"role": "assistant", "content": row["reply"]})
    messages.append({"role": "user", "content": current_user})
    return messages, [row["turn"] for row in rows]


def _direct_completion(client, prereg, history, turn, condition, recent_window):
    window = recent_window if condition == "plain_recent" else None
    messages, history_turns = _history_messages(history, turn["user"], window=window)
    started = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=prereg["model"]["model"],
            messages=messages,
            temperature=float(prereg["model"]["temperature"]),
            max_tokens=int(prereg["model"]["max_tokens"]),
        )
        reply = str(response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        error = None
    except Exception as exc:
        reply = ""
        usage = None
        error = f"{type(exc).__name__}:{exc}"
    elapsed = round(time.monotonic() - started, 4)
    try:
        from human_pragmatic_comparison_v2_14 import normalize_visible_reply

        reply = normalize_visible_reply(reply)
    except Exception:
        pass
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    return {
        "condition": condition,
        "reply": reply,
        "elapsed_seconds": elapsed,
        "history_turns_supplied": history_turns,
        "history_turn_count": len(history_turns),
        "source_trace_available": False,
        "visible_contract": _visible_contract(reply),
        "transport_error": error,
        "compute": {
            "model_call_count": 1 if error is None else 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "model_latency_seconds": elapsed,
            "stages": ["direct_visible_reply"],
            "contains_raw_prompt_or_reply": False,
        },
    }


def _contains_any(text, values):
    return any(str(value) in str(text or "") for value in values)


def _term_positive(text, terms):
    text = str(text or "")
    for term in terms:
        start = text.find(term)
        while start >= 0:
            window = text[max(0, start - 14): start + len(term) + 18]
            if not _contains_any(window, NEGATION_MARKERS):
                return True
            start = text.find(term, start + len(term))
    return False


def _term_negated(text, terms):
    text = str(text or "")
    for term in terms:
        start = text.find(term)
        while start >= 0:
            window = text[max(0, start - 14): start + len(term) + 18]
            if _contains_any(window, NEGATION_MARKERS):
                return True
            start = text.find(term, start + len(term))
    return False


def _source_turn_for_role(case, role):
    if role == "delayed_recall":
        return int(case["source_turns"]["initial"])
    if role in {"corrected_recall", "withdrawal_probe"}:
        return int(case["source_turns"]["correction"])
    if role == "explicit_correction":
        return None
    return None


def _score_condition(row, turn, case):
    role = turn["role"]
    reply = str(row.get("reply") or "")
    values = case["values"]
    initial_terms = values["initial"]["japanese"]
    current_terms = values["current"]["japanese"]
    false_terms = values["false_control"]["japanese"]
    expected_terms = initial_terms if role == "delayed_recall" else current_terms
    current_hit = _contains_any(reply, expected_terms)
    stale_positive = role in {"corrected_recall", "withdrawal_probe"} and _term_positive(reply, initial_terms)
    old_negated = _term_negated(reply, initial_terms)
    false_positive = role == "false_memory_control" and _term_positive(reply, false_terms)
    false_negated = role == "false_memory_control" and _term_negated(reply, false_terms)
    uncertainty = _contains_any(reply, UNCERTAINTY_MARKERS)

    source_turn = _source_turn_for_role(case, role)
    if row["condition"] == "uruha_memory":
        if role in PRIMARY_RECALL_ROLES:
            source_available = bool(row.get("passed_target_rows"))
        elif role == "explicit_correction":
            source_available = True
        elif role == "withdrawal_probe":
            source_available = bool(row.get("passed_target_rows"))
        else:
            source_available = True
    elif role == "false_memory_control":
        source_available = row["condition"] == "plain_full"
    elif role == "explicit_correction":
        source_available = True
    else:
        source_available = bool(source_turn in set(row.get("history_turns_supplied") or []))

    if role in PRIMARY_RECALL_ROLES:
        task_pass = current_hit and not stale_positive
    elif role == "explicit_correction":
        task_pass = current_hit
    elif role == "withdrawal_probe":
        task_pass = (old_negated or current_hit) and not stale_positive
    else:
        task_pass = (false_negated or uncertainty or not _contains_any(reply, false_terms)) and not false_positive

    if source_available:
        epistemic_safe = bool(task_pass and not stale_positive and not false_positive)
    else:
        epistemic_safe = bool(uncertainty and not stale_positive and not false_positive)

    source_grounded_hit = bool(
        role in PRIMARY_RECALL_ROLES
        and current_hit
        and source_available
        and not stale_positive
    )
    return {
        "expected_current_value_hit": current_hit,
        "source_evidence_available": source_available,
        "source_grounded_current_value_hit": source_grounded_hit,
        "stale_value_revival": bool(stale_positive),
        "old_value_explicitly_negated": bool(old_negated),
        "false_memory_assertion": bool(false_positive),
        "false_value_explicitly_negated": bool(false_negated),
        "uncertainty_or_abstention": bool(uncertainty),
        "epistemic_safe": epistemic_safe,
        "task_pass": bool(task_pass),
        "visible_japanese_contract_pass": bool((row.get("visible_contract") or {}).get("pass")),
        "source_turn": source_turn,
    }


def _condition_summary(comparisons, condition):
    rows = [item["conditions"][condition] for item in comparisons]
    primary = [row for row in rows if row["role"] in PRIMARY_RECALL_ROLES]
    return {
        "checkpoint_count": len(rows),
        "primary_current_value_hit_count": sum(bool(row["score"]["expected_current_value_hit"]) for row in primary),
        "primary_source_grounded_recall_count": sum(bool(row["score"]["source_grounded_current_value_hit"]) for row in primary),
        "primary_recall_denominator": len(primary),
        "task_pass_count": sum(bool(row["score"]["task_pass"]) for row in rows),
        "epistemic_safe_count": sum(bool(row["score"]["epistemic_safe"]) for row in rows),
        "stale_value_revival_count": sum(bool(row["score"]["stale_value_revival"]) for row in rows),
        "false_memory_assertion_count": sum(bool(row["score"]["false_memory_assertion"]) for row in rows),
        "visible_japanese_count": sum(bool(row["score"]["visible_japanese_contract_pass"]) for row in rows),
        "source_trace_checkpoint_count": sum(bool(row.get("source_trace_available")) for row in rows),
        "model_call_count": sum(int((row.get("compute") or {}).get("model_call_count") or 0) for row in rows),
        "prompt_tokens": sum(int((row.get("compute") or {}).get("prompt_tokens") or 0) for row in rows),
        "completion_tokens": sum(int((row.get("compute") or {}).get("completion_tokens") or 0) for row in rows),
        "latency_seconds": round(sum(float(row.get("elapsed_seconds") or 0.0) for row in rows), 4),
        "transport_error_count": sum(bool(row.get("transport_error")) for row in rows),
    }


def summarize(comparisons, prereg, production_unchanged, final_profile, session_turn_count):
    conditions = {name: _condition_summary(comparisons, name) for name in CONDITIONS}
    criteria = prereg["success_criteria"]
    uruha = conditions["uruha_memory"]
    bounded = conditions["plain_recent"]
    full = conditions["plain_full"]
    uruha_gate = bool(
        uruha["primary_source_grounded_recall_count"] >= int(criteria["uruha_primary_source_grounded_recall_min"])
        and uruha["primary_recall_denominator"] == int(criteria["uruha_primary_recall_denominator"])
        and uruha["stale_value_revival_count"] <= int(criteria["uruha_stale_value_revival_max"])
        and uruha["false_memory_assertion_count"] <= int(criteria["uruha_false_memory_assertion_max"])
        and uruha["visible_japanese_count"] >= int(criteria["uruha_visible_japanese_checkpoint_min"])
        and production_unchanged
    )
    bounded_context_advantage = bool(
        uruha["primary_source_grounded_recall_count"]
        > bounded["primary_source_grounded_recall_count"]
    )
    full_context_answer_superiority = bool(
        uruha["primary_current_value_hit_count"]
        > full["primary_current_value_hit_count"]
    )
    full_matches_system = bool(
        uruha["primary_current_value_hit_count"]
        == full["primary_current_value_hit_count"]
        and uruha["stale_value_revival_count"] == full["stale_value_revival_count"]
        and uruha["false_memory_assertion_count"] == full["false_memory_assertion_count"]
    )
    if bounded_context_advantage and full_matches_system:
        interpretation = (
            "This case supports a persistence/traceability advantage over an eight-turn context window. "
            "Because the full-transcript LLM matched the system on answer accuracy, it does not support "
            "superior reasoning or universally better answers than a plain LLM."
        )
    elif bounded_context_advantage and full_context_answer_superiority:
        interpretation = (
            "UruhaBrain outperformed both direct conditions on this one scaling case, but the comparison is "
            "not token-parity and is not an independent semantic holdout; broader superiority is unsupported."
        )
    elif not bounded_context_advantage:
        interpretation = (
            "The external-memory system did not establish a primary recall advantage over the bounded direct LLM in this case."
        )
    else:
        interpretation = (
            "The conditions produced a mixed result; inspect checkpoint answers and costs rather than claiming a winner."
        )
    return {
        "turn_count": 50,
        "checkpoint_count": len(comparisons),
        "recent_window_turns": int(prereg["invariants"]["recent_window_turns"]),
        "conditions": conditions,
        "uruha_preregistered_gate_pass": uruha_gate,
        "bounded_recent_context_advantage_supported": bounded_context_advantage,
        "answer_quality_superiority_over_full_context_llm_supported": full_context_answer_superiority,
        "full_context_llm_matches_system": full_matches_system,
        "production_db_unchanged": production_unchanged,
        "isolated_session_turn_count": session_turn_count,
        "final_profile": final_profile,
        "interpretation": interpretation,
        "human_preference_supported": False,
        "general_llm_superiority_supported": False,
        "independent_semantic_holdout": False,
    }


def build_blind_packet(comparisons, seed=20260814):
    rng = random.Random(seed)
    packet_rows = []
    key_rows = []
    for item in comparisons:
        order = ["uruha_memory", "plain_recent"]
        rng.shuffle(order)
        packet_rows.append(
            {
                "turn": item["turn"],
                "role": item["role"],
                "recent_context": deepcopy(item["recent_context"]),
                "current_user": item["user"],
                "reply_A": item["conditions"][order[0]]["reply"],
                "reply_B": item["conditions"][order[1]]["reply"],
                "ratings": {
                    "which_answer_is_more_useful_in_this_conversation": "A/B/tie/both_bad",
                    "which_answer_feels_more_naturally_understanding": "A/B/tie/both_bad",
                    "which_answer_is_more_trustworthy_about_memory": "A/B/tie/both_bad",
                    "uruha_public_behavior_fit_A_1_to_5": None,
                    "uruha_public_behavior_fit_B_1_to_5": None,
                    "notes": "",
                },
            }
        )
        key_rows.append({"turn": item["turn"], "A": order[0], "B": order[1]})
    return (
        {
            "schema": "uruha_v2_18_fifty_turn_memory_blind_packet",
            "status": "rating_instrument_not_human_result",
            "condition_labels_hidden": True,
            "cases": packet_rows,
            "evidence_boundary": "Blank ratings are an instrument, not human preference evidence.",
        },
        {"schema": "uruha_v2_18_fifty_turn_memory_blind_key", "cases": key_rows},
    )


def run_fresh(case, prereg):
    from openai import OpenAI
    import uruha_compute_ledger as ledger_module

    production_before = tree_sha256(PRODUCTION_DB_PATH)
    recent_window = int(case["recent_window_turns"])
    plain_client = OpenAI(base_url=prereg["model"]["base_url"], api_key="ollama")
    plain_histories = {"plain_recent": [], "plain_full": []}
    rows = []
    comparisons = []
    rng = random.Random(20260814)

    with tempfile.TemporaryDirectory(prefix="uruha-v218-fifty-turn-") as isolated_db:
        os.environ["URUHA_MEMORY_DB_PATH"] = isolated_db
        os.environ["URUHA_SKIP_AUTO_VENV"] = "1"
        brain_mod = importlib.import_module("uruha_brain_mac")
        ledger = ledger_module.ComputeLedger()
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            bot = brain_mod.UruhaBrainV4_Mac(load_right_brain_model=False, compute_ledger=ledger)

        for turn in case["turns"]:
            if turn["execution"] == "replayed_writeback":
                row = _replay_turn(bot, turn)
                rows.append(row)
                for history in plain_histories.values():
                    history.append({"turn": turn["turn"], "user": turn["user"], "reply": turn["reply"]})
                continue

            if turn["role"] == "delayed_recall":
                target_probes = [case["values"]["initial"]["raw"]]
            elif turn["role"] == "false_memory_control":
                target_probes = [case["values"]["false_control"]["raw"]]
            elif turn["role"] == "withdrawal_probe":
                target_probes = [case["values"]["initial"]["raw"]]
            else:
                target_probes = [case["values"]["current"]["raw"]]

            print(f"[{turn['turn']}/50] comparison checkpoint: {turn['role']}", flush=True)
            direct_order = ["plain_recent", "plain_full"]
            rng.shuffle(direct_order)
            condition_rows = {}
            for condition in direct_order:
                condition_rows[condition] = _direct_completion(
                    plain_client,
                    prereg,
                    plain_histories[condition],
                    turn,
                    condition,
                    recent_window,
                )
            condition_rows["uruha_memory"] = _run_system_checkpoint(bot, ledger, turn, target_probes)

            for condition, condition_row in condition_rows.items():
                condition_row["turn"] = turn["turn"]
                condition_row["role"] = turn["role"]
                condition_row["score"] = _score_condition(condition_row, turn, case)
                if condition == "uruha_memory":
                    condition_row["source_trace_available"] = bool(
                        condition_row.get("passed_target_rows")
                        if turn["role"] != "false_memory_control"
                        else True
                    )

            recent_context = deepcopy(plain_histories["plain_recent"][-recent_window:])
            comparisons.append(
                {
                    "turn": turn["turn"],
                    "role": turn["role"],
                    "user": turn["user"],
                    "direct_execution_order": direct_order,
                    "recent_context": recent_context,
                    "conditions": {name: condition_rows[name] for name in CONDITIONS},
                }
            )
            system_row = condition_rows["uruha_memory"]
            rows.append(
                {
                    "turn": turn["turn"],
                    "role": turn["role"],
                    "execution": turn["execution"],
                    "user": turn["user"],
                    "reply": system_row["reply"],
                    "profile_after": system_row.get("profile_after") or {},
                }
            )
            for condition in ("plain_recent", "plain_full"):
                plain_histories[condition].append(
                    {
                        "turn": turn["turn"],
                        "user": turn["user"],
                        "reply": condition_rows[condition]["reply"],
                    }
                )

        final_profile = bot.memory.get_runtime_snapshot().get("profile") or {}
        session_turn_count = len(bot.memory.session_turns)

    production_after = tree_sha256(PRODUCTION_DB_PATH)
    summary = summarize(
        comparisons,
        prereg,
        production_before == production_after,
        final_profile,
        session_turn_count,
    )
    return {
        "schema": "uruha_v2_18_fifty_turn_memory_comparison_raw",
        "status": "fresh_generation_complete_human_ratings_pending",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "case_id": case["case_id"],
        "inputs": {
            "case": relative_binding(CASE_PATH),
            "preregistration": relative_binding(PREREG_PATH),
            "lock": relative_binding(LOCK_PATH),
            "model": deepcopy(prereg["model"]),
        },
        "execution_boundary": deepcopy(case["evidence_boundary"]),
        "rows": rows,
        "comparisons": comparisons,
        "summary": summary,
        "production_db_hash_before": production_before,
        "production_db_hash_after": production_after,
        "claims": {
            "supported": summary["interpretation"],
            "not_supported": [
                "general superiority over plain LLMs",
                "human felt-understanding preference",
                "an independent semantic holdout",
                "token-parity or equal-compute full-system comparison",
                "unbounded, cross-day, or universal long-term memory",
                "human-like autobiographical memory",
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("validate-design", "freeze-lock", "validate-lock", "run-fresh"),
        required=True,
    )
    args = parser.parse_args()
    case = load_json(CASE_PATH)
    prereg = load_json(PREREG_PATH)
    design = validate_design(case, prereg)
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
    raw = run_fresh(case, prereg)
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    packet, key = build_blind_packet(raw["comparisons"])
    BLIND_PACKET_PATH.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    BLIND_KEY_PATH.write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(RAW_PATH), "summary": raw["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
