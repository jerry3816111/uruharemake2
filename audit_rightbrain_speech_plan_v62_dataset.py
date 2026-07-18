#!/usr/bin/env python3
"""Audit the frozen V62 speech-plan payload pilot before model use."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT / "configs/rightbrain_speech_plan_payload_v62_preregistration.json"
)
DATASET_PATH = ROOT / "datasets/rightbrain_speech_plan_payload_v62.json"
DEFAULT_JSON = ROOT / "reports/rightbrain_speech_plan_payload_v62_dataset_audit.json"
DEFAULT_MD = ROOT / "reports/rightbrain_speech_plan_payload_v62_dataset_audit.md"
PRIOR_DATASET_PATHS = (
    ROOT / "datasets/rightbrain_pipeline_shadow_v61.json",
    ROOT / "datasets/rightbrain_qwen35_migration_v33_holdout.json",
    ROOT / "datasets/rightbrain_role_specialization_v34_confirmation.json",
)
TEXT_KEYS = {
    "user_input",
    "input",
    "prompt",
    "query",
    "source_input",
    "display_input",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(text):
    return re.sub(r"[\W_]+", "", str(text or "").lower(), flags=re.UNICODE)


def _load_json_or_jsonl(path):
    if path.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_texts(value, path=""):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if key in TEXT_KEYS and isinstance(item, str) and item.strip():
                found.append({"path": child, "text": item.strip()})
            found.extend(_collect_texts(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_collect_texts(item, f"{path}[{index}]"))
    return found


def _prior_sources():
    human_paths = tuple(
        path
        for base in (ROOT / "datasets", ROOT / "reports", ROOT / "analysis")
        if base.exists()
        for path in base.rglob("*")
        if path.is_file()
        and path != DATASET_PATH
        and any(
            token in path.name.lower()
            for token in ("human_blind", "rightbrain_v21", "rightbrain_v29")
        )
        and path.suffix.lower() in {".json", ".jsonl", ".csv"}
    )
    return (*PRIOR_DATASET_PATHS, *human_paths)


def _prior_texts():
    rows = []
    seen = set()
    for source in _prior_sources():
        if not source.exists() or source in seen:
            continue
        seen.add(source)
        try:
            payload = _load_json_or_jsonl(source)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        for item in _collect_texts(payload):
            item["source"] = str(source.relative_to(ROOT))
            rows.append(item)
    return rows


def audit():
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    expected = prereg["fresh_dataset"]
    cases = dataset.get("cases") or []
    family_counts = Counter(case.get("scenario_family") for case in cases)
    ids = [case.get("id") for case in cases]
    normalized_inputs = [_normalize(case.get("user_input")) for case in cases]
    threshold = float(
        prereg["leakage_controls"][
            "normalized_user_text_similarity_threshold"
        ]
    )

    required_fields = set(expected["required_case_fields"])
    missing_fields = {
        case.get("id", f"row_{index}"): sorted(required_fields - set(case))
        for index, case in enumerate(cases)
        if required_fields - set(case)
    }
    malformed_propositions = []
    for case in cases:
        for field in (
            "required_meaning_propositions",
            "forbidden_meaning_propositions",
        ):
            for proposition in case.get(field) or []:
                if (
                    not isinstance(proposition, dict)
                    or not proposition.get("id")
                    or not proposition.get("description")
                    or not isinstance(proposition.get("accepted_surfaces"), list)
                    or not proposition.get("accepted_surfaces")
                ):
                    malformed_propositions.append(
                        {"case_id": case.get("id"), "field": field}
                    )

    internal_near_duplicates = []
    for left in range(len(cases)):
        for right in range(left + 1, len(cases)):
            ratio = SequenceMatcher(
                None,
                normalized_inputs[left],
                normalized_inputs[right],
            ).ratio()
            if ratio >= threshold:
                internal_near_duplicates.append(
                    {
                        "left": ids[left],
                        "right": ids[right],
                        "similarity": round(ratio, 4),
                    }
                )

    prior = _prior_texts()
    prior_normalized = [
        (_normalize(row["text"]), row)
        for row in prior
        if _normalize(row["text"])
    ]
    exact_overlaps = []
    external_near_duplicates = []
    for case, normalized in zip(cases, normalized_inputs):
        for old_normalized, old in prior_normalized:
            if normalized == old_normalized:
                exact_overlaps.append(
                    {
                        "case_id": case["id"],
                        "source": old["source"],
                        "source_path": old["path"],
                    }
                )
                continue
            ratio = SequenceMatcher(None, normalized, old_normalized).ratio()
            if ratio >= threshold:
                external_near_duplicates.append(
                    {
                        "case_id": case["id"],
                        "source": old["source"],
                        "source_path": old["path"],
                        "similarity": round(ratio, 4),
                    }
                )

    memory_cases = [case for case in cases if case["memory_fixture"]]
    memory_policy_cases = [
        case
        for case in cases
        if case["scenario_family"] == "memory_update_or_suppression"
    ]
    private_cases = [case for case in cases if case["private_memory_terms"]]
    checks = {
        "schema_matches": dataset.get("schema")
        == "uruha_rightbrain_speech_plan_payload_pilot_v62",
        "status_frozen_before_inference": dataset.get("status")
        == "frozen_before_plan_capture_or_model_inference",
        "official_benchmark_items_false": dataset.get(
            "official_benchmark_items"
        )
        is False,
        "benchmark_answers_present_false": dataset.get(
            "benchmark_answers_present"
        )
        is False,
        "case_count_exact": len(cases) == expected["case_count"],
        "scenario_family_count_exact": len(family_counts)
        == expected["scenario_family_count"],
        "cases_per_family_exact": all(
            family_counts.get(family) == expected["cases_per_family"]
            for family in expected["scenario_families"]
        ),
        "scenario_family_set_exact": set(family_counts)
        == set(expected["scenario_families"]),
        "case_ids_unique": len(ids) == len(set(ids)) and all(ids),
        "user_inputs_unique": len(normalized_inputs)
        == len(set(normalized_inputs))
        and all(normalized_inputs),
        "required_fields_complete": not missing_fields,
        "required_propositions_nonempty": all(
            case["required_meaning_propositions"] for case in cases
        ),
        "proposition_contract_well_formed": not malformed_propositions,
        "memory_fixture_shape_valid": all(
            isinstance(case["memory_fixture"], list) for case in cases
        ),
        "memory_update_and_private_suppression_present": len(
            memory_policy_cases
        )
        == 2
        and all(case["memory_fixture"] for case in memory_policy_cases)
        and len(private_cases) == 1,
        "psyche_fixture_shape_valid": all(
            isinstance(case["psyche_fixture"], dict)
            and set(case["psyche_fixture"]) == {"mood", "trust"}
            for case in cases
        ),
        "maximum_reply_chars_valid": all(
            isinstance(case["maximum_reply_chars"], int)
            and 32 <= case["maximum_reply_chars"] <= 120
            for case in cases
        ),
        "internal_near_duplicate_count_zero": not internal_near_duplicates,
        "exact_prior_text_overlap_count_zero": not exact_overlaps,
        "external_near_duplicate_count_zero": not external_near_duplicates,
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_rightbrain_speech_plan_payload_dataset_audit_v62",
        "passed": passed,
        "bindings": {
            "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
            "preregistration_sha256": _sha256(PREREG_PATH),
            "dataset_path": str(DATASET_PATH.relative_to(ROOT)),
            "dataset_sha256": _sha256(DATASET_PATH),
        },
        "counts": {
            "case_count": len(cases),
            "scenario_family_count": len(family_counts),
            "family_counts": dict(sorted(family_counts.items())),
            "required_proposition_count": sum(
                len(case["required_meaning_propositions"]) for case in cases
            ),
            "forbidden_proposition_count": sum(
                len(case["forbidden_meaning_propositions"]) for case in cases
            ),
            "memory_fixture_count": sum(
                len(case["memory_fixture"]) for case in cases
            ),
            "prior_text_count_scanned": len(prior),
            "internal_near_duplicate_count": len(internal_near_duplicates),
            "exact_prior_text_overlap_count": len(exact_overlaps),
            "external_near_duplicate_count": len(external_near_duplicates),
        },
        "checks": checks,
        "missing_fields": missing_fields,
        "malformed_propositions": malformed_propositions,
        "internal_near_duplicates": internal_near_duplicates,
        "exact_overlaps": exact_overlaps,
        "external_near_duplicates": external_near_duplicates,
        "authorizations": {
            "harness_implementation": passed,
            "plan_capture": False,
            "candidate_inference": False,
            "human_blind_review": False,
            "runtime_change": False,
        },
        "evidence_boundary": "This audit freezes project-authored dialogue inputs and scoring-only semantic propositions. It runs no model and cannot establish RightBrain quality, naturalness, runtime readiness, or broad human likeness.",
    }


def _markdown(report):
    counts = report["counts"]
    return "\n".join(
        [
            "# V62 speech-plan payload dataset audit",
            "",
            f"- Gate: **{'PASS' if report['passed'] else 'FAIL'}**",
            f"- Cases: `{counts['case_count']}`",
            f"- Scenario families: `{counts['scenario_family_count']}`",
            f"- Required propositions: `{counts['required_proposition_count']}`",
            f"- Exact prior-text overlaps: `{counts['exact_prior_text_overlap_count']}`",
            f"- Near duplicates: `{counts['internal_near_duplicate_count'] + counts['external_near_duplicate_count']}`",
            "",
            "No LeftBrain or RightBrain model was called by this audit.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = audit()
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {"passed": report["passed"], "counts": report["counts"]},
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
