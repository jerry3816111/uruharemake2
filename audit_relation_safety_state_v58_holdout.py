#!/usr/bin/env python3
"""Audit V58 independent-holdout construction without state/model evaluation."""

import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from action_selective_deliberation_v37 import FRAME_TO_CALL
from grounded_commitment_classifier_v42 import ground_supported_targets
from precise_target_mentions_v52 import audit_precise_event_maps


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "relation_safety_state_v58_holdout.json"
SOURCE_PATH = ROOT / "datasets" / "sources" / "tatoeba_jpn_v58_selected.tsv"
MENTION_CONFIG_PATH = ROOT / "configs" / "relation_bound_event_graph_v56_holdout_preregistration.json"
DEFAULT_JSON = ROOT / "reports" / "relation_safety_state_v58_holdout_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "relation_safety_state_v58_holdout_audit.md"
NEAR_DUPLICATE_THRESHOLD = 0.94


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _target_id(frame):
    return f"{frame['domain']}.{frame['value']}"


def _canonical_call(call):
    return json.dumps(call, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _walk_user_inputs(value):
    if isinstance(value, dict):
        if isinstance(value.get("user_input"), str):
            yield value["user_input"]
        for child in value.values():
            yield from _walk_user_inputs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_user_inputs(child)


def _historical_inputs():
    rows = []
    inventory = []
    for path in sorted((ROOT / "datasets").glob("*.json")):
        if path == DATASET_PATH:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        values = list(_walk_user_inputs(payload))
        if values:
            relative = str(path.relative_to(ROOT))
            rows.extend((text, relative) for text in values)
            inventory.append(
                {
                    "path": relative,
                    "sha256": _sha256(path),
                    "user_input_count": len(values),
                }
            )
    return rows, inventory


def _source_rows(path):
    rows = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        fields = raw.split("\t")
        if len(fields) != 6:
            raise ValueError(f"{path.name} must have six fields per row")
        sentence_id, language, text, username, added, modified = fields
        rows[int(sentence_id)] = {
            "language": language,
            "text": text,
            "username": username,
            "date_added": added,
            "date_modified": modified,
        }
    return rows


def _normalize(text):
    return re.sub(r"[\s、。！？!?「」『』・]", "", str(text or ""))


def _nearest_historical(case_id, text, historical_rows):
    normalized = _normalize(text)
    best = {"ratio": 0.0, "text": "", "path": ""}
    for old_text, path in historical_rows:
        ratio = SequenceMatcher(None, normalized, _normalize(old_text)).ratio()
        if ratio > best["ratio"]:
            best = {"ratio": ratio, "text": old_text, "path": path}
    return {"case_id": case_id, "user_input": text, **best}


def audit(dataset, mention_patterns):
    ontology = load_v47_anchor_ontology()
    source_rows = _source_rows(SOURCE_PATH)
    old_source_ids = set()
    old_source_inventory = []
    for path in sorted((ROOT / "datasets" / "sources").glob("tatoeba_jpn_v*_selected.tsv")):
        if path == SOURCE_PATH:
            continue
        rows = _source_rows(path)
        old_source_ids.update(rows)
        old_source_inventory.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": _sha256(path),
                "sentence_count": len(rows),
            }
        )
    historical_rows, historical_inventory = _historical_inputs()
    historical_lookup = {}
    for text, path in historical_rows:
        historical_lookup.setdefault(text, []).append(path)

    candidate_rows = []
    candidate_mismatches = []
    evidence_errors = []
    call_errors = []
    source_errors = []
    old_source_id_overlaps = []
    exact_overlap_rows = []
    duplicate_inputs = []
    nearest_rows = []
    seen_inputs = set()
    commitment_counts = Counter()
    target_counts = Counter()

    for case in dataset["cases"]:
        text = case["user_input"]
        if text in seen_inputs:
            duplicate_inputs.append(case["id"])
        seen_inputs.add(text)
        if text in historical_lookup:
            exact_overlap_rows.append(
                {
                    "case_id": case["id"],
                    "user_input": text,
                    "historical_paths": historical_lookup[text],
                }
            )
        nearest_rows.append(_nearest_historical(case["id"], text, historical_rows))

        candidates = ground_supported_targets(text, ontology)
        candidate_rows.append(
            {"case_id": case["id"], "user_input": text, "candidates": candidates}
        )
        observed = {candidate["target_id"] for candidate in candidates}
        expected = {_target_id(frame) for frame in case["expected_frames"]}
        if observed != expected:
            candidate_mismatches.append(
                {
                    "case_id": case["id"],
                    "expected": sorted(expected),
                    "observed": sorted(observed),
                }
            )

        for frame in case["expected_frames"]:
            target_id = _target_id(frame)
            commitment_counts[frame["commitment"]] += 1
            target_counts[target_id] += 1
            if not frame["evidence_options"] or not all(
                evidence in text for evidence in frame["evidence_options"]
            ):
                evidence_errors.append(
                    {"case_id": case["id"], "target_id": target_id}
                )

        expected_calls = [
            FRAME_TO_CALL[(frame["domain"], frame["value"])]
            for frame in case["expected_frames"]
            if frame["commitment"] == "requested"
        ]
        if list(map(_canonical_call, expected_calls)) != list(
            map(_canonical_call, case["expected_calls"])
        ):
            call_errors.append(case["id"])
        if case["expected_no_action"] != (not expected_calls):
            call_errors.append(case["id"])
        policy = "execute_exact_plan" if expected_calls else "withhold_action"
        if case["expected_execution_policy"] != policy:
            call_errors.append(case["id"])

        if case["source_type"] == "external_exact":
            provenance = case["source_provenance"]
            sentence_id = provenance.get("sentence_id")
            source = source_rows.get(sentence_id)
            if sentence_id in old_source_ids:
                old_source_id_overlaps.append(sentence_id)
            if (
                source is None
                or source["language"] != "jpn"
                or source["text"] != text
                or source["username"] != provenance.get("username")
                or source["date_added"] != provenance.get("date_added")
                or source["date_modified"] != provenance.get("date_modified")
                or not provenance.get("sentence_url")
            ):
                source_errors.append(case["id"])

    representation = audit_precise_event_maps(candidate_rows, mention_patterns)
    source_counts = Counter(case["source_type"] for case in dataset["cases"])
    family_counts = Counter(case["family"] for case in dataset["cases"])
    controlled_families = {
        family: count
        for family, count in family_counts.items()
        if family.startswith("controlled_")
    }
    near_duplicates = [
        row for row in nearest_rows if row["ratio"] >= NEAR_DUPLICATE_THRESHOLD
    ]
    action_cases = sum(not case["expected_no_action"] for case in dataset["cases"])
    no_action_cases = sum(case["expected_no_action"] for case in dataset["cases"])
    checks = {
        "case_count_64": len(dataset["cases"]) == 64 == dataset["case_count"],
        "external_exact_count_16": source_counts["external_exact"] == 16,
        "controlled_compositional_count_48": source_counts[
            "controlled_compositional"
        ]
        == 48,
        "four_controlled_families_have_twelve": (
            len(controlled_families) == 4
            and all(count == 12 for count in controlled_families.values())
        ),
        "action_and_no_action_controls_present": action_cases == 13 and no_action_cases == 51,
        "candidate_target_sets_exact": not candidate_mismatches,
        "evidence_substrings_exact": not evidence_errors,
        "ordered_expected_calls_derived_mechanically": not call_errors,
        "external_rows_match_snapshot": not source_errors,
        "no_reused_prior_external_sentence_ids": not old_source_id_overlaps,
        "no_duplicate_holdout_inputs": not duplicate_inputs,
        "no_exact_historical_input_overlap": not exact_overlap_rows,
        "no_near_duplicate_historical_input": not near_duplicates,
        "construction_provenance_is_honest": (
            not dataset["construction"]["external_exact_model_generation_used"]
            and dataset["construction"]["controlled_model_assistance_used"]
            and not dataset["construction"]["controlled_human_blind_review_used"]
            and not dataset["construction"]["evaluation_model_inference_used"]
            and not dataset["construction"]["v56_or_v58_state_evaluation_used"]
            and not dataset["construction"]["gold_visible_to_state_or_compiler"]
        ),
        "base_pretraining_exclusion_not_overclaimed": not dataset["construction"][
            "base_model_pretraining_exclusion_guaranteed"
        ],
        "mention_coverage_100_percent": representation[
            "grounded_occurrence_mention_coverage"
        ]
        == 1.0,
        "mention_fallback_zero": representation["fallback_occurrence_count"] == 0,
        "mention_inside_evidence_100_percent": representation[
            "mention_inside_predicate_evidence_rate"
        ]
        == 1.0,
        "cross_target_mention_overlap_zero": representation[
            "cross_target_mention_overlap_count"
        ]
        == 0,
    }
    return {
        "schema": "uruha_relation_safety_state_holdout_audit_v58",
        "evidence_status": "construction_only_no_state_or_model_evaluation",
        "dataset_sha256": _sha256(DATASET_PATH),
        "source_snapshot_sha256": _sha256(SOURCE_PATH),
        "case_count": len(dataset["cases"]),
        "target_count": sum(len(row["candidates"]) for row in candidate_rows),
        "distinct_target_count": len(target_counts),
        "target_counts": dict(sorted(target_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "commitment_counts": dict(sorted(commitment_counts.items())),
        "action_case_count": action_cases,
        "no_action_case_count": no_action_cases,
        "historical_exact_input_overlap_count": len(exact_overlap_rows),
        "historical_near_duplicate_count": len(near_duplicates),
        "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
        "maximum_historical_similarity": max(row["ratio"] for row in nearest_rows),
        "prior_external_source_id_overlap_count": len(old_source_id_overlaps),
        "historical_dataset_inventory": historical_inventory,
        "prior_source_inventory": old_source_inventory,
        "candidate_mismatches": candidate_mismatches,
        "evidence_errors": evidence_errors,
        "call_errors": sorted(set(call_errors)),
        "source_errors": source_errors,
        "old_source_id_overlaps": sorted(set(old_source_id_overlaps)),
        "exact_historical_overlaps": exact_overlap_rows,
        "near_duplicate_rows": sorted(
            near_duplicates, key=lambda row: row["ratio"], reverse=True
        ),
        "nearest_historical_rows_top10": sorted(
            nearest_rows, key=lambda row: row["ratio"], reverse=True
        )[:10],
        "duplicate_inputs": duplicate_inputs,
        "representation_audit": representation,
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "passed": all(checks.values()),
    }


def render_markdown(report):
    lines = [
        "# V58 relation-safety independent-holdout construction audit",
        "",
        "This audit performs no V56/V58 state evaluation and no model inference.",
        "",
        f"- Cases / grounded targets: {report['case_count']} / {report['target_count']}",
        f"- External exact / controlled: {report['source_counts']['external_exact']} / {report['source_counts']['controlled_compositional']}",
        f"- Action / no-action cases: {report['action_case_count']} / {report['no_action_case_count']}",
        f"- Exact historical overlaps: {report['historical_exact_input_overlap_count']}",
        f"- Near duplicates at >= {report['near_duplicate_threshold']:.0%}: {report['historical_near_duplicate_count']}",
        f"- Prior Tatoeba source-ID overlaps: {report['prior_external_source_id_overlap_count']}",
        f"- Construction gate: {'PASS' if report['passed'] else 'FAIL'}",
        "",
        "## Families",
        "",
        "| Family | Cases |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {name} | {count} |" for name, count in report["family_counts"].items()
    )
    lines.extend(["", "## Checks", "", "| Check | Result |", "|---|---|"])
    lines.extend(
        f"| {name} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in report["checks"].items()
    )
    lines.append("")
    return "\n".join(lines)


def main():
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    mention_config = json.loads(MENTION_CONFIG_PATH.read_text(encoding="utf-8"))
    report = audit(dataset, mention_config["target_mention_patterns"])
    DEFAULT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    DEFAULT_MARKDOWN.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "failed_checks": report["failed_checks"],
                "case_count": report["case_count"],
                "target_count": report["target_count"],
                "maximum_historical_similarity": report[
                    "maximum_historical_similarity"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
