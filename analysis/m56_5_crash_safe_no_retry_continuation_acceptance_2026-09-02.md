# M56.5 Crash-safe No-retry Formal Generation Continuation Acceptance

Date: 2026-09-02 to 2026-09-03
Decision: **PASS for the bounded engineering variable; live formal generation remains DENIED**

## What changed

M56.3 previously retained intermediate summary and prediction results only in process memory. A process loss after
many successful calls therefore discarded all progress and required a new human-authorized run. M56.5 changes only
that recovery boundary:

- it commits the M56.5 execution mode before the M56.3 schedule can exist;
- it rematerializes and checkpoints the unchanged pre-outcome Equation bundle;
- every model step receives an immutable intent marker before its single allowed transport attempt;
- a complete result and its actual call telemetry are atomically committed together;
- a valid completed checkpoint is reused without calling that task again;
- an intent without a complete checkpoint is ambiguous and terminal, so the task is never recalled;
- the unchanged M56.3 submission, call ledger, prediction commitment and scoring release are created only after all
  steps validate, then revalidated through the M56.4 pre-score contract.

The public execution surface is exactly `execute_resumable_formal_generation(run_id)`. There is no provider,
prediction, outcome, retry, fallback or resume-policy injection.

## Fault-injection evidence

The forged 30-row fixture has one shared empty-history B4 summary step plus 210 prediction steps, so it contains 211
steps and 180 model calls. This is a test shape, not a promise that real data will have exactly one summary: formal B4
summary count is determined by the frozen distinct histories.

| Check | Result |
|---|---|
| interrupted then continued | exactly 180 total calls; completed step checkpoints reused |
| uninterrupted comparison | exactly 180 total calls |
| resumed vs uninterrupted content | summary artifacts, 210 predictions and call ledger identical |
| M56.3 validation | PASS |
| M56.4 pre-score compatibility | PASS |
| private scoring sentinel | unchanged; generation target-outcome access 0 |
| crash after checkpoint but before intent cleanup | checkpoint reused; no repeated call |
| intent without checkpoint | terminal; 0 calls on continuation |
| transport exception | one attempt, terminal failure, no second attempt |
| completed run invoked again | validation only; no additional call |
| schedule created without pre-transport M56.5 mode | rejected before a call |
| mutated or unexpected checkpoint artifact | rejected before continuation |
| raw response, reasoning, outcome or excess authority in checkpoint | rejected |

SHA-256 protects against accidental or ordinary artifact drift at the application layer. It is not a digital
signature and does not protect against an attacker who can rewrite a checkpoint and every expected hash.

## Retained development failures

- The first test draft incorrectly treated the forged fixture as a universal 212-step formal schedule. The fixture is
  211 steps; real summary count is data-dependent. The test and dashboard wording were corrected without changing
  the M56.3 schedule.
- An early mutation test assumed recomputing every SHA should still be detected as a hostile rewrite. That security
  claim is unsupported; the plan now explicitly limits hashes to application-level drift control.
- The first forbidden-content test selected a non-B0 step while constructing a deterministic checkpoint. It was fixed
  to test the intended boundary; no production behavior was relaxed.
- Safari inspection found the graphical page still said `212 fixed steps`. It was corrected to `fixed B4 summary
  order + 210 predictions`, with summary count described as data-dependent, then reloaded and rechecked.

## Tests

- focused M56.5 suite: **15/15 passed** in 8.81 seconds;
- direct M54–M56.5 compatibility: **169/169 passed**, plus 4 subtests, in 22.81 seconds;
- selected M1/M2/V7/V9/M54–M56.5 compatibility: **234/234 passed**, plus 4 subtests, in 24.67 seconds;
- Python compilation, JSON parsing, contract validation, implementation-freeze hashes and diff check: PASS;
- current formal model calls: **0**;
- current target-outcome access: **0**;
- current formal commitment, scoring release and result: **absent**.

Contract hash: `4961034f87fb0eb8f812fed88d7722d1e042f0668f102fba88398e377fc9780e`
Live audit hash: `5f8a9ec165d82a99f0d0b5af3f2af09b79b6f6043b9daa7086e2bffc9f41ef3c`
No-call rehearsal hash: `a35bd451848b579b22ee1df7dd37f2a8d76cadbc6eafa34eca5fbfb2152ff161`

## Safari graphical acceptance

The existing local Safari test tab was reused at `http://127.0.0.1:7913/dashboard`; no tab was opened or closed and
the tab count remained 30. The read-only page has no form and shows:

- `DENIED NOW`, two human ledgers at 0/18 and 0/18, real temporal rows 0/30 and formal calls/outcomes/results 0;
- authority and schedule, intent, atomic checkpoint, restart reuse, ambiguous terminal state and final commitment;
- a visual contrast between complete checkpoint, intent-only terminal state and fully complete release;
- an explicit statement that the fixture is not a formal result.

Safari caught the stale 212-step wording noted above. After correction, both the upper checkpoint flow and lower
terminal boundary were visually rechecked, with no horizontal overflow:

- `analysis/m56_5_safari_checkpoint_flow_2026-09-02.jpeg`
- `analysis/m56_5_safari_terminal_boundary_2026-09-02.jpeg`

The local port 7913 service was stopped after acceptance. The remaining read-only Safari tab is safe to close and
does not hold private data or execution state.

## Honest boundary and long-term contribution

M56.5 prevents completed calls and a human-authorized formal run from being wasted by an ordinary process
interruption, without weakening the one-attempt rule or exposing outcomes. It improves the reliability of the future
same-model longitudinal comparison and preserves auditable resource evidence per call.

It does **not** add human labels, real temporal rows, fresh model predictions, actual resource measurements, an M56
score, Uruha predictive evidence, Equation V1 validity, a solved human-response equation, full-pipeline readiness or
production readiness. The live state remains V7 0/18 and 0/18, V9 0/30 and real temporal rows 0/30. The next
non-substitutable scientific dependency remains two different humans completing the frozen V7 reliability pilot.
