# V59 event-role independent-holdout construction audit

This audit performs no V58/V59 state, compiler, or model evaluation.

- Cases / grounded targets: 72 / 73
- External exact / controlled: 16 / 56
- Action / no-action cases: 14 / 58
- Exact historical overlaps: 0
- Near duplicates at >= 94%: 0
- Prior Tatoeba source-ID overlaps: 0
- Construction gate: PASS

## Families

| Family | Cases |
|---|---:|
| controlled_direct_focus_request_contrast | 14 |
| controlled_embedded_speech_content | 14 |
| controlled_past_experiential_description | 14 |
| controlled_third_party_habitual_description | 14 |
| external_tatoeba_event_role | 16 |

## Checks

| Check | Result |
|---|---|
| case_count | PASS |
| source_counts | PASS |
| family_matrix_exact | PASS |
| grounded_target_count | PASS |
| distinct_target_count | PASS |
| commitment_counts | PASS |
| action_and_no_action_counts | PASS |
| candidate_target_sets_exact | PASS |
| evidence_substrings_exact | PASS |
| expected_calls_derived_mechanically | PASS |
| external_rows_match_snapshot | PASS |
| no_prior_external_sentence_ids | PASS |
| no_duplicate_case_ids | PASS |
| no_duplicate_inputs | PASS |
| no_exact_historical_inputs | PASS |
| no_near_duplicate_historical_inputs | PASS |
| controlled_provenance_honest | PASS |
| construction_firewall_preserved | PASS |
| base_pretraining_exclusion_not_overclaimed | PASS |
| mention_coverage | PASS |
| mention_fallback_zero | PASS |
| mention_inside_evidence | PASS |
| cross_target_overlap_zero | PASS |
