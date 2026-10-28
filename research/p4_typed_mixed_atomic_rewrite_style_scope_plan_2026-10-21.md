# P4 typed mixed-act atomic delivery: bounded rewrite style scope

Status: **prospective second and final correction batch**, developer-authored,
not a temporal holdout or a same-model baseline comparison. Freeze this plan,
its paired S0–S9 dataset, and their preimplementation SHA **before** code,
new model calls, or Safari. The old N and Q raw/gold remain strict FAIL; never
replay them to claim a fresh pass. If this S batch fails, issue
`REVIEW_REQUIRED` with the smallest counterexample and design alternatives,
not a third incremental rule patch.

## Before, falsifiable cause, one variable

Q0/Q3/Q7 had a legitimate linked M31/M32 mixed-act chain, entered the new
atomic path, completed one bounded rewrite call, and rejected its candidate as
`new_number`. This is a correct rejection, not a delivered rewrite. The call
site currently passes the whole normalized text *outside* the quote as
`requested_style`; this includes a second act and its absolute date, although
the generator is supposed to edit only `source_quote`. Outer-date leakage is a
plausible prompt-scope cause, **not proven**: the rejected raw generated phrase
is not preserved in Q receipts. Q2/Q5 M32=false, User `私`→character `うち`
actor reversal, Q8 wording, and >20 s Q waits are independently observed
failures. This batch neither fixes nor waives them.

Change exactly one variable in the *mixed atomic call site*: supply the
existing bounded rewrite generator with a canonical, narrowly extracted
`requested_style` from the observable outer **style_goal** only, not the whole
outer request. Preserve the complete normalized quoted source, including a
date genuinely inside the quote. The style extraction must check the existing
current-turn role certificate, allow only an unambiguous supported audience/
tone cue (for example friend-facing + softer/casual), and fail closed with no
extra call or terminal authority if that cue is absent, contradictory, or
malformed. It must not infer user intent or copy the other task, requested
date/place, personal facts, sensitive text, or a fallback default into the
style field. A deterministic rendering such as `友達向けの柔らかい日本語` may be used
only when that meaning was actually present in the outer text. Do not alter
`source_quote`, model/system prompt, model, temperature, token/timeout cap, or
the existing `new_number`, polarity, time and promise validators. In
particular, never make new numbers acceptable just to improve delivery.

This is a testable prompt-boundary hypothesis: zero-model inspection should
show the full source quote and a style-only field with no outer date; fresh
generation should yield valid rewrites more often **without** invented
numbers. A fresh negative result, including continued `new_number` or another
quality failure, remains negative evidence and triggers the stop rule.

## Allowed files and non-changes

Allowed implementation surface after this freeze: only
`uruha_typed_mixed_atomic_delivery_p4.py` and its focused
`test_p4_typed_mixed_atomic_delivery.py` for the extraction/call-site and
zero-model boundary tests; additive product SHA, S result report, and the top
of `CURRENT_TASK.md`. The existing graph renderer may be **inspected** but
not edited in this one-variable batch. Do not change M31/M32, producer
lineage, source certificate, the shared single-rewrite `_generate`/validator,
Web route/controller, old data/contracts, baseline, model parameters, formal
DB, original dirty checkout, or unrelated output.

## Prospective S cases, preflight, and conditional gold

`datasets/p4_typed_mixed_atomic_rewrite_style_scope_probe_2026-10-21.json`
defines S0–S9 in a single isolated-conversation order: no-source mixed;
direct User place seed; same-date mixed; **quote-internal date different from
the outer recall date**; friend report; friend-only mixed; direct User
retraction; retracted-source mixed; protected quote; single-rewrite control.
Its `zero_model_scope_controls` also require a no-style and a contradictory-
style mixed request to fail closed without any atomic rewrite call. The S
inputs use new absolute dates/place names and new quoted wording; verify
exact prompt collisions against all other repository dataset JSON before
implementation, then run answer-independent source-role/action/source-status
preflight. Preflight does not force M31/M32 statuses, provenance transport,
or model behavior.

Five S turns request both actions. Every actually eligible mixed turn must
visibly deliver a natural Japanese, friend-facing soft rewrite **of the quote**
and, separately, the correct same-date direct-User place or honest unknown.
S3 must preserve the *inner quoted* date and must not introduce the different
outer date into its rewrite; the place clause must assess the outer date.
S1 must keep the User as the actor, S4/S5 must never promote friend speech to
a User fact, S6/S7 must not revive a retracted place, S8 must not disclose a
secret or activate atomic delivery, and S9 must not activate atomic delivery.
The bounded validator is only a rejection filter, never a semantic-equivalence
certificate. At least **two** mixed turns must naturally yield linked,
unblocked actual M31=true/M32=true to claim target-authority-variant coverage;
otherwise that coverage is inconclusive and strict PASS is unavailable.
M31=false/M32=true is a valid positive-control variant if naturally observed;
M32=false remains fail-closed and is not weakened to create coverage.

Zero-model contract tests must check exact `source_quote` and style-only
`requested_style` arguments at the generator boundary, including S3's inner
date and the absence of the outer date. Check missing/contradictory tone,
wrong role, protected input, tampered quote/outer scope, and the unchanged
`new_number` rejection. Existing neighboring lineage/source/graph/guard tests
must still pass. This is not permission to make the tests accept a fixed
answer keyed to S strings.

## Whole-batch hard gates and cost

S0–S9 are sent once each, 0 retries, in a new mode-0700 isolated product root
through real Safari **after** code/product SHA is committed and pushed. Before
S0, perform 0-turn same-PID ready/planned stop, private official-SHA offline
ONNX prewarm, and T0 empty profile. After *every* turn inspect visible reply,
native graph action/producer edges, source and final-guard receipts, raw and
SQLite episode, RightBrain history, and full profile snapshot. The visible
bubble, raw, last guard, utterance, history and saved episode must agree; no
unverified hypothesis becomes a persistent profile fact. The graph may show
action/terminal coverage only for a delivered and fully checked receipt, not
for a rejected call or merely linked producers.

Strict PASS requires **all** applicable source, actor, both-act, quote-date,
safe Japanese, graph/storage and cost gates. Any hard failure means whole S
batch strict FAIL, even if the prompt boundary mechanism itself works. Every
delivery-complete Safari M19 wait must be ≤20.000 s. Added atomic calls:
≤1 per eligible mixed turn; ≤5 total and ≤400 completion tokens in S;
qwen2.5:7b, temperature 0, max 80 completion tokens, 6 s call timeout.
No atomic call for seed, friend report, retraction, protected, single rewrite,
or failed style/admission. Record per-call prompt/completion tokens and latency;
if full-system token accounting is unavailable, say so. Do not increase
budget, weaken the safety validator, change gold, or quietly exclude slow or
failed cases.

## Sequence and evidence boundary

First commit/push this plan, S JSON, and 2/2 preimplementation SHA; verify PR
#435 head. Then implement only the scoped boundary change, run focused and
affected zero-model regressions, review diff, make a product SHA and push the
exact code before any S model/Web turn. Preserve raw ten-line SHA, per-round
snapshots and exact PID stop/port-vacant evidence. Report mechanism evidence,
fresh generation, Safari product, and pending formal same-model/human/
temporal-holdout levels separately. Even S strict PASS would establish only a
bounded mixed-act product behavior, not general human understanding, strong
LLM superiority, human preference, production readiness, or Goal completion.
