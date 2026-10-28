# P4 reviewer Japanese counterfactual: isolated product result

Status: **instruction wiring PASS; reviewer completion, useful answer, and
20-second target FAIL**. Japanese-field conformance is **not measured**:
the reviewer timed out before returning a review. This is one fresh
developer-authored Web turn, not a sealed holdout, human rating, or fair
same-model comparison. The prospective design is
`research/p4_reviewer_japanese_counterfactual_freeze_2026-10-28.md`.
The exact source/test/prompt hashes and input were released in
`research/p4_reviewer_japanese_counterfactual_release_2026-10-28.json`
at commit `bfb192e64ec523d072889afa99ad8a32b4be3859`, pushed and checked
as PR #435's exact head **before** the only new Safari Send.

## Intervention and actual turn

The previous, exposed handouts turn had a valid M47 route, M51 2 unique /
1 structurally valid candidate, and M53 zero unsupported labels. M46
rejected because both counterfactual `_jp` free-text fields were Chinese;
the two allowed but different mechanism labels were nonfatal. This batch
changed only the instruction of the existing M46 reviewer model call for
the exact eligible current-User first-step route. The original M46 schema,
verifier, source span, transport, call count, deadline, and 20-second gate
remained unchanged. Test-first contracts were 6 expected failures / 4
passes; new and affected tests became **93/93 pass**. Compile, diff and six
frozen source hashes passed. An actual isolated launcher preflight found
both candidate and reviewer prompt adapters installed, with **zero model
calls, Safari Sends, or running server**. Read-only patch review allowed
this scoped release; none of those checks proved generated quality.

Native Safari opened one new tab (52→53) at `127.0.0.1:7899`, verified
the precommitted input, and sent it exactly once:

> 我要整理抽屜裡的幾張收據，還沒決定怎麼分。你會叫我先做什麼？

The only final visible reply was:

> 今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。

It is Japanese, but it does not answer the explicit request with a first
step or stopping point. `post_check.did_reply_cover_focus=false`. It must
not be counted as a useful Japanese answer. No reviewer output exists with
which to grade the two counterfactual `_jp` fields.

The decoded private row and the reloaded Safari runtime node graph agree:

1. M47 `practical_help_authorized`, `route_consistent=true`, exact current
   task span, `solve_regulation`; M46 was entered.
2. M51 recorded the previously released candidate instruction as applied
   (`6bb806bf...`), produced **2 unique / 1 structurally valid** candidate,
   selected index 0. The other candidate failed
   `unsupported_concrete_scaffold_label_m53`; selected M53 found no
   unsupported named labels. This is a different input from the earlier
   result, not an estimated before/after quality lift.
3. M45 recorded `reviewer_japanese_counterfactual_prompt_p4.applied=true`
   with released new instruction SHA-256
   `d10117c9f4669a9057b95db16a94c879a66f7c3dbceedfc10332d7de49050f35`
   and `model_calls_added=0`. This verifies instruction dispatch, **not**
   model compliance. M45 `reason=TimeoutError`, status
   `withheld_model_unavailable`, 2 attempted calls / **1 completed** call,
   and `token_accounting_complete=false`. M46 status became
   `counterfactual_review_unavailable`; content and surface did not pass.
4. The candidate diagnostic mentions an internal amount/date list and
   completion condition. Because M46 did not finish, its source support
   and usefulness were **not** certified; neither this candidate nor its
   diagnostic text was delivered. The graph showed M51 2/1, M46 unavailable,
   and the same fallback UTTERANCE after Safari reload. The graph replay
   agrees with the observed chat bubble and private row.

Read-only source inspection locates the hard boundary: M46 starts one
**34.0-second shared deadline** for candidate generation and counterfactual
review. The second `_native_json` call increments `attempted` before its
HTTP read; `completed` increments only after the full response. Here the
reviewer was attempted but did not complete before that shared deadline.
The prior exposed run already spent 32.61336 s inside M45, near the same
budget. The timeout cannot be attributed to the Japanese instruction from
this single nonpaired turn: input, completion state and local timing differ.
The previous Chinese-field rejection remains a preserved failure, not a
problem silently marked solved.

## Cost, isolation, and decision

M45 delivery took **34.00254 s**. The complete click-to-visible user wait
was **37.2387 s** (>20.0 s); runtime queue was 0.0156 s and brain work
36.3323 s. The one completed call reported **1,101 prompt + 322 completion
tokens**. There were two attempted calls but only one completed, so these
1,423 reported tokens are **partial accounting**, not the full cost or a
token-parity result. Provider-wide usage was not measured.

The isolated 0700 runtime root is
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-6mr1n9u7`.
The 0600 conversation JSONL contains exactly **1 row**, **482,737 bytes**
on disk versus **1,481,752 bytes** for the strictly decoded logical JSON
(67.42% smaller), and **78** runtime blackboard events. Raw-row SHA-256:
`7fc6bdd96f8d650a01a81327410b700e58309cbf0ed309b410a93ed0d0c7bb63`.
Session `20261028_153526_93d1e59d`, turn 1. M45 reported zero mental-fact
writes; M51 reported no raw candidate or long-term-memory write. The
isolated sandbox protected both worktrees. No formal DB path was used, but
this turn did not compute a formal-DB before/after aggregate hash. Only
this run's new Safari tab was closed (53→52); the exact 7899 server and PID
exited with no remaining listener. The private root remains for audit.

This release **does not pass the product gate**. The read-only deadline
diagnosis is complete; the next step is a prospective, single-variable
decision that addresses the two-call cost while preserving M46 review and
the fixed ≤20 s user gate. Merely enlarging the 34 s internal timeout would
not satisfy that user gate. Do not rerun this exposed receipts case, adjust
the released prompt to chase it, bypass M46/M53, or count 93 tests as
real-answer evidence. P4-B real runner remains `REVIEW_REQUIRED`; the larger
Goal is still active and incomplete.
