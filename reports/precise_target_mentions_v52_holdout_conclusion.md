# V52 fresh-holdout conclusion

## Decision

Reject V52 for runtime or shadow advancement. Do not tune V52 on this now-consumed holdout.

## Frozen result

| condition | commitment | exact calls | false actions |
|---|---:|---:|---:|
| V51 event-map control | 67/85 (78.82%) | 56/64 (87.50%) | 2 |
| V52 precise target mentions | 66/85 (77.65%) | 54/64 (84.38%) | 3 |

The candidate fixed three target judgments but regressed four. It fixed no complete call case and regressed two. On the prespecified cross-target subset, exact calls fell from 4/5 to 3/5. The exact paired target McNemar test was `p = 1.0`; there is no evidence of a stable gain.

## External-text boundary

On the 24 exact Tatoeba sentences, V51 produced 22/24 exact calls with one false action. V52 produced 21/24 exact calls with two false actions. V52 newly converted the descriptive sentence `犬が遊びたいオーラ全開でこっちを見てる。` into an executable gaze request.

The Tatoeba subset is project-fresh and source-attributed, but absence from the base model's pretraining data cannot be guaranteed.

## Architectural interpretation

Exact target mentions are a useful deterministic representation audit, but asking the 4B model to infer all six discourse states from that representation remains prompt-sensitive. The result does not support replacing V51 with V52, changing runtime, or enabling physical VRM execution.

The preregistered next path is an explicit per-target discourse-state machine for deterministic quotation, question, negation, cancellation, conditional, pending-choice, and positive-request transitions. A model may be used only as a selective fallback for unresolved cases, and its output must still pass the deterministic compiler. A new independent holdout is required before any later advancement.
