# Memory Utterance Attention V1

## Scope

This is a development-only matched experiment. It uses 36 synthetic, source-separated cases and zero official LongMemEval items. It does not authorize a runtime change.

- Complete: `True` (36/36)
- Model: `qwen2.5:7b`
- Model digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- Decision: `not_eligible_for_runtime_or_heldout_promotion`

## Overall

| condition | evidence recall | answer spans | relation | semantic pass | position-invariant | latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full session + freeform | 97.22% | 91.67% | 88.89% | 83.33% | 66.67% | 15.02s |
| utterance attention + freeform | 75.00% | 72.22% | 83.33% | 63.89% | 58.33% | 11.26s |
| utterance attention + proposition | 75.00% | 38.89% | 75.00% | 38.89% | 33.33% | 13.31s |

## Paired comparisons

- `utterance_attention_freeform - full_session_freeform`: -19.44 pp; wins/losses 2/9; McNemar p=0.065430; bootstrap 95% CI [-36.11, -2.78] pp.
- `utterance_attention_proposition - utterance_attention_freeform`: -25.00 pp; wins/losses 3/12; McNemar p=0.035156; bootstrap 95% CI [-44.44, -5.56] pp.

## Development / transfer

- development: full session + freeform=77.78%, utterance attention + freeform=44.44%, utterance attention + proposition=27.78%
- transfer: full session + freeform=88.89%, utterance attention + freeform=83.33%, utterance attention + proposition=50.00%

## Capability families

| capability | control | attention | proposition |
| --- | ---: | ---: | ---: |
| change_direction | 83.33% | 100.00% | 0.00% |
| current_count | 100.00% | 50.00% | 50.00% |
| current_location | 83.33% | 83.33% | 83.33% |
| current_time | 83.33% | 100.00% | 50.00% |
| historical_yes_no | 50.00% | 0.00% | 50.00% |
| previous_frequency | 100.00% | 50.00% | 0.00% |

## Gates

- PASS `dataset_hash_match`
- PASS `all_source_quotes_grounded`
- FAIL `all_valid_proposition_spans_grounded`
- FAIL `development_semantic_pass_not_lower_than_control`
- FAIL `transfer_semantic_pass_not_lower_than_control`
- FAIL `no_capability_family_regression`
- FAIL `position_invariance_not_lower_than_control`

## Failure localization

