# P3-B40 explicit playful-guess authority acceptance

Date: 2026-09-17

## Outcome

**PASS for the bounded exposed-development repair.** In immutable B38 case02 u4, the user explicitly
said not to calm them down, stated excitement and invited a guess about the first photograph. The
product ignored that action request and returned generic presence.

- immutable before: `そっか。まあ、今はうちがここにいる。`
- isolated four-turn product replay after:
  `最初は、窓の外の景色……とか？ まあ、うちのただの予想だけど。`
- planner route: `explicit_playful_guess_authority_p3`;
- added general-planner model calls: 0;
- fact-memory writes: 0;
- graph: one connected `playful_guess_authority_p3` node before `selected_plan`.

The response makes one actual guess rather than asking the user to provide the answer, but marks it
as a prediction and leaves room for correction. It does not claim knowledge of the future photograph.

## Selection boundary

The authority requires two observable clauses in the same current turn:

1. explicit positive arousal or rejection of calming; and
2. a first-person invitation to guess the first photography subject.

Source-disjoint Chinese, English and Japanese positive forms passed. The route fails closed for an
invitation without the positive/no-calm clause, an explicit `do not guess`, script/example text,
third-person reports, VRM/function commands, protected self-harm text and excitement without a guess
invitation. A runtime safety route still has priority.

The trace stores cue types and digests, not raw dialogue. The tentative guess is not written as a
stable preference, private state or fact memory; ordinary turn-episode persistence remains unchanged.

## Verification

- 13 classifier, plan, surface and graph tests passed before runtime replay;
- 1 isolated actual-product four-turn B38 replay passed in 36.73 seconds;
- 93 playful-guess, shared-amusement, current-request, explicit-space, repeated-refusal,
  contextual-expression and Japanese-guard tests passed in 86.10 seconds with 9 dependency warnings;
- `git diff --check` passed.

## Evidence boundary

B40 is derived from the exposed B38 output, so it is not independent evidence that the product beats
the direct baseline or generalizes to implicit playfulness. The fixed output deliberately covers a
narrow explicit act. A new ungenerated prospective case is required for the next product comparison;
B38 must not be regenerated or rescored as if the repair had existed beforehand.

