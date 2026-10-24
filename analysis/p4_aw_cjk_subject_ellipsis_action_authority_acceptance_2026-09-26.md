# P4-AW bounded CJK subject-ellipsis action authority

Status: **offline deterministic contract PASS; real Safari/product effect not yet authorized by this result**.

## Problem and single variable

The frozen P4-AV real run visibly performed `calibrate_need`, but the Chinese
source omitted an explicit first-person pronoun. M39 preserved
`speaker_role=unspecified`; P4-AS therefore did not register the visible action
as an executed event. The new variable is only a bounded authority bridge for
this CJK subject-ellipsis boundary.

P4-AW leaves the source frame unchanged. It first records a provisional
current-user ellipsis candidate when an existing typed
`cognitive_overactivity` signal is a direct current-user statement with no
third party, quote, report, hypothetical/question frame, physical-object-only
signal, or resolved-state wording. It becomes final only if the existing M39
surface, `calibrate_need`, P1 event, pending state, turn/input digest, and plan
identity checks all pass exactly. One missing final check still fails closed.

## Frozen results

- exposed development: `1/1` authorized after the fix;
- fresh Chinese/Japanese subjectless positives: `6/6` authorized;
- fresh controls: `12/12` blocked across third-party, quoted/metalinguistic,
  news/report, physical-object motion, resolved state, and ambiguous role;
- explicit first-person predecessor controls: `2/2` preserved;
- typed-trigger and complete final P4-AS/P4-AR chain: `7/7`;
- false control authority: `0/12`;
- source-frame or trigger-detector mutation: `0/0`;
- P1/P4-AR weakening, candidate rerank, feedback change, visible-reply change:
  `0/0/0/0`;
- new model calls, factual-memory writes, raw-dialogue trace, private-state
  truth claims, and full fresh-string patches: `0/0/0/0/0`.

The first implementation result is preserved separately. It reached only
development `0/1` and fresh positives `4/6`, while all controls remained
correct. The root cause was that P4-AS advanced only newly additive P4-AH
triggers; three cases already had the same typed predicate upstream. The one
informed correction composes that already-typed signal into a copied shadow
state. Neither detector, the frozen data, nor the gate changed.

## Verification and cost

The final P4-AW focused suite is `15 passed`; the affected total is `74 passed`
(`15` P4-AW plus `59` P4-AS/P4-AR/P4-AT/P4-AU/P4-AV/M44/temporal tests). The isolated product launcher
preflight at port `7886` is `ready`, uses the existing sandbox, starts no
server, performs zero model calls, zero Safari operations, and zero VRM/tool
operations.

## What this does and does not establish

This result establishes a narrow deterministic bridge: in the frozen CJK
grammar, subject omission no longer prevents an otherwise exact executed-action
chain, while the specified false-authority families remain closed. It is not
open-domain coreference, proof that the inferred state is true, proof that the
reply is useful, felt-understanding evidence, human evaluation, a human
equation, or an advantage over a matched LLM.

The prior P4-AV Safari failure remains a failure. The next authorized step is
to commit this offline implementation, then prospectively freeze a completely
new two-turn private-runtime/Safari pair. Only that new pair may test whether
P4-AW reaches P4-AV and a visible practical action in the real product path.
