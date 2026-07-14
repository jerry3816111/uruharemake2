# Memory cue-driven extractive fallback V4

## Scope and decision

This preregistered development experiment compares two fallback methods after the same provenance-gated primary path. It contains no official benchmark item and cannot authorize a runtime change.

- Complete: `True` (48/48)
- Model: `qwen2.5:7b`
- Model digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- Decision: `eligible_for_new_untouched_evaluation`

## Overall

| condition | answerable | abstention | cognitive | fallback semantic recovery | latency | prompt tokens |
|---|---:|---:|---:|---:|---:|---:|
| A: existing full-session freeform | 77.78% | 0.00% | 58.33% | - | 14.065s | 1571.8 |
| P: user-source provenance gate | 69.44% | 100.00% | 77.08% | - | 11.165s | 1433.4 |
| R: P + model reread fallback | 72.22% | 100.00% | 79.17% | 25.00% | 13.614s | 1785.3 |
| E: P + exact user-utterance fallback | 72.22% | 100.00% | 79.17% | 25.00% | 11.203s | 1439.9 |

## Candidate integrity

- Exact user-source rate: 100.00%
- Assistant admission rate: 0.00%
- Candidate gate sufficiency: 6.25%

## Paired comparisons

- `overall_cognitive_case_pass`: `provenance_gate_freeform - full_session_freeform` = +18.75 pp; wins/losses 12/3; McNemar p=0.035156; bootstrap 95% CI [+4.17, +33.33] pp.
- `answerable_semantic_case_pass`: `provenance_gate_freeform - full_session_freeform` = -8.33 pp; wins/losses 0/3; McNemar p=0.250000; bootstrap 95% CI [-19.44, +0.00] pp.
- `overall_cognitive_case_pass`: `model_reread_fallback - provenance_gate_freeform` = +2.08 pp; wins/losses 1/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +6.25] pp.
- `answerable_semantic_case_pass`: `model_reread_fallback - provenance_gate_freeform` = +2.78 pp; wins/losses 1/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +8.33] pp.
- `overall_cognitive_case_pass`: `cue_extractive_fallback - provenance_gate_freeform` = +2.08 pp; wins/losses 1/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +6.25] pp.
- `answerable_semantic_case_pass`: `cue_extractive_fallback - provenance_gate_freeform` = +2.78 pp; wins/losses 1/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +8.33] pp.
- `overall_cognitive_case_pass`: `cue_extractive_fallback - model_reread_fallback` = +0.00 pp; wins/losses 0/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +0.00] pp.
- `answerable_semantic_case_pass`: `cue_extractive_fallback - model_reread_fallback` = +0.00 pp; wins/losses 0/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +0.00] pp.

## Capability families

| capability | A | P | R | E |
|---|---:|---:|---:|---:|
| change_direction | 100.00% | 100.00% | 100.00% | 100.00% |
| current_count | 50.00% | 50.00% | 50.00% | 50.00% |
| current_location | 100.00% | 100.00% | 100.00% | 100.00% |
| current_time | 83.33% | 83.33% | 100.00% | 100.00% |
| historical_yes_no | 33.33% | 33.33% | 33.33% | 33.33% |
| previous_frequency | 100.00% | 50.00% | 50.00% | 50.00% |
| unanswerable_count | 0.00% | 100.00% | 100.00% | 100.00% |
| unanswerable_identity | 0.00% | 100.00% | 100.00% | 100.00% |
| unanswerable_location | 0.00% | 100.00% | 100.00% | 100.00% |

## Gates

- PASS `dataset_hash_match`
- PASS `no_v1_v2_v3_scenario_or_question_reuse`
- PASS `all_candidate_context_is_exact_user_source`
- PASS `no_assistant_turn_admitted_to_candidate_context`
- PASS `fallback_runs_only_after_primary_insufficiency`
- PASS `cue_unanswerable_abstention_rate_equals_one`
- PASS `cue_unsafe_answer_rate_on_unanswerable_equals_zero`
- PASS `cue_answerable_pass_strictly_higher_than_provenance`
- PASS `cue_overall_pass_strictly_higher_than_provenance`
- PASS `cue_development_answerable_not_lower_than_provenance`
- PASS `cue_transfer_answerable_not_lower_than_provenance`
- PASS `no_capability_family_regression_cue_vs_provenance`
- PASS `cue_position_invariance_not_lower_than_provenance`
- PASS `cue_fallback_recovery_rate_greater_than_zero`
- PASS `cue_mean_latency_not_higher_than_model_reread`
- PASS `cue_mean_prompt_tokens_not_higher_than_model_reread`

## Failure localization

