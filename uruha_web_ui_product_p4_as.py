"""Additive P4-AS product entry layered after P4-AR."""

import uruha_web_ui_product_p4_ar as _p4_ar
import uruha_web_ui as _base
from uruha_selected_action_surface_execution_p4 import install_selected_action_surface_execution_p4


install_selected_action_surface_execution_p4()
RUNTIME = _p4_ar.RUNTIME


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
