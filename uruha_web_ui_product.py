"""Current opt-in product entry; frozen research entrypoints remain unchanged."""
import uruha_web_ui_m54
import uruha_web_ui as _base
from uruha_prediction_identity_p1 import install_prediction_identity_p1

install_prediction_identity_p1()
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
