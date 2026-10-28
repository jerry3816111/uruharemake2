"""Zero-call tests for the arm-masked P4 transaction annotation contract."""

from __future__ import annotations

from copy import deepcopy
import json

import pytest

import p4_action_transaction_annotation as annotation
import p4_action_transaction_scoring as tx


RAW_COMMIT = "a" * 40
SEED = bytes(range(32))


def _verified_raw() -> dict:
    order = [f"p4_tx_fake_{index:02d}" for index in range(18)]
    cases = {}
    observations = {}
    output_digests = {}
    for index, case_id in enumerate(order):
        cases[case_id] = {"case_id": case_id,
                          "raw_user_input": f"私の資料 {index} を確認して。"}
        observations[case_id] = {}
        output_digests[case_id] = {}
        for arm in tx.ARMS:
            reply = f"資料 {index} の見出しを一つ確認してみて。" if arm == tx.ARMS[0] else (
                f"資料 {index} の日付を一つ確認してみて。")
            observed = {
                "arm": arm, "decision": "action", "instruction_jp": reply,
                "fallback_reply_jp": None,
                "raw_stage_record": {"private_stage_marker": "STAGE_SECRET"},
                "transport_metadata": "TRANSPORT_SECRET",
                "prompt_tokens": 123, "completion_tokens": 42,
                "full_turn_seconds": 9.87654,
            }
            observations[case_id][arm] = observed
            output_digests[case_id][arm] = tx.output_evidence_digest(
                case_id, arm, observed)
    return {
        "verified_raw_evidence": True, "raw_commit": RAW_COMMIT,
        "raw_lock": {"commit_sha": RAW_COMMIT,
                     "output_digests": deepcopy(output_digests)},
        "case_order": order, "prepared_cases": cases,
        "observations": observations, "output_digests": output_digests,
        "gold": {"sentinel": "GOLD_SECRET"},
    }


def _labels(packet: dict, *, value: str = "pass") -> list[dict]:
    return [{"item_id": record["item_id"],
             "axes": {axis: value for axis in tx.SEMANTIC_AXES}}
            for record in packet["records"]]


def test_masked_packet_is_randomized_homomorphic_and_leak_free():
    raw = _verified_raw()
    packet, mapping = annotation.build_masked_packet(raw, seed=SEED)
    annotation.validate_masked_packet(packet, mapping, raw)
    assert len(packet["records"]) == 36
    assert all(set(record) == {"item_id", "user_text", "reply_jp"}
               for record in packet["records"])
    assert len({record["item_id"] for record in packet["records"]}) == 36
    assert [item["case_id"] for item in mapping["items"]] != [
        case_id for case_id in raw["case_order"] for _ in tx.ARMS]
    assert mapping["seed_hex"] == SEED.hex()
    assert packet["mapping_commitment"] == mapping["mapping_commitment"]
    assert annotation.build_masked_packet(raw, seed=SEED) == (packet, mapping)
    serialized = json.dumps(packet, ensure_ascii=False)
    for secret in (*tx.ARMS, *raw["case_order"], "GOLD_SECRET", "STAGE_SECRET",
                   "TRANSPORT_SECRET", "prompt_tokens", "completion_tokens",
                   "full_turn_seconds", RAW_COMMIT, SEED.hex()):
        assert secret not in serialized


def test_source_or_reply_that_exposes_an_identity_cannot_be_packetized():
    raw = _verified_raw()
    first = raw["case_order"][0]
    raw["prepared_cases"][first]["raw_user_input"] = f"この ID は {first}"
    with pytest.raises(ValueError, match="leaks"):
        annotation.build_masked_packet(raw, seed=SEED)
    raw = _verified_raw()
    first = raw["case_order"][0]
    observed = raw["observations"][first][tx.ARMS[0]]
    observed["instruction_jp"] = f"{tx.ARMS[0]} を見て"
    digest = tx.output_evidence_digest(first, tx.ARMS[0], observed)
    raw["output_digests"][first][tx.ARMS[0]] = digest
    raw["raw_lock"]["output_digests"][first][tx.ARMS[0]] = digest
    with pytest.raises(ValueError, match="leaks"):
        annotation.build_masked_packet(raw, seed=SEED)


def test_mapping_swap_and_presentation_tamper_fail_closed():
    raw = _verified_raw()
    packet, mapping = annotation.build_masked_packet(raw, seed=SEED)
    swapped = deepcopy(mapping)
    swapped["items"][0]["arm"] = tx.ARMS[1] if (
        swapped["items"][0]["arm"] == tx.ARMS[0]) else tx.ARMS[0]
    with pytest.raises(ValueError):
        annotation.validate_masked_packet(packet, swapped, raw)
    redacted = deepcopy(packet)
    redacted["records"][0]["reply_jp"] = "後から変えた返答"
    with pytest.raises(ValueError):
        annotation.validate_masked_packet(redacted, mapping, raw)
    leaked = deepcopy(packet)
    leaked["records"][0]["gold"] = "action"
    with pytest.raises(ValueError):
        annotation.validate_masked_packet(leaked, mapping, raw)


