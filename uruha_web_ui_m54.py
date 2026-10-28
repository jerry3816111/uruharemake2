"""Opt-in Web entry for the M54 human-response equation contract."""

import uruha_web_ui_m53
import uruha_web_ui as _base
from uruha_human_response_equation_m54 import install_m54_human_response_equation, render_m54


install_m54_human_response_equation()
_base.render_memory_observatory = render_m54
RUNTIME = _base.RUNTIME


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
