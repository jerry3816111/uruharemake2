# V38 action ontology grounding development replay

This is a zero-inference replay of the frozen V37 primary outputs. It can authorize only a fresh holdout, not runtime integration.

| condition | exact | no-action | recall | false action | parse | anchor coverage | failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| v37_single_control | 91.7% | 95.0% | 90.9% | 2.8% | 88.9% | 0.0% | 3 |
| anchor_grounding_only | 94.4% | 100.0% | 90.9% | 0.0% | 88.9% | 100.0% | 2 |
| local_isolation_only | 94.4% | 95.0% | 95.5% | 2.8% | 91.7% | 0.0% | 2 |
| full_v38_candidate | 97.2% | 100.0% | 95.5% | 0.0% | 91.7% | 100.0% | 1 |

## Causal attribution relative to V37 single pass

- `anchor_grounding_only` fixed `['v34c_action_none_music', 'v34c_action_negated_angry_neutral']` and regressed `['v34c_action_single_nod_colloquial']`.
- `local_isolation_only` fixed `['v34c_action_negated_nod_shake']` and regressed `[]`.
- `full_v38_candidate` fixed `['v34c_action_none_music', 'v34c_action_negated_nod_shake', 'v34c_action_negated_angry_neutral']` and regressed `['v34c_action_single_nod_colloquial']`.

## Candidate gate

- Passed: `False`
- Failed checks: `['parse_success_rate']`
- Decision: `do_not_advance_v38_action_ontology_grounding`
