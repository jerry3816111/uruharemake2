#!/usr/bin/env python3
"""Build the frozen LoCoMo V2.5 case manifest without exposing source text."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_5_locomo_fresh_holdout_preregistration.json"
DATASET = ROOT / "external_data/locomo/locomo10.json"
OUTPUT = ROOT / "configs/source_preserving_memory_projection_v2_5_locomo_cases.json"


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def canonical_sha256(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def content_tokens(value):
    return set(re.findall(r"[\w']+", str(value).casefold(), flags=re.UNICODE))


def lexical_overlap(question, text):
    query = content_tokens(question)
    source = content_tokens(text)
    if not query or not source:
        return 0.0
    return len(query & source) / ((len(query) * len(source)) ** 0.5)


def load_preregistration(path=PREREG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ensure_official_dataset(prereg, path=DATASET):
    path = Path(path)
    source = prereg["official_source"]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".download")
        urllib.request.urlretrieve(source["dataset_url"], temporary)
        if temporary.stat().st_size != source["dataset_bytes"]:
            raise ValueError("downloaded LoCoMo byte size differs from preregistration")
        if file_sha256(temporary) != source["dataset_sha256"]:
            raise ValueError("downloaded LoCoMo hash differs from preregistration")
        temporary.replace(path)
    if path.stat().st_size != source["dataset_bytes"]:
        raise ValueError("local LoCoMo byte size differs from preregistration")
    if file_sha256(path) != source["dataset_sha256"]:
        raise ValueError("local LoCoMo hash differs from preregistration")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) != source["expected_conversation_count"]:
        raise ValueError("LoCoMo conversation count differs from preregistration")
    sample_ids = [str(row.get("sample_id") or "") for row in data]
    if not all(sample_ids) or len(sample_ids) != len(set(sample_ids)):
        raise ValueError("LoCoMo sample IDs are missing or duplicated")
    return data


def split_digest(sample_id, prereg):
    salt = prereg["dataset_partition"]["split_salt"]
    return text_sha256(f"{salt}:{sample_id}")


def split_conversations(data, prereg):
    ordered = sorted(data, key=lambda row: split_digest(str(row["sample_id"]), prereg))
    count = prereg["dataset_partition"]["holdout_conversation_count"]
    return ordered[:count], ordered[count:]


def session_keys(conversation):
    keys = [
        key
        for key, value in conversation.items()
        if re.fullmatch(r"session_\d+", str(key)) and isinstance(value, list)
    ]
    return sorted(keys, key=lambda key: int(key.split("_")[1]))


def session_timestamp(conversation, session_key):
    return str(conversation.get(f"{session_key}_date_time") or "")


def turn_text(turn):
    return str(turn.get("text") or "")


def serialize_session(conversation, session_key, selected_indices=None):
    turns = conversation[session_key]
    indices = list(range(len(turns))) if selected_indices is None else list(selected_indices)
    lines = [f"Time: {session_timestamp(conversation, session_key)}"]
    for index in indices:
        turn = turns[index]
        text = turn_text(turn)
        if text:
            lines.append(f"{str(turn.get('speaker') or '')}: {text}")
    return "\n".join(lines)


def evidence_session_keys(conversation, evidence_ids):
    evidence = set(map(str, evidence_ids or []))
    matched = []
    for key in session_keys(conversation):
        ids = {str(turn.get("dia_id") or "") for turn in conversation[key]}
        if evidence & ids:
            matched.append(key)
    return matched


def all_evidence_ids_exist(conversation, evidence_ids):
    expected = set(map(str, evidence_ids or []))
    available = {
        str(turn.get("dia_id") or "")
        for key in session_keys(conversation)
        for turn in conversation[key]
    }
    return bool(expected) and expected.issubset(available)


def projection_indices(conversation, session_key, question, top_k=3):
    ranked = []
    for index, turn in enumerate(conversation[session_key]):
        text = turn_text(turn)
        if not text:
            continue
        ranked.append((-lexical_overlap(question, text), index))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return sorted(index for _, index in ranked[:top_k])


def case_digest(sample_id, qa_index, question, prereg):
    salt = prereg["case_selection"]["selection_salt"]
    return text_sha256(f"{salt}:{sample_id}:{qa_index}:{question}")


def negative_tie_digest(sample_id, qa_index, session_key, prereg):
    salt = prereg["case_selection"]["selection_salt"]
    return text_sha256(f"{salt}:{sample_id}:{qa_index}:{session_key}")


def choose_hard_negative(sample, qa_index, question, answer, evidence_sessions, prereg):
    conversation = sample["conversation"]
    candidates = []
    for key in session_keys(conversation):
        if key in evidence_sessions:
            continue
        complete = serialize_session(conversation, key)
        if len(complete) > 32000 or answer.casefold() in complete.casefold():
            continue
        candidates.append(
            (
                -lexical_overlap(question, complete),
                negative_tie_digest(sample["sample_id"], qa_index, key, prereg),
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
    selection = prereg["case_selection"]
    conversation = sample["conversation"]
    eligible = []
    for qa_index, qa in enumerate(sample.get("qa") or []):
        if qa.get("category") != selection["official_category"]:
            continue
        question = str(qa.get("question") or "").strip()
        answer = str(qa.get("answer") or "").strip()
        evidence = list(qa.get("evidence") or [])
        if not question or not answer or not evidence:
            continue
        if not all_evidence_ids_exist(conversation, evidence):
            continue
        target_keys = evidence_session_keys(conversation, evidence)
        if len(target_keys) != 1:
            continue
        target_key = target_keys[0]
        target_complete = serialize_session(conversation, target_key)
        if len(target_complete) > 32000 or answer.casefold() not in target_complete.casefold():
            continue
        negative = choose_hard_negative(
            sample,
            qa_index,
            question,
            answer,
            set(target_keys),
            prereg,
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
                "target_key": target_key,
                "target_complete": target_complete,
                "negative_key": negative_key,
                "negative_complete": negative_complete,
                "selection_digest": case_digest(
                    sample["sample_id"], qa_index, question, prereg
                ),
            }
        )
    return sorted(eligible, key=lambda row: row["selection_digest"])


def record_manifest(sample, session_key, complete, question, answer):
    conversation = sample["conversation"]
    indices = projection_indices(conversation, session_key, question)
    projected = serialize_session(conversation, session_key, indices)
    return {
        "session_key": session_key,
        "timestamp_sha256": text_sha256(session_timestamp(conversation, session_key)),
        "source_turn_indices": list(range(len(conversation[session_key]))),
        "source_turn_ids": [str(turn.get("dia_id") or "") for turn in conversation[session_key]],
        "complete_text_sha256": text_sha256(complete),
        "complete_character_count": len(complete),
        "projection_source_turn_indices": indices,
        "projection_text_sha256": text_sha256(projected),
        "projection_character_count": len(projected),
        "contains_answer_complete": answer.casefold() in complete.casefold(),
        "contains_answer_projection": answer.casefold() in projected.casefold(),
    }


def build_manifest(data, prereg):
    holdout, reserve = split_conversations(data, prereg)
    selected = []
    per_sample = prereg["case_selection"]["cases_per_holdout_conversation"]
    for sample in holdout:
        eligible = eligible_cases_for_sample(sample, prereg)
        if len(eligible) < per_sample:
            raise ValueError(
                f"holdout conversation {sample['sample_id']} has only {len(eligible)} eligible cases"
            )
        for row in eligible[:per_sample]:
            selected.append((sample, row))
    cases = []
    for sample, row in selected:
        cases.append(
            {
                "case_id": f"locomo-v2-5-{sample['sample_id']}-{row['qa_index']}",
                "sample_id": str(sample["sample_id"]),
                "qa_index": row["qa_index"],
                "official_category": prereg["case_selection"]["official_category"],
                "question_sha256": text_sha256(row["question"]),
                "answer_sha256": text_sha256(row["answer"]),
                "evidence_ids_sha256": canonical_sha256(row["evidence"]),
                "target": record_manifest(
                    sample,
                    row["target_key"],
                    row["target_complete"],
                    row["question"],
                    row["answer"],
                ),
                "hard_negative": record_manifest(
                    sample,
                    row["negative_key"],
                    row["negative_complete"],
                    row["question"],
                    row["answer"],
                ),
            }
        )
    return {
        "schema": "uruha_source_preserving_memory_projection_locomo_cases_v2_5",
        "status": "frozen_before_model_generation",
        "experiment_id": prereg["experiment_id"],
        "source": {
            "dataset_sha256": prereg["official_source"]["dataset_sha256"],
            "dataset_bytes": prereg["official_source"]["dataset_bytes"],
        },
        "partition": {
            "holdout_sample_ids": [str(row["sample_id"]) for row in holdout],
            "holdout_sample_ids_sha256": canonical_sha256(
                [str(row["sample_id"]) for row in holdout]
            ),
            "reserve_sample_ids_sha256": canonical_sha256(
                [str(row["sample_id"]) for row in reserve]
            ),
            "holdout_count": len(holdout),
            "reserve_count": len(reserve),
            "overlap_count": 0,
        },
        "case_count": len(cases),
        "case_ids_sha256": canonical_sha256([row["case_id"] for row in cases]),
        "contains_official_text": False,
        "contains_official_answers": False,
        "construction_model_calls": 0,
        "cases": cases,
        "authorization": {
            "freeze_evaluation_contract": True,
            "model_generation": False,
            "runtime_change": False,
            "production_enablement": False,
        },
    }


def validate_construction_gates(manifest, prereg):
    gates = prereg["construction_gates_before_model_calls"]
    cases = manifest["cases"]
    by_sample = {}
    for case in cases:
        by_sample[case["sample_id"]] = by_sample.get(case["sample_id"], 0) + 1
    checks = {
        "conversation_count_equals": manifest["partition"]["holdout_count"]
        + manifest["partition"]["reserve_count"]
        == prereg["official_source"]["expected_conversation_count"],
        "holdout_conversation_count_equals": manifest["partition"]["holdout_count"]
        == gates["holdout_conversation_count_equals"],
        "reserve_conversation_count_equals": manifest["partition"]["reserve_count"]
        == gates["reserve_conversation_count_equals"],
        "holdout_reserve_overlap_equals": manifest["partition"]["overlap_count"]
        == gates["holdout_reserve_overlap_equals"],
        "question_count_equals": manifest["case_count"] == gates["question_count_equals"],
        "cases_per_holdout_conversation_equals": sorted(by_sample.values())
        == [gates["cases_per_holdout_conversation_equals"]]
        * gates["holdout_conversation_count_equals"],
        "all_case_text_and_answer_fields_absent_from_committed_manifest": all(
            not ({"question", "answer", "text"} & set(case)) for case in cases
        )
        and manifest["contains_official_text"] is False
        and manifest["contains_official_answers"] is False,
        "all_complete_target_sessions_contain_official_answer": all(
            case["target"]["contains_answer_complete"] for case in cases
        ),
        "all_hard_negative_sessions_exclude_official_answer": all(
            not case["hard_negative"]["contains_answer_complete"] for case in cases
        ),
        "model_calls_equal": manifest["construction_model_calls"]
        == gates["model_calls_equal"],
    }
    if not all(checks.values()):
        failed = [name for name, value in checks.items() if not value]
        raise ValueError("construction gates failed: " + ", ".join(failed))
    return checks


def main():
    if OUTPUT.exists():
        raise SystemExit("frozen LoCoMo V2.5 case manifest already exists")
    prereg = load_preregistration()
    data = ensure_official_dataset(prereg)
    manifest = build_manifest(data, prereg)
    manifest["construction_gates"] = validate_construction_gates(manifest, prereg)
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": file_sha256(OUTPUT),
                "holdout_count": manifest["partition"]["holdout_count"],
                "reserve_count": manifest["partition"]["reserve_count"],
                "case_count": manifest["case_count"],
                "construction_model_calls": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
