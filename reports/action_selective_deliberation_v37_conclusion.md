# V37 selective action deliberation conclusion

## Question

V37 tested whether the same local Qwen3.5 4B model could make safer VRM action decisions by spending two additional independent judgments only on risky utterances.

The comparison held the model, prompt, dataset, output schema, and compiler constant. The only policy difference was one judgment, selective three-judgment consensus, or three judgments on every case.

## Development result

All 36 cases were already-observed V36 development cases. They are diagnostic only.

| policy | exact calls | no-action | required recall | false action | mean passes | mean latency |
|---|---:|---:|---:|---:|---:|---:|
| single 4B judgment | 91.7% | 95.0% | 90.9% | 2.8% | 1.00 | 4.08s |
| selective three judgments | 91.7% | 95.0% | 90.9% | 2.8% | 2.28 | 7.33s |
| always three judgments | 91.7% | 95.0% | 90.9% | 2.8% | 3.00 | 9.50s |

The risk router found all 20 annotated high-risk cases, with three additional escalations. It stayed within the preregistered compute and latency limits. Accuracy did not improve at all.

## Why extra judgments failed

1. The three structured judgments were strongly correlated. Different fixed seeds and a small nonzero temperature usually produced the same semantic error, so majority voting repeated rather than corrected the error.
2. `少し疲れたから、静かな曲の話をしよう。` was incorrectly grounded to `play_motion(idle)`. The compiler verified valid syntax and evidence copying, but not whether the evidence actually named the proposed action.
3. `うなずかないで、首を横に振って。` produced a duplicated `shake_head` target with different commitments. The strict parser rejected the whole utterance and erased the valid positive request.
4. `怒った顔じゃなく、普通の表情へ戻して。` used one evidence span crossing both clauses. The coarse negation guard blocked the correctly requested neutral expression together with the negated clause.

## Decision

- V37 failed six preregistered gates and does not advance.
- No fresh holdout is created or consumed.
- No runtime or VRM execution change is authorized.
- Repeating the same 4B model is removed from the next candidate because it added latency without independent information.

## Next falsifiable hypothesis

V38 should test action-ontology grounding instead of more voting:

- every supported call must be grounded by an input span that actually denotes that exact domain and value;
- negation scope should be evaluated around that semantic anchor, not the model's potentially oversized evidence span;
- a duplicate or incorrect non-requested frame should remain observable as a warning without invalidating a separately grounded requested frame;
- the same single 4B model remains fixed, so improvement can be attributed to grounding and local error isolation.

This change is general to the finite VRM action vocabulary. It does not encode case IDs, expected calls, or benchmark answers.
