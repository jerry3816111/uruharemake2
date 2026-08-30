#!/usr/bin/env python3
"""Freeze and run the V2.19 new-value remediation comparison."""

from __future__ import annotations

import argparse
import contextlib
import json
from copy import deepcopy
from pathlib import Path

import run_v2_18_fifty_turn_memory_comparison as base


ROOT = Path(__file__).resolve().parent
CASE_PATH = ROOT / "datasets/v2_19_fifty_turn_memory_remediation_comparison.json"
PREREG_PATH = ROOT / "configs/v2_19_fifty_turn_memory_remediation_preregistration.json"
LOCK_PATH = ROOT / "configs/v2_19_fifty_turn_memory_remediation_lock.json"
RAW_PATH = ROOT / "analysis/v2_19_fifty_turn_memory_remediation_raw.json"
BLIND_PACKET_PATH = ROOT / "analysis/v2_19_fifty_turn_memory_remediation_blind_packet.json"
BLIND_KEY_PATH = ROOT / "analysis/v2_19_fifty_turn_memory_remediation_blind_key.json"
RUNTIME_PATH = ROOT / "uruha_brain_mac.py"
PERSONHOOD_PATH = ROOT / "uruha_personhood_loop.py"
VISIBLE_CONTRACT_PATH = ROOT / "human_pragmatic_comparison_v2_14.py"
REMEDIATION_TEST_PATH = ROOT / "test_memory_remediation_v2_19.py"

