# P4-AT offline executed-action outcome closure

Status: **PASS at the bounded deterministic/offline layer; real product and Safari remain pending.**

## Capability change

P4-AT separates two variables that the previous product collapsed:

1. observable feedback about the exact clarification action executed on the previous turn;
2. the response form explicitly requested for the current turn.

The new layer is allowed to close the previous action only when the product's pending P1 identity, the M44 executed-action receipt, policy, and next-turn window all match. The current request remains current-turn evidence; it is not written as a stable preference or private mental fact.

For example, the preserved real development utterance `Yes—that question was right. I want a practical method now.` previously produced `unknown` for the old action and no usable current request. The bounded contract now represents it as:

- previous executed `calibrate_need`: `supported`;
- current request: `solve_regulation`;
- current Japanese action act: practical help;
- no candidate score/order change, no model call, and no factual-memory write.

## Frozen result

- all expected previous outcomes: `17/17`
- all expected current requests: `17/17`
- exposed development closure: `1/1`
- fresh Chinese/English/Japanese dual-act sequences: `9/9`
- fresh controls: `7/7`
- false prior-action link in controls: `0/7`
- exact receipt identity and strictly-earlier action: `17/17`
- unrelated inputs remain unknown: `3/3`
- third-party/quoted/metalinguistic false link: `0/3`
- unknown counted as success: `0`
- candidate score/order changes: `0`
- new model calls / factual-memory writes / raw-dialogue trace leaks: `0 / 0 / 0`

The temporal contract deliberately distinguishes an action that occurred on turn 1 from outcome evidence first observed on turn 2. The old action is strictly earlier and its future commitment is consumed; the new turn-2 evidence is not backdated as if it had been known on turn 1. Existing temporal delivery may promote the verified result on a later turn.

## Verification and limits

P4-AT freeze and implementation tests total `14 passed`; the targeted set including P4-AS, P4-AR, P4-AG, M44, and temporal behavior is `51 passed`. The isolated launcher preflight is `ready` with the existing product Python. The earlier failed preflight used the system Python and is an invocation error, not a product capability result.

This evidence does **not** show open-domain pragmatic understanding, natural-distribution coverage, human preference, advantage over a strong LLM, or a solved human reaction equation. Those claims require fresh real product/Safari evidence and later independent evaluation.
