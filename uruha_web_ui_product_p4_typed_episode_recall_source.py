"""Opt-in product Web entry for typed episode-source explicit recall."""

import uruha_web_ui_product_p4_terminal_copula_commit_latency as _prior
from uruha_typed_episode_recall_source_p4 import install_typed_episode_recall_source_p4


RUNTIME = _prior.RUNTIME


if __name__ == "__main__":
    _prior.install_current_statement_source_authority_p4()
    _prior.install_third_party_question_evidence_p4()
    _prior.install_selected_offer_action_surface_fidelity_p4()
    _prior.install_reported_offer_source_scope_p4()
    _prior.install_hash_prefix_provenance_gate_p4()
    _prior.install_hash_prefix_event_transport_p4()
    _prior.install_temporal_actor_scope_p4()
    _prior.install_reported_ack_m31_priority_p4()
    _prior.install_reported_ack_route_admission_p4()
    _prior.install_reported_ack_selected_visible_p4()
    _prior.install_explicit_episode_recall_focus_p4()
    _prior.install_quoted_line_act_scope_p4()
    _prior.install_relationship_context_answer_authority_p4()
    _prior.install_temporal_specific_recall_admission_p4()
    _prior.install_terminal_copula_commit_latency_p4()
    install_typed_episode_recall_source_p4()
    demo = _prior._base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(
        server_name=_prior._base.WEB_SERVER_NAME,
        server_port=_prior._base.WEB_SERVER_PORT,
        inbrowser=False,
        css=_prior._base.WEB_CSS,
        head=_prior._base.WEB_HEAD,
    )
