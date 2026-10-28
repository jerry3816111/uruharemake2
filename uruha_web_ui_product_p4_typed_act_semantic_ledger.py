"""Isolated opt-in Web entry for the bounded two-act semantic ledger.

Reuse the existing typed mixed-act product stack; this file changes only the
terminal realization flag and does not duplicate the HTTP/UI handler.
"""

import os
import runpy


if __name__ == "__main__":
    os.environ["URUHA_P4_TYPED_ACT_SEMANTIC_LEDGER"] = "1"
    runpy.run_module("uruha_web_ui_product_p4_typed_mixed_atomic_delivery", run_name="__main__")
