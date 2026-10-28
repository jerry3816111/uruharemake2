"""Isolated opt-in product entry for mixed past-place source authorization."""

import os

import uruha_web_ui_product_p4_explicit_rewrite_action as _prior
from uruha_brain_mac import UruhaBrainV4_Mac
from uruha_explicit_rewrite_action_p4 import install_explicit_rewrite_action_p4
from uruha_location_advice_act_handoff_p4 import install_location_advice_act_handoff_p4
from uruha_mixed_past_place_source_authority_p4 import install_mixed_past_place_source_authority_p4
from uruha_repair_cue_boundary_p4 import install_repair_cue_boundary_p4


RUNTIME = _prior.RUNTIME


if __name__ == "__main__":
    os.environ["URUHA_P4_LOCATION_ADVICE_FORMAL_SURFACE"] = "1"
    os.environ["URUHA_P4_CREDENTIAL_PAPER_VISIBLE"] = "1"
    os.environ["URUHA_P4_REPAIR_CUE_BOUNDARY"] = "1"
    os.environ["URUHA_P4_EXPLICIT_REWRITE_ACTION"] = "1"
    os.environ["URUHA_P4_MIXED_PAST_PLACE_SOURCE_AUTHORITY"] = "1"
    _prior._prior._legacy.install_current_statement_source_authority_p4()
    _prior._prior._legacy.install_third_party_question_evidence_p4()
    _prior._prior._legacy.install_selected_offer_action_surface_fidelity_p4()
    _prior._prior._legacy.install_reported_offer_source_scope_p4()
    _prior._prior._legacy.install_hash_prefix_provenance_gate_p4()
    _prior._prior._legacy.install_hash_prefix_event_transport_p4()
    _prior._prior._legacy.install_temporal_actor_scope_p4()
    _prior._prior._legacy.install_reported_ack_m31_priority_p4()
    _prior._prior._legacy.install_reported_ack_route_admission_p4()
    _prior._prior._legacy.install_reported_ack_selected_visible_p4()
    _prior._prior._legacy.install_explicit_episode_recall_focus_p4()
    _prior._prior._legacy.install_quoted_line_act_scope_p4()
    _prior._prior._legacy.install_relationship_context_answer_authority_p4()
    _prior._prior._legacy.install_temporal_specific_recall_admission_p4()
    _prior._prior._legacy.install_terminal_copula_commit_latency_p4()
    _prior._prior._typed.install_typed_episode_recall_source_p4()
    _prior._prior._deterministic.install_deterministic_plan_leak_surface_p4()
    _prior._prior._reference.install_reference_probe_evidence_p4()
    _prior._prior._local_fact.install_local_fact_answer_authority_p4()
    install_location_advice_act_handoff_p4()
    install_repair_cue_boundary_p4()
    install_explicit_rewrite_action_p4(UruhaBrainV4_Mac)
    install_mixed_past_place_source_authority_p4()
    demo = _prior._prior._legacy._base.build_demo()
    demo.queue(default_concurrency_limit=4)
    RUNTIME.start_brain_prewarm()
    demo.launch(
        server_name=_prior._prior._legacy._base.WEB_SERVER_NAME,
        server_port=_prior._prior._legacy._base.WEB_SERVER_PORT,
        inbrowser=False,
        css=_prior._prior._legacy._base.WEB_CSS,
        head=_prior._prior._legacy._base.WEB_HEAD,
    )
