#!/usr/bin/env python3
"""Exact-identity isolated product controller for the opt-in M29 priority entry."""

from pathlib import Path
from types import ModuleType

import p4_preference_fallback_launchd_control as launchd
import p4_reported_receipt_destination_detached_control as prior


ENTRYPOINT = Path(__file__).resolve().parent / "uruha_web_ui_product_p4_direct_reply_act_m29_priority.py"
_seen = set()
_pending = [prior]
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


def main(argv: list[str] | None = None) -> int:
    original_env = launchd._isolated_env

    def compute_env(layout: dict[str, Path], *, port: int | None) -> dict[str, str]:
        env = original_env(layout, port=port)
        return {**env, "URUHA_WEB_COMPUTE_LEDGER": "1"}

    launchd._isolated_env = compute_env
    try:
        return prior.base_controller.main(argv)
    finally:
        launchd._isolated_env = original_env


if __name__ == "__main__":
    raise SystemExit(main())
