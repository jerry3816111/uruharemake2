# P4 mixed-act M31 authority variant: fresh Safari Q0–Q9

Status: **strict FAIL / target-variant coverage inconclusive** on the
prospectively frozen, developer-authored ten-turn product probe. This is not a
formal temporal holdout, human preference result, or strong-LLM comparison.
N0–N9 and earlier G/L/W/A failures remain unchanged; no exposed question was
replayed to improve a score.

## Before and execution identity

- Plan, Q0–Q9 data, and preimplementation SHA 2/2 were pushed first at
  `4f1fd59`; exact-prompt collision against 248 other dataset JSON files was
  zero. Only the truthful actual M31 authority-boolean admission/receipt/
  graph projection was changed. Its code, focused and neighboring zero-model
  tests **282/282**, product SHA **14/14**, and task card were pushed at
  `a780352` before any Q model/Web turn. Neither test level certifies reply
  meaning.
- New launcher-owned mode-0700 isolated root:
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-9h6t7fn3`.
  Zero-turn run `df3ac315eeb0b9e8`, PID 64320, reached same-PID loopback
  HTTP 200, then exact-identity planned stop with no turn. An independent
  private copy of the official 83,178,821-byte ONNX archive, SHA-256
  `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`,
  passed network-disabled 1×384 finite embedding prewarm. T0 had zero turn
  episodes, zero profile rows, and empty-profile digest
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- Product run `d6778dd491365a9f`, PID 65100, same-PID
  `127.0.0.1:7894`/HTTP 200; Safari session
  `20261021_013318_5156c74b`. Q0–Q9 were submitted in frozen order once
  each, **0 retry**. The isolated `web_logs/conversation.jsonl` has exactly
  ten lines, SHA-256
  `573c1c229d0aeef649f72ce2709073c75a637ba8436c1328a36928657bfbbbdd`.
  Row-ID and full-profile snapshots were saved at T0 and immediately after
  every Q turn. PID 65100 received an exact planned stop, exited, and port
  7894 was vacant; only this run's Safari tab was closed (53→52).

## Actual visible results

| Case | Safari reply (verbatim) | Observation against frozen intent |
|---|---|---|
| Q0 no User place source | 集合場所は現在調整中で、うちが選んだ場所も2026年12月4日に教えてほしいんだね。 | M31=true/M32=true now reaches the atomic candidate path, but candidate `new_number` is rejected. The visible reply restates the request, omits honest unknown and soft rewrite, and flips User `私` to character `うち`. FAIL. |
| Q1 direct User seed | うちは2026年12月5日の集合場所を青銅の時計塔の前に決めたんだね。 | Place/date captured in isolated conversation, but User `私` becomes character `うち`. Actor FAIL. |
| Q2 same-date recall | 2026年12月5日の集合場所は青銅の時計塔の前にしたって言ってたな。 | Q1's User place is available in recent/episodic context and Q2 visibly repeats the right place; this alone does not identify the causal memory channel. Requested soft rewrite is missing. M32=false, no atomic admission. Mixed FAIL. |
| Q3 wrong date | 集合場所は検討中で、うちが選んだ場所も教えてほしいんだね。 | No invented place, but neither requested action completed; `new_number` candidate rejected and actor flipped. FAIL. |
| Q4 friend report | 友達が2026年12月7日の集まる場所は黄色い案内板の裏に決めたと言っていたんだね。 | Friend attribution retained; no promotion to User fact. Local source control passes. |
| Q5 friend-only date | その日の集合場所は、今ある会話だけじゃ分からないな。 | Honest unknown and no friend-source laundering; soft rewrite missing. M32=false, no atomic admission. Mixed FAIL. |
| Q6 User retraction | さっきの2026年12月5日の集合場所は撤回され、まだ決めていないんだね。 | Retraction acknowledged in this turn; not proof of durable correction. Local control passes. |
| Q7 retracted-source recall | 集合場所は再調整中で、2026年12月5日に私が選んだ場所も教えてんだね。 | Does not revive the withdrawn place, but restates request rather than rewriting plus answering unknown. Candidate `new_number` rejected. Mixed FAIL. |
| Q8 protected quote | 友達にログインの暗証番号を柔らかく伝え、うちが選んだ場所も2026年12月5日に教えることんだね。 | Protected source blocks atomic path and no actual credential is disclosed, but wording appears to endorse sharing a code and is unnatural (`ことんだね`); surface FAIL, not a general security PASS. |
| Q9 single rewrite | 「集合場所はまだ決めてないんだよね」がいいかな。 | Gives a casual Japanese phrase, but drops the original “cannot yet narrow candidates” distinction; semantic fidelity unverified/insufficient. Separate from atomic path. |

Mixed positives Q0/Q2/Q3/Q5/Q7 delivered both requested acts **0/5**.
Only **Q0 (1/5)** naturally produced a linked, unblocked mixed request with
actual M31=true and M32=true; frozen target coverage required at least two.
Thus the intended authority variant is only partially observed, even though
Q0 proves the narrower mechanical admission change. Human-inspected surface
judgments are not semantic-equivalence certification.

## Causal receipts, graph, storage, and cost

- Q0's actual M31=true, M32=true, two typed actions, linked event→M31→M32
  and no blocker generated an atomic receipt with
  `prior_m31_surface_authority=true`. This is the concrete before/after:
  comparable N0 was wrongly bypassed before the correction; Q0 is admitted
  now. The reply was **not** delivered by atomic because the bounded rewrite
  returned `new_number` and the unchanged validator rejected it. Q3 and Q7
  were admitted with M31=false/M32=true and rejected for the same status.
  `new_number` is a necessary safety rejection, not a delivered rewrite.
  The outer date's appearance in the rewrite style prompt is a plausible
  contributor, not a proven origin, since raw model text is not persisted.
- Q2/Q5 had linked two-action producer chains with no lineage blocker, but
  M32 `repair_rejected`/`surface_authority=false` because its grounded-anchor
  check failed; fail-closed atomic admission was correct under this contract.
  This does **not** authorize weakening M32. Q7's source receipt says
  `source_retracted_or_ambiguous`; Q4's third-party attribution and Q8's
  protected role prevent inappropriate atomic authority. Q1/Q0/Q3 actor
  reversal is a separate visible surface defect: in Q0 the final language
  guard's `localized_known_terms` changed its own `original_reply` containing
  `私が選んだ` into `うちが選んだ` without preserving the User subject.
- In all ten Safari rounds the native runtime graph showed the verified
  producer EVENT→M31→M32 projection (3 expandable nodes, 2
  `is-producer` edges). It displayed **zero** atomic delivery/action/terminal
  edges because no final atomic receipt was delivered; a rejected candidate
  is not drawn as action coverage. This matches the raw receipt state, but
  graph completeness is not answer quality. Per-round inspection used Safari
  AX/visual state; no per-round screenshots are claimed.
- Safari bubbles matched raw `assistant_reply`, final visible-language guard,
  blackboard `utterance.payload.reply`, runtime `last_reply`, local
  `conversation.txt`, and the corresponding SQLite episodic document
  **10/10**; atomic logic/trace mirrors matched **10/10**, including null on
  non-admitted turns. This is transport consistency even when the reply is
  wrong. Isolated snapshots show distinct persisted *turn* episodes 0→10,
  one new ID per round. The episodic collection has 12 rows after background
  consolidation (ten turn episodes plus two summaries), so its total is not
  misreported as ten. T0–Q9 full-profile snapshots all have zero User
  profile rows and the same empty-content digest; no guessed mental state was
  promoted to a profile fact.
- Final delivery-complete M19 User wait passed the ≤20.000 s gate in **7/10**
  turns; Q0 20.5696 s, Q2 20.5269 s, and Q5 20.7730 s failed. Mean wait
  **15.5922 s**, max **20.7730 s**. The new atomic path completed **3**
  qwen2.5:7b rewrite calls, Q0/Q3/Q7, all temperature 0, max 80 tokens,
  6 s timeout; aggregate 425 prompt tokens, 115 completion tokens, and
  6.942871 s call latency. This stays within its ≤5-call/≤400-completion
  cap, but a full-system token ledger is unavailable. Existing planner and
  single-rewrite costs are not silently included in the atomic subtotal.

## Decision and claim boundary

Keep Q strict FAIL and M31 target coverage inconclusive. The change fixes a
real *admission/receipt/graph truthfulness* error on a legitimate variant; it
has **not** made multi-act user requests reliably complete. A separate
read-only causal review is required before any remaining correction batch:
rewrite prompt scope (`new_number`), M32 false anchor loss, User/character
subject scope, and latency must not be bundled into one score-chasing edit.
At most one additional grounded, source-disjoint, prospectively frozen
correction batch is allowed under the current plan; if it still fails, record
`REVIEW_REQUIRED` with a minimal counterexample and design options. No claim
of general human understanding, LLM superiority, human preference, temporal
generalization, production readiness, or Goal completion follows from Q.
