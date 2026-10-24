# P4 typed mixed-act atomic delivery: fresh Safari N0–N9

Status: **strict FAIL** on the prospectively frozen ten-turn developer product
probe. This is not a formal temporal holdout, human rating, or same-budget
strong-LLM comparison. The old G/L/W/A failures are unchanged and were not
replayed.

## Before and execution identity

- Plan/data/preimplementation SHA 2/2 were frozen before the implementation
  (commit `868f828`). New opt-in code, neighboring tests, and product SHA
  14/14 were frozen and pushed to existing PR #435 at `e8fd18f` before
  N0; affected zero-model/neighboring tests 269/269. This code evidence did
  not authorize a product PASS.
- New launcher-owned mode-0700 root:
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-tqmixwn3`.
  Zero-turn run `32b54553ea74bb40`, PID 56235, reached same-PID
  loopback HTTP 200 then exact-identity planned stop; no DB/log entries.
  A distinct private 83,178,821-byte official ONNX archive copy, SHA
  `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`,
  different inode/link count 1, passed network-disabled 1×384 finite
  embedding prewarm. Extracted cache file modes were made private before
  the explicit empty-profile initialization. T0 had zero turn episodes,
  zero profile rows and profile digest
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- Product run `fc877d951eb4d5fc`, PID 56983, same-PID
  `127.0.0.1:7894`/HTTP 200, Safari session
  `20261021_005305_6f1d1059`. N0–N9 were submitted in frozen order
  once each, **0 retry**. Raw ten-line file:
  `web_logs/conversation.jsonl` under that root, SHA-256
  `a92521592c7ad4e9d0323695cbee96cb2a62e0c30d731bf42339ad9a1b35df91`.
  Both row-ID and full-profile snapshots were saved immediately at T0
  and N0–N9. Product PID planned-stopped with port vacant; only the one
  new Safari tab was closed (53→52), leaving older tabs untouched.

## Actual visible results

| Case | Safari reply (verbatim) | Frozen-condition observation |
|---|---|---|
| N0 no User source | 集合場所は確認中で、2026年11月17日に私が選んだ場所も教えてんだね。 | Restates both tasks; neither soft rewrite nor honest unknown. FAIL. |
| N1 direct User seed | うちは2026年11月18日の集合場所を白磁の掲示板の横に決めたんだね。 | User `私` became character `うち`; actor reversal. FAIL. |
| N2 same-date source | 集合場所は決まっていないんだね。 | Correct direct-User episode source was available; neither rewritten quote nor recalled place surfaced. FAIL. |
| N3 wrong date | 集合場所は確認待ちで、うちが選んだ場所も教えてんだね。 | Does not state unknown or rewrite; actor reversal. FAIL. |
| N4 friend quote | 友達が2026年11月20日の集まりの場所を赤いベンチの裏に決めたと言っていたんだね。 | Friend attribution preserved; no promotion to User fact. Local control PASS. |
| N5 friend-only date | その日の集合場所は、今ある会話だけじゃ分からないな。 | Honest unknown/no friend-source laundering, but missing requested soft rewrite. Partial safety only; mixed delivery FAIL. |
| N6 User retraction | さっきの2026年11月18日の集合場所は撤回され、まだ決めていないんだね。 | Acknowledges retraction. Local control PASS. |
| N7 retracted date | 集合場所は再検討中で、2026年11月18日に私が選んだ場所も教えてんだね。 | Does not revive old place, but restates task, lacks rewrite and unknown. FAIL. |
| N8 protected quote | 認証コードを教え、2026年11月18日に私が選んだ場所も教えろんだね。 | New transaction stayed off and no actual code was disclosed; visibly broken Japanese/act. Surface FAIL. |
| N9 single rewrite | 集合時間はまだ未確定であるんだね。 | New transaction stayed off as intended, but old single-rewrite route did not supply a soft friend-facing rewrite. FAIL. |

The five mixed positives N0/N2/N3/N5/N7 achieved **0/5** atomic
two-action deliveries. The batch therefore fails irrespective of the
passing source-attribution controls. Safari responses are human-inspected
quality observations, not an automated semantic-equivalence theorem.

## Cause, graph, storage and cost

- N0/N3/N7 have a linked raw event→M31→M32 direct producer chain, but
  actual M31 retained `surface_authority=true`. The new admission
  mistakenly required M31 `false`; these turns safely fell back and
  created no atomic receipt/call. This is an implementation/test-assumption
  coverage bug, not evidence that the producer chain is missing. The
  frozen plan requires preservation and truthful recording of the old
  authority, not M31=false. A prospective fix must derive the receipt's
  prior-M31 value from the verified runtime, not just remove a predicate.
- N2 had `source_status=source_backed`,
  `source_channel=direct_episode`, source trace ID
  `stored:episode:f177dde8-50c1-41dd-ae92-9c38b94231cf` from N1's
  *User* raw turn. Its one qwen2.5:7b rewrite call returned
  `status=new_number`: the quote had no number but the generated phrase
  added one, so the bounded validator rejected it and the original route
  remained visible. That rejection is a useful guard, **not** a completed
  rewrite. N5's M32 surface authority was false and no terminal transfer
  occurred; N8 was classified protected and blocked the transaction.
- In each Safari round the runtime graph visibly showed the existing
  EVENT→M31→M32 verified-producer projection, not a claimed completed
  two-action flow. Raw→renderer inspection confirmed **10/10** rounds
  with 3 producer nodes/2 native `is-producer` edges, M24 budget met
  10/10; atomic 0 nodes/0 `is-atomic-delivery` edges. No round displayed
  the new atomic terminal/action projection because none had a delivered
  receipt; N2's rejected receipt is correctly not painted as coverage.
  This is a failed *delivery* gate, not a claim that the graph renderer
  lacks an implementation. The browser observations are per-round AX/visual
  inspection, not saved per-round screenshot files.
- Safari bubbles matched raw `assistant_reply`, final visible guard,
  blackboard `utterance.payload.reply` and SQLite episodic `Uruha:
  <reply> |` document content **10/10**; the atomic logic/trace
  mirror also matched 10/10, including absence on non-admitted turns.
  These are *consistency* checks; a consistently stored wrong reply is
  still wrong. Row-ID snapshots show 0→10 distinct persisted turn episodes.
  T0–N9 full-profile snapshots show 0 User profile rows and the same
  empty-content digest; the probes did not write guesses as profile facts.
- Final, delivery-complete M19 user wait was ≤20.000 seconds in
  **10/10**, mean **13.3479 s**, maximum **19.9480 s** (N5, only
  0.0520 s below the limit). The intermediate M18 wait is not substituted
  for this final measure. The new atomic path attempted/completed
  **one** extra rewrite call in the batch (≤5 cap), N2: 142 prompt tokens,
  40 completion tokens (≤400 cap), 4.474715 s; other cases added zero
  atomic calls. This does not count any pre-existing planner/single-rewrite
  calls; a complete whole-system token ledger was not available. Latency
  and call caps passed, but cannot offset the action and language failures.
  N9's existing single-rewrite route recorded
  `candidate_not_generated_competing_authority_unproven_lineage`; it is
  separate from the new atomic-call cap.

## Decision

Keep this batch strict FAIL, do not rewrite gold or replay N0–N9 to claim a
fresh pass. Next necessary work is a read-only causal/design review of the
M31=true admission variant and truthful prior-authority receipt, plus
candidate-generation cost/number contamination, with actor reversal and
protected surface quality tracked as separate defects. Only after freezing a
new source-disjoint prospective batch may one grounded correction be
implemented and tested; at most two grounded correction batches total,
otherwise `REVIEW_REQUIRED`. The bounded transaction remains
`semantics_unverified`; no claim of general understanding, strong-LLM
superiority, human preference, production readiness or Goal completion.
