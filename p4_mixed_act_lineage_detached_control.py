#!/usr/bin/env python3
"""Reuse exact-identity localhost lifecycle for the mixed-act lineage entry."""

from pathlib import Path
from types import ModuleType

import p4_mixed_past_place_source_authority_detached_control as prior_controller
import p4_preference_fallback_detached_control as base_controller


ENTRYPOINT = Path(__file__).resolve().parent / "uruha_web_ui_product_p4_mixed_act_lineage.py"
_seen = set()
_pending = [prior_controller, base_controller]
while _pending:
    controller = _pending.pop()
    if controller.__name__ in _seen:
        continue
    _seen.add(controller.__name__)
    controller.ENTRYPOINT = ENTRYPOINT
    for name in (
        "prior_controller", "actor_controller", "transport_controller",
        "gate_controller", "reported_controller", "action_controller",
        "base_controller", "launcher",
    ):
        dependency = getattr(controller, name, None)
        if isinstance(dependency, ModuleType) and dependency.__name__.startswith("p4_"):
            _pending.append(dependency)


if __name__ == "__main__":
    raise SystemExit(base_controller.main())
