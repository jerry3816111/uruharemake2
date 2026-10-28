# P4 retrospective decision actor authority: prospective product freeze

Status: **preimplementation, zero C model/Safari turns**. This is a
developer-authored, source-disjoint product probe, not a blinded temporal
holdout, independent human evaluation, or same-model LLM comparison. The
earlier B0–B6 batch remains whole-batch strict FAIL; neither its prompts nor
its gold may be repaired or re-labelled.

## Before, research question, and one causal variable

B4 asked whether Uruha herself chose a dated place. The full earlier User
statement was already in `memory_snapshot.recent_turns` and authenticated
`memory_provenance.passed_to_leftbrain`, yet the ordinary planner selected
`core_message_jp=うるは決めたんだ。`; M39 accepted and Safari, raw, guard and episode
all delivered that false self-attribution. The existing local-fact gate only
recognizes `...私が決めたのはどこ...` place-value questions, not retrospective
`...決めたのは、うるは自身だった？` actor questions. This is an answer-admission gap,
not a retrieval miss. The B0/B5 exact-echo acknowledgment problem is a
different variable and is **not** modified here.

**Only changed core variable:** admit a final answer to a bounded dated-place
decision-*owner* question only after binding it to authenticated direct User
source already passed to this turn's decision. A matched raw User assertion
licenses `the User said they chose this event`; it does **not** prove a world
fact, an exhaustive absence of Uruha actions, or a current place when source
values conflict. No source, ambiguous same-date subjects, quoted/third-party
first person, malformed/stale trace or unsafe placement must fail closed in
natural Japanese. An explicit correction remains a User-origin statement but
must fail closed for **which place is current** until supersession is resolved.
The full source, date/subject match,
actor, selected plan, final guard and utterance must have a bounded trace
receipt. Never promote assistant text, summary, model core or a plausible
memory anchor into source proof.

The existing `uruha_local_fact_answer_authority_p4.py` is the only allowed
product file. Reuse its `_handed_user_sources`, direct-User assertion parser,
plan→final SHA guard, visible-history transaction and runtime node; add one
focused `test_p4_retrospective_decision_actor_authority.py`. Do **not** query
the DB afresh, change memory retrieval/write rules, M31/M32, M39, general
planner, persona, B0/B5 guard, safety routes, renderer or model. If those are
necessary, stop for a new design review rather than widening this item.
Records allowed: this plan, paired C JSON, preimplementation/product SHA,
top of `CURRENT_TASK.md`, and an honest result report. No original dirty
checkout, formal/private DB, unrelated `output/graduate_application_report/`,
new permanent dashboard, external deployment, or unapproved external action.

## Fresh ordered C0–C9 probe and conditional gold

Use the paired `datasets/p4_retrospective_decision_actor_probe_2026-10-21.json`
in one new isolated Safari session, exactly C0–C9 in order, once each,
zero retries. C2, C7 and C9 deliberately repeat the same question text after
different intervening evidence. They are three pre-frozen state-transition
observations, **not** retries of a failed prompt. Before writing this
plan/data, repository search excluding
unrelated `output/` found no hits for the 2049-06-14/15/16 dates or the four
new synthetic place strings. These are development probes, **not** formal
holdout cases.

| Turn | Purpose | Conditional gold |
|---|---|---|
| C0 | Direct User decides a dated handoff place | Preserve complete raw User source and never attribute it to Uruha. Natural acknowledgment is measured as a product quality gate; the known B0-type failure is not silently excused. |
| C1 | Full-subject `did Uruha decide?` question | If C0 full direct source is ordinarily handed through verified `recent_turns` or typed `direct_episode`, say in natural Japanese that User *said* they chose it and Uruha's own decision is not evidenced; no `うるは決めた`, invented private biography, clipped value, or categorical `うるは never`. If source is missing, abstain and mark actor product gate FAIL. |
| C2 | B4-shaped abbreviated date-only owner question | Same as C1 only if exactly one normalized User event/subject key is admitted for that date. Multiple statements about that one event may conflict on *place* while retaining User-reported ownership; date alone cannot choose among different subjects. |
| C3 | Friend's quoted first-person decision on another date | Never install it as User/Uruha ownership or stable User fact. |
| C4 | Ask if Uruha chose C3's event | The quoted friend statement is no direct-User decision source; do not certify User or Uruha as owner. Brief uncertainty is allowed. This negative control counts only if the decoy was handed to the decision path. |
| C5 | Ask about a date with no known decision | Abstain without pretending to know Uruha's private activity or inferring a decision from the question. |
| C6 | Second direct User assertion, same date/subject, different place | Preserve complete raw source; recency alone does not revoke C0. Do not install either place as unqualified stable fact. |
| C7 | Ask ownership with conflicting places | Do not make Uruha the chooser or pick a current place. Acknowledge two User-origin claims and ask which place is current, or boundedly clarify. Both sources must be actually handed or the conflict gate FAIL. |
| C8 | Explicit User correction of that event | Preserve correction raw and history; do not treat it as automatic authorization to select a current place or erase earlier assertions. |
| C9 | Ask ownership after correction | Do not self-attribute, select a stale place, or pretend certainty about which place is current. A bounded correction-aware clarification is acceptable. |

