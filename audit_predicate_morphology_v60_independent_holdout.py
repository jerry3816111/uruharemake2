#!/usr/bin/env python3
"""Audit V60 holdout construction without running V59, V60, compiler, or a model."""

import ast
import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from action_candidate_perception_v47 import load_v47_anchor_ontology
from grounded_commitment_classifier_v42 import ground_supported_targets


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "predicate_morphology_v60_independent_holdout_construction_preregistration.json"
)
DATASET_PATH = ROOT / "datasets" / "predicate_morphology_v60_independent_holdout.json"
SOURCE_PATH = ROOT / "datasets" / "sources" / "tatoeba_jpn_v60_selected.tsv"
DEFAULT_JSON = ROOT / "reports" / "predicate_morphology_v60_independent_holdout_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "predicate_morphology_v60_independent_holdout_audit.md"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(text):
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    return re.sub(r"[^0-9a-zぁ-ゖァ-ヺー一-龯]", "", normalized)


def _target_id(frame):
    return f"{frame['domain']}.{frame['value']}"


def _json_strings(value):
    if isinstance(value, str):
        if len(value) >= 8:
            yield value
        return
    if isinstance(value, dict):
        for child in value.values():
            yield from _json_strings(child)
        return
    if isinstance(value, list):
        for child in value:
            yield from _json_strings(child)


def _historical_texts(config):
    texts = []
    exclusion = config["historical_exclusion"]
    paths = {ROOT / relative for relative in exclusion["exclude_exact_text_from"]}
    for pattern in exclusion.get("exclude_exact_text_from_globs", []):
        paths.update(ROOT.glob(pattern))
    paths.discard(DATASET_PATH)
    for path in sorted(paths):
        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            texts.extend(_json_strings(payload))
        elif path.suffix == ".py":
            tree = ast.parse(path.read_text(encoding="utf-8"))
            texts.extend(
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and len(node.value) >= 8
            )
    return texts


def audit(dataset, config):
    totals = config["frozen_totals"]
    cases = dataset["cases"]
    ontology = load_v47_anchor_ontology()
    selected_ids = set(config["external_source"]["selected_sentence_ids"])
    source_rows = {
        int(line.split("\t", 1)[0])
        for line in SOURCE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    historical_ids = {
        int(line.split("\t", 1)[0])
        for path in (ROOT / "datasets" / "sources").glob("tatoeba_jpn_v*.tsv")
        if path != SOURCE_PATH
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    grounding_failures = []
    for case in cases:
        expected = {_target_id(frame) for frame in case["expected_frames"]}
        grounded = {
            row["target_id"]
            for row in ground_supported_targets(case["user_input"], ontology)
        }
        if grounded != expected:
            grounding_failures.append(
                {
                    "case_id": case["id"],
                    "expected": sorted(expected),
                    "grounded": sorted(grounded),
                }
            )

    historical = _historical_texts(config)
    threshold = config["historical_exclusion"][
        "normalized_near_duplicate_similarity_at_or_above"
    ]
    exact_overlaps = []
    near_overlaps = []
    normalized_historical = [(_normalize(text), text) for text in historical]
    for case in cases:
        normalized = _normalize(case["user_input"])
        for old_normalized, old_text in normalized_historical:
            if normalized == old_normalized:
                exact_overlaps.append(
                    {"case_id": case["id"], "historical_text": old_text}
                )
                break
            similarity = SequenceMatcher(None, normalized, old_normalized).ratio()
            if similarity >= threshold:
                near_overlaps.append(
                    {
                        "case_id": case["id"],
                        "similarity": similarity,
                        "historical_text": old_text,
                    }
                )
                break

    internal_duplicates = []
    seen = {}
    for case in cases:
        normalized = _normalize(case["user_input"])
        if normalized in seen:
            internal_duplicates.append([seen[normalized], case["id"]])
        seen[normalized] = case["id"]

    action_cases = sum(bool(case["expected_calls"]) for case in cases)
    target_count = sum(len(case["expected_frames"]) for case in cases)
    checks = {
        "source_snapshot_rows": source_rows == selected_ids,
        "historical_source_ids": not (selected_ids & historical_ids),
        "case_count": len(cases) == totals["case_count"],
        "target_count": target_count == totals["grounded_target_count"],
        "action_case_count": action_cases == totals["expected_action_case_count"],
        "no_action_case_count": len(cases) - action_cases
        == totals["expected_no_action_case_count"],
        "unique_case_ids": len({case["id"] for case in cases}) == len(cases),
        "ontology_grounding": not grounding_failures,
        "historical_exact_overlap": not exact_overlaps,
        "historical_near_overlap": not near_overlaps,
        "internal_exact_duplicates": not internal_duplicates,
        "no_evaluation_model_inference": not dataset["construction"][
            "evaluation_model_inference_used"
        ],
        "no_v59_evaluation": not dataset["construction"]["v59_state_evaluation_used"],
        "no_v60_evaluation": not dataset["construction"]["v60_state_evaluation_used"],
        "no_compiler_evaluation": not dataset["construction"][
            "compiler_evaluation_used"
        ],
    }
    return {
        "schema": "uruha_predicate_morphology_independent_holdout_audit_v60",
        "dataset_sha256": _sha256(DATASET_PATH),
        "selected_source_sha256": _sha256(SOURCE_PATH),
        "case_count": len(cases),
        "target_count": target_count,
        "action_case_count": action_cases,
        "no_action_case_count": len(cases) - action_cases,
        "grounding_failures": grounding_failures,
        "historical_exact_overlaps": exact_overlaps,
        "historical_near_overlaps": near_overlaps,
        "internal_exact_duplicates": internal_duplicates,
        "checks": checks,
        "passed": all(checks.values()),
        "v59_state_evaluated": False,
        "v60_state_evaluated": False,
        "compiler_evaluated": False,
        "model_calls": 0,
    }


def render_markdown(report):
    return "\n".join(
        [
            "# V60 independent holdout construction audit",
            "",
            f"- Cases / grounded targets: {report['case_count']} / {report['target_count']}",
            f"- Action / no-action cases: {report['action_case_count']} / {report['no_action_case_count']}",
            f"- Grounding failures: {len(report['grounding_failures'])}",
            f"- Historical exact / near overlaps: {len(report['historical_exact_overlaps'])} / {len(report['historical_near_overlaps'])}",
            f"- Internal duplicates: {len(report['internal_exact_duplicates'])}",
            f"- Model calls: {report['model_calls']}",
            f"- Construction audit: {'PASS' if report['passed'] else 'FAIL'}",
            "",
            "No V59 state, V60 state, compiler output, or model answer was inspected.",
            "",
        ]
    )


def main():
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = audit(load(DATASET_PATH), load(CONFIG_PATH))
    DEFAULT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    DEFAULT_MARKDOWN.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "case_count": report["case_count"],
                "target_count": report["target_count"],
                "grounding_failures": report["grounding_failures"],
                "exact_overlaps": len(report["historical_exact_overlaps"]),
                "near_overlaps": len(report["historical_near_overlaps"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
