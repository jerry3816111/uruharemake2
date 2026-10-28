"""P4-O product entry layered after the released P4-N product entry."""

import uruha_web_ui_product as _product
import uruha_web_ui as _base
from uruha_persisted_reference_time_p4 import install_persisted_reference_time_p4


install_persisted_reference_time_p4()
RUNTIME = _product.RUNTIME


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
