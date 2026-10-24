# P4-AT real executed-action outcome closure: formal FAIL

The prospectively frozen two-turn private-runtime/Safari gate is **FAIL**. Both turns were executed exactly once in one isolated session at port `7883`; the inputs will not be rerun and the frozen gate will not be changed.

## Observable result

Turn 1 input:

> 我的思緒一層一層堆上來，今晚腦袋完全安靜不下來。

Turn 1 visible reply:

> しんどくて止まらないのと、楽しみで止まらないの、今はどっち寄り？

Turn 2 input:

> 你剛才先問是對的；我現在需要一個馬上能做的步驟。

Turn 2 visible reply:

> 今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。

The only failed frozen metric is `turn_2_m39_practical_act_count`: expected `1`, observed `0`.

## What the real product did prove

- Turn 1 executed the `calibrate_need` action, registered an exact M44 receipt for `p1-1-54b3425d01de0b33`, created six P4-AG candidates, and locked the next-turn outcome commitment.
- Turn 2 linked the user's support back to that exact earlier action. P4-AT was `closed_supported`; M44 and P4-AG both recorded `supported` with exact identity.
- The same turn was not collapsed into one act: the current request was separately identified as `solve_regulation` / `practical_help`.
- The temporal trace kept the performed action strictly earlier, consumed the prior future commitment, and did not backdate the current observation.
- The P4-AT node was visible in Safari at graph index `66`, before P4-AG `67`, temporal `68`, and utterance `69`.
- Both visible replies were natural Japanese, both episodes were durably written in the isolated store, and P4-AT itself added zero model calls and zero factual-memory writes.

This supports a narrow claim: one real product path can distinguish feedback about a previously executed response action from a new response request, preserve exact event identity, and expose the distinction in the runtime graph.

## What failed and why it matters

The current action was not delivered. Before the final verifier, the candidate reply was:

> 今すぐできる一個だけ、一緒に決めよ。

M45 attempted actionable-help delivery twice, completed one model call, then ended `withheld_model_unavailable` with `TimeoutError`; token accounting was incomplete. M46 was `counterfactual_review_unavailable`. M39 therefore failed closed on `practical_action_not_delivered_m45` and changed the surface to another context request. The second turn took `37.9706s`, above the frozen `20s` target.

This result separates three claims that must not be conflated:

1. the system recognized support for the earlier clarification;
2. the system recognized that the user now wanted practical help;
3. the system actually delivered useful practical help.

The first two passed in this case; the third failed. Therefore this result is not evidence of felt understanding, user preference, natural-distribution generalization, a recovered human equation, or superiority over a strong LLM.

## Next bounded correction

This pair is now exposed development evidence only. It must not be rerun. The next prospective task must freeze new cases before implementation and change one causal boundary: make the immediately preceding source-bound problem context available to a current explicit response request when, and only when, the current turn is exact feedback on the executed action plus a new request. It must not weaken M39/M45, invent a method without source context, change the P4-AT outcome classifier, or count a generic promise to help as an executed practical action.
