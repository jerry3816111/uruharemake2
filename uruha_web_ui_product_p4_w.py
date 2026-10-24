"""Additive P4-W product entry layered after the released P4-V entry."""

import uruha_web_ui_product_p4_v as _p4_v
import uruha_web_ui as _base
from uruha_frame_preserving_visible_repair_p4 import install_frame_preserving_visible_repair_p4


install_frame_preserving_visible_repair_p4()
RUNTIME = _p4_v.RUNTIME


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
