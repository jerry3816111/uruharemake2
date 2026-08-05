#!/usr/bin/env python3
"""Run the frozen evidence-ID analysis on the final two LoCoMo reserves."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import build_source_preserving_memory_projection_v2_9_evidence_id_development as v29


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_10_final_reserve_preregistration.json"
OUTPUT = ROOT / "reports/source_preserving_memory_projection_v2_10_final_reserve.json"


def load_preregistration(path=PREREG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def frozen_dependencies(prereg):
    development = prereg["development_authorization"]
    implementation = prereg["frozen_implementation"]
    return (
        (development["v2_9_result_lock_path"], development["v2_9_result_lock_sha256"]),
        (development["v2_9_report_path"], development["v2_9_report_sha256"]),
        (implementation["v2_9_analyzer_path"], implementation["v2_9_analyzer_sha256"]),
        (
            implementation["v2_9_preregistration_path"],
            implementation["v2_9_preregistration_sha256"],
        ),
        (
            implementation["v2_8_partition_path"],
            implementation["v2_8_partition_sha256"],
        ),
        (
            implementation["v2_8_preregistration_path"],
            implementation["v2_8_preregistration_sha256"],
        ),
    )


def verify_frozen_dependencies(prereg, root=ROOT):
    for relative, expected in frozen_dependencies(prereg):
        if v25.file_sha256(Path(root) / relative) != expected:
            raise ValueError(f"frozen source hash drift: {relative}")


def partition_digest(sample_id, prereg):
    salt = prereg["frozen_partition"]["partition_salt"]
    return v25.text_sha256(f"{salt}:{sample_id}")


def final_reserve_samples(data, prereg):
    partition = prereg["frozen_partition"]
    excluded = set(partition["excluded_exposed_sample_ids"])
    reserve_pool = [row for row in data if str(row["sample_id"]) not in excluded]
    reserve_pool.sort(key=lambda row: partition_digest(str(row["sample_id"]), prereg))
    final = reserve_pool[partition["fresh_holdout_conversation_count"] :]
    final_ids = [str(row["sample_id"]) for row in final]
    if len(final) != partition["final_reserve_conversation_count"]:
        raise ValueError("final reserve conversation count drift")
    if v25.canonical_sha256(final_ids) != partition["final_reserve_sample_ids_sha256"]:
        raise ValueError("final reserve sample ID hash drift")
    return final, final_ids


def adapted_v29_preregistration(prereg, final_ids):
    adapted = copy.deepcopy(v29.load_preregistration())
    adapted["experiment_id"] = prereg["experiment_id"]
    adapted["official_source"].update(prereg["official_source"])
    adapted["development_scope"]["exposed_sample_ids"] = final_ids
    adapted["development_scope"]["exposed_sample_ids_sha256"] = v25.canonical_sha256(
        final_ids
    )
    adapted["development_scope"]["final_reserve_sample_ids_sha256"] = v25.canonical_sha256(
        final_ids
    )
    adapted_gates = adapted["success_gates"]
    for name, value in prereg["success_gates"].items():
        if name in adapted_gates:
            adapted_gates[name] = value
    adapted["evidence_boundary"] = prereg["evidence_boundary"]
    return adapted


def alias_final_samples(report, final_ids):
    aliases = {
        sample_id: f"final-reserve-{index + 1}"
        for index, sample_id in enumerate(final_ids)
    }
    for case in report["cases"]:
        alias = aliases[case["sample_id"]]
        case["sample_id"] = alias
        case["case_id"] = f"locomo-v2-10-{alias}-{case['qa_index']}"
    counts = report["scope"].pop("case_count_by_sample")
    report["scope"].pop("exposed_sample_ids")
    report["scope"].pop("exposed_sample_ids_sha256")
    report["scope"]["final_reserve_aliases"] = list(aliases.values())
    report["scope"]["case_count_by_final_reserve_alias"] = {
        aliases[sample_id]: count for sample_id, count in counts.items()
    }
    report["scope"]["final_reserve_sample_ids_sha256"] = v25.canonical_sha256(
        final_ids
    )
    return report


def build_report(data, prereg, dataset_sha256=None, dataset_bytes=None):
    _final, final_ids = final_reserve_samples(data, prereg)
    adapted = adapted_v29_preregistration(prereg, final_ids)
    report = v29.build_report(
        data,
        adapted,
        dataset_sha256=dataset_sha256,
        dataset_bytes=dataset_bytes,
    )
    report = alias_final_samples(report, final_ids)
    report["schema"] = "uruha_source_preserving_memory_projection_final_reserve_report_v2_10"
    report["evidence_scope"] = prereg["evidence_scope"]
    report["metrics"].pop("final_reserve_case_selection_payload_access_count")
    report["metrics"]["final_reserve_evaluation_payload_access_count"] = len(final_ids)
    report["gates"].pop("exposed_sample_ids_hash_matches")
    report["gates"].pop("final_reserve_case_selection_payload_access_count_equals")
    report["gates"]["final_reserve_sample_ids_hash_matches"] = (
        report["scope"]["final_reserve_sample_ids_sha256"]
        == prereg["frozen_partition"]["final_reserve_sample_ids_sha256"]
    )
    report["gates"]["final_reserve_evaluation_payload_access_count_equals"] = (
        report["metrics"]["final_reserve_evaluation_payload_access_count"]
        == prereg["success_gates"][
            "final_reserve_evaluation_payload_access_count_equals"
        ]
    )
    passed = all(report["gates"].values())
    report["decision"] = (
        "final_reserve_pass_authorize_independent_model_preregistration_only"
        if passed
        else "final_reserve_reject_adjacency_evidence_retention"
    )
    report["authorization"] = {
        "preregister_independent_model_evaluation": passed,
        "run_model_generation": False,
        "runtime_change": False,
        "runtime_shadow": False,
        "production_enablement": False,
    }
    report["evidence_boundary"] = prereg["evidence_boundary"]
    return report


def main():
    if OUTPUT.exists():
        raise SystemExit("V2.10 final reserve report already exists")
    prereg = load_preregistration()
    verify_frozen_dependencies(prereg)
    source_prereg = v25.load_preregistration()
    data = v25.ensure_official_dataset(source_prereg)
    report = build_report(
        data,
        prereg,
        dataset_sha256=v25.file_sha256(v25.DATASET),
        dataset_bytes=v25.DATASET.stat().st_size,
    )
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": v25.file_sha256(OUTPUT),
                "decision": report["decision"],
                "metrics": report["metrics"],
                "failed_gates": [
                    name for name, passed in report["gates"].items() if not passed
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
