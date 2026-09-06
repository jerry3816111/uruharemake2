"""Keep distinct committed prediction events across local turn-counter resets.

Product adapter: install after the existing M54/M53 stack. Changes identity only,
not response policy, Japanese realization, learning rules or formal experiment files.
The persisted sequence is per adaptive-person store, not a global person identity.
Single-writer runtime remains required, as in the existing store.
"""
from copy import deepcopy
import hashlib
import re

import uruha_adaptive_person_model as adaptive

SEQUENCE = "prediction_event_sequence_p1"
TRACE = "prediction_identity_p1"
_ID = re.compile(r"^p1-(\d+)-[0-9a-f]{16}$")
_previous_normalise = adaptive._normalise_model
_previous_decide = adaptive.decide_response
_previous_pending = adaptive.set_pending_prediction


def _sequence_from_id(value):
    match = _ID.fullmatch(str(value or ""))
    return int(match.group(1)) if match else 0


def _sequence_floor(model):
    model = model if isinstance(model, dict) else {}
    stored = model.get(SEQUENCE, 0)
    if type(stored) is not int or stored < 0:
        raise ValueError("Invalid P1 committed prediction sequence")
    # Also recover from records when an older adapter preserved the ledger but
    # omitted the additive scalar. Never infer a sequence from dialogue content.
    entries = list(model.get("outcome_calibration_ledger_m27") or [])
    entries.append(model.get("pending_prediction") or {})
    return max([stored] + [_sequence_from_id(row.get("prediction_id"))
                           for row in entries if isinstance(row, dict)])


def normalise_model_p1(payload):
    state = _previous_normalise(payload)
    if isinstance(payload, dict) and payload.get("schema") in {
        adaptive.MODEL_SCHEMA, adaptive.M17_MODEL_SCHEMA, adaptive.LEGACY_MODEL_SCHEMA
    }:
        state[SEQUENCE] = _sequence_floor(payload)
    else:
        state[SEQUENCE] = 0
    return state


def decide_response_p1(state, model):
    decision = _previous_decide(state, model)
    if decision.get("status") != "applied" or not decision.get("selected"):
        return decision
    result = deepcopy(decision)
    sequence = _sequence_floor(model) + 1
    previous_id = str(decision.get("prediction_id") or "")
    fingerprint = hashlib.sha256(previous_id.encode("utf-8")).hexdigest()[:16]
    result["prediction_id"] = f"p1-{sequence}-{fingerprint}"
    result[TRACE] = {
        "sequence": sequence,
        "status": "reserved_until_pending_commit",
        "legacy_prediction_id": previous_id,
        "raw_dialogue_persisted": False,
        "added_model_calls": 0,
        "policy_or_surface_changed": False,
    }
    return result


def set_pending_prediction_p1(model, decision, turn_index=0):
    if not (decision or {}).get("selected"):
        return _previous_pending(model, decision, turn_index=turn_index)
    prediction_id = str((decision or {}).get("prediction_id") or "")
    sequence = _sequence_from_id(prediction_id)
    if not sequence:
        # Existing historical decisions are still readable. Fresh product
        # decisions always come through decide_response_p1.
        if any(row.get("prediction_id") == prediction_id and row.get("result_status") != "pending"
               for row in (model or {}).get("outcome_calibration_ledger_m27") or []):
            raise ValueError("P1 stale legacy prediction cannot overwrite a completed event")
        return _previous_pending(model, decision, turn_index=turn_index)
    floor = _sequence_floor(model)
    if sequence <= floor:
        pending = (model or {}).get("pending_prediction") or {}
        if pending.get("prediction_id") != prediction_id:
            raise ValueError("P1 stale prediction cannot overwrite a completed event")
        candidate = _previous_pending(model, decision, turn_index=turn_index)
        if candidate.get("pending_prediction") != pending:
            raise ValueError("P1 repeated pending commit changed event content")
        # An identical re-delivery does not overwrite a resolved ledger row or
        # mint a second observation. The source model is not mutated.
        return normalise_model_p1(model)
    if sequence != floor + 1:
        raise ValueError("P1 prediction sequence skipped the next event")
    result = _previous_pending(model, decision, turn_index=turn_index)
    result[SEQUENCE] = sequence
    return result


def install_prediction_identity_p1():
    global _previous_normalise, _previous_decide, _previous_pending
    if adaptive.decide_response is decide_response_p1:
        return False
    _previous_normalise = adaptive._normalise_model
    _previous_decide = adaptive.decide_response
    _previous_pending = adaptive.set_pending_prediction
    adaptive._normalise_model = normalise_model_p1
    adaptive.decide_response = decide_response_p1
    adaptive.set_pending_prediction = set_pending_prediction_p1
    return True
