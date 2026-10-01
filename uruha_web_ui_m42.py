"""M42 isolated local UI; frozen earlier entrypoints stay unchanged."""
import uruha_web_ui_m41_1
import uruha_web_ui as _base
from uruha_cjk_relationship_evidence_m42 import install_m42_relationship_evidence
from uruha_m42_memory_observatory import render_memory_observatory_m42

install_m42_relationship_evidence()
_base.render_memory_observatory = render_memory_observatory_m42
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME,server_port=_base.WEB_SERVER_PORT,
                inbrowser=False,css=_base.WEB_CSS,head=_base.WEB_HEAD)
