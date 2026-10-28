# P4 source-bound first-step candidate: isolated product result

Status: **candidate wiring and source-label boundary PASS; useful-answer FAIL;
20-second target FAIL**. This is one developer-authored fresh Web turn, not a
sealed holdout, a human rating, or an equal-resource LLM comparison. The
prospective design is `research/p4_source_bound_candidate_generation_freeze_2026-10-28.md`;
the exact prompt/source/test hashes and input were released in
`research/p4_source_bound_candidate_generation_release_2026-10-28.json`
at commit `20a11345a0ad781f057bb322b0cdb6ce9722dc81`, pushed and verified
as PR #435's head **before** the only Safari Send.

## Before, intervention, and real result

The previous, exposed two-pile-paper turn had a valid first-step route but
M51 **0/2 structurally valid** candidates, M53 **2 unsupported named
labels**, M46 rejected, and no visible first step (20.6047 s wait). This
batch changed only the candidate-generation instruction passed to the
existing M51 model call when an exact current-User first-step receipt is
present. It did not change frozen M45/M46/M47/M51/M53 code, candidate schema,
model, transport, verifier, memory, or Japanese surface guard. Test-first
contracts were 5 expected failures / 3 existing passes; affected tests
became **87/87 pass**. Isolated launcher preflight confirmed the route and
candidate adapters installed inside the write sandbox without any model,
Safari, or server call. A same-model read-only review gave a scoped GO for
generation; it is not independent quality evidence.

Native Safari opened only one new tab (52→53) at `127.0.0.1:7898` and sent
the precommitted input exactly once:

> 我要整理桌上的幾張舊講義，還沒決定怎麼分。你會叫我先做什麼？

The final visible reply was:

> 今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。

It is Japanese and does not invent a document category, but gives no
concrete reversible first step or stopping point. `post_check.did_reply_cover_focus`
was false. **The useful-answer gate therefore failed**, irrespective of
the improved candidate structure.

The decoded private row and Safari graph agree on the chain:

1. M47 `practical_help_authorized`, `solve_regulation`, exact current-User
   task span; `route_consistent=true` and M46 entered.
2. M51 recorded `source_bound_candidate_prompt_p4.applied=true` with released
   prompt SHA `6bb806bff1c2ea0923c4b106eae00ef2746ed863f3b93faa53d5da4810e0be3d`.
   It generated **2 unique candidates, 1 structurally valid**, and selected
   index 0. The second candidate lacked an action verb. This is a different
   input from the before row, so 0/2→1/2 is a bounded observation, not a
   randomized causal lift estimate.
3. M53 found **0 unsupported named labels** and did not rewrite the plan;
   M46's content review remained authoritative. The selected action was to
   align the old handouts in one direction and stop when aligned. This was
   a plausible reversible operation, not a verified user-preferred sorting
   rule. M51 still marked its mechanism `group_by_rule`, while M46 observed
   `structure_scaffold` (`mechanism_exact_agreement=false`).
4. M46 rejected the plan with the explicit content violations
   `invalid_counterfactual_before_jp` and `invalid_counterfactual_after_jp`:
   those fields contained Chinese text despite their Japanese contract.
   M45 status became `withheld_progress_review_failed`, and the UI delivered
   the conservative fallback. Correcting only the field language is **not
   yet proven sufficient** because the mechanism mismatch also remains.
5. After a native Safari reload, the graph still showed the exact USER
   SIGNAL, M51 **2 / 1 / selected 0**, M46 `rejected`, and the same UTTERANCE.
   The chat bubble itself was observed before reload; the graph is the
   persisted replay evidence.

## Cost, isolation, and boundary

M45 reported **2 attempted/completed local model calls**, 2,381 prompt +
563 completion = **2,944 reported tokens**, with 32.61336 s inside its
delivery. The whole user wait was **36.1007 s**, above the fixed ≤20 s
target. The extra same-model counterfactual review is a known possible cost
of advancing a candidate to M46; this single different-prompt observation
does not isolate latency causality or prove a typical p95. Provider-wide
usage beyond these fields was not measured.

The private 0700 runtime root is
`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-pv6wcjff`;
the 0600 conversation JSONL has exactly **1 row**, **492,840 bytes** on disk
versus **1,519,255 bytes** for the decoded logical JSON (67.56% smaller),
and **78** runtime blackboard events. Raw-row SHA-256:
`6d99a3156be02f7ab842c4e83c4de905bc7feb5b7b735ad31447e9dcde1af6c5`.
M45 reported 0 mental-fact writes; M51 reported no raw candidate text or
long-term-memory write. The isolated sandbox's profile protected both the
safe worktree and original dirty checkout. No formal DB path was used, but
this turn did not compute a before/after formal-DB aggregate hash.
Only the new Safari tab was closed (53→52); the exact 7898 server exited,
with no listener or PID left. The isolated root remains for audit.

## Decision

The source-bound instruction improved one internal candidate boundary while
the actual product objective failed. Do not edit this released prompt and
rerun the exposed handout case to chase a pass. The next single-variable
diagnostic must inspect the M51→M46 candidate/reviewer contract and distinguish
counterfactual field-language failure from the `group_by_rule` versus
`structure_scaffold` mismatch, then prospectively freeze a remedy and use a
new input. Neither the 87 tests nor this Safari observation establishes
general pragmatic understanding, human preference, same-model advantage,
production readiness, or a complete human-response equation.
