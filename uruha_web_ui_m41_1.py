"""M41 plus same-cycle history mirror repair; local-only entrypoint."""
import uruha_web_ui_m41
import uruha_web_ui as _base
from uruha_trace_history_sync_m41_1 import install_m41_1_history_sync

install_m41_1_history_sync()
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME,server_port=_base.WEB_SERVER_PORT,
                inbrowser=False,css=_base.WEB_CSS,head=_base.WEB_HEAD)
