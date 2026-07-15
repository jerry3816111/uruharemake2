# V53 selective discourse-state development conclusion

## Decision

Close V53 as a failed near-pass. Do not advance this exact implementation to a new holdout, shadow mode, runtime, or physical VRM execution.

## Result on consumed development data

| condition | commitment | exact calls | false actions |
|---|---:|---:|---:|
| Frozen V51 model | 67/85 (78.82%) | 56/64 (87.50%) | 2 |
| Deterministic state machine only | 79/85 (92.94%) | 61/64 (95.31%) | 0 |
| Selective state machine + frozen V51 fallback | 82/85 (96.47%) | 62/64 (96.88%) | 0 |

The state machine resolved 82/85 targets at 96.34% accuracy and used frozen fallback for 3/85. The hybrid fixed 17 semantic targets and six complete calls, with no complete-call regression. However, it introduced two semantic regressions, exceeding the preregistered maximum of one.

## Narrow failure

All three wrong high-confidence states came from one rule. It treated metalinguistic statements such as `これは指示ではない` and `あなたへのお願いではない` as explicit prohibition (`negated`) rather than non-request mention (`mentioned`). Both states correctly prevent action, but they are not cognitively equivalent.

## Next experiment

V54 may change only that distinction: an explicit execution prohibition such as `実行しないで` remains `negated`, while denial that quoted text is an instruction/request becomes `mentioned`. Every other V53 transition, fallback, ontology, compiler, dataset, and gate remains fixed. Because the corpus is consumed, a V54 development pass can authorize only a new independent holdout.
