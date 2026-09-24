# P4-AK post-morphology learning chain — preserved formal failure

## Result

P4-AK is **FAIL** under its prospectively frozen contract.  The only failed
gate was `japanese_morphology_extension_count`: observed `2`, required `3`.
The dataset, predecessor hashes, classifiers, thresholds, and gate were not
changed after the result, and no formal retry was performed.

The formal command completed with one passing and one failing test.  A later
deterministic run was used only to capture the already observed metrics as a
regression artifact; it reproduced the same failure and is not a new formal
execution or authorization.

## What worked, but does not erase the failure

- typed cognitive-overactivity trigger: `9/9`
- current-interaction eligibility: `9/9`
- six operational response candidates: `9/9`
- exact first-turn prediction/ledger identity binding: `9/9`
- exact next-turn outcome: `9/9`
- support retained selected action: `3/3`
- contradiction revoked the selected action and supported the explicit
  replacement: `3/3`
- unrelated next turn stayed unknown: `3/3`; unknown counted as success: `0`
- visible reply/model/factual-profile-episode writes/raw dialogue persistence:
  `0`

The Japanese unknown case contained `次々`, which the older M37 trigger family
already recognizes.  It therefore entered P4-AJ as `baseline_retained` rather
than `inflection_matched`.  Its final unknown outcome was correct, but the
frozen requirement that all three Japanese cases specifically exercise the
new morphology extension was not met.

## Academically defensible interpretation

This is evidence for the usefulness of causal-path gates: an output-only score
would have reported `9/9`, while the prospective mechanism gate detected that
one item did not traverse the intended new component.  It is not evidence that
the whole chain passed, that visible replies improved, that natural dialogue
generalizes, that future behavior is predictable, or that the system beats a
strong LLM.  P4-AK is closed as a negative result rather than tuned against its
exposed cases.
