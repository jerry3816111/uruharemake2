# P4-AN post-turn temporal graph — preserved failure

## Outcome

P4-AN is a formal **FAIL** and stopped after the first fresh formal turn. The
post-`run_turn_debug` repair did fix the exact P4-AM delivery defect: Safari
showed `runtime_temporal_graph_delivery_p4` before `utterance`, and the graph
payload exactly matched the same-turn logic/runtime payload.

However, the visible node truthfully showed:

`過去 0｜現在 0候選/選択 なし｜本輪未來 無承諾`

That violates the frozen six-candidate and locked-future gates, so the same
case was neither continued nor rerun.

## Newly exposed root cause

The first input produced a valid P4-AH additive compositional trigger:

- predicate: `cognitive_overactivity`
- language: `zh`
- private truth claimed: `false`

But the P4-AD/P4-AF candidate ledger had already been assembled before that
late extension was available. The trace therefore had an authorized
bounded-emotional eligibility reason but the predecessor ledger remained
`not_applicable`, with zero candidates. P4-AG consequently had no current
binding for P4-AM to commit.

This is a separate real-product ordering gap from the P4-AM graph-delivery
failure. Passing a synthetic P4-AH trigger test did not prove that the trigger
fed the live candidate ledger.

## Evidence boundary and next split

P4-AN supports only the narrow claim that the post-turn graph delivery hook
works for an existing payload. It does not support the full three-turn temporal
cycle.

The next work must keep two questions separate:

1. use a fresh input whose released base trigger already reaches P4-AD, to
   finish the isolated three-turn product graph acceptance without changing
   any cognitive mechanism;
2. separately freeze and repair the P4-AH-to-P4-AD live ordering gap, followed
   by a new downstream chain. The P4-AN input is now exposed development data.
