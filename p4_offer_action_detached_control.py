#!/usr/bin/env python3
"""Reuse the existing exact-PID isolated controller for the new product entry.

Only the frozen entrypoint identity changes.  Lifecycle, sandbox, reuse-tree,
ready and planned-stop checks stay in the already tested prior controller.
"""

from pathlib import Path

import p4_preference_fallback_detached_control as controller
import p4_preference_fallback_safe_isolated_product_launcher as launcher


ENTRYPOINT = Path(__file__).resolve().parent / "uruha_web_ui_product_p4_offer_action.py"
controller.ENTRYPOINT = ENTRYPOINT
launcher.ENTRYPOINT = ENTRYPOINT


if __name__ == "__main__":
    raise SystemExit(controller.main())
