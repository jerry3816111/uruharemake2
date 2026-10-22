#!/usr/bin/env python3
"""Opt in to the Web compute ledger using the frozen detached product chain.

The detached controller builds its child environment twice.  Scope the one
additional, fixed flag to this one-shot CLI invocation; all root, preflight,
sandbox, PID and listener checks remain in the existing controller.
"""

from __future__ import annotations

from pathlib import Path

import p4_preference_fallback_launchd_control as launchd
import p4_reported_receipt_destination_detached_control as latest_controller


ENTRYPOINT = Path(__file__).resolve().parent / "uruha_web_ui_product_p4_reported_receipt_destination.py"


def main(argv: list[str] | None = None) -> int:
    if latest_controller.ENTRYPOINT != ENTRYPOINT:
        raise RuntimeError("latest_product_entrypoint_changed")
    original_env = launchd._isolated_env

    def compute_env(layout: dict[str, Path], *, port: int | None) -> dict[str, str]:
        env = original_env(layout, port=port)
        return {**env, "URUHA_WEB_COMPUTE_LEDGER": "1"}

    launchd._isolated_env = compute_env
    try:
        return latest_controller.base_controller.main(argv)
    finally:
        launchd._isolated_env = original_env


if __name__ == "__main__":
    raise SystemExit(main())
