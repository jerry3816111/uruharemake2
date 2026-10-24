#!/usr/bin/env python3
"""Released additive P4-AB entry: readable P4-Z graph summaries."""

import uruha_web_ui_product_p4_z as _p4_z
import uruha_web_ui as _base
from uruha_source_proposition_graph_summary_p4 import install_source_proposition_graph_summary_p4


install_source_proposition_graph_summary_p4()
RUNTIME = _p4_z.RUNTIME


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
