# Memory Source Monitoring + Adaptive Reread V3

## Scope and decision

This development-only matched experiment tests source authority, explicit abstention, and conditional rereading. It contains no official benchmark item and cannot authorize a runtime change.

- Complete: `True` (48/48)
- Model: `qwen2.5:7b`
- Model digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- Decision: `reject_v3_runtime_integration`

## Overall

| condition | answerable | abstention | cognitive | unsafe answer | evidence recall | assistant admitted | fallback | latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A: existing full-session freeform | 72.22% | 0.00% | 54.17% | 0.00% | 68.75% | 0.00% | - | 14.86s |
| P: user-source provenance gate | 72.22% | 100.00% | 79.17% | 0.00% | 68.75% | 0.00% | 31.25% | 12.17s |
| R: P + low-sufficiency reread | 72.22% | 100.00% | 79.17% | 0.00% | 72.92% | 0.00% | 31.25% | 14.58s |
| S: R + source-span contract | 75.00% | 100.00% | 81.25% | 0.00% | 72.92% | 0.00% | 31.25% | 15.67s |

## Paired comparisons

- `overall_cognitive_case_pass`: `provenance_gate_only_freeform - full_session_freeform` = +25.00 pp; wins/losses 12/0; McNemar p=0.000488; bootstrap 95% CI [+12.50, +37.50] pp.
- `answerable_semantic_case_pass`: `provenance_gate_only_freeform - full_session_freeform` = +0.00 pp; wins/losses 0/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +0.00] pp.
- `overall_cognitive_case_pass`: `adaptive_provenance_reread_freeform - provenance_gate_only_freeform` = +0.00 pp; wins/losses 0/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +0.00] pp.
- `answerable_semantic_case_pass`: `adaptive_provenance_reread_freeform - provenance_gate_only_freeform` = +0.00 pp; wins/losses 0/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +0.00] pp.
- `overall_cognitive_case_pass`: `adaptive_provenance_reread_freeform - full_session_freeform` = +25.00 pp; wins/losses 12/0; McNemar p=0.000488; bootstrap 95% CI [+12.50, +37.50] pp.
- `answerable_semantic_case_pass`: `adaptive_provenance_reread_freeform - full_session_freeform` = +0.00 pp; wins/losses 0/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +0.00] pp.
- `overall_cognitive_case_pass`: `adaptive_provenance_reread_span_contract - adaptive_provenance_reread_freeform` = +2.08 pp; wins/losses 4/3; McNemar p=1.000000; bootstrap 95% CI [-8.33, +12.50] pp.
- `answerable_semantic_case_pass`: `adaptive_provenance_reread_span_contract - adaptive_provenance_reread_freeform` = +2.78 pp; wins/losses 4/3; McNemar p=1.000000; bootstrap 95% CI [-11.11, +16.67] pp.

## Development / transfer

- development: A: existing full-session freeform=54.17%, P: user-source provenance gate=79.17%, R: P + low-sufficiency reread=79.17%, S: R + source-span contract=75.00%
- transfer: A: existing full-session freeform=54.17%, P: user-source provenance gate=79.17%, R: P + low-sufficiency reread=79.17%, S: R + source-span contract=87.50%

## Capability families

| capability | A | P | R | S |
| --- | ---: | ---: | ---: | ---: |
| change_direction | 16.67% | 16.67% | 16.67% | 50.00% |
| current_count | 50.00% | 50.00% | 50.00% | 50.00% |
| current_location | 100.00% | 100.00% | 100.00% | 100.00% |
| current_time | 100.00% | 100.00% | 100.00% | 100.00% |
| historical_yes_no | 66.67% | 66.67% | 66.67% | 50.00% |
| previous_frequency | 100.00% | 100.00% | 100.00% | 100.00% |
| unanswerable_count | 0.00% | 100.00% | 100.00% | 100.00% |
| unanswerable_location | 0.00% | 100.00% | 100.00% | 100.00% |
| unanswerable_time | 0.00% | 100.00% | 100.00% | 100.00% |
| unanswerable_yes_no | 0.00% | 100.00% | 100.00% | 100.00% |

## Gates

