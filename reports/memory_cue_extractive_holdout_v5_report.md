# Memory cue-driven fallback V5 untouched holdout

## Decision

- Complete: `True` (72/72)
- Decision: `replicated_efficiency_only_no_runtime`
- Active runtime change authorized: `False`

## Overall

| Condition | Answerable | Unanswerable abstention | Overall | Position-invariant | Latency | Prompt tokens |
|---|---:|---:|---:|---:|---:|---:|
| A: full-session freeform | 77.78% | 0.00% | 58.33% | 58.33% | 14.460s | 1590.8 |
| P: provenance gate | 66.67% | 100.00% | 75.00% | 75.00% | 11.528s | 1439.5 |
| R: model reread fallback | 66.67% | 94.44% | 73.61% | 70.83% | 15.216s | 1870.1 |
| E: exact user-utterance fallback | 70.37% | 100.00% | 77.78% | 75.00% | 11.661s | 1473.0 |

## Recovery breadth

- Recovered cases: `2`
- Distinct recovered scenarios: `1`
- Recovery splits: `holdout_b`
- Scenario IDs: `holdout_b_precollege_guitar_nonownership`

## Gates

- PASS `dataset_and_treatment_hashes_match`
- PASS `no_v1_v2_v3_v4_scenario_or_question_reuse`
- PASS `all_candidate_context_is_exact_user_source`
- PASS `no_assistant_turn_admitted_to_candidate_context`
- PASS `fallback_runs_only_after_primary_insufficiency`
- PASS `cue_unanswerable_abstention_rate_equals_one`
- PASS `cue_unsafe_answer_rate_on_unanswerable_equals_zero`
- PASS `cue_answerable_pass_not_lower_than_provenance`
- PASS `cue_overall_pass_not_lower_than_provenance`
- PASS `cue_vs_provenance_paired_loss_count_equals_zero`
- FAIL `cue_vs_provenance_distinct_recovered_scenario_count_at_least_two`
- FAIL `cue_recovery_represented_in_both_holdout_splits`
- PASS `no_capability_family_regression_cue_vs_provenance`
- PASS `cue_position_invariance_not_lower_than_provenance`
- PASS `cue_correctness_not_lower_than_model_reread`
- PASS `cue_vs_reread_paired_loss_count_equals_zero`
- PASS `cue_mean_latency_strictly_lower_than_model_reread`
- PASS `cue_mean_prompt_tokens_strictly_lower_than_model_reread`

## Failure localization

