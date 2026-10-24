"""Opt-in M46 Web entrypoint; earlier M45 evidence remains frozen."""
import uruha_web_ui_m45_2
import uruha_web_ui as _base
from uruha_goal_progress_delivery_m46 import install_m46_goal_progress_delivery, render_m46

install_m46_goal_progress_delivery()
_base.render_memory_observatory = render_m46
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
