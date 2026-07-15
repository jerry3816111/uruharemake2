# V57 compiler independent-holdout construction audit

This audit performs no evaluation-model inference.

- Cases: 64
- Grounded targets: 85
- Action cases: 29
- No-action cases: 35
- Exact historical input overlaps: 0
- Prior Tatoeba source-ID overlaps: 0
- Construction gate: PASS

## Sources

| Source | Cases |
|---|---:|
| controlled_compositional | 32 |
| external_exact | 32 |

## Checks

| Check | Result |
|---|---|
| case_count_64 | PASS |
| external_exact_count_32 | PASS |
| controlled_compositional_count_32 | PASS |
| eight_controlled_families_have_four | PASS |
| candidate_target_sets_exact | PASS |
| evidence_substrings_exact | PASS |
| ordered_expected_calls_derived_mechanically | PASS |
| external_rows_match_snapshot | PASS |
| no_reused_prior_external_sentence_ids | PASS |
| no_duplicate_holdout_inputs | PASS |
| no_exact_historical_input_overlap | PASS |
| construction_provenance_is_honest | PASS |
| base_pretraining_exclusion_not_overclaimed | PASS |
| mention_coverage_100_percent | PASS |
| mention_fallback_zero | PASS |
| mention_inside_evidence_100_percent | PASS |
| cross_target_mention_overlap_zero | PASS |
