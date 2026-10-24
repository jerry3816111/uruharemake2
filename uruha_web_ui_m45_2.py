"""Opt-in extraction-contract repair; no production entrypoint change."""
import uruha_web_ui_m45_1
import uruha_web_ui as _base
from uruha_action_extraction_contract_m45_2 import install_m45_2_extraction_contract, render_m45_2

install_m45_2_extraction_contract()
_base.render_memory_observatory = render_m45_2
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
