#!/usr/bin/env python3
"""Independently audit the V2 support-equivalence construction."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "consolidation_support_equivalence_v2_construction_preregistration.json"
)
MEMORY_KINDS = ("episodic", "wisdom", "procedural")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path, text):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _normalize(text):
    normalized = unicodedata.normalize("NFKC", str(text)).lower()
    return "".join(char for char in normalized if char.isalnum())


def _collect_fields(payload, field):
    values = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == field and isinstance(value, str):
                values.append(value)
            values.extend(_collect_fields(value, field))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_collect_fields(value, field))
    return values


def _canonical_minimal_sets(raw_sets):
    unique = {
        tuple(sorted(set(indices)))
        for indices in raw_sets
        if indices
    }
    ordered = sorted(unique, key=lambda item: (len(item), item))
    antichain = []
    for candidate in ordered:
        if any(set(existing) < set(candidate) for existing in antichain):
            continue
        antichain.append(candidate)
    return [list(item) for item in antichain]


def _acceptable_unions(minimal_sets):
    if not minimal_sets:
        return []
    unions = set()
    for count in range(1, len(minimal_sets) + 1):
        for selected in itertools.combinations(minimal_sets, count):
            unions.add(
                tuple(
                    sorted(
                        set().union(
                            *(set(indices) for indices in selected)
                        )
                    )
                )
            )
    return [list(item) for item in sorted(unions, key=lambda x: (len(x), x))]


def _freshness_counts(config, pool):
    controls = config["freshness_and_leakage_controls"]
    prior_payloads = [
        _load(ROOT / path)
        for path in controls["excluded_consumed_datasets"]
    ]
    prior_texts = [
        text
        for payload in prior_payloads
        for text in _collect_fields(payload, "user")
    ]
    prior_scenarios = {
        value
        for payload in prior_payloads
        for value in _collect_fields(payload, "scenario_family")
    }
    current_texts = [
        event["user"]
        for case in pool["cases"]
        for event in case["source_events"]
    ]
    current_scenarios = {
        case["scenario_family"] for case in pool["cases"]
    }
    prior_normalized = {_normalize(text) for text in prior_texts}
    current_normalized = [_normalize(text) for text in current_texts]
    exact = sum(text in prior_normalized for text in current_normalized)
    threshold = controls["normalized_user_text_similarity_threshold"]
    near_prior = sum(
        SequenceMatcher(None, current, prior).ratio() >= threshold
        for current in current_normalized
        for prior in prior_normalized
    )
    near_internal = sum(
        SequenceMatcher(None, left, right).ratio() >= threshold
        for left, right in itertools.combinations(current_normalized, 2)
    )
    return {
        "exact_consumed_text_overlap_count": exact,
        "near_consumed_text_count": near_prior,
        "near_internal_duplicate_count": near_internal,
        "near_duplicate_count": near_prior + near_internal,
        "prior_scenario_family_overlap_count": len(
            current_scenarios & prior_scenarios
        ),
    }


def _memory_contract_checks(pool):
    total = 0
    valid_union = 0
    valid_antichain = 0
    valid_unsupported = 0
    for case in pool["cases"]:
        for kind in MEMORY_KINDS:
            total += 1
            memory = case["derived_memories"][kind]
            minimal = memory["minimal_support_sets"]
            if minimal == _canonical_minimal_sets(minimal):
                valid_antichain += 1
            if memory["acceptable_support_unions"] == _acceptable_unions(
                minimal
            ):
                valid_union += 1
            unsupported_valid = (
                memory["support_mode"] != "unsupported"
                or (
                    not minimal
                    and not memory["acceptable_support_unions"]
                    and not memory["support_universe"]
                )
            )
            valid_unsupported += unsupported_valid
    return {
        "memory_count": total,
        "valid_union_count": valid_union,
        "valid_antichain_count": valid_antichain,
        "valid_unsupported_count": valid_unsupported,
        "valid_union_rate": (
            round(valid_union / total, 4) if total else 0.0
        ),
        "valid_antichain_rate": (
            round(valid_antichain / total, 4) if total else 0.0
        ),
        "valid_unsupported_rate": (
            round(valid_unsupported / total, 4) if total else 0.0
        ),
    }


def _review_checks(config, pool, final_dataset, audit):
    reviewers = config["independent_machine_review"]
    calls = audit["calls"]
    call_by_key = {row["call_key"]: row for row in calls}
    expected_keys = {
        f"{reviewer}::{case['id']}::{kind}"
        for reviewer in ("reviewer_a", "reviewer_b")
        for case in pool["cases"]
        for kind in MEMORY_KINDS
    }
    snapshots_valid = all(
        audit["reviewer_snapshots"][name]["digest"]
        == reviewers[name]["digest"]
        for name in ("reviewer_a", "reviewer_b")
    )
    model_identity_valid = all(
        row["model_digest"] == reviewers[row["reviewer"]]["digest"]
        and row["model"] == reviewers[row["reviewer"]]["ollama_tag"]
        for row in calls
    )
    all_single_attempt = all(
        row["transport_attempts"] == 1 for row in calls
    )
    comparisons = {
        row["case_id"]: row for row in audit["comparisons"]
    }
    retained_ids = {case["id"] for case in final_dataset["cases"]}
    expected_retained = {
        case_id
        for case_id, row in comparisons.items()
        if row["retained"]
        and len(row["items"]) == 3
        and all(
            item["three_way_canonical_agreement"]
            for item in row["items"]
        )
    }
    three_way_items = [
        item
        for case_id in retained_ids
        for item in comparisons[case_id]["items"]
    ]
    return {
        "expected_call_key_count": len(expected_keys),
        "observed_call_key_count": len(call_by_key),
        "call_keys_exact": set(call_by_key) == expected_keys,
        "reviewer_snapshots_valid": snapshots_valid,
        "model_identity_valid": model_identity_valid,
        "all_calls_single_attempt": all_single_attempt,
        "transport_attempt_count_exact": (
            audit["transport_attempts"] == len(calls)
        ),
        "retained_case_ids_exact": retained_ids == expected_retained,
        "retained_item_count": len(three_way_items),
        "retained_three_way_agreement_rate": (
            round(
                sum(
                    item["three_way_canonical_agreement"]
                    for item in three_way_items
                )
                / len(three_way_items),
                4,
            )
            if three_way_items
            else 0.0
        ),
        "candidate_model_call_count": audit[
            "candidate_model_calls"
        ],
        "production_database_write_count": audit[
            "production_database_writes"
        ],
    }


def _gate(required, observed, comparison):
    if comparison == "exact":
        passed = observed == required
    elif comparison == "minimum":
        passed = observed >= required
    elif comparison == "maximum":
        passed = observed <= required
    else:
        raise ValueError(comparison)
    return {
        "required": required,
        "observed": observed,
        "comparison": comparison,
        "passed": passed,
    }


def _construction_gates(config, pool, final_dataset, audit, checks):
    expected = config["construction_success_gates"]
    metrics = audit["review_metrics"]
    final_memories = [
        memory
        for case in final_dataset["cases"]
        for memory in case["derived_memories"].values()
    ]
    language_counts = Counter(
        case["language"] for case in final_dataset["cases"]
    )
    kind_counts = Counter(
        memory["memory_kind"] for memory in final_memories
    )
    phenomena = Counter(
        memory["support_phenomenon"] for memory in final_memories
    )
    observed = {
        "pool_case_count_exact": len(pool["cases"]),
        "pool_derived_memory_count_exact": sum(
            len(case["derived_memories"]) for case in pool["cases"]
        ),
        "review_call_count_exact": len(audit["calls"]),
        "review_transport_error_count_exact": sum(
            bool(row["transport_error"]) for row in audit["calls"]
        ),
        "final_case_count_min": len(final_dataset["cases"]),
        "final_derived_memory_count_min": len(final_memories),
        "final_case_count_per_language_min": min(
            (language_counts.get(language, 0) for language in ("eng", "jpn", "cmn")),
            default=0,
        ),
        "final_derived_memory_count_per_kind_min": min(
            (kind_counts.get(kind, 0) for kind in MEMORY_KINDS),
            default=0,
        ),
        "final_single_minimal_set_count_min": phenomena[
            "single_minimal_set"
        ],
        "final_alternative_minimal_sets_count_min": phenomena[
            "alternative_minimal_sets"
        ],
        "final_complementary_multi_event_set_count_min": phenomena[
            "complementary_multi_event_set"
        ],
        "final_current_state_override_count_min": phenomena[
            "current_state_override"
        ],
        "final_unsupported_count_min": phenomena["unsupported"],
        "retained_item_three_way_canonical_agreement": checks[
            "review"
        ]["retained_three_way_agreement_rate"],
        "retained_item_valid_union_enumeration": checks[
            "final_memory_contract"
        ]["valid_union_rate"],
        "retained_item_minimal_set_antichain": checks[
            "final_memory_contract"
        ]["valid_antichain_rate"],
        "exact_consumed_text_overlap_count_exact": checks[
            "freshness"
        ]["exact_consumed_text_overlap_count"],
        "near_duplicate_count_exact": checks["freshness"][
            "near_duplicate_count"
        ],
        "candidate_model_call_count_exact": checks["review"][
            "candidate_model_call_count"
        ],
        "production_database_write_count_exact": checks["review"][
            "production_database_write_count"
        ],
    }
    gates = {}
    for key, value in observed.items():
        if key.endswith("_min"):
            comparison = "minimum"
        elif key.endswith("_max"):
            comparison = "maximum"
        else:
            comparison = "exact"
        gates[key] = _gate(expected[key], value, comparison)
    gates["review_call_keys_exact"] = _gate(
        True,
        checks["review"]["call_keys_exact"],
        "exact",
    )
    gates["reviewer_snapshots_valid"] = _gate(
        True,
        checks["review"]["reviewer_snapshots_valid"],
        "exact",
    )
    gates["review_model_identity_valid"] = _gate(
        True,
        checks["review"]["model_identity_valid"],
        "exact",
    )
    gates["all_calls_single_attempt"] = _gate(
        True,
        checks["review"]["all_calls_single_attempt"],
        "exact",
    )
    gates["retained_case_ids_exact"] = _gate(
        True,
        checks["review"]["retained_case_ids_exact"],
        "exact",
    )
    gates["prior_scenario_family_overlap_count"] = _gate(
        0,
        checks["freshness"]["prior_scenario_family_overlap_count"],
        "exact",
    )
    gates["pool_memory_contract_valid"] = _gate(
        1.0,
        checks["pool_memory_contract"]["valid_union_rate"],
        "exact",
    )
    if metrics["final_case_count"] != len(final_dataset["cases"]):
        gates["review_metrics_match_final_dataset"] = _gate(
            True,
            False,
            "exact",
        )
    else:
        gates["review_metrics_match_final_dataset"] = _gate(
            True,
            True,
            "exact",
        )
    return gates


def _markdown(audit):
    metrics = audit["review_metrics"]
    failed = [
        name
        for name, gate in audit["construction_gates"].items()
        if not gate["passed"]
    ]
    retired = [
        row["case_id"] for row in audit["retired_cases"]
    ]
    return "\n".join(
        [
            "# Consolidation Support Equivalence V2 Construction Audit",
            "",
            f"- Decision: `{audit['decision']}`",
            f"- All gates pass: `{audit['all_construction_gates_pass']}`",
            f"- Review calls: `{metrics['pool_review_call_count']}`",
            f"- Transport errors: `{metrics['transport_error_count']}`",
            f"- Parse errors: `{metrics['parse_error_count']}`",
            f"- Retained cases: `{metrics['final_case_count']}/18`",
            (
                "- Retained derived memories: "
                f"`{metrics['final_derived_memory_count']}/54`"
            ),
            f"- Retired cases: `{', '.join(retired) if retired else 'none'}`",
            f"- Failed gates: `{', '.join(failed) if failed else 'none'}`",
            "- Candidate Qwen3.5 4B calls: `0`",
            "- Production database writes: `0`",
            "",
            "This construction result is machine-consensus development "
            "evidence only. It is not human-quality gold and does not "
            "authorize candidate inference, runtime restoration, retrieval "
            "claims, dialogue claims, or human-likeness claims.",
            "",
        ]
    )


def audit_construction():
    config = _load(CONFIG_PATH)
    paths = config["construction_pool"]
    pool_path = ROOT / paths["pool_dataset_path"]
    final_path = ROOT / paths["final_dataset_path"]
    audit_path = ROOT / paths["audit_json_path"]
    markdown_path = ROOT / paths["audit_markdown_path"]
    if markdown_path.exists():
        raise RuntimeError("construction audit markdown already exists")

    pool = _load(pool_path)
    final_dataset = _load(final_path)
    audit = _load(audit_path)
    if not audit.get("complete"):
        raise RuntimeError("review checkpoint is incomplete")

    checks = {
        "freshness": _freshness_counts(config, pool),
        "pool_memory_contract": _memory_contract_checks(pool),
        "final_memory_contract": _memory_contract_checks(final_dataset),
    }
    checks["review"] = _review_checks(
        config,
        pool,
        final_dataset,
        audit,
    )
    gates = _construction_gates(
        config,
        pool,
        final_dataset,
        audit,
        checks,
    )
    all_pass = all(gate["passed"] for gate in gates.values())
    audit.update(
        {
            "audit_run_count": 1,
            "audit_checks": checks,
            "construction_gates": gates,
            "all_construction_gates_pass": all_pass,
            "decision": (
                "construction_pass_authorize_evaluation_preregistration"
                if all_pass
                else "construction_fail_stop_support_attribution_hypothesis"
            ),
            "artifact_sha256": {
                "preregistration": _sha256(CONFIG_PATH),
                "pool": _sha256(pool_path),
                "final_dataset": _sha256(final_path),
                "builder": _sha256(
                    ROOT / paths["builder_path"]
                ),
                "reviewer": _sha256(
                    ROOT / paths["reviewer_path"]
                ),
                "auditor": _sha256(
                    ROOT / paths["auditor_path"]
                ),
            },
            "evidence_limits": {
                "human_quality_gold": False,
                "candidate_inference_authorized": all_pass,
                "runtime_restoration_authorized": False,
                "production_activation_authorized": False,
                "retrieval_improvement_validated": False,
                "dialogue_improvement_validated": False,
                "human_likeness_validated": False,
            },
        }
    )
    _atomic_write(
        audit_path,
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write(markdown_path, _markdown(audit))
    return audit


def main():
    audit = audit_construction()
    print(
        json.dumps(
            {
                "decision": audit["decision"],
                "all_construction_gates_pass": audit[
                    "all_construction_gates_pass"
                ],
                "failed_gates": [
                    name
                    for name, gate in audit[
                        "construction_gates"
                    ].items()
                    if not gate["passed"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