| case | split | capability | condition | evidence | spans | relation | response |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| dev_spare_key_location__end | development | current_location | full_session_freeform | 100.00% | False | True | cedar drawer |
| dev_spare_key_location__end | development | current_location | utterance_attention_freeform | 100.00% | False | True | cedar drawer |
| dev_spare_key_location__end | development | current_location | utterance_attention_proposition | 100.00% | False | True | cedar drawer. |
| dev_running_previous_frequency__beginning | development | previous_frequency | utterance_attention_freeform | 0.00% | False | True |  |
| dev_running_previous_frequency__beginning | development | previous_frequency | utterance_attention_proposition | 0.00% | False | True |  |
| dev_running_previous_frequency__middle | development | previous_frequency | utterance_attention_freeform | 0.00% | False | True |  |
| dev_running_previous_frequency__middle | development | previous_frequency | utterance_attention_proposition | 0.00% | False | True |  |
| dev_running_previous_frequency__end | development | previous_frequency | utterance_attention_freeform | 0.00% | False | True |  |
| dev_running_previous_frequency__end | development | previous_frequency | utterance_attention_proposition | 0.00% | False | True |  |
| dev_vehicle_historical_ownership__beginning | development | historical_yes_no | full_session_freeform | 100.00% | True | False | No. According to the evidence on 2026-07-13 12:00:00, you already owned a small motorcycle alongside your city bicycle. The question asks about the state before |
| dev_vehicle_historical_ownership__beginning | development | historical_yes_no | utterance_attention_freeform | 100.00% | True | False | No. According to the evidence on 2026-07-13 12:00:00, you already owned a small motorcycle alongside your city bicycle. The question asks about the state before |
| dev_vehicle_historical_ownership__middle | development | historical_yes_no | full_session_freeform | 100.00% | True | False | No. According to the evidence on 2026-07-13 12:00:00, you already owned a small motorcycle alongside your city bicycle. Therefore, before purchasing the electri |
| dev_vehicle_historical_ownership__middle | development | historical_yes_no | utterance_attention_freeform | 100.00% | True | False | No. According to the evidence on 2026-07-13 12:00:00, you already owned a small motorcycle alongside your city bicycle. Therefore, before purchasing the electri |
| dev_vehicle_historical_ownership__end | development | historical_yes_no | full_session_freeform | 100.00% | True | False | No. According to the evidence on 2026-07-13 12:00:00, you already owned a small motorcycle alongside your city bicycle. The question asks about the state before |
| dev_vehicle_historical_ownership__end | development | historical_yes_no | utterance_attention_freeform | 100.00% | True | False | No. According to the evidence on 2026-07-13 12:00:00, you already owned a small motorcycle alongside your city bicycle. The question asks about the state before |
| dev_houseplant_current_count__beginning | development | current_count | utterance_attention_freeform | 0.00% | False | True |  |
| dev_houseplant_current_count__beginning | development | current_count | utterance_attention_proposition | 0.00% | False | True |  |
| dev_houseplant_current_count__middle | development | current_count | utterance_attention_freeform | 0.00% | False | True |  |
| dev_houseplant_current_count__middle | development | current_count | utterance_attention_proposition | 0.00% | False | True |  |
| dev_houseplant_current_count__end | development | current_count | utterance_attention_freeform | 0.00% | False | True |  |
| dev_houseplant_current_count__end | development | current_count | utterance_attention_proposition | 0.00% | False | True |  |
| dev_coffee_limit_change__beginning | development | change_direction | utterance_attention_proposition | 100.00% | False | False |  |
| dev_coffee_limit_change__middle | development | change_direction | utterance_attention_proposition | 100.00% | False | False |  |
| dev_coffee_limit_change__end | development | change_direction | utterance_attention_proposition | 100.00% | False | False |  |
| dev_dentist_current_time__beginning | development | current_time | utterance_attention_proposition | 100.00% | False | True |  |
| dev_dentist_current_time__middle | development | current_time | utterance_attention_proposition | 100.00% | False | True |  |
| dev_dentist_current_time__end | development | current_time | utterance_attention_proposition | 100.00% | False | True |  |
| transfer_parent_call_previous_frequency__beginning | transfer | previous_frequency | utterance_attention_proposition | 100.00% | False | True |  |
| transfer_parent_call_previous_frequency__middle | transfer | previous_frequency | utterance_attention_proposition | 100.00% | False | True |  |
| transfer_parent_call_previous_frequency__end | transfer | previous_frequency | utterance_attention_proposition | 100.00% | False | True |  |
| transfer_pet_historical_ownership__beginning | transfer | historical_yes_no | utterance_attention_freeform | 0.00% | False | False |  |
| transfer_pet_historical_ownership__beginning | transfer | historical_yes_no | utterance_attention_proposition | 0.00% | False | False |  |
| transfer_pet_historical_ownership__middle | transfer | historical_yes_no | utterance_attention_freeform | 0.00% | False | False |  |
| transfer_pet_historical_ownership__middle | transfer | historical_yes_no | utterance_attention_proposition | 0.00% | False | False |  |
| transfer_pet_historical_ownership__end | transfer | historical_yes_no | utterance_attention_freeform | 0.00% | False | False |  |
| transfer_pet_historical_ownership__end | transfer | historical_yes_no | utterance_attention_proposition | 0.00% | False | False |  |
| transfer_commute_duration_change__beginning | transfer | change_direction | utterance_attention_proposition | 100.00% | False | False |  |
| transfer_commute_duration_change__middle | transfer | change_direction | full_session_freeform | 100.00% | False | False |  |
| transfer_commute_duration_change__middle | transfer | change_direction | utterance_attention_proposition | 100.00% | False | False |  |
| transfer_commute_duration_change__end | transfer | change_direction | utterance_attention_proposition | 100.00% | False | False |  |
| transfer_class_current_time__end | transfer | current_time | full_session_freeform | 0.00% | False | True | The current start time of your evening class is 2026-07-13 12:00:00. However, this is the start time as recorded on the specified session ID, and it may have be |

## Evidence boundary

Passing this development gate means only that the mechanism may proceed to a new, untouched evaluation. The consumed LongMemEval heldout was not reused, and runtime integration remains unauthorized.
