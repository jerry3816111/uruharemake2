#!/usr/bin/env python3
"""Reuse private localhost lifecycle for explicit episode recall probe."""

from pathlib import Path

import p4_reported_ack_selected_visible_detached_control as prior_controller


ENTRYPOINT = Path(__file__).resolve().parent / "uruha_web_ui_product_p4_explicit_episode_recall_focus.py"
for controller in (
    prior_controller,
    prior_controller.prior_controller,
    prior_controller.actor_controller,
    prior_controller.transport_controller,
    prior_controller.gate_controller,
    prior_controller.reported_controller,
    prior_controller.action_controller,
    prior_controller.base_controller,
    prior_controller.launcher,
):
    controller.ENTRYPOINT = ENTRYPOINT


if __name__ == "__main__":
    raise SystemExit(prior_controller.base_controller.main())
