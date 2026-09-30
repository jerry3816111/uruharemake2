"""Current product entry with truthful read-only tool failure metadata.

The historical P4-C and P4-AZ entries remain immutable for their frozen results.
"""

import uruha_web_ui_product_p4_az as _prior
import uruha_web_ui as _base
from uruha_product_tool_failure_truth_p4 import install_product_tool_failure_truth_p4


install_product_tool_failure_truth_p4(_base)
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
