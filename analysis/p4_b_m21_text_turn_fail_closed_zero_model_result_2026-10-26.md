# P4-B M21 text-turn fail-closed — isolated result (2026-10-26)

## Before/after and changed component

Before this change, an isolated Brain with a fake B gate error returned
`error_fallback`, produced the role reply
`どの選択を捨てたくないのか、まずそこから整理しよ。`, and saved **one** episode.
The text browser path also displayed a new assistant `"..."` bubble before
`_run_turn`; if the turn then raised, the generator propagated the error
without a cleanup update. These were source/fake reproductions, not true B
product sends. The prospective contract was independently reviewed, revised,
frozen and pushed as `7a65040` before product code changed.

After the change, the validated constructor B mode is passed to `LeftBrain`
independently of the mutable resource-gate reference. In a private/gated M21
exception, `LeftBrain.think` rethrows before printing exception text or
building the ordinary fallback plan. An isolated full `run_turn_debug` then
has **zero** final role reply and **zero** saved episodes. Non-B fake model
errors retain the prior `error_fallback` and one episode. This is a B text
error-routing change, not a model or reply-quality improvement.

The B browser text path now shows only the new user row while pending,
retains the original textbox content, and on `_run_turn` exception restores
prior history/input and clears pending panels with a fixed non-role status.
Normal completion adds exactly one assistant row and streams the actual
reply. Non-B pending/streaming behavior stays unchanged. Existing exact-input
rejection still takes precedence when both arms are set.

## Evidence, costs, and limits

| Evidence | Observed result |
|---|---|
| Focused red/green | Initial isolated new suite: **6 expected failures / 2 controls passed** after test fixtures were made independent of unrelated M31 routing. After product patch and a test-only correction to read the serialized receipt schema, focused + constructor tests **18/18 passed**. |
| Affected regression | Ten files covering B constructor, M21 planner, Web compute receipts, admission attribution, exact-input Web boundary, compact failure taxonomy, B Web ledger and source manifest: **164/164 passed in 79.56s**; 9 pre-existing dependency warnings. |
| Fake full Brain→Web failure | B gate error keeps its original type. In a private 0700 test log directory, `compute_failures.jsonl` exists as 0600, has raw-free `terminal_error` and `generative_call_count=0`; no conversation JSONL or episode. In a non-private directory the writer refuses to create the failure file. The file append is not crash-durable proof. |
| Fake browser-bound UI | Each yielded update has 14 fields. Prior assistant history is preserved; B pending/error adds no new assistant row, restores exact unstripped input, clears pending flow/state, and finishes once with `error`. Fake successful B text turn keeps the user row, streams one assistant reply, and finishes `delivered`. Non-B fake exception still raises after its old `"..."` pending state; dual B/exact-input without permit rejects before turn. |
| Syntax/diff | Changed Python `py_compile` and `git diff --check` passed. |

Important process deviation: while diagnosing why an early Brain test took a
non-M21 route, **two exploratory isolated direct probes inadvertently invoked
the local M31 semantic model** (observed M31 elapsed about 6.58s and 6.64s).
They used the fake memory fixture, did not enter B Send/Safari/formal data, and
are excluded from the zero-provider acceptance counts. Their token usage is
unavailable. The new test fixture forces a source-only M21 route and replaces
the native M31 authorizer with a failing sentinel, so the reported final test
runs are zero-provider contracts. This deviation is retained rather than
called a successful B model check.

No true Ollama B Send, native Safari, 20-second delivery, production DB,
human rating, VRM or Function Calling was tested. The Brain may have changed
transient cognitive state or queried fake memory before M21; this is not a
whole-turn rollback. The zero-episode claim applies to thrown M21 errors,
not errors after emit/writeback. Web private failure append is best effort,
not fsync/readback durability. Audio, non-M21 B routes, and post-response
gate terminal states (e.g. missing usage after provider return) remain open.
Production still has **no proved same-model prompt-token upper bound**, and
the real B daemon/runner identity, full source/effect closure, A author
ratings and Safari gate remain unverified. Therefore true B Send is still
**NO-GO**, and no human-response-equation claim changes from this item.

Next necessary delivery: predeclare and test a B-only boundary for
post-provider-result gate terminal failures, ensuring a returned SDK response
with invalid/missing usage cannot reach final role utterance or episode. Keep
ordinary non-B response behavior as a negative control. Commit/source closure
and any real B trial require their own later gates.
