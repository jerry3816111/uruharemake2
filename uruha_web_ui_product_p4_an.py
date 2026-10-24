"""Additive P4-AN product entry layered after the preserved P4-AM result."""

import uruha_web_ui_product_p4_am as _p4_am
import uruha_web_ui as _base
from uruha_post_turn_temporal_graph_delivery_p4 import install_post_turn_temporal_graph_delivery_p4


install_post_turn_temporal_graph_delivery_p4()
RUNTIME = _p4_am.RUNTIME


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
