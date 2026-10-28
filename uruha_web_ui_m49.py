"""Opt-in M49 Web entrypoint; M48 evidence remains frozen."""
import uruha_web_ui_m48
import uruha_web_ui as _base
from uruha_route_qualified_task_handoff_m49 import (
    install_m49_route_qualified_task_handoff,
    render_m49,
)

install_m49_route_qualified_task_handoff()
_base.render_memory_observatory = render_m49
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
