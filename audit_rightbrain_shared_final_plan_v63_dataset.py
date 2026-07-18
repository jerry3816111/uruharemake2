#!/usr/bin/env python3
"""Audit V63 fresh cases before any plan capture or model inference."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_shared_final_plan_v63_preregistration.json"
DATASET_PATH = ROOT / "datasets/rightbrain_shared_final_plan_v63.json"
DEFAULT_JSON = ROOT / "reports/rightbrain_shared_final_plan_v63_dataset_audit.json"
DEFAULT_MD = ROOT / "reports/rightbrain_shared_final_plan_v63_dataset_audit.md"
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


def _load(path):
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
    rows = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if key in TEXT_KEYS and isinstance(item, str) and item.strip():
                rows.append({"path": child, "text": item.strip()})
            rows.extend(_collect_texts(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            rows.extend(_collect_texts(item, f"{path}[{index}]"))
    return rows


def _prior_sources():
    sources = []
    for base in (ROOT / "datasets", ROOT / "reports", ROOT / "analysis"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if (
                path.is_file()
                and path not in {DATASET_PATH, DEFAULT_JSON}
                and path.suffix.lower() in {".json", ".jsonl", ".csv"}
                and any(
                    token in path.name.lower()
                    for token in ("rightbrain", "human_blind")
                )
            ):
                sources.append(path)
    return tuple(sorted(set(sources)))


def _prior_texts():
    rows = []
    for source in _prior_sources():
        try:
            payload = _load(source)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        for item in _collect_texts(payload):
            item["source"] = str(source.relative_to(ROOT))
            rows.append(item)
    return rows


def audit():
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    expected = prereg["fresh_dataset"]
    cases = dataset.get("cases") or []
    ids = [case.get("id") for case in cases]
    inputs = [_normalize(case.get("user_input")) for case in cases]
    families = Counter(case.get("scenario_family") for case in cases)
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
    proposition_ids = []
    for case in cases:
        for field in (
            "required_meaning_propositions",
            "forbidden_meaning_propositions",
        ):
            for proposition in case.get(field) or []:
                valid = (
                    isinstance(proposition, dict)
                    and proposition.get("id")
                    and proposition.get("description")
                    and isinstance(proposition.get("accepted_surfaces"), list)
                    and proposition.get("accepted_surfaces")
                )
                if not valid:
                    malformed_propositions.append(
                        {"case_id": case.get("id"), "field": field}
                    )
                elif field == "required_meaning_propositions":
                    proposition_ids.append(
                        f"{case.get('id')}::{proposition['id']}"
                    )

    internal_near_duplicates = []
    for left in range(len(cases)):
        for right in range(left + 1, len(cases)):
            ratio = SequenceMatcher(None, inputs[left], inputs[right]).ratio()
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
    for case, normalized in zip(cases, inputs):
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

    memory_policy_cases = [
        case
        for case in cases
        if case.get("scenario_family") == "memory_update_or_suppression"
    ]
    checks = {
        "schema_matches": dataset.get("schema")
        == "uruha_rightbrain_shared_final_plan_pilot_v63",
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
        "scenario_family_count_exact": len(families)
        == expected["scenario_family_count"],
        "scenario_family_set_exact": set(families)
        == set(expected["scenario_families"]),
        "cases_per_family_exact": all(
            families.get(family) == expected["cases_per_family"]
            for family in expected["scenario_families"]
        ),
        "case_ids_unique": len(ids) == len(set(ids)) and all(ids),
        "user_inputs_unique": len(inputs) == len(set(inputs)) and all(inputs),
        "required_fields_complete": not missing_fields,
        "required_propositions_nonempty": all(
            case.get("required_meaning_propositions") for case in cases
        ),
        "required_proposition_ids_unique": len(proposition_ids)
        == len(set(proposition_ids)),
        "proposition_contract_well_formed": not malformed_propositions,
        "memory_fixture_shape_valid": all(
            isinstance(case.get("memory_fixture"), list) for case in cases
        ),
        "memory_policy_cases_exact": len(memory_policy_cases) == 2,
        "memory_policy_fixtures_present": all(
            case.get("memory_fixture") for case in memory_policy_cases
        ),
        "private_suppression_case_exact": sum(
            bool(case.get("private_memory_terms")) for case in cases
        )
        == 1,
        "psyche_fixture_shape_valid": all(
            isinstance(case.get("psyche_fixture"), dict)
            and set(case["psyche_fixture"]) == {"mood", "trust"}
            for case in cases
        ),
        "maximum_reply_chars_valid": all(
            isinstance(case.get("maximum_reply_chars"), int)
            and 32 <= case["maximum_reply_chars"] <= 120
            for case in cases
        ),
        "internal_near_duplicate_count_zero": not internal_near_duplicates,
        "exact_prior_text_overlap_count_zero": not exact_overlaps,
        "external_near_duplicate_count_zero": not external_near_duplicates,
    }
    return {
        "schema": "uruha_rightbrain_shared_final_plan_dataset_audit_v63",
        "passed": all(checks.values()),
        "bindings": {
            "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
            "preregistration_sha256": _sha256(PREREG_PATH),
            "dataset_path": str(DATASET_PATH.relative_to(ROOT)),
            "dataset_sha256": _sha256(DATASET_PATH),
        },
        "counts": {
            "case_count": len(cases),
            "scenario_family_count": len(families),
            "required_meaning_proposition_count": sum(
                len(case["required_meaning_propositions"]) for case in cases
            ),
            "forbidden_meaning_proposition_count": sum(
                len(case["forbidden_meaning_propositions"]) for case in cases
            ),
            "memory_fixture_count": sum(
                len(case["memory_fixture"]) for case in cases
            ),
            "prior_source_count": len(_prior_sources()),
            "prior_text_count_scanned": len(prior),
            "internal_near_duplicate_count": len(internal_near_duplicates),
            "exact_prior_text_overlap_count": len(exact_overlaps),
            "external_near_duplicate_count": len(external_near_duplicates),
        },
        "family_counts": dict(sorted(families.items())),
        "checks": checks,
        "failures": {
            "missing_fields": missing_fields,
            "malformed_propositions": malformed_propositions,
            "internal_near_duplicates": internal_near_duplicates,
            "exact_prior_text_overlaps": exact_overlaps,
            "external_near_duplicates": external_near_duplicates,
        },
        "evidence_boundary": "This audit proves only structural completeness and no detected overlap in the scanned sources. It contains no plan capture, model output, ability score, or human-likeness evidence.",
    }


def _markdown(report):
    state = "PASS" if report["passed"] else "FAIL"
    counts = report["counts"]
    lines = [
        "# V63 全新資料建構稽核",
        "",
        f"**結果：{state}**",
        "",
        "| 檢查 | 數量 |",
        "|---|---:|",
        f"| 全新案例 | {counts['case_count']} |",
        f"| 情境類別 | {counts['scenario_family_count']} |",
        f"| 必要意思 | {counts['required_meaning_proposition_count']} |",
        f"| 禁止意思 | {counts['forbidden_meaning_proposition_count']} |",
        f"| 記憶項目 | {counts['memory_fixture_count']} |",
        f"| 掃描過去文字 | {counts['prior_text_count_scanned']} |",
        f"| 完全重複 | {counts['exact_prior_text_overlap_count']} |",
        f"| 高相似重複 | {counts['external_near_duplicate_count']} |",
        "",
        "本報告只證明題目形狀、類別平衡與未偵測到重複；尚未呼叫左腦或右腦，不能代表能力改善。",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    report = audit()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
