"""Additive P4-AX product entry layered after P4-AW."""

import uruha_web_ui_product_p4_aw as _p4_aw
import uruha_web_ui as _base
from uruha_compound_feedback_request_split_p4 import (
    install_compound_feedback_request_split_p4_ax,
)


install_compound_feedback_request_split_p4_ax()
RUNTIME = _p4_aw.RUNTIME


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