_BASE_SCORE = base._score_condition
_BASE_SUMMARIZE = base.summarize
_BASE_PATH_NAMES = (
    "CASE_PATH",
    "PREREG_PATH",
    "LOCK_PATH",
    "RAW_PATH",
    "BLIND_PACKET_PATH",
    "BLIND_KEY_PATH",
    "RUNTIME_PATH",
    "VISIBLE_CONTRACT_PATH",
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative_binding(path):
    return base.relative_binding(path)


def build_lock():
    return {
        "schema": "uruha_v2_19_fifty_turn_memory_remediation_lock",
        "status": "frozen_before_first_comparison_generation",
        "policy": {
            "retain_first_generation_failures": True,
            "post_generation_case_or_scoring_tuning_forbidden": True,
            "automatic_metrics_are_not_human_preference": True,
            "development_remediation_not_independent_holdout": True,
        },
        "artifacts": {
            "case": relative_binding(CASE_PATH),
            "preregistration": relative_binding(PREREG_PATH),
            "runner": relative_binding(Path(__file__)),
            "runtime": relative_binding(RUNTIME_PATH),
            "personhood": relative_binding(PERSONHOOD_PATH),
            "visible_contract": relative_binding(VISIBLE_CONTRACT_PATH),
            "remediation_tests": relative_binding(REMEDIATION_TEST_PATH),
        },
    }


def validate_lock():
    lock = load_json(LOCK_PATH)
    checks = {}
    for name, binding in (lock.get("artifacts") or {}).items():
        path = ROOT / binding["path"]
        checks[name] = bool(path.is_file() and base.sha256_file(path) == binding.get("sha256"))
    return {"passed": bool(checks) and all(checks.values()), "checks": checks, "lock": lock}


def validate_design(case, prereg):
    result = base.validate_design(case, prereg)
    errors = list(result.get("errors") or [])
    if not str(case.get("schema") or "").startswith("uruha_v2_19_"):
        errors.append("case schema must be v2.19")
    old_values = set()
    if base.CASE_PATH.exists():
        old_case = load_json(base.CASE_PATH)
        old_values = {
            str((row or {}).get("raw") or "").lower()
            for row in (old_case.get("values") or {}).values()
        }
    new_values = {
        str((row or {}).get("raw") or "").lower()
        for row in (case.get("values") or {}).values()
    }
    if old_values & new_values:
        errors.append("v2.19 values must not reuse v2.18 values")
    result["new_values_disjoint_from_v2_18"] = not bool(old_values & new_values)
    result["errors"] = errors
    result["passed"] = not errors
    return result


def _contains_any(text, values):
    return any(str(value) in str(text or "") for value in values)


def _score_condition(row, turn, case):
    score = _BASE_SCORE(row, turn, case)
    reply = str(row.get("reply") or "")
    current_terms = list((case["values"]["current"] or {}).get("japanese") or [])
    false_terms = list((case["values"]["false_control"] or {}).get("japanese") or [])
    if turn["role"] == "explicit_correction":
        acknowledged = _contains_any(reply, current_terms)
        score["explicit_update_acknowledged"] = acknowledged
        score["task_pass"] = bool(
            acknowledged and score.get("visible_japanese_contract_pass")
        )
    elif turn["role"] == "false_memory_control":
        queried_value_named = _contains_any(reply, false_terms)
        direct_denial = _contains_any(
            reply,
            ("聞いてない", "言ってない", "記録はない", "覚えてない", "お前の一番好きとは", "あなたの一番好きとは"),
        )
        relational_attribution = _contains_any(reply, ("友達", "友人", "別の人"))
        non_answer = _contains_any(reply, ("もう一回", "教えて", "分からない", "わからない")) and not direct_denial
        if direct_denial:
            score["false_memory_assertion"] = False
            score["false_value_explicitly_negated"] = True
        score.update(
            {
                "queried_false_value_named": queried_value_named,
                "direct_false_claim_denial": direct_denial,
                "relational_attribution": relational_attribution,
                "non_answer": non_answer,
                "relational_false_claim_directly_denied": bool(
                    queried_value_named and direct_denial and relational_attribution and not non_answer
                ),
            }
        )
        score["task_pass"] = bool(
            score["relational_false_claim_directly_denied"]
            and not score.get("false_memory_assertion")
            and score.get("visible_japanese_contract_pass")
        )
    return score


def summarize(comparisons, prereg, production_unchanged, final_profile, session_turn_count):
    summary = _BASE_SUMMARIZE(
        comparisons,
        prereg,
        production_unchanged,
        final_profile,
        session_turn_count,
    )
    explicit = next(row for row in comparisons if row["role"] == "explicit_correction")
    false_control = next(row for row in comparisons if row["role"] == "false_memory_control")
    system_explicit = explicit["conditions"]["uruha_memory"]["score"]
    system_false = false_control["conditions"]["uruha_memory"]["score"]
    summary["uruha_explicit_update_acknowledged"] = bool(system_explicit.get("explicit_update_acknowledged"))
    summary["uruha_relational_false_claim_directly_denied"] = bool(
        system_false.get("relational_false_claim_directly_denied")
    )
    summary["uruha_preregistered_gate_pass"] = bool(
        summary.get("uruha_preregistered_gate_pass")
        and summary["uruha_explicit_update_acknowledged"]
        and summary["uruha_relational_false_claim_directly_denied"]
    )
    summary["development_remediation_pass"] = summary["uruha_preregistered_gate_pass"]
    summary["independent_semantic_holdout"] = False
    summary["human_preference_supported"] = False
    return summary


@contextlib.contextmanager
def _bound_base_module():
    old = {name: getattr(base, name) for name in _BASE_PATH_NAMES}
    old_score = base._score_condition
    old_summary = base.summarize
    updates = {
        "CASE_PATH": CASE_PATH,
        "PREREG_PATH": PREREG_PATH,
        "LOCK_PATH": LOCK_PATH,
        "RAW_PATH": RAW_PATH,
        "BLIND_PACKET_PATH": BLIND_PACKET_PATH,
        "BLIND_KEY_PATH": BLIND_KEY_PATH,
        "RUNTIME_PATH": RUNTIME_PATH,
        "VISIBLE_CONTRACT_PATH": VISIBLE_CONTRACT_PATH,
    }
    try:
        for name, value in updates.items():
            setattr(base, name, value)
        base._score_condition = _score_condition
        base.summarize = summarize
        yield
    finally:
        for name, value in old.items():
            setattr(base, name, value)
        base._score_condition = old_score
        base.summarize = old_summary


def run_fresh(case, prereg):
    with _bound_base_module():
        raw = base.run_fresh(case, prereg)
    raw["schema"] = "uruha_v2_19_fifty_turn_memory_remediation_raw"
    raw["claims"]["not_supported"] = list(
        dict.fromkeys(
            [
                *raw["claims"].get("not_supported", []),
                "independent remediation generalization",
                "human preference without completed blind ratings",
            ]
        )
    )
    return raw


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
    lock = validate_lock()
    if not lock["passed"]:
        raise SystemExit(json.dumps(lock, ensure_ascii=False, indent=2))
    if args.mode == "validate-lock":
        print(json.dumps(lock, ensure_ascii=False, indent=2))
        return
    if RAW_PATH.exists():
        raise SystemExit("raw result already exists; refusing to overwrite frozen generation")
    raw = run_fresh(case, prereg)
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    packet, key = base.build_blind_packet(raw["comparisons"], seed=20260814 + 19)
    packet["schema"] = "uruha_v2_19_fifty_turn_memory_remediation_blind_packet"
    key["schema"] = "uruha_v2_19_fifty_turn_memory_remediation_blind_key"
    BLIND_PACKET_PATH.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    BLIND_KEY_PATH.write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(RAW_PATH), "summary": raw["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
