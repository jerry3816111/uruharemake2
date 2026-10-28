"""Additive product entry for a source-bound simple self-preference fallback."""

import os as _os
import sys as _sys

# B opt-in must be validated before `_prior` imports the base Web module,
# which otherwise creates log/runtime/DB state during import.  Missing or
# malformed B intent fails here; no fallback to the shared Ollama endpoint.
if any(_key.upper().startswith("URUHA_P4_B_") for _key in _os.environ):
    if any(_name.startswith("uruha_web_ui") and _name != __name__
           for _name in _sys.modules):
        raise RuntimeError("p4_b_private_child_web_imported_before_bootstrap")
    from uruha_p4_b_private_child_bootstrap import bootstrap_private_child

    bootstrap_private_child()

import uruha_web_ui_product_p4_question_evidence as _prior
import uruha_web_ui as _base
from uruha_source_bound_preference_fallback_p4 import install_source_bound_preference_fallback_p4
from uruha_source_bound_third_party_statement_act_p4 import install_source_bound_third_party_statement_act_p4
from uruha_current_statement_source_authority_p4 import install_current_statement_source_authority_p4
from uruha_third_party_question_evidence_p4 import install_third_party_question_evidence_p4


install_source_bound_preference_fallback_p4()
install_source_bound_third_party_statement_act_p4()
RUNTIME = _prior.RUNTIME


if __name__ == "__main__":
    # The detached launcher's import-only preflight checks the prior frozen
    # chain; install this product-only layer only for the running UI process.
    install_current_statement_source_authority_p4()
    install_third_party_question_evidence_p4()
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
