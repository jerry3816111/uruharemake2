"""Additive product entry for bounded selected food-offer surface fidelity."""

import uruha_web_ui_product_p4_preference_fallback as _prior
import uruha_web_ui as _base
from uruha_current_statement_source_authority_p4 import install_current_statement_source_authority_p4
from uruha_third_party_question_evidence_p4 import install_third_party_question_evidence_p4
from uruha_selected_offer_action_surface_fidelity_p4 import (
    install_selected_offer_action_surface_fidelity_p4,
)


RUNTIME = _prior.RUNTIME


if __name__ == "__main__":
    install_current_statement_source_authority_p4()
    install_third_party_question_evidence_p4()
    install_selected_offer_action_surface_fidelity_p4()
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
