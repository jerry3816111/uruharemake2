"""Additive P4-AW product entry layered after P4-AV."""

import uruha_web_ui_product_p4_av as _p4_av
import uruha_web_ui as _base
from uruha_cjk_subject_ellipsis_action_authority_p4 import (
    install_cjk_subject_ellipsis_action_authority_p4_aw,
)


install_cjk_subject_ellipsis_action_authority_p4_aw()
RUNTIME = _p4_av.RUNTIME


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
