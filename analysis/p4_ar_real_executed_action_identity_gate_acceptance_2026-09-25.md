# P4-AR real executed-action authority gate — acceptance

## Outcome

P4-AR is a formal **PASS** for its prospectively frozen, one-turn causal-authority
contract. It is not a response-quality pass.

The fresh English input was executed once in a private product runtime and
inspected in Safari. P4-AQ first rebuilt the fixed late trigger into six
candidate response actions and selected `calibrate_need`. P4-AR then checked
whether the product had actually performed that action. It had not: the
released M18 decision was `not_applied`, the M44 receipt was `not_registered`,
and there was no genuine P1 event. P4-AR therefore blocked the pending shadow
binding instead of assigning feedback to an action the user never saw.

## Exact observed chain

1. base M37 trigger: `no_bounded_observable_trigger`;
2. additive P4-AH trigger: `additive_compositional_trigger`;
3. P4-AQ: `0 -> 6` candidates, selected shadow policy `calibrate_need`;
4. P4-AR: `blocked_unexecuted_shadow_action`;
5. current verification binding: `not_available`, candidate count `0`, while
   retaining `suppressed_shadow_candidate_count=6` for inspection;
6. temporal graph: `過去 0｜現在 0候選/選択 なし｜本輪未來 無承諾`;
7. utterance delivery.

The final graph indexes were guard `64`, ordering `65`, binding `66`, temporal
`67`, and utterance `68`. All four causal nodes therefore precede the visible
utterance. Logic-to-graph payload equality was exact for the guard, ordering,
binding, and temporal nodes.

## Safari evidence

Safari at `http://127.0.0.1:7879/` showed the runtime node graph and the exact
temporal summary. Expanding `executed_action_identity_gate_p4` exposed:

- status `blocked_unexecuted_shadow_action`;
- reason `pending_shadow_action_lacks_exact_executed_product_event`;
- selected shadow policy `calibrate_need`;
- failed exact execution/identity checks;
- `outcome_verification_authorized=false`;
- `fallback_identity_promoted_to_p1=false`.

The product runtime, isolated database, and Safari tab remain open for local
inspection. No Safari tab was closed.

## Metrics and preserved artifacts

- formal turns: `1`;
- conversation rows: `1`;
- durable Chroma embeddings: `1`;
- Japanese-visible replies: `1/1`;
- P4-AQ repair / P4-AR block: `1/1` / `1/1`;
- six-candidate ambiguity preserved: `1/1`;
- false future commitments: `0`;
- fallback identities promoted to P1: `0`;
- P4-AR-added model calls / factual-memory writes: `0 / 0`;
- user-visible latency: `17.6066s`, below the frozen `30s` ceiling;
- JSONL SHA-256:
  `d034772f40261d4d85a50c68027b41667a48378d78d63838664a8be64364fb86`.

## Important quality failure outside this gate

The visible reply was:

> うちの頭は考えで埋まって今夜落ち着かないんだね。

It is Japanese, but it changes the user's first-person experience into the
character's `うちの頭`. It also does not actually perform the selected
low-pressure clarification. Consequently this acceptance supports only causal
honesty: unexecuted internal candidates cannot receive later credit. It does
**not** support felt understanding, correct speaker ownership, preferred reply,
prediction accuracy, a human equation, or superiority to a strong LLM.

## Next necessary capability

P4-AS must align the chosen bounded response action with the delivered Japanese
surface and the executed-action receipt. It may create a P1 verification event
only after the visible reply demonstrably realizes the selected action. The
P4-AR input is now exposed development evidence and must not be rerun as a new
formal case.
