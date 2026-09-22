"""Additive P4-V product entry layered after the released P4-T entry."""

import uruha_web_ui_product_p4_t as _p4_t
import uruha_web_ui as _base
from uruha_utterance_frame_shadow_extension_p4 import install_utterance_frame_coverage_extension_p4


install_utterance_frame_coverage_extension_p4()
RUNTIME = _p4_t.RUNTIME


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
