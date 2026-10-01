"""Isolated opt-in M44 entrypoint; frozen M37-M43 entrypoints unchanged."""
import uruha_web_ui_m43
import uruha_web_ui as _base
from uruha_executed_action_receipt_m44 import install_m44_executed_action_receipts
from uruha_m44_memory_observatory import render_memory_observatory_m44

install_m44_executed_action_receipts()
_base.render_memory_observatory = render_memory_observatory_m44
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
