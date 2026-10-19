"""Opt-in P4 correction for Japanese repair interjections in speech planning.

The legacy classifier treats every occurrence of the character ``え`` as a
request to repair the conversation.  This wrapper only narrows that one cue;
it does not generate a reply or alter the selected semantic plan.
"""

from __future__ import annotations

import os
import re

from uruha_location_advice_act_handoff_p4 import _outside_quotes


_FLAG = "URUHA_P4_REPAIR_CUE_BOUNDARY"
_OTHER_REPAIR_CUES = ("蛤", "huh", "啥", "什麼意思", "什么意思")
_STANDALONE_E = re.compile(r"(?:^|[\s、，。.!！?？])え(?=$|[\s、，。.!！?？])")
_INSTALLED = False
_ORIGINAL_DIALOGUE_ACT = None


def dialogue_act_with_repair_cue_boundary_p4(self, logic_data, user_input):
    """Preserve every old branch except an embedded ``え`` false positive."""
    if _ORIGINAL_DIALOGUE_ACT is None:
        raise RuntimeError("Repair-cue boundary is not installed")
    original_act = _ORIGINAL_DIALOGUE_ACT(self, logic_data, user_input)
    if os.environ.get(_FLAG) != "1" or original_act != "repair_check":
        return original_act
    raw = str(user_input or "")
    lowered = raw.lower()
    if "え" not in raw or any(cue in lowered for cue in _OTHER_REPAIR_CUES):
        return original_act
    outside, _, _ = _outside_quotes(raw)
    if _STANDALONE_E.search(outside):
        return original_act
    return "direct_chat_answer"


def install_repair_cue_boundary_p4() -> bool:
    """Install once in the isolated product process; flag-off is inert."""
    global _INSTALLED, _ORIGINAL_DIALOGUE_ACT
    if _INSTALLED:
        return False
    from uruha_brain_mac import RightBrain

    _ORIGINAL_DIALOGUE_ACT = RightBrain._dialogue_act_from_plan
    RightBrain._dialogue_act_from_plan = dialogue_act_with_repair_cue_boundary_p4
    _INSTALLED = True
    return True


__all__ = ["dialogue_act_with_repair_cue_boundary_p4", "install_repair_cue_boundary_p4"]
