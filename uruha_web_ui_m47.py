"""Opt-in M47 Web entrypoint; M46 evidence remains frozen."""
import uruha_web_ui_m46
import uruha_web_ui as _base
from uruha_crosslingual_help_routing_m47 import (
    install_m47_crosslingual_help_routing,
    render_m47,
)

install_m47_crosslingual_help_routing()
_base.render_memory_observatory = render_m47
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
