"""Opt-in local M45 entrypoint; prior frozen entrypoints remain unchanged."""
import uruha_web_ui_m44
import uruha_web_ui as _base
from uruha_actionable_help_delivery_m45 import install_m45_action_delivery
from uruha_m45_memory_observatory import render_memory_observatory_m45

install_m45_action_delivery()
_base.render_memory_observatory = render_memory_observatory_m45
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
