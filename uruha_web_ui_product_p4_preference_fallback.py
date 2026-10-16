"""Additive product entry for a source-bound simple self-preference fallback."""

import uruha_web_ui_product_p4_question_evidence as _prior
import uruha_web_ui as _base
from uruha_source_bound_preference_fallback_p4 import install_source_bound_preference_fallback_p4
from uruha_source_bound_third_party_statement_act_p4 import install_source_bound_third_party_statement_act_p4


install_source_bound_preference_fallback_p4()
install_source_bound_third_party_statement_act_p4()
RUNTIME = _prior.RUNTIME


if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(
        server_name=_base.WEB_SERVER_NAME,
        server_port=_base.WEB_SERVER_PORT,
        inbrowser=False,
        css=_base.WEB_CSS,
        head=_base.WEB_HEAD,
    )