Focused zero-model contracts must additionally cover full-subject and
date-only matches across at least two unrelated dates/subjects; two distinct
subjects on one date (abstain on date-only question); typed episode vs recent
turn de-duplication; assistant/summary-only and untyped episode; stale trace;
quoted/third-party/anonymous first person; copied User words in the assistant
reply; contradiction; correction; malformed question/quotation; sensitive
subject **and sensitive value**; protected route; genuine Uruha self-speech
outside this exact owner question; existing place-value slot; final-language
guard, post-guard overlay, episode and graph equality. Do not encode C dates,
places or answer keys in product logic or tests. A passing contract does not
prove fresh model or Safari behavior.

Anonymous quotation, same-date/different-subject ambiguity, genuine Uruha
self-speech and malformed-question controls are zero-model contracts, not
separate live Safari cases in C0–C9; no report may claim live coverage of
them. The known B0-type acknowledgment failure and earlier lack of savable
native Safari image/full token ledger may make the whole C batch strict FAIL
even if the new actor slot works. Narrow actor and whole-batch outcomes must
be reported separately without moving the frozen quality gates.

Exact initial verification commands (using the product's available Python
3.12.10 path; expand only if a directly affected failure points farther):

```sh
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m unittest -v test_p4_retrospective_decision_actor_authority.py
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m unittest -v test_p4_source_bound_prior_user_decision_recall.py test_p4_local_fact_answer_authority.py test_p4_user_first_person_actor_surface.py test_p4_mixed_past_place_source_authority.py test_semantic_persona_surface_m39.py test_p4_y_runtime_graph_trace_delivery.py test_p4_am_runtime_temporal_graph_delivery.py
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m py_compile uruha_local_fact_answer_authority_p4.py test_p4_retrospective_decision_actor_authority.py
git diff --check
```

Also import and construct the existing Web `build_demo()` without launching
a model, then validate both SHA manifests before product execution.

## Product, graph, privacy and resource gates

- Start a wholly new launcher-owned 0700 root and 0600 logs, with explicit
  empty T0 profile and source snapshot. **Provision the official-SHA ONNX
  archive privately before any zero-turn server launch**, using an independent
  inode, owner-only cache and a no-network prewarm; verify zero-turn stderr
  shows no download attempt. Then same-PID HTTP-ready/planned-stop, followed
  by one new product PID and native Safari tab/session. B's startup network
  attempt is a retained failure, not evidence this setup is clean.
- Every final bubble must be natural Japanese, with the correct act/actor and
  no exposed technical analysis. Bubble = private raw reply = final guard =
  graph `UTTERANCE` = matching SQLite episode, including after reload. Verify
  current source, selected/verification node and no stale positive node;
  guard/hash receipt must bind plan to final visible text. A final overlay that
  changes the authorized answer is FAIL. Save native Safari PNG/AX if tool
  support permits; otherwise saved-visual gate remains unmet. The graph must
  make the source/actor/conflict legible rather than merely show a generic
  memory node; otherwise visual gate FAIL.
- Per-turn delivery-complete wait ≤20.0000 s. Gate-added model calls = 0;
  record ordinary planner calls, available prompt/completion tokens, elapsed
  time, raw log/graph/DB bytes and the overhead of the new gate. Missing
  complete cost evidence is not zero cost. Preserve T0–T10 profile snapshots,
  ten distinct turn episodes, full raw SHA and source provenance. No factive
  profile write from quote, conflict or correction; no formal DB writes.
- Any source, actor, naturalness, safety, privacy, latency, isolation, visual
  or cost hard-gate failure makes **whole-batch strict FAIL**, even if C1/C2
  narrow actor repair succeeds. Do not re-prompt, change gold after output or
  replay exposed A/B/C cases as fresh. At most two reasoned prospective repair
  batches before `REVIEW_REQUIRED`.

## Order and claim boundary

Commit/push this plan, paired JSON and preimplementation SHA and verify PR
#435 head **before** product code. Then change only the allowed product file
and focused test, run focused plus affected zero-model regression,
compile/diff/Web build, create product SHA, commit/push and verify PR before
fresh generation. Finally execute the isolated zero-turn and Safari session,
preserve failures, planned-stop only our PID, close only our new tab, publish
result and task/PR state. Formal same-model LLM comparison, independent
human rating/temporal holdout and unified VRM/Function Calling acceptance
remain pending regardless of this product probe.
