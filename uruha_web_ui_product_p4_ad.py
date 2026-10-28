"""Additive P4-AD product entry layered after P4-AB."""

import uruha_web_ui_product_p4_ab as _p4_ab
import uruha_web_ui as _base
from uruha_desired_response_ambiguity_p4 import install_desired_response_ambiguity_p4


install_desired_response_ambiguity_p4()
RUNTIME = _p4_ab.RUNTIME


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
