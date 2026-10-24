"""M43 unchanged cognition plus visually verified presentation-only overlay."""
import uruha_web_ui_m43
import uruha_web_ui as _base
from uruha_m43_readable_memory_observatory import render_readable_memory_observatory_m43

_base.render_memory_observatory = render_readable_memory_observatory_m43
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME,server_port=_base.WEB_SERVER_PORT,
                inbrowser=False,css=_base.WEB_CSS,head=_base.WEB_HEAD)
