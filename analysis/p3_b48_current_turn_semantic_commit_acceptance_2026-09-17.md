# P3-B48 current-turn semantic commit acceptance

## Result

P3-B48 adds one authority invariant at the existing desired-response planning seam: a policy may still select interaction style, but an arousal-regulation example sentence may not replace an already-grounded current-turn semantic core in another domain unless the current turn explicitly authorizes that response form.

The retained B47 counterexample now changes as follows in deterministic replay:

| Stage | Semantic core |
| --- | --- |
| Before B48 policy application | `第三版まで来て、また注釈かよ。` |
| Before repair, after `calibrate_need` | `寝てないのか、考え事で止まんないのか、まずそこだけどっち？` |
| After B48 policy application | `第三版まで来て、また注釈かよ。` |

The policy id and response mode remain traceable, but `policy_performed=false` when the policy's domain-specific sentence was not actually surfaced. This avoids claiming that a fluent but unrelated template fulfilled the current turn.

## Single causal change

The six M18 policy surface sentences are identified as `arousal_regulation` realizations. `apply_decision_to_plan` may use one as semantic content only when at least one condition is true:

1. the current context domain is `arousal_regulation`;
2. an authoritative current-turn explicit response request or correction grants surface authority; or
3. there is no existing semantic core to preserve.

Otherwise the selected policy may shape `reply_goal`, `response_mode` and dimensions, while the current semantic core remains authoritative. The new `uruha_current_turn_semantic_commit_m48` trace records only domains, booleans and digests; it does not persist raw dialogue. The node is carried through the brain runtime, compact Web trace and memory-observatory graph before the adaptive surface commitment.

## Development counterevidence retained

The first implementation denied all cross-domain policy semantic replacements. It broke 6 of 41 focused/adjacent tests because authoritative corrections and explicit current-turn requests legitimately need to change the surface. The rule was narrowed to keep those two current-turn authority paths. This is evidence for the final authority boundary, not a hidden green-only history.

One shell invocation also joined 21 test filenames into one zsh argument and ran zero tests. It was not counted. The corrected `xargs` invocation produced the reported 164-test result below.

## Verification

- `test_current_turn_semantic_commit_m48.py`: **6 passed**;
- focused/adjacent development set after narrowing: **41 passed**;
- every test file that directly imports `uruha_adaptive_person_model`: **164 passed**, 9 existing dependency/deprecation warnings;
- `git diff --check`: clean before freeze;
- model calls: **0**;
- network calls: **0**;
- formal B46/v3 regeneration: **not performed**.

The tests cover cross-domain preservation, explicit-current-turn authority, in-domain legacy behavior, prevention of late surface reintroduction, graph exposure and Web compact-trace retention.

## Claim boundary and remaining failures

This is a deterministic mechanism repair derived from an exposed failed developer case. It is not fresh generation evidence, Safari evidence, human preference evidence, formal temporal holdout evidence or proof of UruhaBrain advantage.

It directly addresses the u1/u2 class in which an unrelated policy template overwrote an existing grounded semantic candidate. It does **not** yet repair:

- u3: a non-Japanese semantic core is rejected and the safe language fallback loses its meaning;
- u4: the explicit request `陪我吐槽` is still collapsed into generic `share_arousal`.

Those remain separate causal variables. P3-B49 takes only the u3 language-repair boundary next; B46's immutable one-time release remains closed.
