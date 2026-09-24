"""Additive P4-AR product entry layered after P4-AQ."""

import uruha_web_ui_product_p4_aq as _p4_aq
import uruha_web_ui as _base
from uruha_executed_action_identity_gate_p4 import install_executed_action_identity_gate_p4


install_executed_action_identity_gate_p4()
RUNTIME = _p4_aq.RUNTIME


if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(
        server_name=_base.WEB_SERVER_NAME,
        server_port=_base.WEB_SERVER_PORT,
        inbrowser=False,
        css=_base.WEB_CSS,
        head=_base.WEB_HEAD,
    )
