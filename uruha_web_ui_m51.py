"""Opt-in Web entry for M51 bounded candidate generation."""
import uruha_web_ui_m50
import uruha_web_ui as _base
from uruha_state_changing_candidates_m51 import install_m51_state_changing_candidates, render_m51


install_m51_state_changing_candidates()
_base.render_memory_observatory = render_m51
RUNTIME = _base.RUNTIME


if __name__ == "__main__":
    demo = _base.build_demo(); demo.queue(default_concurrency_limit=4); RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