def test_raw_output_digest_and_commit_tamper_fail_closed():
    raw = _verified_raw()
    packet, mapping = annotation.build_masked_packet(raw, seed=SEED)
    mutated = deepcopy(raw)
    first = mutated["case_order"][0]
    mutated["observations"][first][tx.ARMS[0]]["full_turn_seconds"] = 0.1
    with pytest.raises(ValueError, match="digest"):
        annotation.validate_masked_packet(packet, mapping, mutated)
    mutated = deepcopy(raw)
    mutated["raw_commit"] = "b" * 40
    with pytest.raises(ValueError, match="commit"):
        annotation.validate_masked_packet(packet, mapping, mutated)
    mutated = deepcopy(mapping)
    mutated["items"][0]["output_digest"] = "0" * 64
    with pytest.raises(ValueError):
        annotation.validate_masked_packet(packet, mutated, raw)


def test_duplicate_missing_and_incomplete_axes_cannot_become_pass():
    packet, _ = annotation.build_masked_packet(_verified_raw(), seed=SEED)
    labels = _labels(packet)
    with pytest.raises(ValueError):
        annotation.build_annotation_submission(packet, labels[:-1])
    duplicated = deepcopy(labels)
    duplicated[-1]["item_id"] = duplicated[0]["item_id"]
    with pytest.raises(ValueError, match="duplicate"):
        annotation.build_annotation_submission(packet, duplicated)
    incomplete = deepcopy(labels)
    del incomplete[0]["axes"][tx.SEMANTIC_AXES[0]]
    with pytest.raises(ValueError, match="every fixed semantic axis"):
        annotation.build_annotation_submission(packet, incomplete)
    invalid = deepcopy(labels)
    invalid[0]["axes"][tx.SEMANTIC_AXES[0]] = "PASS"
    with pytest.raises(ValueError):
        annotation.build_annotation_submission(packet, invalid)


def test_submission_binding_preserves_uncertain_and_requires_later_git_check():
    raw = _verified_raw()
    packet, mapping = annotation.build_masked_packet(raw, seed=SEED)
    labels = _labels(packet)
    labels[0]["axes"][tx.SEMANTIC_AXES[0]] = "uncertain"
    submission = annotation.build_annotation_submission(packet, labels)
    bound = annotation.unblind_annotations(packet, mapping, submission, raw)
    assert bound["authority"] == annotation.AUTHORITY
    assert bound["git_order_verified"] is False
    assert bound["raw_lock_commit"] == RAW_COMMIT
    assert len(bound["adjudications"]) == 18
    entries = [entry for arms in bound["adjudications"].values()
               for entry in arms.values()]
    assert len(entries) == 36
    assert all(entry["output_locked_before_annotation"] is False for entry in entries)
    assert any("uncertain" in entry["axes"].values() for entry in entries)
    assert all(entry["output_digest"] == raw["output_digests"][entry["case_id"]][entry["arm"]]
               for entry in entries)
    # Even all-pass labels cannot be accepted by the scorer without the formal
    # raw-before-annotation Git attestation.
    sample = entries[0]
    assert tx._adjudicated_axes(sample, case_id=sample["case_id"], arm=sample["arm"],
                                observed=raw["observations"][sample["case_id"]][sample["arm"]],
                                raw_lock=raw["raw_lock"]) is None


def test_submission_digest_and_mapping_commitment_tamper_fail_closed():
    raw = _verified_raw()
    packet, mapping = annotation.build_masked_packet(raw, seed=SEED)
    submission = annotation.build_annotation_submission(packet, _labels(packet))
    mutated = deepcopy(submission)
    mutated["packet_digest"] = "0" * 64
    with pytest.raises(ValueError, match="commitment"):
        annotation.unblind_annotations(packet, mapping, mutated, raw)
    mutated = deepcopy(submission)
    mutated["records"][0]["axes"][tx.SEMANTIC_AXES[0]] = "fail"
    # A changed label is distinguishable by its full submission digest; the
    # Git verifier must compare that digest to the committed annotation file.
    rebound = annotation.unblind_annotations(packet, mapping, mutated, raw)
    assert rebound["submission_digest"] != annotation.unblind_annotations(
        packet, mapping, submission, raw)["submission_digest"]
    mutated_mapping = deepcopy(mapping)
    mutated_mapping["mapping_commitment"] = "0" * 64
    with pytest.raises(ValueError):
        annotation.unblind_annotations(packet, mutated_mapping, submission, raw)