| case | condition | gate | abstained | spans | polarity | relation | response |
|---|---|---:|---:|---:|---:|---:|---|
| dev_water_bottles_current_count__beginning | full_session_freeform | None | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only states the current total count of water bottles, whic |
| dev_water_bottles_current_count__beginning | provenance_gate_freeform | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only states the current total count of water bottles, whic |
| dev_water_bottles_current_count__beginning | model_reread_fallback | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only states the current total count of water bottles, whic |
| dev_water_bottles_current_count__beginning | cue_extractive_fallback | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only states the current total count of water bottles, whic |
| dev_water_bottles_current_count__middle | full_session_freeform | None | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only mentions a total count of seven water bottles, but do |
| dev_water_bottles_current_count__middle | provenance_gate_freeform | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only mentions a total count of seven water bottles, but do |
| dev_water_bottles_current_count__middle | model_reread_fallback | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only mentions a total count of seven water bottles, but do |
| dev_water_bottles_current_count__middle | cue_extractive_fallback | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only mentions a total count of seven water bottles, but do |
| dev_water_bottles_current_count__end | full_session_freeform | None | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only indicates a total count of seven water bottles, but d |
| dev_water_bottles_current_count__end | provenance_gate_freeform | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only indicates a total count of seven water bottles, but d |
| dev_water_bottles_current_count__end | model_reread_fallback | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only indicates a total count of seven water bottles, but d |
| dev_water_bottles_current_count__end | cue_extractive_fallback | True | True | True | True | True | Insufficient evidence to determine the number of stainless steel water bottles. The provided evidence only indicates a total count of seven water bottles, but d |
| dev_lap_pool_previous_frequency__beginning | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_lap_pool_previous_frequency__beginning | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_lap_pool_previous_frequency__beginning | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_lap_pool_previous_frequency__middle | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_lap_pool_previous_frequency__middle | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_lap_pool_previous_frequency__middle | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_lap_pool_previous_frequency__end | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_lap_pool_previous_frequency__end | model_reread_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_lap_pool_previous_frequency__end | cue_extractive_fallback | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_precamera_binoculars_ownership__beginning | full_session_freeform | None | False | True | False | True | Before buying the camera, you owned binoculars. |
| dev_precamera_binoculars_ownership__beginning | provenance_gate_freeform | True | False | True | False | True | Before buying the camera, you owned binoculars. |
| dev_precamera_binoculars_ownership__beginning | model_reread_fallback | True | False | True | False | True | Before buying the camera, you owned binoculars. |
| dev_precamera_binoculars_ownership__beginning | cue_extractive_fallback | True | False | True | False | True | Before buying the camera, you owned binoculars. |
| dev_house_key_unknown_location__beginning | full_session_freeform | None | False | None | None | None |  |
| dev_house_key_unknown_location__middle | full_session_freeform | None | False | None | None | None |  |
| dev_house_key_unknown_location__end | full_session_freeform | None | False | None | None | None |  |
| dev_houseplants_unknown_count__beginning | full_session_freeform | None | False | None | None | None |  |
| dev_houseplants_unknown_count__middle | full_session_freeform | None | False | None | None | None |  |
| dev_houseplants_unknown_count__end | full_session_freeform | None | False | None | None | None |  |
| transfer_predog_rabbit_nonownership__beginning | full_session_freeform | None | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__beginning | provenance_gate_freeform | True | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__beginning | model_reread_fallback | True | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__beginning | cue_extractive_fallback | True | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__middle | full_session_freeform | None | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__middle | provenance_gate_freeform | True | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__middle | model_reread_fallback | True | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__middle | cue_extractive_fallback | True | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__end | full_session_freeform | None | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__end | provenance_gate_freeform | True | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__end | model_reread_fallback | True | False | False | True | True | No. |
| transfer_predog_rabbit_nonownership__end | cue_extractive_fallback | True | False | False | True | True | No. |
| transfer_dentist_current_time__end | full_session_freeform | None | False | False | True | True |  |
| transfer_dentist_current_time__end | provenance_gate_freeform | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| transfer_garage_code_unknown_count__beginning | full_session_freeform | None | False | None | None | None |  |
| transfer_garage_code_unknown_count__middle | full_session_freeform | None | False | None | None | None |  |
| transfer_garage_code_unknown_count__end | full_session_freeform | None | False | None | None | None |  |
| transfer_emergency_contact_unknown_identity__beginning | full_session_freeform | None | False | None | None | None |  |
| transfer_emergency_contact_unknown_identity__middle | full_session_freeform | None | False | None | None | None |  |
| transfer_emergency_contact_unknown_identity__end | full_session_freeform | None | False | None | None | None |  |

## Evidence boundary

Passing means only that E may proceed to a new untouched evaluation. V4 cases then become consumed development evidence. Runtime integration remains unauthorized.