- PASS `dataset_hash_match`
- PASS `all_highlighted_contexts_restore_exactly`
- PASS `all_markup_repairs_exactly_grounded`
- PASS `no_assistant_only_fact_admitted_to_treatment_ledgers`
- PASS `provenance_gate_unanswerable_abstention_rate_equals_one`
- PASS `adaptive_unanswerable_abstention_rate_equals_one`
- PASS `span_unanswerable_abstention_rate_equals_one`
- FAIL `adaptive_answerable_false_abstention_rate_equals_zero`
- PASS `adaptive_development_answerable_pass_not_lower_than_control`
- PASS `adaptive_transfer_answerable_pass_not_lower_than_control`
- PASS `adaptive_overall_cognitive_pass_not_lower_than_control`
- PASS `no_capability_family_regression_adaptive_vs_control`
- PASS `span_overall_cognitive_pass_not_lower_than_adaptive`
- PASS `position_invariance_not_lower_adaptive_vs_control`
- PASS `fallback_runs_only_after_primary_insufficiency`

## Failure localization

| case | condition | answerable | gate | abstained | spans | polarity | relation | response |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| dev_preharp_violin_ownership__beginning | adaptive_provenance_reread_span_contract | True | True | False | True | False | True | No - No, the violin was already mine before the harp.. |
| dev_preharp_violin_ownership__middle | adaptive_provenance_reread_span_contract | True | True | False | True | False | True | No - No, the violin was already mine before the harp.. |
| dev_preharp_violin_ownership__end | adaptive_provenance_reread_span_contract | True | True | False | True | False | True | No - No, the violin was already mine before the harp.. |
| dev_mug_current_count__beginning | full_session_freeform | True | None | False | False | True | True |  |
| dev_mug_current_count__beginning | provenance_gate_only_freeform | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_mug_current_count__beginning | adaptive_provenance_reread_freeform | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_mug_current_count__beginning | adaptive_provenance_reread_span_contract | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_mug_current_count__middle | full_session_freeform | True | None | False | False | True | True |  |
| dev_mug_current_count__middle | provenance_gate_only_freeform | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_mug_current_count__middle | adaptive_provenance_reread_freeform | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_mug_current_count__middle | adaptive_provenance_reread_span_contract | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_mug_current_count__end | full_session_freeform | True | None | False | False | True | True |  |
| dev_mug_current_count__end | provenance_gate_only_freeform | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_mug_current_count__end | adaptive_provenance_reread_freeform | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_mug_current_count__end | adaptive_provenance_reread_span_contract | True | False | True | False | True | True | I do not have enough grounded user evidence to answer that. |
| dev_commute_increase__beginning | full_session_freeform | True | None | False | False | True | True | Before the change, the commute duration was 25 minutes. Now, it takes 40 minutes. The commute increased by 15 minutes. |
| dev_commute_increase__beginning | provenance_gate_only_freeform | True | True | False | False | True | True | Before the change, the commute duration was 25 minutes. Now, it takes 40 minutes. The commute increased by 15 minutes. |
| dev_commute_increase__beginning | adaptive_provenance_reread_freeform | True | True | False | False | True | True | Before the change, the commute duration was 25 minutes. Now, it takes 40 minutes. The commute increased by 15 minutes. |
| dev_commute_increase__middle | full_session_freeform | True | None | False | False | True | True | Before the change, the commute duration was 25 minutes. Now, it takes 40 minutes. The commute increased by 15 minutes. |
| dev_commute_increase__middle | provenance_gate_only_freeform | True | True | False | False | True | True | Before the change, the commute duration was 25 minutes. Now, it takes 40 minutes. The commute increased by 15 minutes. |
| dev_commute_increase__middle | adaptive_provenance_reread_freeform | True | True | False | False | True | True | Before the change, the commute duration was 25 minutes. Now, it takes 40 minutes. The commute increased by 15 minutes. |
| dev_spare_glasses_unknown_location__beginning | full_session_freeform | False | None | False | None | None | None |  |
| dev_spare_glasses_unknown_location__middle | full_session_freeform | False | None | False | None | None | None |  |
| dev_spare_glasses_unknown_location__end | full_session_freeform | False | None | False | None | None | None |  |
| dev_tablet_unknown_historical_ownership__beginning | full_session_freeform | False | None | False | None | None | None |  |
| dev_tablet_unknown_historical_ownership__middle | full_session_freeform | False | None | False | None | None | None |  |
| dev_tablet_unknown_historical_ownership__end | full_session_freeform | False | None | False | None | None | None |  |
| transfer_preparrot_hamster_nonownership__beginning | full_session_freeform | True | None | False | False | True | True | No. |
| transfer_preparrot_hamster_nonownership__beginning | provenance_gate_only_freeform | True | True | False | False | True | True | No. |
| transfer_preparrot_hamster_nonownership__beginning | adaptive_provenance_reread_freeform | True | True | False | False | True | True | No. |
| transfer_preparrot_hamster_nonownership__end | full_session_freeform | True | None | False | False | True | True | No. According to your statement on 2026-07-13 18:00:00, you owned a cat but not a hamster before adopting the parrot. |
| transfer_preparrot_hamster_nonownership__end | provenance_gate_only_freeform | True | True | False | False | True | True | No. According to your statement on 2026-07-13 18:00:00, you owned a cat but not a hamster before adopting the parrot. |
| transfer_preparrot_hamster_nonownership__end | adaptive_provenance_reread_freeform | True | True | False | False | True | True | No. According to your statement on 2026-07-13 18:00:00, you owned a cat but not a hamster before adopting the parrot. |
| transfer_takeout_frequency_decrease__beginning | full_session_freeform | True | None | False | False | True | True | Before the change, the number of takeout meals per week was five. Now, it is twice a week. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__beginning | provenance_gate_only_freeform | True | True | False | False | True | True | Before the change, the number of takeout meals per week was five. Now, it is twice a week. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__beginning | adaptive_provenance_reread_freeform | True | True | False | False | True | True | Before the change, the number of takeout meals per week was five. Now, it is twice a week. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__beginning | adaptive_provenance_reread_span_contract | True | True | True | False | True | False | I do not have enough grounded user evidence to answer that. |
| transfer_takeout_frequency_decrease__middle | full_session_freeform | True | None | False | False | True | True | Before the change, the number of takeout meals per week was 5. Currently, it is 2. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__middle | provenance_gate_only_freeform | True | True | False | False | True | True | Before the change, the number of takeout meals per week was 5. Currently, it is 2. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__middle | adaptive_provenance_reread_freeform | True | True | False | False | True | True | Before the change, the number of takeout meals per week was 5. Currently, it is 2. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__middle | adaptive_provenance_reread_span_contract | True | True | True | False | True | False | I do not have enough grounded user evidence to answer that. |
| transfer_takeout_frequency_decrease__end | full_session_freeform | True | None | False | False | True | True | Before the change, the number of takeout meals per week was 5. Now, it is 2. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__end | provenance_gate_only_freeform | True | True | False | False | True | True | Before the change, the number of takeout meals per week was 5. Now, it is 2. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__end | adaptive_provenance_reread_freeform | True | True | False | False | True | True | Before the change, the number of takeout meals per week was 5. Now, it is 2. The direction of change is a decrease. |
| transfer_takeout_frequency_decrease__end | adaptive_provenance_reread_span_contract | True | True | True | False | True | False | I do not have enough grounded user evidence to answer that. |
| transfer_board_games_unknown_count__beginning | full_session_freeform | False | None | False | None | None | None |  |
| transfer_board_games_unknown_count__middle | full_session_freeform | False | None | False | None | None | None |  |
| transfer_board_games_unknown_count__end | full_session_freeform | False | None | False | None | None | None |  |
| transfer_dental_unknown_time__beginning | full_session_freeform | False | None | False | None | None | None |  |
| transfer_dental_unknown_time__middle | full_session_freeform | False | None | False | None | None | None |  |
| transfer_dental_unknown_time__end | full_session_freeform | False | None | False | None | None | None |  |

## Evidence boundary

Passing means only that V3 may proceed to a new untouched evaluation. These cases then become consumed development evidence. Runtime integration remains unauthorized.
