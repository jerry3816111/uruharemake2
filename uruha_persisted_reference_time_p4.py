"""Additive P4-O adapter sharing one validity instant across P4-N reads.

P4-N is already bound to released evidence and remains byte-for-byte intact.
This adapter only supplies one effective non-null reference time to the whole
P4-N path when its caller omits the argument.
"""

from __future__ import annotations

import datetime

import uruha_source_bound_japanese_value_surface_p4 as p4n
import uruha_typed_current_preference_recall_p4 as p4j


LABEL = "persisted_reference_time_p4"
SCHEMA = "uruha_persisted_reference_time_p4"
_INSTALLED = False
_BASE_BUILD = p4n.build_source_bound_japanese_value_surface_p4


def build_with_persisted_reference_time_p4(
    user_input, profile_collection, *, reference_time=None
):
    effective_reference_time = reference_time or datetime.datetime.now().astimezone().isoformat(
        timespec="microseconds"
    )
    return _BASE_BUILD(
        user_input,
        profile_collection,
        reference_time=effective_reference_time,
    )


def install_persisted_reference_time_p4():
    global _INSTALLED
    if _INSTALLED:
        return False
    p4j.build_typed_current_preference_recall_contract_p4 = (
        build_with_persisted_reference_time_p4
    )
    _INSTALLED = True
    return True
