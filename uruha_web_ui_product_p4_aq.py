"""Additive P4-AQ product entry layered after P4-AP."""

import uruha_web_ui_product_p4_ap as _p4_ap
import uruha_web_ui as _base
from uruha_live_extended_trigger_ordering_p4 import install_live_extended_trigger_ordering_p4


install_live_extended_trigger_ordering_p4()
RUNTIME = _p4_ap.RUNTIME


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
