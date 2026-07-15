#!/usr/bin/env python3
"""Audit the V52 fresh holdout construction without calling a model."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from action_selective_deliberation_v37 import FRAME_TO_CALL
from grounded_commitment_classifier_v42 import ground_supported_targets
from precise_target_mentions_v52 import audit_precise_event_maps


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "precise_target_mentions_v52_holdout.json"
SOURCE_PATH = ROOT / "datasets" / "sources" / "tatoeba_jpn_v52_selected.tsv"
V52_CONFIG_PATH = ROOT / "configs" / "precise_target_mentions_v52_preregistration.json"
DEFAULT_JSON = ROOT / "reports" / "precise_target_mentions_v52_holdout_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "precise_target_mentions_v52_holdout_audit.md"


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
            rows.extend((text, str(path.relative_to(ROOT))) for text in values)
            inventory.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": _sha256(path),
                    "user_input_count": len(values),
                }
            )
    return rows, inventory


def _source_rows():
    rows = {}
    for raw in SOURCE_PATH.read_text(encoding="utf-8").splitlines():
        fields = raw.split("\t")
        if len(fields) != 6:
            raise ValueError("Tatoeba selected snapshot must have six fields per row")
        sentence_id, language, text, username, added, modified = fields
        rows[int(sentence_id)] = {
            "language": language,
            "text": text,
            "username": username,
            "date_added": added,
            "date_modified": modified,
        }
    return rows


def audit(dataset, mention_patterns):
    ontology = load_v47_anchor_ontology()
    source_rows = _source_rows()
    historical_rows, historical_inventory = _historical_inputs()
    historical_lookup = {}
    for text, path in historical_rows:
        historical_lookup.setdefault(text, []).append(path)

    candidate_rows = []
    candidate_mismatches = []
    evidence_errors = []
    call_errors = []
    source_errors = []
    overlap_rows = []
    seen_inputs = set()
    duplicate_inputs = []
    commitment_counts = Counter()

    for case in dataset["cases"]:
        text = case["user_input"]
        if text in seen_inputs:
            duplicate_inputs.append(case["id"])
        seen_inputs.add(text)
        if text in historical_lookup:
            overlap_rows.append(
                {
                    "case_id": case["id"],
                    "user_input": text,
                    "historical_paths": historical_lookup[text],
                }
            )

        candidates = ground_supported_targets(text, ontology)
        candidate_rows.append(
            {
                "case_id": case["id"],
                "user_input": text,
                "candidates": candidates,
            }
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
            commitment_counts[frame["commitment"]] += 1
            if not frame["evidence_options"] or not all(
                evidence in text for evidence in frame["evidence_options"]
            ):
                evidence_errors.append(
                    {"case_id": case["id"], "target_id": _target_id(frame)}
                )
        expected_calls = [
            FRAME_TO_CALL[(frame["domain"], frame["value"])]
            for frame in case["expected_frames"]
            if frame["commitment"] == "requested"
        ]
        if sorted(map(_canonical_call, expected_calls)) != sorted(
            map(_canonical_call, case["expected_calls"])
        ):
            call_errors.append(case["id"])
        if case["expected_no_action"] != (not expected_calls):
            call_errors.append(case["id"])

        if case["source_type"] == "external_exact":
            provenance = case["source_provenance"]
            source = source_rows.get(provenance.get("sentence_id"))
            if (
                source is None
                or source["language"] != "jpn"
                or source["text"] != text
                or source["username"] != provenance.get("username")
                or not provenance.get("sentence_url")
            ):
                source_errors.append(case["id"])

    representation = audit_precise_event_maps(candidate_rows, mention_patterns)
    source_counts = Counter(case["source_type"] for case in dataset["cases"])
    family_counts = Counter(case["family"] for case in dataset["cases"])
    checks = {
        "case_count_64": len(dataset["cases"]) == 64 == dataset["case_count"],
        "external_exact_count_24": source_counts["external_exact"] == 24,
        "controlled_authored_count_40": source_counts["controlled_authored"] == 40,
        "all_controlled_families_have_five": all(
            count == 5
            for family, count in family_counts.items()
            if family.startswith("controlled_")
        ),
        "candidate_target_sets_exact": not candidate_mismatches,
        "evidence_substrings_exact": not evidence_errors,
        "expected_calls_derived_mechanically": not call_errors,
        "external_rows_match_snapshot": not source_errors,
        "no_duplicate_holdout_inputs": not duplicate_inputs,
        "no_exact_historical_input_overlap": not overlap_rows,
        "construction_used_no_model": not dataset["construction"][
            "model_generation_used"
        ]
        and not dataset["construction"]["model_inference_used"],
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
        "schema": "uruha_precise_target_mentions_holdout_audit_v52",
        "evidence_status": "construction_only_no_model_inference",
        "dataset_sha256": _sha256(DATASET_PATH),
        "source_snapshot_sha256": _sha256(SOURCE_PATH),
        "case_count": len(dataset["cases"]),
        "target_count": sum(len(row["candidates"]) for row in candidate_rows),
        "source_counts": dict(sorted(source_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "commitment_counts": dict(sorted(commitment_counts.items())),
        "historical_input_count": len(historical_rows),
        "historical_dataset_inventory": historical_inventory,
        "candidate_mismatches": candidate_mismatches,
        "evidence_errors": evidence_errors,
        "call_errors": sorted(set(call_errors)),
        "source_errors": source_errors,
        "duplicate_input_case_ids": duplicate_inputs,
        "historical_exact_overlaps": overlap_rows,
        "representation_audit": representation,
        "checks": checks,
        "passed": all(checks.values()),
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def render_markdown(report):
    lines = [
        "# V52 fresh holdout construction audit",
        "",
        "No model was called while constructing or auditing this dataset.",
        "",
        f"- Cases / grounded targets: `{report['case_count']}` / `{report['target_count']}`.",
        f"- External exact / controlled authored: `{report['source_counts']['external_exact']}` / "
        f"`{report['source_counts']['controlled_authored']}`.",
        f"- Historical exact input overlaps: `{len(report['historical_exact_overlaps'])}`.",
        f"- Mention coverage / fallback / cross-target overlap: "
        f"`{report['representation_audit']['grounded_occurrence_mention_coverage']}` / "
        f"`{report['representation_audit']['fallback_occurrence_count']}` / "
        f"`{report['representation_audit']['cross_target_mention_overlap_count']}`.",
        f"- Construction gate passed: `{report['passed']}`.",
        "- Tatoeba project freshness does not guarantee exclusion from base-model pretraining.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    v52_config = json.loads(V52_CONFIG_PATH.read_text(encoding="utf-8"))
    report = audit(dataset, v52_config["causal_change"]["target_mention_patterns"])
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "failed_checks": report["failed_checks"],
                "case_count": report["case_count"],
                "target_count": report["target_count"],
            },
            indent=2,
        )
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
