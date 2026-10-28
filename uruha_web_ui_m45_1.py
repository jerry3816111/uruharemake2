"""Opt-in M45.1; frozen M45 first results remain reproducible."""
import uruha_web_ui_m45
import uruha_web_ui as _base
from uruha_task_evidence_authorization_m45_1 import install_m45_1_task_evidence, render_m45_1

install_m45_1_task_evidence()
_base.render_memory_observatory = render_m45_1
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
