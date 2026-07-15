#!/usr/bin/env python3
"""Distinguish metalinguistic non-requests from action prohibition in V54."""

import re

from selective_discourse_state_v53 import resolve_target_state as resolve_v53


EXPLICIT_EXECUTION_PROHIBITION_RE = re.compile(
    r"(?:実行|動作)[^。！？!?]{0,12}(?:しない|しません|しないで|禁止)"
)
METALINGUISTIC_NONREQUEST_RE = re.compile(
    r"(?:指示|命令|お願い)[^。！？!?]{0,8}(?:ではない|じゃない|ではありません)"
)


def resolve_target_state(user_input, candidates, focus_target_id, mention_patterns):
    """Apply one V54 correction after the frozen V53 transition chain."""

    result = resolve_v53(user_input, candidates, focus_target_id, mention_patterns)
    if result["resolution_rule"] != "quoted_data_with_explicit_nonexecution":
        return result
    text = str(user_input or "")
    if EXPLICIT_EXECUTION_PROHIBITION_RE.search(text):
        return result
    marker = METALINGUISTIC_NONREQUEST_RE.search(text)
    if marker is None:
        return result
    return {
        **result,
        "commitment": "mentioned",
        "resolution_rule": "quoted_data_declared_nonrequest",
        "evidence": [marker.group(0)],
        "v54_correction": {
            "from": "action_prohibition",
            "to": "metalinguistic_nonrequest",
        },
    }
