"""Project a generic content-unit realization obligation into a RightBrain payload."""

from __future__ import annotations

from copy import deepcopy


SCHEMA = "uruha_rightbrain_realization_obligation_v11"
FIELD = "realization_obligation"

# This contract adds no semantic content. It changes only the requiredness of the
# content units that the LeftBrain already supplied.
OBLIGATION = {
    "schema": SCHEMA,
    "source": "leftbrain_plan.content_units",
    "coverage": "every_content_unit",
    "criterion": "make_each_intended_communicative_effect_evident",
    "verbalization": "natural_reply_not_planning_language",
    "omission": "forbidden_unless_required_or_safety_contract_conflicts",
}


def project(payload_data):
    """Return a copy with one generic realization obligation on the existing plan."""
    payload = deepcopy(payload_data) if isinstance(payload_data, dict) else {}
    leftbrain_plan = deepcopy(payload.get("leftbrain_plan") or {})
    leftbrain_plan[FIELD] = deepcopy(OBLIGATION)
    payload["leftbrain_plan"] = leftbrain_plan
    return payload

def remove(payload_data):
    """Remove the V11-only field for paired identity checks."""
    payload = deepcopy(payload_data) if isinstance(payload_data, dict) else {}
    leftbrain_plan = deepcopy(payload.get("leftbrain_plan") or {})
    leftbrain_plan.pop(FIELD, None)
    payload["leftbrain_plan"] = leftbrain_plan
    return payload
