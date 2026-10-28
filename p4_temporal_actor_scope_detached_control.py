#!/usr/bin/env python3
"""Reuse the existing private localhost lifecycle for the actor/scope entry."""

from pathlib import Path

import p4_hash_prefix_transport_detached_control as prior_controller
import p4_hash_prefix_gate_detached_control as hash_controller
import p4_reported_offer_scope_detached_control as reported_controller
import p4_offer_action_detached_control as action_controller
import p4_preference_fallback_detached_control as base_controller
import p4_preference_fallback_safe_isolated_product_launcher as launcher


ENTRYPOINT = Path(__file__).resolve().parent / "uruha_web_ui_product_p4_temporal_actor_scope.py"
prior_controller.ENTRYPOINT = ENTRYPOINT
hash_controller.ENTRYPOINT = ENTRYPOINT
reported_controller.ENTRYPOINT = ENTRYPOINT
action_controller.ENTRYPOINT = ENTRYPOINT
base_controller.ENTRYPOINT = ENTRYPOINT
launcher.ENTRYPOINT = ENTRYPOINT


if __name__ == "__main__":
    raise SystemExit(base_controller.main())
