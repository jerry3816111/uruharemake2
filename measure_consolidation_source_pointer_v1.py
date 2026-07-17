#!/usr/bin/env python3
"""Measure exact-source pointer rereading under distractor delay."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import uruha_brain_mac as brain


ROOT = Path(__file__).resolve().parent
DATASET_PATH = (
    ROOT / "datasets" / "consolidation_source_pointer_v1.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports" / "consolidation_source_pointer_v1_baseline.json"
)
CONDITIONS = ("control", "treatment")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _encoded_source_ids(source_ids):
    return json.dumps(
        sorted(source_ids),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _pointer_metadata(case, source_ids, batch_id, timestamp):
    encoded = _encoded_source_ids(source_ids)
    metadata = {
        "source": "idle_consolidation",
        "timestamp": timestamp,
        "salience": 0.9,
        "last_accessed_at": timestamp,
        "decay_flag": False,
        "decay_multiplier": 1.0,
        "consolidation_batch_id": batch_id,
    }
    policy = case["pointer_policy"]
    if policy == "missing_pointer":
        return metadata
    if policy == "malformed_ids":
        metadata.update(
            {
                "source_episode_ids": "[not-valid-json",
                "source_episode_count": len(source_ids),
                "source_episode_ids_sha256": hashlib.sha256(
                    encoded.encode("utf-8")
                ).hexdigest(),
            }
        )
        return metadata
    metadata.update(
        {
            "source_episode_ids": encoded,
            "source_episode_count": len(source_ids),
            "source_episode_ids_sha256": (
                "0" * 64
                if policy == "invalid_digest"
                else hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            ),
        }
    )
    return metadata


def _base_working_memory(memory, question):
    candidates = []
    candidates.extend(memory._profile_candidates())
    candidates.extend(memory._short_term_candidates())
    candidates.extend(memory._recent_turn_candidates())
    candidates.extend(
        memory._query_collection_candidates(
            memory.episode_col,
            question,
            "episode",
            limit=brain.WORKING_MEMORY_RETRIEVAL_LIMIT,
        )
    )
    candidates.extend(
        memory._query_collection_candidates(
            memory.wisdom_col,
            question,
            "wisdom",
            limit=brain.WORKING_MEMORY_RETRIEVAL_LIMIT,
        )
    )
    candidates.extend(
        memory._query_collection_candidates(
            memory.procedural_col,
            question,
            "procedural",
            limit=brain.WORKING_MEMORY_RETRIEVAL_LIMIT,
        )
    )
    candidates.extend(
        memory._query_collection_candidates(
            memory.kb_col,
            question,
            "knowledge",
            limit=brain.WORKING_MEMORY_RETRIEVAL_LIMIT,
        )
    )
    return brain.umr.build_working_memory(
        question,
        candidates,
        working_memory_limit=brain.WORKING_MEMORY_LIMIT,
        scoring_profile=brain.WORKING_MEMORY_SCORING_PROFILE,
    )


def _populate_case(memory, case, global_count, local_count):
    now = datetime.datetime.now()
    batch_id = f"{case['case_id']}-batch"
    source_ids = [
        f"{case['case_id']}-source-{index}"
        for index in range(local_count + 1)
    ]
    ids = []
    documents = []
    metadatas = []
    source_utterances = [
        case["target_user_utterance"],
        *[
            case["local_distractor_template"]
            for _ in range(local_count)
        ],
    ]
    for index, (source_id, utterance) in enumerate(
        zip(source_ids, source_utterances)
    ):
        timestamp = (
            now - datetime.timedelta(days=40 - index)
        ).strftime("%Y-%m-%d %H:%M:%S")
        source_batch = (
            f"{batch_id}-mismatch"
            if case["pointer_policy"] == "wrong_batch"
            else batch_id
        )
        ids.append(source_id)
        documents.append(
            f"Time: {timestamp} | Intent: chat | Scene: casual | "
            f"User: {utterance} | Summary: | Uruha: noted"
        )
        metadatas.append(
            {
                "source": "turn_episode",
                "timestamp": timestamp,
                "consolidation_state": "consolidated",
                "consolidation_batch_id": source_batch,
                "decay_flag": True,
                "decay_multiplier": (
                    brain.CONSOLIDATED_EPISODE_DECAY_MULTIPLIER
                ),
            }
        )
    for index in range(global_count):
        timestamp = (
            now - datetime.timedelta(minutes=index)
        ).strftime("%Y-%m-%d %H:%M:%S")
        ids.append(f"{case['case_id']}-global-{index}")
        documents.append(
            f"Time: {timestamp} | Intent: chat | Scene: casual | "
            f"User: {case['global_distractor_template'].format(index=index)} "
            "| Summary: | Uruha: noted"
        )
        metadatas.append(
            {
                "source": "turn_episode",
                "timestamp": timestamp,
                "consolidation_state": "pending",
                "decay_flag": False,
                "decay_multiplier": 1.0,
            }
        )
    memory.episode_col.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    derived_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    pointer_metadata = _pointer_metadata(
        case,
        source_ids,
        batch_id,
        derived_timestamp,
    )
    if case["split"] == "unrelated":
        pointer_metadata.update(
            {
                "salience": 0.0,
                "timestamp": (
                    now - datetime.timedelta(days=90)
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "decay_flag": True,
                "decay_multiplier": 0.35,
            }
        )
    derived_id = f"{case['case_id']}-derived"
    memory.wisdom_col.add(
        ids=[derived_id],
        documents=[case["derived_text"]],
        metadatas=[pointer_metadata],
    )
    return {
        "target_source_id": source_ids[0],
        "source_ids": source_ids,
        "batch_id": batch_id,
        "derived_id": derived_id,
    }


def _source_evidence(items):
    evidence = []
    for item in items:
        for source in item.get("source_evidence") or []:
            evidence.append(source)
    return evidence


def _run_case(case, condition, global_count, local_count):
    original_db_path = brain.DB_PATH
    with tempfile.TemporaryDirectory(
        prefix="uruha_consolidation_source_pointer_"
    ) as temporary:
        brain.DB_PATH = temporary
        try:
            memory = brain.MemoryManager()
            setup = _populate_case(
                memory,
                case,
                global_count,
                local_count,
            )
            control_items = _base_working_memory(
                memory,
                case["question"],
            )
            if condition == "control":
                items = control_items
            elif condition == "treatment":
                attach = getattr(
                    memory,
                    "_attach_consolidation_source_evidence",
                    None,
                )
                if attach is None:
                    raise RuntimeError(
                        "Treatment runtime is not implemented"
                    )
                items = attach(case["question"], control_items)
            else:
                raise ValueError(condition)
            evidence = _source_evidence(items)
            top_level_ids = [
                item.get("memory_id") for item in items
            ]
            control_top_level_ids = [
                item.get("memory_id") for item in control_items
            ]
            evidence_ids = [
                item.get("memory_id") for item in evidence
            ]
            evidence_user_texts = [
                str(item.get("user_text") or "") for item in evidence
            ]
            pointer_audits = [
                item["source_pointer_audit"]
                for item in items
                if isinstance(item.get("source_pointer_audit"), dict)
            ]
            working_memory_summary = memory._working_memory_summary(items)
            target_hit = (
                setup["target_source_id"] in top_level_ids
                if condition == "control"
                else setup["target_source_id"] in evidence_ids
            )
            return {
                "case_id": case["case_id"],
                "split": case["split"],
                "language": case["language"],
                "pointer_policy": case["pointer_policy"],
                "expected_pointer_activation": case[
                    "expected_pointer_activation"
                ],
                "target_source_id": setup["target_source_id"],
                "derived_id": setup["derived_id"],
                "derived_selected": (
                    setup["derived_id"] in control_top_level_ids
                ),
                "top_level_selection_unchanged": (
                    top_level_ids == control_top_level_ids
                ),
                "source_evidence_ids": evidence_ids,
                "source_evidence_user_texts": evidence_user_texts,
                "source_evidence_count": len(evidence),
                "pointer_activated": bool(evidence),
                "source_pointer_audits": pointer_audits,
                "source_pointer_rejection_reasons": [
                    audit.get("reason")
                    for audit in pointer_audits
                    if audit.get("status") == "rejected"
                ],
                "target_source_hit": target_hit,
                "target_user_text_exact": (
                    case["target_user_utterance"]
                    in evidence_user_texts
                ),
                "target_user_text_in_working_memory_summary": (
                    case["target_user_utterance"]
                    in working_memory_summary
                ),
            }
        finally:
            brain.DB_PATH = original_db_path


def _summary(cases, condition):
    positives = [row for row in cases if row["split"] == "positive"]
    integrity = [row for row in cases if row["split"] == "integrity"]
    unrelated = [row for row in cases if row["split"] == "unrelated"]
    return {
        "condition": condition,
        "case_count": len(cases),
        "positive_case_count": len(positives),
        "positive_target_source_hits": sum(
            row["target_source_hit"] for row in positives
        ),
        "positive_target_source_recall": round(
            sum(row["target_source_hit"] for row in positives)
            / len(positives),
            4,
        ),
        "positive_pointer_activations": sum(
            row["pointer_activated"] for row in positives
        ),
        "positive_exact_user_text_hits": sum(
            row["target_user_text_exact"] for row in positives
        ),
        "positive_summary_exact_user_text_hits": sum(
            row["target_user_text_in_working_memory_summary"]
            for row in positives
        ),
        "integrity_pointer_activations": sum(
            row["pointer_activated"] for row in integrity
        ),
        "unrelated_pointer_activations": sum(
            row["pointer_activated"] for row in unrelated
        ),
        "wrong_source_injections": sum(
            row["pointer_activated"] and not row["target_source_hit"]
            for row in positives
        ),
        "top_level_selection_unchanged_count": sum(
            row["top_level_selection_unchanged"] for row in cases
        ),
        "maximum_source_evidence_count": max(
            row["source_evidence_count"] for row in cases
        ),
    }


def measure(condition):
    if condition not in CONDITIONS:
        raise ValueError(condition)
    runtime_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    global_count = int(dataset["global_distractor_count"])
    local_count = int(dataset["local_distractor_count"])
    cases = [
        _run_case(case, condition, global_count, local_count)
        for case in dataset["cases"]
    ]
    return {
        "schema": "uruha_consolidation_source_pointer_measurement_v1",
        "condition": condition,
        "runtime_commit": runtime_commit,
        "runtime_sha256": _sha256(ROOT / "uruha_brain_mac.py"),
        "dataset_sha256": _sha256(DATASET_PATH),
        "temporary_chroma_per_case": True,
        "external_model_calls": 0,
        "gold_or_expected_answer_passed_to_runtime": False,
        "summary": _summary(cases, condition),
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--condition",
        choices=CONDITIONS,
        default="control",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = measure(args.condition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "condition": report["condition"],
                "runtime_commit": report["runtime_commit"],
                "summary": report["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
