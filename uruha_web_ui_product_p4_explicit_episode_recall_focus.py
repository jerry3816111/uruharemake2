"""Opt-in P4 product entry for source-bound explicit episode recall."""

import uruha_web_ui_product_p4_reported_ack_selected_visible as _prior
import uruha_web_ui as _base
from uruha_current_statement_source_authority_p4 import install_current_statement_source_authority_p4
from uruha_third_party_question_evidence_p4 import install_third_party_question_evidence_p4
from uruha_selected_offer_action_surface_fidelity_p4 import install_selected_offer_action_surface_fidelity_p4
from uruha_reported_offer_source_scope_p4 import install_reported_offer_source_scope_p4
from uruha_hash_prefix_provenance_gate_p4 import install_hash_prefix_provenance_gate_p4
from uruha_hash_prefix_event_transport_p4 import install_hash_prefix_event_transport_p4
from uruha_temporal_actor_scope_p4 import install_temporal_actor_scope_p4
from uruha_reported_ack_m31_priority_p4 import install_reported_ack_m31_priority_p4
from uruha_reported_ack_route_admission_p4 import install_reported_ack_route_admission_p4
from uruha_reported_ack_selected_visible_p4 import install_reported_ack_selected_visible_p4
from uruha_explicit_episode_recall_focus_p4 import install_explicit_episode_recall_focus_p4


RUNTIME = _prior.RUNTIME


if __name__ == "__main__":
    install_current_statement_source_authority_p4()
    install_third_party_question_evidence_p4()
    install_selected_offer_action_surface_fidelity_p4()
    install_reported_offer_source_scope_p4()
    install_hash_prefix_provenance_gate_p4()
    install_hash_prefix_event_transport_p4()
    install_temporal_actor_scope_p4()
    install_reported_ack_m31_priority_p4()
    install_reported_ack_route_admission_p4()
    install_reported_ack_selected_visible_p4()
    install_explicit_episode_recall_focus_p4()
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
