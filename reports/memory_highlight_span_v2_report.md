# Memory Highlight + Span Contract V2

## Scope and decision

This development-only matched experiment tests attention that preserves the full source and a controller-owned semantic binding stage. It contains no official LongMemEval item and cannot authorize a runtime change.

- Complete: `True` (36/36)
- Model: `qwen2.5:7b`
- Model digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- Decision: `reject_v2_runtime_integration`

## Overall

| condition | evidence recall | slot spans | polarity | relation | semantic pass | position-invariant | latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A: full context + freeform | 88.89% | 97.22% | 100.00% | 100.00% | 97.22% | 91.67% | 14.71s |
| B: full context + highlights + freeform | 97.22% | 97.22% | 100.00% | 100.00% | 97.22% | 91.67% | 13.57s |
| C: B + controller span contract | 97.22% | 97.22% | 100.00% | 100.00% | 97.22% | 91.67% | 14.98s |

## Frozen attention audit

- Target recall: 100.00%.
- Selection precision: 98.15%; the two preregistered adjacent false positives were retained.
- Full-context restoration: 100.00%.

## Paired comparisons

- `highlighted_full_session_freeform - full_session_freeform`: +0.00 pp; wins/losses 1/1; McNemar p=1.000000; bootstrap 95% CI [-8.33, +8.33] pp.
- `highlighted_full_session_span_contract - highlighted_full_session_freeform`: +0.00 pp; wins/losses 0/0; McNemar p=1.000000; bootstrap 95% CI [+0.00, +0.00] pp.

## Development / transfer

- development: A: full context + freeform=94.44%, B: full context + highlights + freeform=100.00%, C: B + controller span contract=100.00%
- transfer: A: full context + freeform=100.00%, B: full context + highlights + freeform=94.44%, C: B + controller span contract=94.44%

## Capability families

| capability | A | B | C |
| --- | ---: | ---: | ---: |
| change_direction | 100.00% | 100.00% | 100.00% |
| current_count | 100.00% | 100.00% | 100.00% |
| current_location | 100.00% | 100.00% | 100.00% |
| current_time | 83.33% | 100.00% | 100.00% |
| historical_yes_no | 100.00% | 100.00% | 100.00% |
| previous_frequency | 100.00% | 83.33% | 83.33% |

## Gates

- PASS `dataset_hash_match`
- PASS `all_highlighted_contexts_restore_exactly`
- FAIL `all_source_quotes_grounded`
- FAIL `all_span_contracts_valid`
- FAIL `all_required_slots_complete`
- FAIL `all_admitted_spans_grounded`
- PASS `highlight_development_semantic_pass_not_lower_than_control`
- FAIL `highlight_transfer_semantic_pass_not_lower_than_control`
- PASS `span_development_semantic_pass_not_lower_than_highlight`
- PASS `span_transfer_semantic_pass_not_lower_than_highlight`
- FAIL `no_capability_family_regression_for_either_change`
- PASS `position_invariance_not_lower_for_either_change`

## Failure localization

| case | condition | evidence | spans | polarity | relation | contract errors | response |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| dev_therapy_current_time__end | full_session_freeform | 0.00% | False | True | True | - | The current therapy appointment time is 2026-07-13 18:00:00. |
| transfer_grocery_previous_frequency__middle | highlighted_full_session_freeform | 0.00% | False | True | True | - |  |
| transfer_grocery_previous_frequency__middle | highlighted_full_session_span_contract | 0.00% | False | True | True | missing_ledger |  |

## Evidence boundary

Passing means only that V2 may proceed to a new untouched evaluation. These cases then become consumed development evidence. Runtime integration remains unauthorized.
