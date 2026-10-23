"""Opt-in P4 product entry: retained compute ledger plus direct-reply-act priority."""

import uruha_web_ui_product_p4_reported_receipt_destination as _prior
import uruha_web_ui as base
from uruha_direct_reply_act_m29_priority_p4 import install_direct_reply_act_m29_priority_p4


RUNTIME = _prior.RUNTIME


def install_product_chain() -> None:
    """Install the frozen product overlays, then the new M29 admission gate."""
    current = _prior._prior
    local = current._prior
    reference = local._prior
    deterministic = reference._prior
    typed = deterministic._prior
    terminal = typed._prior
    terminal.install_current_statement_source_authority_p4()
    terminal.install_third_party_question_evidence_p4()
    terminal.install_selected_offer_action_surface_fidelity_p4()
    terminal.install_reported_offer_source_scope_p4()
    terminal.install_hash_prefix_provenance_gate_p4()
    terminal.install_hash_prefix_event_transport_p4()
    terminal.install_temporal_actor_scope_p4()
    terminal.install_reported_ack_m31_priority_p4()
    terminal.install_reported_ack_route_admission_p4()
    terminal.install_reported_ack_selected_visible_p4()
    terminal.install_explicit_episode_recall_focus_p4()
    terminal.install_quoted_line_act_scope_p4()
    terminal.install_relationship_context_answer_authority_p4()
    terminal.install_temporal_specific_recall_admission_p4()
    terminal.install_terminal_copula_commit_latency_p4()
    typed.install_typed_episode_recall_source_p4()
    deterministic.install_deterministic_plan_leak_surface_p4()
    reference.install_reference_probe_evidence_p4()
    local.install_local_fact_answer_authority_p4()
    current.install_current_decision_ack_authority_p4()
    _prior.install_reported_receipt_destination_relation_p4()
    install_direct_reply_act_m29_priority_p4()


if __name__ == "__main__":
    install_product_chain()
    demo = base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(
        server_name=base.WEB_SERVER_NAME,
        server_port=base.WEB_SERVER_PORT,
        inbrowser=False,
        css=base.WEB_CSS,
        head=base.WEB_HEAD,
    )
