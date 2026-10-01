"""Additive P4-Y product entry layered after the released P4-W entry."""

import uruha_web_ui_product_p4_w as _p4_w
import uruha_web_ui as _base
from uruha_runtime_graph_trace_delivery_p4 import install_runtime_graph_trace_delivery_p4


install_runtime_graph_trace_delivery_p4()
RUNTIME = _p4_w.RUNTIME


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
