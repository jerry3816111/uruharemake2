#!/usr/bin/env python3
"""Execute the prospectively frozen P4-R zero-model comparison once."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

import chromadb

import p4_r_multiturn_interference_gate as gate
import uruha_multilingual_current_preference_p4 as p4i
import uruha_persisted_reference_time_p4 as p4o
import uruha_preference_scope_canonicalization_p4 as p4l


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_r_multiturn_interference_holdout_v1.json"
COLLECTION = "p4_r_multiturn_interference"


class _Memory:
    def __init__(self, collection):
        self.profile_col = collection
        self.session_profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}
        self._last_profile_state_shadow = {
            "status": "not_refreshed",
            "shadow_only": True,
            "affects_working_memory": False,
            "answer_use_authorized": False,
        }

    def _refresh_profile_state_shadow(self, *, reference_time=None):
        self._last_profile_state_shadow = {
            "status": "refreshed",
            "reference_time": reference_time,
            "shadow_only": True,
            "affects_working_memory": False,
            "answer_use_authorized": False,
        }


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _install_canonical_writer():
    if getattr(_install_canonical_writer, "installed", False):
        return
    p4l._ORIGINAL_EXTRACT = p4i.extract_explicit_current_preference_p4
    p4l._ORIGINAL_TYPED_RECORD = p4i._typed_record
    p4i.extract_explicit_current_preference_p4 = (
        p4l.extract_with_preference_scope_canonicalization_p4
    )
    p4i._typed_record = p4l.typed_record_with_preference_scope_canonicalization_p4
    _install_canonical_writer.installed = True


def _timestamp(turn):
    return f"2026-09-22T06:{int(turn):02d}:00+08:00"


def _recent_lexical_value(prior_turns, *, window, lexicon):
    selected = None
    source_turn = None
    for row in list(prior_turns)[-int(window):]:
        text = str(row.get("user") or "")
        matches = [value for value in lexicon if value in text]
        if matches:
            selected = max(matches, key=text.rfind)
            source_turn = row.get("turn")
    return selected, source_turn


def _snapshot(collection):
    payload = collection.get(include=["metadatas", "documents"])
    rows = [
        {"memory_id": memory_id, "metadata": metadata, "document": document}
        for memory_id, metadata, document in zip(
            payload.get("ids") or [],
            payload.get("metadatas") or [],
            payload.get("documents") or [],
        )
    ]
    rows.sort(key=lambda row: row["memory_id"])
    return rows


def _values(rows, *, scope, semantics):
    values = [
        str((row.get("metadata") or {}).get("value") or "")
        for row in rows
        if str((row.get("metadata") or {}).get("preference_scope") or "") == scope
        and (row.get("metadata") or {}).get("preference_semantics") == semantics
    ]
    return sorted(value for value in values if value)


def run_frozen_probe():
    contract = gate.load_contract()
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    _install_canonical_writer()
    lexicon = list(
        (dataset.get("novelty") or {})
        .get("repository_occurrences_before_dataset_creation", {})
        .keys()
    )
    baseline_recalls = []
    system_recalls = []
    turn_audits = []
    prior_turns = []
    write_audits = {}

    with tempfile.TemporaryDirectory(prefix="uruha-p4-r-") as tempdir:
        collection = chromadb.PersistentClient(path=tempdir).get_or_create_collection(COLLECTION)
        memory = _Memory(collection)
        for row in dataset["turns"]:
            turn = row["turn"]
            timestamp = _timestamp(turn)
            audit = p4i.remember_explicit_current_preference_p4(
                memory, row["user"], timestamp=timestamp
            )
            turn_audits.append(
                {
                    "turn": turn,
                    "role": row["role"],
                    "selected": bool(audit.get("selected")),
                    "status": audit.get("status"),
                    "act": audit.get("act"),
                    "scope": audit.get("scope"),
                    "current_value": audit.get("current_value"),
                    "current_memory_id": audit.get("current_memory_id"),
                    "previous_current_memory_id": audit.get("previous_current_memory_id"),
                    "negative_old_memory_id": audit.get("negative_old_memory_id"),
                    "profile_write_count": audit.get("profile_write_count", 0),
                    "raw_dialogue_persisted": audit.get("raw_dialogue_persisted", False),
                }
            )
            if audit.get("selected"):
                write_audits[turn] = audit

            if row["role"] in {"pre_correction_recall", "post_correction_recall"}:
                baseline_value, baseline_source_turn = _recent_lexical_value(
                    prior_turns,
                    window=dataset["baseline"]["history_window_user_turns"],
                    lexicon=lexicon,
                )
                baseline_recalls.append(
                    {
                        "turn": turn,
                        "selected_value": baseline_value,
                        "source_turn": baseline_source_turn,
                        "expected_value": row["expected_system_value"],
                        "exact": baseline_value == row["expected_system_value"],
                    }
                )
                recall = p4o.build_with_persisted_reference_time_p4(
                    row["user"], collection, reference_time=timestamp
                )
                system_recalls.append(
                    {
                        "turn": turn,
                        "selected_value": recall.get("localized_value_jp"),
                        "visible_surface": recall.get("selected_core_jp"),
                        "expected_value": row["expected_system_value"],
                        "expected_surface": row["expected_system_surface"],
                        "exact": (
                            recall.get("localized_value_jp") == row["expected_system_value"]
                            and recall.get("selected_core_jp") == row["expected_system_surface"]
                        ),
                        "status": recall.get("status"),
                        "answer_use_authorized": recall.get("answer_use_authorized"),
                        "active_memory_id": recall.get("active_memory_id"),
                        "value_surface_strategy": recall.get("value_surface_strategy"),
                        "historical_answer_use_count": recall.get(
                            "historical_answer_use_count", 0
                        ),
                        "explicit_negative_answer_use_count": recall.get(
                            "explicit_negative_answer_use_count", 0
                        ),
                        "profile_write_count": recall.get("profile_write_count", 0),
                        "raw_dialogue_persisted": recall.get(
                            "raw_dialogue_persisted", False
                        ),
                    }
                )
            prior_turns.append(row)

        final_rows = _snapshot(collection)
        resolved = p4i._current_preference_rows(
            collection, reference_time=_timestamp(dataset["turn_count"])
        )
        active = resolved["active"]
        historical = resolved["historical"]
        negative = [
            row
            for row in final_rows
            if (row.get("metadata") or {}).get("preference_semantics")
            == "explicitly_negated_preference"
        ]
        correction = write_audits.get(8) or {}
        by_id = {row["memory_id"]: row.get("metadata") or {} for row in final_rows}
        correction_metadata = by_id.get(correction.get("current_memory_id"), {})
        negative_metadata = by_id.get(correction.get("negative_old_memory_id"), {})
        distractor_roles = {
            "ordinary_distractor",
            "third_person_drink_distractor",
            "quoted_drink_distractor",
            "third_person_old_value_distractor",
            "hypothetical_drink_distractor",
            "cross_language_third_person_distractor",
        }
        baseline_exact = sum(bool(row["exact"]) for row in baseline_recalls)
        system_exact = sum(bool(row["exact"]) for row in system_recalls)
        metrics = {
            "system_exact_recall_count": system_exact,
            "baseline_exact_recall_count": baseline_exact,
            "system_minus_baseline_accuracy": round(
                system_exact / len(system_recalls)
                - baseline_exact / len(baseline_recalls),
                4,
            ),
            "system_japanese_surface_count": sum(
                row["visible_surface"] == row["expected_surface"] for row in system_recalls
            ),
            "system_answer_use_authorized_count": sum(
                row["answer_use_authorized"] is True for row in system_recalls
            ),
            "historical_answer_use_count": sum(
                row["historical_answer_use_count"] for row in system_recalls
            ),
            "negative_answer_use_count": sum(
                row["explicit_negative_answer_use_count"] for row in system_recalls
            ),
            "non_write_distractor_selected_count": sum(
                audit["selected"] and audit["role"] in distractor_roles
                for audit in turn_audits
            ),
            "profile_record_count_after_turn_12": len(final_rows),
            "drink_active_count_after_turn_12": len(
                _values(active, scope="drink", semantics="current_preference")
            ),
            "game_active_count_after_turn_12": len(
                _values(active, scope="game", semantics="current_preference")
            ),
            "drink_historical_count_after_turn_12": len(
                _values(historical, scope="drink", semantics="current_preference")
            ),
            "drink_explicit_negative_count_after_turn_12": len(
                _values(negative, scope="drink", semantics="explicitly_negated_preference")
            ),
            "recall_profile_write_count": sum(
                row["profile_write_count"] for row in system_recalls
            ),
            "unverified_mental_fact_write_count": sum(
                (row.get("metadata") or {}).get("epistemic_status")
                != "observed_explicit_user_self_report"
                for row in final_rows
            ),
        }
        evidence = {
            "schema": "uruha_p4_r_multiturn_interference_evidence_v1",
            "case_id": dataset["case_id"],
            "dataset_sha256": _sha256(DATASET),
            "turn_count": dataset["turn_count"],
            "conditions": {
                "baseline": {
                    "id": dataset["baseline"]["id"],
                    "history_window_user_turns": dataset["baseline"][
                        "history_window_user_turns"
                    ],
                    "recalls": baseline_recalls,
                },
                "system": {
                    "id": dataset["system"]["id"],
                    "recalls": system_recalls,
                    "turn_audits": turn_audits,
                },
            },
            "metrics": metrics,
            "final_state": {
                "drink_active_values": _values(
                    active, scope="drink", semantics="current_preference"
                ),
                "drink_historical_values": _values(
                    historical, scope="drink", semantics="current_preference"
                ),
                "drink_explicit_negative_values": _values(
                    negative,
                    scope="drink",
                    semantics="explicitly_negated_preference",
                ),
                "game_active_values": _values(
                    active, scope="game", semantics="current_preference"
                ),
                "correction_previous_link_valid": (
                    correction_metadata.get("previous_current_memory_id")
                    == (write_audits.get(1) or {}).get("current_memory_id")
                ),
                "negative_correction_link_valid": (
                    negative_metadata.get("correction_current_memory_id")
                    == correction.get("current_memory_id")
                ),
                "record_ids": [row["memory_id"] for row in final_rows],
                "raw_dialogue_persisted": any(
                    (row.get("document") or "")
                    in {turn["user"] for turn in dataset["turns"]}
                    for row in final_rows
                ),
            },
            "accounting": dict(contract["execution"]),
            "claim_boundary": contract["claim_boundary"],
        }
        evidence["gate_evaluation"] = gate.evaluate_evidence(contract, evidence)
        return evidence


def main():
    print(json.dumps(run_frozen_probe(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
