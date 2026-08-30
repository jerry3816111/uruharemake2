"""Opt-in M48 Web entrypoint; M47 evidence remains frozen."""
import uruha_web_ui_m47
import uruha_web_ui as _base
from uruha_crosslingual_action_realization_m48 import (
    install_m48_crosslingual_action_realization,
    render_m48,
)

install_m48_crosslingual_action_realization()
_base.render_memory_observatory = render_m48
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
