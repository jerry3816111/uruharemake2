# V38 action ontology grounding conclusion

## Question

V38 tested whether V37's errors came from the model itself or from the boundary between a model-produced frame and an executable VRM action.

No new model inference was performed. Four compilers replayed the same frozen primary 4B reply for every retired development case.

## Matched replay result

| condition | exact calls | no-action | required recall | false action | parse success |
|---|---:|---:|---:|---:|---:|
| V37 single control | 91.7% | 95.0% | 90.9% | 2.8% | 88.9% |
| action-anchor grounding only | 94.4% | 100.0% | 90.9% | 0.0% | 88.9% |
| local duplicate isolation only | 94.4% | 95.0% | 95.5% | 2.8% | 91.7% |
| full V38 | **97.2%** | **100.0%** | **95.5%** | **0.0%** | 91.7% |

## What each component changed

- Action-anchor grounding corrected the false idle motion for a conversation about quiet music and recovered the positive neutral-expression correction after a negated angry expression.
- Local duplicate isolation recovered the requested head shake even when a malformed non-requested frame duplicated the same target.
- Full V38 corrected all three V37 failures without new inference, but rejected one previously correct colloquial nod request because the frozen ontology did not ground `うんって感じで` to `nod`.
- The model also produced three malformed traces on non-action or unsupported cases. They remained safe, but the preregistered parse-success gate still failed.

## Decision

- V38 passes every action-safety and latency gate but fails the full-trace parse-success gate.
- The development gate therefore fails as preregistered.
- No fresh holdout is created or consumed.
- No runtime or VRM execution change is authorized.

## Next falsifiable hypothesis

V39 should keep the successful grounding compiler and change two explicit components:

1. add general colloquial action anchors, including an affirmation-as-gesture construction, together with near-miss negatives that must remain conversation only;
2. isolate every malformed individual frame as an observable warning while keeping valid grounded requested frames executable. Root-level JSON and array failures remain fatal.

V39 must report execution safety and full-trace well-formedness separately. It may advance only after a frozen fresh holdout confirms zero false actions and adequate trace quality.
