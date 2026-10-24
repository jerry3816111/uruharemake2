# P4-AM real runtime temporal graph — preserved failure

## Outcome

P4-AM is a formal **FAIL**. The frozen three-turn acceptance stopped after its
first formal turn, because the P4-AM node was absent from the Safari runtime
node graph. The same case was not continued or rerun.

The first turn still established a narrower diagnostic fact:

- visible reply was natural Japanese: `今ほしいの、止め方と、ただ聞いてほしいのと、どっちに近い？`
- the isolated local trace contained an honest empty-past commitment with six
  present candidates and a locked future outcome;
- the P4-AM payload in `logic` and the top-level runtime trace was identical;
- but `runtime_trace.blackboard` did not contain either the P4-AG binding node
  or the P4-AM delivery node, so Safari could not render it.

## Root cause

The adapter wrapped `emit_response_if_ready`. After that wrapper returned,
`UruhaBrainV4_Mac.run_turn_debug` copied `self.runtime.blackboard` back into
`result.runtime_trace.blackboard`. That later assignment discarded the
adapter-inserted graph nodes while leaving the top-level trace payloads in
place.

This is why backend payload presence cannot be treated as product graph
delivery evidence.

## Evidence boundary

The result does not test the second-turn verification or third-turn promotion
to past evidence, and it says nothing about future-prediction accuracy, human
preference, a human equation, or an advantage over a strong LLM. It is a
specific product integration failure with a localized hook-order cause.

The next chain must use a fresh case, freeze a post-`run_turn_debug` delivery
contract, and keep this failed result unchanged.
