"""Additive product entry for bounded past-statement source answers.

The status-truth entry remains unchanged so its frozen before run is still
reproducible.  This entry adds one source-bound answer interface after it.
"""

import uruha_web_ui_product_p4_status_truth as _prior
import uruha_web_ui as _base
from uruha_past_statement_source_answer_p4 import install_past_statement_source_answer_p4


install_past_statement_source_answer_p4()
RUNTIME = _prior.RUNTIME


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
