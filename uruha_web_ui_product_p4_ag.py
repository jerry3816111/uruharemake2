"""Additive P4-AG product entry layered after P4-AF."""

import uruha_web_ui_product_p4_af as _p4_af
import uruha_web_ui as _base
from uruha_desired_response_outcome_binding_p4 import install_desired_response_outcome_binding_p4


install_desired_response_outcome_binding_p4()
RUNTIME = _p4_af.RUNTIME


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
