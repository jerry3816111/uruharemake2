"""Additive P4-AZ product entry layered after P4-AY."""

import uruha_web_ui_product_p4_ay as _p4_ay
import uruha_web_ui as _base
from uruha_previous_turn_cjk_ellipsis_authority_p4 import (
    install_previous_turn_cjk_ellipsis_authority_p4_az,
)


install_previous_turn_cjk_ellipsis_authority_p4_az()
RUNTIME = _p4_ay.RUNTIME


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
