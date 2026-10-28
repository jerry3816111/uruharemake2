# P4 explicit first-step route: isolated product result

Status: **route PASS; useful-answer FAIL; 20-second target FAIL**. This is an
exposed product-development case, not a sealed holdout, human rating, or
same-model baseline comparison. The prospective boundary is
`research/p4_explicit_first_step_route_freeze_2026-10-27.md`.

## Problem, change, and controls

The prior two Safari observations of an explicit Chinese first-step question
selected `chat/plain_reply`; frozen M47 gave `no_explicit_help_route`, so M45
was `not_applicable`. The new overlay adds only a source-bound current-User
first-step response-form receipt after frozen M47. It does not create an
answer, authorize unsupported task facts, write a mental-state memory, or
change the old M47 implementation. The new entry and launcher reuse the
frozen status-truth runtime and isolated sandbox.

Read-only review discovered four previously untested false authorizations:
unquoted practice-question and title attribution, explicit refusal of advice,
and `不要回答`. Adding them as negative tests first gave **4 expected failures**.
An initially too-broad example exclusion also rejected two genuine tasks that
happen to contain `練習題`/`例題`; those were added as positive tests (**2 expected
failures**) before narrowing the exclusion to attribution syntax. The bounded
correction then passed both directions. Existing English authorization and old
M47/M49 behavior remain controls.

Focused tests: **69/69** across new overlay/entry/launcher and adjacent
M45/M46/M47/M49. Old source SHA-256 remained unchanged:

- `uruha_crosslingual_help_routing_m47.py`:
  `23bb1df9fad0198375d785ff53fbb614be9586a6f8ec507a707a3ac3245c6e88`
- `uruha_web_ui_product_p4_status_truth.py`:
  `9d6d0d45941649ad2b1eb4768af88b6db0d2aee9896e06c91a9ccd59ba0afdea`
- `p4_status_truth_safe_isolated_product_launcher.py`:
  `f12af4a504d0412771a279c7ab27abbbd23cc404ef4f136cad6b713855e9e7df`

## Fresh native Safari, one isolated turn

Launched the new entry on `127.0.0.1:7897` under the preflighted 0700 private
runtime root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-gy_i_vh4`;
the product write sandbox protects both worktrees. The new preflight independently
confirmed overlay installation and runtime reuse before any Send. Native Safari
opened only one new tab (52→53), sent this fresh non-holdout input once:

> 我要開始整理書桌上的兩疊紙。你會叫我先做什麼？

Visible final reply:

> 今の情報だけで適当な方法は言いたくない。どこで止まってるか教えて。

The reply is Japanese and does not invent a sorting fact, but it supplies no
concrete reversible first step or stopping point. Source-aware useful-answer
gate therefore **FAIL**; `post_check.did_reply_cover_focus=false`.

The actual node graph and decoded private row agree: M25 selected
`solve_regulation`, M47 `practical_help_authorized` with one exact current-User
task span and `route_consistent=true`; M46 was entered; M45 source content was
available; M49 added zero *new* spans because the task clause was already an
independent M45.1 source; M50 bundled two current fragments. Two candidate
plans were generated, but M51 found **0 structurally valid**. M53 correctly
rejected **2 unsupported concrete labels**, so M46 `plan_rejected` and M45
`withheld_goal_plan_failed`; M39 then kept the final reply conservative. The
graph's `USER SIGNAL`, M47/M45/M46/M53, and `UTTERANCE` remained consistent
after a native Safari page reload. This demonstrates route wiring, not answer
success. It would be wrong to weaken M53 merely to make the answer appear.
The final post-Safari edit only narrowed the meta-example exclusion; the
tested current-User task takes the same positive classifier path under the
final source, but the exact final source was not rerun through Safari.

M45 reported **1 attempted/completed local model call**, 621 prompt and 295
completion tokens, 17.11758 s including its delivery. Total visible user wait
was **20.6047 s** against the precommitted 20 s target (**FAIL**). This one
cold-ish observation is not a randomized latency comparison with the earlier
different-prompt Safari rows; total-provider usage beyond fields reported by
M45 is unavailable.

The private JSONL contains exactly one row, **479,975 bytes** on disk versus
1,569,142 bytes for the same decoded logical JSON (about **69.4%** smaller),
with 78 runtime blackboard events. Raw row SHA-256:
`1197f20aa327783230b4eb9210d7fafd7209905015560572aab2af4839dd20b5`.
Root is 0700 and row 0600. No formal DB or original dirty checkout was used.
After evidence capture, only the new Safari tab was closed (53→52), and the
exact 7897 server exited; no listener or child PID remained. The isolated
private root is retained for audit.

## Next decision, not a retroactive pass

The route defect is fixed for bounded examples, but product usefulness remains
partial. The next independent variable should target **source-bound plan
candidate generation**: make M45/M46 propose a reversible first action using
only the actual task span, while retaining M53/M46 refusal of invented
categories. Freeze the new intervention and fresh controls before source edits;
do not rerun this exposed row as a holdout. A later Safari run must show an
actual source-supported action plus stopping condition within the target, or
retain another failure. No claim of general pragmatic understanding, human
preference, production readiness, or complete human-response equation follows
from this result.
