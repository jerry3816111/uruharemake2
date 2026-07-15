# V58 relation-safety independent-holdout construction audit

This audit performs no V56/V58 state evaluation and no model inference.

- Cases / grounded targets: 64 / 87
- External exact / controlled: 16 / 48
- Action / no-action cases: 13 / 51
- Exact historical overlaps: 0
- Near duplicates at >= 94%: 0
- Prior Tatoeba source-ID overlaps: 0
- Construction gate: PASS

## Families

| Family | Cases |
|---|---:|
| controlled_deferred_preference | 12 |
| controlled_exclusive_alternative | 12 |
| controlled_past_benefactive_description | 12 |
| controlled_relation_contrast | 12 |
| external_tatoeba_relation_safety | 16 |

## Checks

| Check | Result |
|---|---|
| case_count_64 | PASS |
| external_exact_count_16 | PASS |
| controlled_compositional_count_48 | PASS |
| four_controlled_families_have_twelve | PASS |
| action_and_no_action_controls_present | PASS |
| candidate_target_sets_exact | PASS |
| evidence_substrings_exact | PASS |
| ordered_expected_calls_derived_mechanically | PASS |
| external_rows_match_snapshot | PASS |
| no_reused_prior_external_sentence_ids | PASS |
| no_duplicate_holdout_inputs | PASS |
| no_exact_historical_input_overlap | PASS |
| no_near_duplicate_historical_input | PASS |
| construction_provenance_is_honest | PASS |
| base_pretraining_exclusion_not_overclaimed | PASS |
| mention_coverage_100_percent | PASS |
| mention_fallback_zero | PASS |
| mention_inside_evidence_100_percent | PASS |
| cross_target_mention_overlap_zero | PASS |
