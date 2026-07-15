# V57 relation-authorized compiler independent holdout

V48 and V57 consumed the same fresh V56 commitments and the same single local-model fallback per target. Only the compiler changed.

## Result

| Condition | Ordered exact cases | Action exact | Required-call recall | False-action cases | No-action specificity |
|---|---:|---:|---:|---:|---:|
| V48 control | 50/64 (78.12%) | 62.07% | 61.54% | 3 | 91.43% |
| V57 candidate | 54/64 (84.38%) | 79.31% | 84.62% | 4 | 88.57% |

- Fresh V56 state commitment accuracy: 73/85 (85.88%)
- V57 vs V48 exact-case delta: +4
- V57 fixes / regressions: 9 / 5
- Safe fail-closed action misses: 4
- Decision: `reject_v57_and_preregister_relation_or_authorization_repair`

A no-action answer cannot pass by safety alone: the gates independently require action-case exactness and required-call recall.

## Source split

| Source | V48 ordered exact | V57 ordered exact |
|---|---:|---:|
| external_exact | 26/32 (81.25%) | 25/32 (78.12%) |
| controlled_compositional | 24/32 (75.00%) | 29/32 (90.62%) |

## Gate summary

| Gate | Result | Failed checks |
|---|---|---|
| state_prerequisite | FAIL | commitment_accuracy, requested_precision |
| candidate_compiler | FAIL | ordered_exact_accuracy, action_ordered_exact_accuracy, required_call_recall, no_action_specificity, false_action_count, external_exact_accuracy, controlled_family_floor |
| matched_comparison | FAIL | regressions, false_action_delta |

## Evidence boundary

This result covers only Japanese action perception and authorization for a future VRM interface. It does not establish active-chat quality, memory quality, personality, complete right-brain quality, physical safety, or broad human likeness.
