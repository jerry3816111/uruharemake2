#!/usr/bin/env python3
"""Exact-identity isolated product controller for the opt-in M29 priority entry."""

from pathlib import Path
from types import ModuleType
import argparse
import sys

import p4_preference_fallback_launchd_control as launchd
import p4_reported_receipt_destination_detached_control as prior
import p4_preference_fallback_safe_isolated_product_launcher as product_launcher
import p4_b_safe_isolated_product_launcher as base_launcher


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
    arm_parser = argparse.ArgumentParser(add_help=False)
    arm_parser.add_argument("--direct-act-arm", choices=("control", "treatment"), default="control")
    arm_parser.add_argument("--product-port", type=int, default=7894)
    arm_parser.add_argument("--turn-admission-journal", action="store_true")
    arm_parser.add_argument("--repair-cue-boundary", action="store_true")
    arm_parser.add_argument("--compact-json-schema", action="store_true")
    arm_args, forwarded = arm_parser.parse_known_args(sys.argv[1:] if argv is None else argv)
    try:
        selected_port = base_launcher.validate_port(arm_args.product_port)
    except base_launcher.LauncherError as exc:
        arm_parser.error(str(exc))
    # The arm is a child-process setting for a product start, never a generic
    # process-global option and never inherited from the invoking shell.
    # Parse only the two fields needed to scope the child flag.  The actual
    # detached controller (not launchd's different parser) owns validation of
    # prepare/start/status/stop and prepared-root arguments.
    scope_parser = argparse.ArgumentParser(add_help=False)
    scope_parser.add_argument("action", nargs="?")
    scope_parser.add_argument("--mode", choices=("product", "inert"), default="product")
    request, _ = scope_parser.parse_known_args(forwarded)
    product_start = request.action == "start" and request.mode == "product"
    if arm_args.direct_act_arm == "treatment" and not product_start:
        arm_parser.error("treatment requires start --mode product")
    if arm_args.turn_admission_journal and not product_start:
        arm_parser.error("turn admission journal requires start --mode product")
    if arm_args.repair_cue_boundary and not product_start:
        arm_parser.error("repair cue boundary requires start --mode product")
    if arm_args.compact_json_schema and not product_start:
        arm_parser.error("compact JSON schema requires start --mode product")
    original_env = launchd._isolated_env
    original_preflight = product_launcher.preflight_preference_fallback
    original_port = prior.base_controller.PORT

    def compute_env(layout: dict[str, Path], *, port: int | None) -> dict[str, str]:
        env = original_env(layout, port=port)
        env = {**env, "URUHA_WEB_COMPUTE_LEDGER": "1"}
        if product_start:
            env.update({
                "URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM": arm_args.direct_act_arm,
                "URUHA_WEB_PREWARM_BRAIN": "1",
                "URUHA_WEB_ACTIVE_DB_RECEIPT_PATH": str(
                    layout["runtime_root"] / "active_db_receipt.json"
                ),
            })
            if arm_args.turn_admission_journal:
                env["URUHA_WEB_TURN_ADMISSION_JOURNAL_PATH"] = str(
                    layout["runtime_root"] / "turn_admission_journal.jsonl"
                )
            if arm_args.repair_cue_boundary and port is not None:
                env["URUHA_P4_REPAIR_CUE_BOUNDARY"] = "1"
            if arm_args.compact_json_schema and port is not None:
                env["URUHA_P4_COMPACT_JSON_SCHEMA"] = "1"
        return env

    # The base controller consistently uses PORT for prepared receipts,
    # listener identity, HTTP readiness and exact stop. Scope an opt-in port
    # to this one CLI call so its default and other wrappers remain unchanged.
    prior.base_controller.PORT = selected_port
    launchd._isolated_env = compute_env
    try:
        if product_start:
            # The detached base controller explicitly invokes preflight with
            # prewarm=False and filters the final environment through that result.
            # Scope the override to this one product start, for both arms alike.
            def same_arm_preflight(**kwargs):
                summary, env, layout, created, profile = original_preflight(
                    **{**kwargs, "prewarm": True}
                )
                if arm_args.repair_cue_boundary:
                    # Preflight uses port=None and must not see the repair flag.
                    # Only the returned environment for the actual Web child
                    # receives it; launchd's port-scoped allowlist retains it.
                    env = {**env, "URUHA_P4_REPAIR_CUE_BOUNDARY": "1"}
                if arm_args.compact_json_schema:
                    # Same child-only scoping as the repair flag: the pure
                    # preflight environment cannot activate model generation.
                    env = {**env, "URUHA_P4_COMPACT_JSON_SCHEMA": "1"}
                return summary, env, layout, created, profile

            product_launcher.preflight_preference_fallback = same_arm_preflight
        return prior.base_controller.main(forwarded)
    finally:
        launchd._isolated_env = original_env
        product_launcher.preflight_preference_fallback = original_preflight
        prior.base_controller.PORT = original_port


if __name__ == "__main__":
    raise SystemExit(main())
