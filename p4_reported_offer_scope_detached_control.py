#!/usr/bin/env python3
"""Reuse exact-PID isolated lifecycle; only the product entrypoint differs."""

from pathlib import Path

import p4_offer_action_detached_control as controller
import p4_preference_fallback_detached_control as base_controller
import p4_preference_fallback_safe_isolated_product_launcher as launcher


ENTRYPOINT = Path(__file__).resolve().parent / "uruha_web_ui_product_p4_reported_offer_scope.py"
controller.ENTRYPOINT = ENTRYPOINT
base_controller.ENTRYPOINT = ENTRYPOINT
launcher.ENTRYPOINT = ENTRYPOINT


if __name__ == "__main__":
    raise SystemExit(base_controller.main())
