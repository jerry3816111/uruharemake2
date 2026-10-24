"""Additive P4-AT product entry layered after P4-AS."""

import uruha_web_ui_product_p4_as as _p4_as
import uruha_web_ui as _base
from uruha_executed_action_outcome_closure_p4 import install_executed_action_outcome_closure_p4


install_executed_action_outcome_closure_p4()
RUNTIME = _p4_as.RUNTIME


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
