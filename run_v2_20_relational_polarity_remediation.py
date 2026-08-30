#!/usr/bin/env python3
"""Run a causal same-case replay of the V2.19 relational-polarity repair."""

from __future__ import annotations

import argparse
import contextlib
import json
from copy import deepcopy
from pathlib import Path

import run_v2_18_fifty_turn_memory_comparison as base
import run_v2_19_fifty_turn_memory_remediation as v219


ROOT = Path(__file__).resolve().parent
CASE_PATH = v219.CASE_PATH
PREREG_PATH = ROOT / "configs/v2_20_relational_polarity_remediation_preregistration.json"
LOCK_PATH = ROOT / "configs/v2_20_relational_polarity_remediation_lock.json"
V219_RAW_PATH = v219.RAW_PATH
RAW_PATH = ROOT / "analysis/v2_20_relational_polarity_remediation_raw.json"
RUNTIME_PATH = ROOT / "uruha_brain_mac.py"
PERSONHOOD_PATH = ROOT / "uruha_personhood_loop.py"
VISIBLE_CONTRACT_PATH = ROOT / "human_pragmatic_comparison_v2_14.py"
REMEDIATION_TEST_PATH = ROOT / "test_memory_remediation_v2_19.py"
RUNNER_TEST_PATH = ROOT / "test_relational_polarity_remediation_v2_20.py"