| Case | Condition | Gate | Abstained | Spans | Polarity | Relation | Response |
|---|---|---:|---:|---:|---:|---:|---|
| holdout_a_vaccination_card_current_location__beginning | full_session_freeform | None | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__beginning | provenance_gate_freeform | True | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__beginning | model_reread_fallback | True | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__beginning | cue_extractive_fallback | True | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__middle | full_session_freeform | None | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__middle | provenance_gate_freeform | True | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__middle | model_reread_fallback | True | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__middle | cue_extractive_fallback | True | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__end | full_session_freeform | None | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__end | provenance_gate_freeform | True | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__end | model_reread_fallback | True | False | False | True | True | behind my passport |
| holdout_a_vaccination_card_current_location__end | cue_extractive_fallback | True | False | False | True | True | behind my passport |
| holdout_a_farmers_market_previous_frequency__beginning | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_farmers_market_previous_frequency__beginning | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_farmers_market_previous_frequency__beginning | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_farmers_market_previous_frequency__middle | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_farmers_market_previous_frequency__middle | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_farmers_market_previous_frequency__middle | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_farmers_market_previous_frequency__end | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_farmers_market_previous_frequency__end | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_farmers_market_previous_frequency__end | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_premove_rice_cooker_ownership__beginning | full_session_freeform | None | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__beginning | provenance_gate_freeform | True | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__beginning | model_reread_fallback | True | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__beginning | cue_extractive_fallback | True | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__middle | full_session_freeform | None | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__middle | provenance_gate_freeform | True | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__middle | model_reread_fallback | True | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__middle | cue_extractive_fallback | True | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__end | full_session_freeform | None | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__end | provenance_gate_freeform | True | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__end | model_reread_fallback | True | False | False | True | True | Yes. |
| holdout_a_premove_rice_cooker_ownership__end | cue_extractive_fallback | True | False | False | True | True | Yes. |
| holdout_a_choir_previous_frequency__beginning | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_choir_previous_frequency__beginning | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_choir_previous_frequency__beginning | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_choir_previous_frequency__middle | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_choir_previous_frequency__middle | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_choir_previous_frequency__middle | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_choir_previous_frequency__end | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_choir_previous_frequency__end | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_choir_previous_frequency__end | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| holdout_a_bike_lock_unknown_digit_count__beginning | full_session_freeform | None | False | None | None | None |  |
| holdout_a_bike_lock_unknown_digit_count__middle | full_session_freeform | None | False | None | None | None |  |
| holdout_a_bike_lock_unknown_digit_count__end | full_session_freeform | None | False | None | None | None |  |
| holdout_a_parcel_locker_unknown_location__beginning | full_session_freeform | None | False | None | None | None |  |
| holdout_a_parcel_locker_unknown_location__middle | full_session_freeform | None | False | None | None | None |  |
| holdout_a_parcel_locker_unknown_location__end | full_session_freeform | None | False | None | None | None |  |
| holdout_a_weekend_pet_sitter_unknown_identity__beginning | full_session_freeform | None | False | None | None | None |  |
| holdout_a_weekend_pet_sitter_unknown_identity__middle | full_session_freeform | None | False | None | None | None |  |
| holdout_a_weekend_pet_sitter_unknown_identity__end | full_session_freeform | None | False | None | None | None |  |
| holdout_a_weekend_pet_sitter_unknown_identity__end | model_reread_fallback | True | False | None | None | None | Based on the current evidence, Ken is only a suggestion; no confirmation has been made regarding any pet sitter. |
| holdout_b_insurance_policy_current_location__beginning | full_session_freeform | None | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__beginning | provenance_gate_freeform | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__beginning | model_reread_fallback | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__beginning | cue_extractive_fallback | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__middle | full_session_freeform | None | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__middle | provenance_gate_freeform | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__middle | model_reread_fallback | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__middle | cue_extractive_fallback | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__end | full_session_freeform | None | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__end | provenance_gate_freeform | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__end | model_reread_fallback | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_insurance_policy_current_location__end | cue_extractive_fallback | True | False | False | True | True | The insurance policy document is currently on the bottom shelf, in the black binder. |
| holdout_b_precollege_guitar_nonownership__beginning | full_session_freeform | None | False | False | True | True | No. |
| holdout_b_precollege_guitar_nonownership__beginning | provenance_gate_freeform | True | False | False | True | True | No. |
| holdout_b_precollege_guitar_nonownership__beginning | model_reread_fallback | True | False | False | True | True | No. |
| holdout_b_precollege_guitar_nonownership__beginning | cue_extractive_fallback | True | False | False | True | True | No. |
| holdout_b_precollege_guitar_nonownership__middle | full_session_freeform | None | False | False | False | True |  |
| holdout_b_precollege_guitar_nonownership__middle | provenance_gate_freeform | False | True | False | False | True | I do not have enough grounded user evidence to answer that. |
| holdout_b_precollege_guitar_nonownership__middle | model_reread_fallback | False | True | False | False | True | I do not have enough grounded user evidence to answer that. |
| holdout_b_precollege_guitar_nonownership__end | full_session_freeform | None | False | False | False | True |  |
| holdout_b_precollege_guitar_nonownership__end | provenance_gate_freeform | False | True | False | False | True | I do not have enough grounded user evidence to answer that. |
| holdout_b_precollege_guitar_nonownership__end | model_reread_fallback | False | True | False | False | True | I do not have enough grounded user evidence to answer that. |
| holdout_b_volunteer_shift_unknown_frequency__beginning | full_session_freeform | None | False | None | None | None |  |
| holdout_b_volunteer_shift_unknown_frequency__middle | full_session_freeform | None | False | None | None | None |  |
| holdout_b_volunteer_shift_unknown_frequency__end | full_session_freeform | None | False | None | None | None |  |
| holdout_b_charity_pickup_unknown_time__beginning | full_session_freeform | None | False | None | None | None |  |
| holdout_b_charity_pickup_unknown_time__middle | full_session_freeform | None | False | None | None | None | The arrival time is still unconfirmed as of 2026-07-31 18:00:00. |
| holdout_b_charity_pickup_unknown_time__end | full_session_freeform | None | False | None | None | None |  |
| holdout_b_soldering_iron_unknown_ownership__beginning | full_session_freeform | None | False | None | None | None |  |
| holdout_b_soldering_iron_unknown_ownership__middle | full_session_freeform | None | False | None | None | None |  |
| holdout_b_soldering_iron_unknown_ownership__end | full_session_freeform | None | False | None | None | None |  |

## Evidence boundary

V5 never authorizes a default-on runtime change. Passing all gates permits only a separate review for an off-by-default shadow integration. Failure or insufficient recovery breadth preserves the current runtime.
