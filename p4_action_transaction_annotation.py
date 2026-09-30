"""Offline arm-masked developer-proxy annotation for the P4 transaction study.

This module never calls a model, reads gold, or attests Git history.  It accepts
only the 36 observations returned by the raw evidence verifier, projects both
arms into the same user-text/final-reply shape, and keeps the reveal mapping in
a separate object.  A single developer annotating this packet is an
*arm-masked developer proxy*, not an independent human evaluation.

The anonymous submission should be committed before the mapping is disclosed.
The formal evidence verifier must check the raw/annotation Git order and then
promote ``output_locked_before_annotation`` for scoring; this module always
leaves that flag false.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import re
import secrets

import p4_action_transaction_scoring as tx


PACKET_SCHEMA = "uruha_p4_action_transaction_masked_packet_v1"
MAPPING_SCHEMA = "uruha_p4_action_transaction_reveal_mapping_v1"
SUBMISSION_SCHEMA = "uruha_p4_action_transaction_masked_submission_v1"
BOUND_SCHEMA = "uruha_p4_action_transaction_bound_annotation_v1"
AUTHORITY = "arm_masked_developer_proxy_not_independent_human"
PACKET_PATH = "analysis/p4_action_transaction_v1_masked_packet_2026-09-30.json"
SUBMISSION_PATH = "analysis/p4_action_transaction_v1_masked_submission_2026-09-30.json"
MAPPING_PATH = "analysis/p4_action_transaction_v1_reveal_mapping_2026-09-30.json"
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_SHA64 = re.compile(r"[0-9a-f]{64}\Z")
_VALUES = {"pass", "fail", "uncertain"}


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _verified_rows(verified_raw: dict) -> list[tuple[str, str, str, str, str]]:
    """Check the verifier's shape and rehash every raw-derived observation.

    The verifier remains responsible for proving these values came from the
    committed raw artifact; this independent check prevents accidental use of
    a partial or internally inconsistent verifier result.
    """

    _require(isinstance(verified_raw, dict)
             and verified_raw.get("verified_raw_evidence") is True,
             "a verified raw-evidence result is required")
    commit = verified_raw.get("raw_commit")
    lock = verified_raw.get("raw_lock")
    _require(type(commit) is str and _SHA40.fullmatch(commit) is not None,
             "raw commit must be a full SHA")
    _require(isinstance(lock, dict) and lock.get("commit_sha") == commit,
             "raw lock commit mismatch")
    order = verified_raw.get("case_order")
    _require(isinstance(order, list) and len(order) == tx.ABSOLUTE_CASE_COUNT
             and all(type(value) is str and value for value in order)
             and len(set(order)) == len(order), "expected 18 unique cases")
    prepared = verified_raw.get("prepared_cases")
    observations = verified_raw.get("observations")
    digests = verified_raw.get("output_digests")
    _require(all(isinstance(value, dict) and set(value) == set(order)
                 for value in (prepared, observations, digests)),
             "case maps must cover exactly the frozen 18 cases")
    _require(lock.get("output_digests") == digests,
             "raw lock output digests mismatch")
    rows = []
    for case_id in order:
        case = prepared[case_id]
        _require(isinstance(case, dict) and case.get("case_id") == case_id
                 and type(case.get("raw_user_input")) is str
                 and bool(case["raw_user_input"].strip()),
                 "prepared case is incomplete")
        _require(isinstance(observations[case_id], dict)
                 and set(observations[case_id]) == set(tx.ARMS)
                 and isinstance(digests[case_id], dict)
                 and set(digests[case_id]) == set(tx.ARMS),
                 "each case requires both arms")
        for arm in tx.ARMS:
            observed = observations[case_id][arm]
            digest = digests[case_id][arm]
            _require(isinstance(observed, dict) and observed.get("arm") == arm
                     and observed.get("decision") in {"action", "abstain"},
                     "invalid observation")
            _require(type(digest) is str and _SHA64.fullmatch(digest) is not None
                     and digest == tx.output_evidence_digest(case_id, arm, observed),
                     "output digest mismatch")
            reply_field = ("instruction_jp" if observed["decision"] == "action"
                           else "fallback_reply_jp")
            other_field = ("fallback_reply_jp" if reply_field == "instruction_jp"
                           else "instruction_jp")
            reply = observed.get(reply_field)
            _require(type(reply) is str and bool(reply.strip())
                     and observed.get(other_field) is None,
                     "observation lacks an unambiguous final reply")
            rows.append((case_id, arm, case["raw_user_input"], reply, digest))
    _require(len(rows) == 36, "expected 36 verified observations")
    return rows


def _tag(seed: bytes, prefix: str, case_id: str, arm: str) -> str:
    return hmac.new(seed, f"{prefix}|{case_id}|{arm}".encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _packet_body(records: list[dict]) -> dict:
    return {"schema": PACKET_SCHEMA,
            "semantic_axes": list(tx.SEMANTIC_AXES),
            "allowed_axis_values": ["pass", "fail", "uncertain"],
            "records": records}


def _reject_identity_leaks(packet: dict, case_ids: list[str]) -> None:
    serialized = json.dumps(packet, ensure_ascii=False)
    _require(not any(case_id in serialized for case_id in case_ids)
             and not any(arm in serialized for arm in tx.ARMS),
             "masked packet leaks a case or arm identity")


def build_masked_packet(verified_raw: dict, *, seed: bytes | None = None
                        ) -> tuple[dict, dict]:
    """Return an anonymous packet and a separately held reveal mapping.

    ``seed`` is injectable only for deterministic offline tests; production
    callers should omit it to use 256-bit OS randomness.  The seed, raw commit,
    case/arm identities and output digests appear only in the reveal mapping.
    """

    rows = _verified_rows(verified_raw)
    if seed is None:
        seed = secrets.token_bytes(32)
    _require(type(seed) is bytes and len(seed) == 32,
             "masking seed must be exactly 32 bytes")
    rows.sort(key=lambda row: _tag(seed, "order", row[0], row[1]))
    records = []
    items = []
    for case_id, arm, source, reply, digest in rows:
        item_id = "m_" + _tag(seed, "alias", case_id, arm)[:24]
        record = {"item_id": item_id, "user_text": source, "reply_jp": reply}
        records.append(record)
        items.append({"item_id": item_id, "case_id": case_id, "arm": arm,
                      "output_digest": digest,
                      "presentation_digest": _digest(record)})
    _require(len({record["item_id"] for record in records}) == 36,
             "anonymous item collision")
    body = _packet_body(records)
    mapping_body = {
        "schema": MAPPING_SCHEMA,
        "raw_lock_commit": verified_raw["raw_commit"],
        "seed_hex": seed.hex(),
        "shuffle": "hmac_sha256_order_v1",
        "packet_body_digest": _digest(body),
        "items": items,
    }
    commitment = _digest(mapping_body)
    packet = {**body, "mapping_commitment": commitment}
    _reject_identity_leaks(packet, verified_raw["case_order"])
    mapping = {**mapping_body, "mapping_commitment": commitment,
               "packet_digest": _digest(packet)}
    return packet, mapping


def validate_masked_packet(packet: dict, reveal_mapping: dict,
                           verified_raw: dict) -> None:
    """Reject leaked, swapped, incomplete or commitment-tampered packets."""

    _verified_rows(verified_raw)
    _require(isinstance(packet, dict)
             and set(packet) == {"schema", "semantic_axes", "allowed_axis_values",
                                 "records", "mapping_commitment"}
             and packet.get("schema") == PACKET_SCHEMA
             and packet.get("semantic_axes") == list(tx.SEMANTIC_AXES)
             and packet.get("allowed_axis_values") == ["pass", "fail", "uncertain"],
             "masked packet schema mismatch")
    _require(isinstance(reveal_mapping, dict)
             and set(reveal_mapping) == {"schema", "raw_lock_commit", "seed_hex",
                                         "shuffle", "packet_body_digest", "items",
                                         "mapping_commitment", "packet_digest"}
             and reveal_mapping.get("schema") == MAPPING_SCHEMA
             and reveal_mapping.get("raw_lock_commit") == verified_raw["raw_commit"]
             and reveal_mapping.get("shuffle") == "hmac_sha256_order_v1",
             "reveal mapping schema or raw commit mismatch")
    seed_hex = reveal_mapping.get("seed_hex")
    _require(type(seed_hex) is str and _SHA64.fullmatch(seed_hex) is not None,
             "invalid reveal seed")
    expected_packet, expected_mapping = build_masked_packet(
        verified_raw, seed=bytes.fromhex(seed_hex))
    _require(packet == expected_packet and reveal_mapping == expected_mapping,
             "packet or reveal mapping does not match verified raw observations")
    # Exact equality above also prevents a case/arm identity, raw stage, token,
    # wall, transport field, or gold field from being added to the packet.
    _reject_identity_leaks(packet, verified_raw["case_order"])


def build_annotation_submission(packet: dict, labels: list[dict]) -> dict:
    """Lock all 36 anonymous nine-axis labels without seeing the mapping.

    Missing labels are errors, never silently filled with ``pass``.  Explicit
    ``uncertain`` is preserved and the scorer will not treat it as a PASS.
    """

    _require(isinstance(packet, dict) and packet.get("schema") == PACKET_SCHEMA
             and isinstance(packet.get("records"), list)
             and len(packet["records"]) == 36,
             "invalid annotation packet")
    ids = [record.get("item_id") for record in packet["records"]
           if isinstance(record, dict)]
    _require(len(ids) == 36 and len(set(ids)) == 36,
             "packet requires 36 unique anonymous items")
    _require(isinstance(labels, list) and len(labels) == 36,
             "annotation requires 36 labels")
    keyed = {}
    for label in labels:
        _require(isinstance(label, dict) and set(label) == {"item_id", "axes"}
                 and type(label.get("item_id")) is str
                 and label["item_id"] in ids and label["item_id"] not in keyed,
                 "duplicate, unknown, or malformed label")
        axes = label["axes"]
        _require(isinstance(axes, dict) and set(axes) == set(tx.SEMANTIC_AXES)
                 and all(type(value) is str and value in _VALUES
                         for value in axes.values()),
                 "label requires every fixed semantic axis")
        keyed[label["item_id"]] = deepcopy(axes)
    _require(set(keyed) == set(ids), "missing annotation labels")
    return {"schema": SUBMISSION_SCHEMA, "authority": AUTHORITY,
            "packet_digest": _digest(packet),
            "mapping_commitment": packet.get("mapping_commitment"),
            "records": [{"item_id": item_id, "axes": keyed[item_id]}
                        for item_id in ids]}


def unblind_annotations(packet: dict, reveal_mapping: dict, submission: dict,
                        verified_raw: dict) -> dict:
    """Bind locked anonymous labels to raw commit/digests, without Git claims.

    The returned adjudications deliberately have
    ``output_locked_before_annotation=False``.  A separate formal verifier
    must establish Git ordering and only then make scorer-ready adjudications.
    """

    validate_masked_packet(packet, reveal_mapping, verified_raw)
    _require(isinstance(submission, dict)
             and set(submission) == {"schema", "authority", "packet_digest",
                                     "mapping_commitment", "records"}
             and submission.get("schema") == SUBMISSION_SCHEMA
             and submission.get("authority") == AUTHORITY
             and submission.get("packet_digest") == _digest(packet)
             and submission.get("mapping_commitment") == packet["mapping_commitment"],
             "annotation submission commitment mismatch")
    rebuilt = build_annotation_submission(packet, submission["records"])
    _require(submission == rebuilt, "annotation submission is noncanonical")
    labels = {row["item_id"]: row["axes"] for row in submission["records"]}
    adjudications = {case_id: {} for case_id in verified_raw["case_order"]}
    for item in reveal_mapping["items"]:
        case_id, arm = item["case_id"], item["arm"]
        adjudications[case_id][arm] = {
            "case_id": case_id, "arm": arm,
            "axes": deepcopy(labels[item["item_id"]]),
            "raw_lock_commit": verified_raw["raw_commit"],
            "output_digest": item["output_digest"],
            "output_locked_before_annotation": False,
        }
    _require(all(set(arms) == set(tx.ARMS) for arms in adjudications.values()),
             "unblinded annotation coverage mismatch")
    return {"schema": BOUND_SCHEMA, "authority": AUTHORITY,
            "raw_lock_commit": verified_raw["raw_commit"],
            "packet_digest": _digest(packet),
            "mapping_commitment": packet["mapping_commitment"],
            "submission_digest": _digest(submission),
            "git_order_verified": False,
            "adjudications": adjudications}
