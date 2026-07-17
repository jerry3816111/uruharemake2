"""Pure validation helpers for support-attributed memory consolidation."""

from __future__ import annotations

import hashlib
import json
import re


MEMORY_KINDS = ("episodic", "wisdom", "procedural")
_HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _parse_episode_document(document):
    text = str(document or "")
    match = re.search(
        r"\|\s*User:\s*(.*?)\s*\|\s*Summary:.*?"
        r"\|\s*Uruha:\s*(.*?)\s*\|\s*Mood:",
        text,
        flags=re.DOTALL,
    )
    if not match:
        return text, ""
    return match.group(1).strip(), match.group(2).strip()


def build_source_events(db_excerpt, excerpt_turns):
    events = []
    if db_excerpt:
        for index, entry in enumerate(db_excerpt, start=1):
            user, assistant = _parse_episode_document(
                entry.get("document")
            )
            events.append(
                {
                    "index": index,
                    "episode_id": str(entry.get("id") or ""),
                    "user": user,
                    "assistant": assistant,
                }
            )
        return events

    for index, turn in enumerate(excerpt_turns, start=1):
        events.append(
            {
                "index": index,
                "episode_id": str(turn.get("episode_id") or ""),
                "user": str(turn.get("user") or ""),
                "assistant": str(turn.get("reply") or ""),
            }
        )
    return events


def _validate_attribution(result, valid_indices):
    if not isinstance(result, dict):
        return None, "result_type"
    if result.get("transport_error"):
        return None, "transport_error"
    if result.get("parse_success") is not True:
        return None, "parse_failure"
    if result.get("index_contract_success") is not True:
        return None, "index_contract_failure"

    indices = result.get("support_event_indices")
    if not isinstance(indices, list):
        return None, "indices_type"
    if (
        any(
            isinstance(index, bool)
            or not isinstance(index, int)
            or index not in valid_indices
            for index in indices
        )
        or len(indices) != len(set(indices))
    ):
        return None, "indices_contract"

    model_digest = str(result.get("model_digest") or "")
    if not _HEX_DIGEST_RE.fullmatch(model_digest):
        return None, "model_digest"
    contract_version = str(result.get("contract_version") or "").strip()
    if not contract_version:
        return None, "contract_version"

    try:
        wall_seconds = max(0.0, float(result.get("wall_seconds") or 0.0))
    except (TypeError, ValueError):
        return None, "wall_seconds"
    return (
        {
            "support_event_indices": sorted(indices),
            "model_digest": model_digest,
            "contract_version": contract_version,
            "wall_seconds": round(wall_seconds, 6),
        },
        None,
    )


def stage_support_attributions(
    support_attributor,
    *,
    derived_memories,
    source_events,
):
    if not callable(support_attributor):
        return {
            "ok": False,
            "error": "attributor_not_callable",
            "attributions": {},
        }
    valid_indices = {
        event.get("index")
        for event in source_events
        if isinstance(event.get("index"), int)
    }
    expected_indices = set(range(1, len(source_events) + 1))
    if valid_indices != expected_indices:
        return {
            "ok": False,
            "error": "source_index_contract",
            "attributions": {},
        }
    if any(not event.get("episode_id") for event in source_events):
        return {
            "ok": False,
            "error": "missing_source_episode_id",
            "attributions": {},
        }

    attributions = {}
    expected_model_digest = None
    expected_contract_version = None
    for memory_kind in MEMORY_KINDS:
        derived_memory = str(
            derived_memories.get(memory_kind) or ""
        ).strip()
        if not derived_memory or derived_memory == "NO_RULE":
            continue
        try:
            raw_result = support_attributor(
                memory_kind=memory_kind,
                derived_memory=derived_memory,
                source_events=[
                    {
                        "index": event["index"],
                        "episode_id": event["episode_id"],
                        "user": event["user"],
                        "assistant": event["assistant"],
                    }
                    for event in source_events
                ],
            )
        except Exception as exc:
            return {
                "ok": False,
                "error": (
                    f"attributor_exception:{type(exc).__name__}"
                ),
                "attributions": attributions,
            }
        validated, error = _validate_attribution(
            raw_result,
            valid_indices,
        )
        if error:
            return {
                "ok": False,
                "error": f"{memory_kind}:{error}",
                "attributions": attributions,
            }
        if expected_model_digest is None:
            expected_model_digest = validated["model_digest"]
            expected_contract_version = validated["contract_version"]
        elif (
            validated["model_digest"] != expected_model_digest
            or validated["contract_version"]
            != expected_contract_version
        ):
            return {
                "ok": False,
                "error": "attribution_identity_drift",
                "attributions": attributions,
            }

        by_index = {
            event["index"]: event for event in source_events
        }
        support_episode_ids = sorted(
            {
                by_index[index]["episode_id"]
                for index in validated["support_event_indices"]
            }
        )
        attributions[memory_kind] = {
            **validated,
            "support_episode_ids": support_episode_ids,
        }

    return {
        "ok": True,
        "error": None,
        "attributions": attributions,
        "model_digest": expected_model_digest,
        "contract_version": expected_contract_version,
        "total_wall_seconds": round(
            sum(
                result["wall_seconds"]
                for result in attributions.values()
            ),
            6,
        ),
    }


def support_provenance(attribution):
    support_episode_ids = sorted(
        {
            str(source_id)
            for source_id in attribution["support_episode_ids"]
            if str(source_id).strip()
        }
    )
    encoded_ids = json.dumps(
        support_episode_ids,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    encoded_indices = json.dumps(
        attribution["support_event_indices"],
        separators=(",", ":"),
    )
    return {
        "support_attribution_status": "verified",
        "support_attribution_contract_version": attribution[
            "contract_version"
        ],
        "support_attribution_model_digest": attribution["model_digest"],
        "support_event_indices": encoded_indices,
        "support_episode_ids": encoded_ids,
        "support_episode_count": len(support_episode_ids),
        "support_episode_ids_sha256": hashlib.sha256(
            encoded_ids.encode("utf-8")
        ).hexdigest(),
        "support_attribution_wall_seconds": attribution["wall_seconds"],
    }
