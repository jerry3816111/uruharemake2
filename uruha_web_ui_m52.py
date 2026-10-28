"""Opt-in Web entry for M52 candidate field and surface realization."""
import uruha_web_ui_m51
import uruha_web_ui as _base
from uruha_candidate_realization_m52 import install_m52_candidate_realization, render_m52


install_m52_candidate_realization()
_base.render_memory_observatory = render_m52
RUNTIME = _base.RUNTIME


if __name__ == "__main__":
    demo = _base.build_demo(); demo.queue(default_concurrency_limit=4); RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
