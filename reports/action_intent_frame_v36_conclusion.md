# V36 action-intent frame conclusion

## Research question

Does parsing the complete utterance into observable action frames before deterministic compilation improve VRM action behavior over direct function calling?

The design follows Frame Semantics and schema-guided dialogue principles: language is first represented as an intent/commitment state, while application code remains responsible for checking and executing calls.

## Preregistered development result

| condition | call exact | no-action | call recall | false action | state | frame exact | p50 | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Qwen3.5 0.8B frame | 58.3% | 100.0% | 9.4% | 2.8% | 8.3% | 2.8% | 1.41s | FAIL |
| Qwen3.5 2B frame | 55.6% | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 2.33s | FAIL |
| Qwen3.5 4B frame | **94.4%** | **95.0%** | **93.8%** | 5.6% | 52.8% | 33.3% | 4.02s | FAIL |
| Qwen2.5 7B frame | 75.0% | 80.0% | 75.0% | 13.9% | 44.4% | 27.8% | 3.09s | FAIL |
| Qwen3.5 9B frame | 91.7% | 95.0% | 93.8% | 5.6% | 69.4% | 36.1% | 8.28s | FAIL |

All 36 cases are retired development cases. No row is fresh confirmation evidence.

## Same-model representation comparison

| same model | exact delta vs direct call | no-action delta | recall delta | false-action delta |
|---|---:|---:|---:|---:|
| Qwen2.5 7B | +16.7 pp | +45.0 pp | -12.5 pp | -27.8 pp |
| Qwen3.5 9B | **+36.1 pp** | **+70.0 pp** | 0.0 pp | **-38.9 pp** |

The representation materially improves action selection for the same model, especially no-action specificity. It still fails the strict zero-false-action gate and therefore cannot enter runtime.

## Root-cause findings

1. The 4B frame parser recovered multiple requested actions and reached 34/36 exact calls, overcoming V35's inability to restore omitted proposals.
2. The two remaining 4B action failures were semantic grounding errors: a negated happy expression became a neutral-expression request, and gaze toward the interlocutor became right gaze.
3. Global `utterance_state` duplicates information already present in frame commitments. Models often produced useful local frames but an inconsistent state label, causing avoidable parse failure.
4. A special `unsupported` frame is unnatural. Models frequently identified the correct domain but used `value=unsupported`, which the frozen schema rejected.
5. Smaller models were not sufficient merely because the output was structured. The 0.8B and 2B conditions failed semantic and/or JSON adherence.

## Post-hoc exploration boundary

The following analysis was performed only after opening V36 results. It is diagnostic and cannot authorize promotion:

| exploratory combination | exact | no-action | recall | false action |
|---|---:|---:|---:|---:|
| loose 4B frames | 94.4% | 95.0% | 93.8% | 5.6% |
| intersection of 4B and 9B calls | 97.2% | 100.0% | 93.8% | 0.0% |
| majority of 4B, Qwen2.5 7B, and 9B | 100.0% | 100.0% | 100.0% | 0.0% |

The three-model result is not evidence of deployable performance: it is post-hoc, uses already-seen cases, and is too expensive for the local-PC target.

## Decision

- Do not integrate V36 into runtime or enable VRM execution.
- Do not create a fresh V36 holdout because no preregistered candidate passed.
- Preserve utterance-level frames as the promising representation, but remove redundant state prediction and redesign unsupported actions as attributes rather than a synthetic action class.
- The next experiment should test selective deliberation: one 4B pass normally, with additional independent 4B judgments only for high-risk negation, cancellation, unsupported, or parse-failure cases. Its routing and latency gates must be preregistered before new inference.