_V219_SCORE = v219._score_condition
_BASE_PATH_NAMES = (
    "CASE_PATH",
    "PREREG_PATH",
    "LOCK_PATH",
    "RAW_PATH",
    "RUNTIME_PATH",
    "VISIBLE_CONTRACT_PATH",
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative_binding(path):
    return base.relative_binding(path)


def build_lock():
    return {
        "schema": "uruha_v2_20_relational_polarity_remediation_lock",
        "status": "frozen_before_first_repaired_system_generation",
        "policy": {
            "reuse_v2_19_outputs_without_regeneration": True,
            "fresh_generation_only_for_repaired_uruha": True,
            "retain_first_generation_failures": True,
            "automatic_metrics_are_not_human_preference": True,
            "same_case_replay_not_independent_holdout": True,
        },
        "artifacts": {
            "case": relative_binding(CASE_PATH),
            "preregistration": relative_binding(PREREG_PATH),
            "v2_19_frozen_raw": relative_binding(V219_RAW_PATH),
            "runner": relative_binding(Path(__file__)),
            "runtime": relative_binding(RUNTIME_PATH),
            "personhood": relative_binding(PERSONHOOD_PATH),
            "visible_contract": relative_binding(VISIBLE_CONTRACT_PATH),
            "remediation_tests": relative_binding(REMEDIATION_TEST_PATH),
            "runner_tests": relative_binding(RUNNER_TEST_PATH),
        },
    }


def validate_lock():
    lock = load_json(LOCK_PATH)
    checks = {}
    for name, binding in (lock.get("artifacts") or {}).items():
        path = ROOT / binding["path"]
        checks[name] = bool(path.is_file() and base.sha256_file(path) == binding.get("sha256"))
    return {"passed": bool(checks) and all(checks.values()), "checks": checks, "lock": lock}


def validate_design(case, prereg, frozen_raw):
    errors = []
    base_design = base.validate_design(case, v219.load_json(v219.PREREG_PATH))
    if not base_design["passed"]:
        errors.extend(base_design["errors"])
    if frozen_raw.get("case_id") != case.get("case_id"):
        errors.append("frozen V2.19 raw and case id differ")
    if len(frozen_raw.get("comparisons") or []) != 5:
        errors.append("frozen V2.19 raw must contain five checkpoints")
    if not prereg["invariants"].get("same_dataset_as_v2_19"):
        errors.append("V2.20 must declare same-case replay")
    if prereg["claim_boundary"].get("independent_semantic_holdout"):
        errors.append("same-case replay cannot be independent holdout")
    return {
        "passed": not errors,
        "errors": errors,
        "turn_count": len(case.get("turns") or []),
        "checkpoint_count": len(frozen_raw.get("comparisons") or []),
        "frozen_reference_sha256": base.sha256_file(V219_RAW_PATH),
    }


def _contains_any(text, values):
    return any(str(value) in str(text or "") for value in values)


def _score_condition(row, turn, case):
    score = _V219_SCORE(row, turn, case)
    reply = str(row.get("reply") or "")
    if turn["role"] == "withdrawal_probe":
        old_terms = list((case["values"]["initial"] or {}).get("japanese") or [])
        old_named = _contains_any(reply, old_terms)
        direct_denial = _contains_any(
            reply,
            ("前の情報", "今の好みとして見てない", "本命から外して", "今は", "じゃない", "ではない", "違う"),
        )
        score["withdrawn_old_value_directly_denied"] = bool(old_named and direct_denial)
        if score["withdrawn_old_value_directly_denied"]:
            score["stale_value_revival"] = False
            score["old_value_explicitly_negated"] = True
            score["epistemic_safe"] = bool(score.get("visible_japanese_contract_pass"))
            score["task_pass"] = bool(score.get("visible_japanese_contract_pass"))
    return score


def _frozen_condition_lookup(raw):
    return {
        (int(comparison["turn"]), condition): deepcopy(row)
        for comparison in raw.get("comparisons") or []
        for condition, row in comparison.get("conditions", {}).items()
    }


def _frozen_direct_completion_factory(frozen_raw):
    lookup = _frozen_condition_lookup(frozen_raw)

    def frozen_direct_completion(client, prereg, history, turn, condition, recent_window):
        row = deepcopy(lookup[(int(turn["turn"]), condition)])
        row["reused_from_v2_19"] = True
        row["fresh_in_v2_20"] = False
        return row

    return frozen_direct_completion


@contextlib.contextmanager
def _bound_base_module(frozen_raw):
    old_paths = {name: getattr(base, name) for name in _BASE_PATH_NAMES}
    old_score = base._score_condition
    old_summary = base.summarize
    old_direct = base._direct_completion
    updates = {
        "CASE_PATH": CASE_PATH,
        "PREREG_PATH": PREREG_PATH,
        "LOCK_PATH": LOCK_PATH,
        "RAW_PATH": RAW_PATH,
        "RUNTIME_PATH": RUNTIME_PATH,
        "VISIBLE_CONTRACT_PATH": VISIBLE_CONTRACT_PATH,
    }
    try:
        for name, value in updates.items():
            setattr(base, name, value)
        base._score_condition = _score_condition
        base.summarize = v219.summarize
        base._direct_completion = _frozen_direct_completion_factory(frozen_raw)
        yield
    finally:
        for name, value in old_paths.items():
            setattr(base, name, value)
        base._score_condition = old_score
        base.summarize = old_summary
        base._direct_completion = old_direct


def run_fresh(case, prereg, frozen_raw):
    with _bound_base_module(frozen_raw):
        raw = base.run_fresh(case, prereg)
    before_lookup = _frozen_condition_lookup(frozen_raw)
    for comparison in raw["comparisons"]:
        turn = int(comparison["turn"])
        repaired = comparison["conditions"]["uruha_memory"]
        repaired["fresh_in_v2_20"] = True
        repaired["reused_from_v2_19"] = False
        comparison["conditions"]["pre_fix_uruha_memory"] = deepcopy(
            before_lookup[(turn, "uruha_memory")]
        )
        comparison["conditions"]["pre_fix_uruha_memory"]["fresh_in_v2_20"] = False
        comparison["conditions"]["pre_fix_uruha_memory"]["reused_from_v2_19"] = True
        comparison["conditions"]["pre_fix_uruha_memory"]["score_v2_20"] = _score_condition(
            comparison["conditions"]["pre_fix_uruha_memory"],
            next(row for row in case["turns"] if int(row["turn"]) == turn),
            case,
        )
    raw["schema"] = "uruha_v2_20_relational_polarity_remediation_raw"
    raw["comparison_boundary"] = {
        "fresh_outputs": "Only repaired uruha_memory checkpoint outputs are fresh in V2.20.",
        "frozen_outputs": "pre_fix_uruha_memory, plain_recent, and plain_full are copied byte-for-byte from the first V2.19 raw result.",
        "independent_holdout": False,
    }
    raw["claims"]["not_supported"] = list(
        dict.fromkeys(
            [
                *raw["claims"].get("not_supported", []),
                "independent semantic generalization",
                "fresh V2.20 baseline generation",
                "human felt-understanding preference",
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
    frozen_raw = load_json(V219_RAW_PATH)
    design = validate_design(case, prereg, frozen_raw)
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
    raw = run_fresh(case, prereg, frozen_raw)
    RAW_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(RAW_PATH), "summary": raw["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
