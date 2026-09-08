"""Current opt-in product entry; frozen research entrypoints remain unchanged."""
import os
import uruha_web_ui_m54
import uruha_web_ui as _base
import uruha_brain_mac as _brain
from uruha_prediction_identity_p1 import install_prediction_identity_p1
from uruha_grounded_validation_p2 import install_grounded_validation_p2
from uruha_compact_planner_p2 import install_compact_planner_p2, product_planner_budget
from uruha_contextual_expression_commit_p2 import install_contextual_expression_commit_p2
from uruha_current_request_authority_p2 import install_current_request_authority_p2

# Product-only resource contract. Do not import this entry in a frozen formal
# experiment interpreter. Existing research entrypoints retain their own budget.
_brain.LEFT_BRAIN_SLOW_PATH_BUDGET_SECONDS = product_planner_budget(os.environ.get("URUHA_PRODUCT_PLANNER_BUDGET_SECONDS", "20"))
install_prediction_identity_p1()
install_grounded_validation_p2()
install_compact_planner_p2()
install_contextual_expression_commit_p2()
install_current_request_authority_p2()
RUNTIME = _base.RUNTIME

if __name__ == "__main__":
    demo = _base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(server_name=_base.WEB_SERVER_NAME, server_port=_base.WEB_SERVER_PORT,
                inbrowser=False, css=_base.WEB_CSS, head=_base.WEB_HEAD)
