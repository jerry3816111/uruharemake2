"""Additive P4-AY product entry layered after P4-AX."""

import uruha_web_ui_product_p4_ax as _p4_ax
import uruha_web_ui as _base
from uruha_response_form_constraint_boundary_p4 import (
    install_response_form_constraint_boundary_p4_ay,
)


install_response_form_constraint_boundary_p4_ay()
RUNTIME = _p4_ax.RUNTIME


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
