#!/usr/bin/env python3
"""Rebuild exposed LoCoMo development cases with a turn-text-only oracle."""

from __future__ import annotations

import json
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_6_corrected_oracle_preregistration.json"
OUTPUT = ROOT / "configs/source_preserving_memory_projection_v2_6_corrected_oracle_cases.json"


def load_preregistration(path=PREREG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def session_turn_texts(conversation, session_key):
    return [
        v25.turn_text(turn)
        for turn in conversation[session_key]
        if v25.turn_text(turn)
    ]


def answer_in_turn_text(conversation, session_key, answer):
    needle = str(answer).casefold()
    return bool(needle) and any(
        needle in text.casefold() for text in session_turn_texts(conversation, session_key)
    )


def choose_hard_negative(sample, qa_index, question, answer, evidence_sessions, prereg):
    conversation = sample["conversation"]
    candidates = []
    for key in v25.session_keys(conversation):
        if key in evidence_sessions:
            continue
        complete = v25.serialize_session(conversation, key)
        if len(complete) > prereg["controlled_variables"]["maximum_session_characters"]:
            continue
        if answer_in_turn_text(conversation, key, answer):
            continue
        candidates.append(
            (
                -v25.lexical_overlap(question, complete),
                v25.negative_tie_digest(sample["sample_id"], qa_index, key, {
                    "case_selection": {
                        "selection_salt": prereg["controlled_variables"]["selection_salt"]
                    }
                }),
                key,
                complete,
            )
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    _, _, key, complete = candidates[0]
    return key, complete


def eligible_cases_for_sample(sample, prereg):
    controlled = prereg["controlled_variables"]
    conversation = sample["conversation"]
    selection_prereg = {
        "case_selection": {"selection_salt": controlled["selection_salt"]}
    }
    eligible = []
    for qa_index, qa in enumerate(sample.get("qa") or []):
        if qa.get("category") != controlled["official_category"]:
            continue
        question = str(qa.get("question") or "").strip()
        answer = str(qa.get("answer") or "").strip()
        evidence = list(qa.get("evidence") or [])
        if not question or not answer or not evidence:
            continue
        if not v25.all_evidence_ids_exist(conversation, evidence):
            continue
        target_keys = v25.evidence_session_keys(conversation, evidence)
        if len(target_keys) != 1:
            continue
        target_key = target_keys[0]
        target_complete = v25.serialize_session(conversation, target_key)
        if len(target_complete) > controlled["maximum_session_characters"]:
            continue
        if not answer_in_turn_text(conversation, target_key, answer):
            continue
        negative = choose_hard_negative(
            sample, qa_index, question, answer, set(target_keys), prereg
        )
        if negative is None:
            continue
        negative_key, negative_complete = negative
        eligible.append(
            {
                "qa_index": qa_index,
                "question": question,
                "answer": answer,
                "evidence": evidence,
                "all_evidence_ids_exist": True,
                "evidence_session_count": len(target_keys),
                "target_key": target_key,
                "target_complete": target_complete,
                "negative_key": negative_key,
                "negative_complete": negative_complete,
                "selection_digest": v25.case_digest(
                    sample["sample_id"], qa_index, question, selection_prereg
                ),
            }
        )
    return sorted(eligible, key=lambda row: row["selection_digest"])


def corrected_record_manifest(sample, session_key, complete, question, answer):
    record = v25.record_manifest(sample, session_key, complete, question, answer)
    conversation = sample["conversation"]
    selected_texts = [
        v25.turn_text(conversation[session_key][index])
        for index in record["projection_source_turn_indices"]
    ]
    projected_turn_text = "\n".join(selected_texts)
    record["contains_answer_complete"] = answer_in_turn_text(
        conversation, session_key, answer
    )
    record["contains_answer_projection"] = answer.casefold() in projected_turn_text.casefold()
    record["membership_oracle"] = "original_dialogue_turn_text_only_v1"
    return record


def build_manifest(data, prereg):
    by_id = {str(row["sample_id"]): row for row in data}
    exposed_ids = prereg["controlled_variables"]["exposed_sample_ids"]
    exposed = [by_id[sample_id] for sample_id in exposed_ids]
    per_sample = prereg["controlled_variables"]["cases_per_conversation"]
    cases = []
    for sample in exposed:
        eligible = eligible_cases_for_sample(sample, prereg)
        if len(eligible) < per_sample:
            raise ValueError(
                f"exposed conversation {sample['sample_id']} has only {len(eligible)} corrected cases"
            )
        for row in eligible[:per_sample]:
            cases.append(
                {
                    "case_id": f"locomo-v2-6-{sample['sample_id']}-{row['qa_index']}",
                    "sample_id": str(sample["sample_id"]),
                    "qa_index": row["qa_index"],
                    "official_category": prereg["controlled_variables"][
                        "official_category"
                    ],
                    "question_sha256": v25.text_sha256(row["question"]),
                    "answer_sha256": v25.text_sha256(row["answer"]),
                    "evidence_ids_sha256": v25.canonical_sha256(row["evidence"]),
                    "evidence_id_count": len(row["evidence"]),
                    "all_evidence_ids_exist": row["all_evidence_ids_exist"],
                    "evidence_session_count": row["evidence_session_count"],
                    "target": corrected_record_manifest(
                        sample,
                        row["target_key"],
                        row["target_complete"],
                        row["question"],
                        row["answer"],
                    ),
                    "hard_negative": corrected_record_manifest(
                        sample,
                        row["negative_key"],
                        row["negative_complete"],
                        row["question"],
                        row["answer"],
                    ),
                }
            )
    return {
        "schema": "uruha_source_preserving_memory_projection_corrected_oracle_cases_v2_6",
        "status": "frozen_exposed_development_before_projection_revision",
        "experiment_id": prereg["experiment_id"],
        "source": {
            "dataset_sha256": prereg["controlled_variables"]["official_dataset_sha256"]
        },
        "exposed_sample_ids": exposed_ids,
        "reserve_sample_access_count": 0,
        "case_count": len(cases),
        "case_ids_sha256": v25.canonical_sha256([case["case_id"] for case in cases]),
        "contains_official_text": False,
        "contains_official_answers": False,
        "construction_model_calls": 0,
        "cases": cases,
    }


def validate_gates(manifest, prereg):
    gates = prereg["construction_gates"]
    cases = manifest["cases"]
    per_sample = {}
    for case in cases:
        per_sample[case["sample_id"]] = per_sample.get(case["sample_id"], 0) + 1
    checks = {
        "question_count_equals": manifest["case_count"] == gates["question_count_equals"],
        "cases_per_exposed_conversation_equals": sorted(per_sample.values())
        == [gates["cases_per_exposed_conversation_equals"]]
        * len(prereg["controlled_variables"]["exposed_sample_ids"]),
        "all_target_answers_exist_in_original_turn_text": all(
            case["target"]["contains_answer_complete"] for case in cases
        ),
        "all_hard_negative_answers_absent_from_original_turn_text": all(
            not case["hard_negative"]["contains_answer_complete"] for case in cases
        ),
        "all_official_evidence_ids_exist": all(
            case["all_evidence_ids_exist"] for case in cases
        ),
        "all_official_evidence_for_case_belongs_to_one_session": all(
            case["evidence_session_count"] == 1 for case in cases
        ),
        "manifest_contains_official_text": manifest["contains_official_text"]
        is gates["manifest_contains_official_text"],
        "manifest_contains_official_answers": manifest["contains_official_answers"]
        is gates["manifest_contains_official_answers"],
        "reserve_sample_access_count_equals": manifest["reserve_sample_access_count"]
        == gates["reserve_sample_access_count_equals"],
        "model_calls_equal": manifest["construction_model_calls"]
        == gates["model_calls_equal"],
    }
    if not all(checks.values()):
        raise ValueError(
            "corrected construction gates failed: "
            + ", ".join(name for name, passed in checks.items() if not passed)
        )
    return checks


def main():
    if OUTPUT.exists():
        raise SystemExit("V2.6 corrected case manifest already exists")
    prereg = load_preregistration()
    base = v25.load_preregistration()
    data = v25.ensure_official_dataset(base)
    manifest = build_manifest(data, prereg)
    manifest["construction_gates"] = validate_gates(manifest, prereg)
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": v25.file_sha256(OUTPUT),
                "case_count": manifest["case_count"],
                "projection_answer_retention_count": sum(
                    case["target"]["contains_answer_projection"]
                    for case in manifest["cases"]
                ),
                "reserve_sample_access_count": 0,
                "model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
