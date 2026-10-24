"""Opt-in Web entry for M50 current-task source composition."""
import uruha_web_ui_m49
import uruha_web_ui as _base
from uruha_current_task_source_bundle_m50 import (
    install_m50_current_task_source_bundle,
    render_m50,
)


install_m50_current_task_source_bundle()
_base.render_memory_observatory = render_m50
RUNTIME = _base.RUNTIME


if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
