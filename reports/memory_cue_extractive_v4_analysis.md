# Memory cue-driven extractive fallback V4 analysis

## Decision

**Proceed only to a new untouched evaluation. Runtime integration remains unauthorized.** V4 is weak positive development evidence, not a generalization claim.

## Condition results

| Condition | Answerable | Unanswerable abstention | Overall | Mean latency | Mean prompt tokens |
|---|---:|---:|---:|---:|---:|
| A: full-session freeform | 28/36 (77.78%) | 0/12 (0.00%) | 28/48 (58.33%) | 14.065s | 1571.8 |
| P: provenance gate | 25/36 (69.44%) | 12/12 (100.00%) | 37/48 (77.08%) | 11.165s | 1433.4 |
| R: model reread fallback | 26/36 (72.22%) | 12/12 (100.00%) | 38/48 (79.17%) | 13.614s | 1785.3 |
| E: exact user-utterance fallback | 26/36 (72.22%) | 12/12 (100.00%) | 38/48 (79.17%) | 11.203s | 1439.9 |

## What actually improved

- E beat P on `1` case and lost on `0`: `transfer_dentist_current_time__end`.
- The overall gain is `+2.08 pp`; McNemar `p=1.000000` and bootstrap 95% CI `[+0.00, +6.25] pp`. This is not statistically persuasive evidence of broad improvement.
- The fallback triggered on `16` cases: `4` answerable and `12` unanswerable. E recovered `1` answerable case.
- Candidate sources were `100.00%` exact user utterances with `0.00%` assistant admission.

## E versus model rereading

- Correctness vectors identical: `True`.
- E saved `2.411s` mean latency (17.71%) and `345.4` mean prompt tokens (19.35%) relative to R.
- Therefore V4 supports a cheaper fallback, not a more accurate fallback than R.

## Remaining answerable failures

| Failure family | Cases | Localized cause |
|---|---:|---|
| current_count | 3 | The ledger and answer gate passed, but the answer generator narrowed the remembered water-bottle set against a material qualifier and refused the grounded count. |
| previous_frequency | 3 | The frozen generic sufficiency gate does not normalize the natural frequency phrase 'three mornings a week', so both fallbacks abstain. |
| historical_yes_no | 4 | One polarity error and three bare 'No.' answers remain. The evidence was available, but the final answer did not preserve the requested entity. |

## Evidence boundary

- E improved P by one of 48 cases (+2.08 percentage points), but the paired McNemar p-value is 1.0 and the bootstrap interval includes zero.
- E and R have identical correctness on all 48 cases. E's demonstrated advantage is efficiency, not higher accuracy than model rereading.
- E recovered one end-position current-time case while preserving 12/12 unanswerable abstentions and admitting no assistant source.
- Ten answerable failures remain in count scope, natural frequency, and historical yes/no realization; most are not retrieval failures.

## Next experiment constraints

- Do not modify runtime from V4; the report explicitly authorizes only a new untouched evaluation.
- Treat all 48 V4 cases and both pilots as consumed development evidence.
- Freeze the V4 implementation and preregister a new scenario-disjoint holdout before running it.
- Require more than one paired recovery and report uncertainty before any runtime promotion.
- Evaluate answer-contract failures separately from retrieval so a better surface answer is not misattributed to memory retrieval.

## Audit

- Source report SHA-256: `b9086660d4387e153a18e9e9c7113b749e3381871cce1fc704606f577a861414`.
- Source results SHA-256: `fb5745139d4557363e03676332770512f216eb137f3976f20b45942c2e5e8f98`.
- Frozen dataset, selector, sufficiency gate, implementation, model digest, and all 48 result IDs verified.
