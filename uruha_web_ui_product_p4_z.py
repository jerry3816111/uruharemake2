"""Additive P4-Z product entry layered after the released P4-Y entry."""

import uruha_web_ui_product_p4_y as _p4_y
import uruha_web_ui as _base
from uruha_source_bound_proposition_preservation_p4 import install_source_bound_proposition_preservation_p4


install_source_bound_proposition_preservation_p4()
RUNTIME = _p4_y.RUNTIME


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
