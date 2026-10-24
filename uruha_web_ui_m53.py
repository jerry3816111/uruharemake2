"""Opt-in Web entry for M53 source-neutral scaffold authorization."""
import uruha_web_ui_m52
import uruha_web_ui as _base
from uruha_source_neutral_scaffold_m53 import install_m53_source_neutral_scaffold, render_m53


install_m53_source_neutral_scaffold(); _base.render_memory_observatory = render_m53; RUNTIME = _base.RUNTIME


if __name__ == "__main__":
    demo = _base.build_demo(); demo.queue(default_concurrency_limit=4); RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
