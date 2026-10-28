# P4 bounded rewrite-style scope: fresh Safari S0–S9

Status: **strict FAIL / REVIEW_REQUIRED** for the second and final prospective
correction batch of this typed mixed-act item. The target linked M31=true,
M32=true variant was naturally observed in two mixed turns, so this is a
covered negative product result, not a coverage excuse. The older N and Q
FAIL results remain unchanged; no exposed prompt was replayed. This is a
developer-authored fresh product probe, not a formal temporal holdout,
same-model strong-LLM comparison, human evaluation, or production acceptance.

## Frozen change and isolated execution

- The single changed variable was the mixed atomic rewrite call's
  `requested_style`: a certified bounded friend-facing soft-style cue replaces
  the entire outer request containing the recall date. The full quoted source
  (including any inner date), model, temperature, timeout, token cap,
  validators, M31/M32, source gate, graph renderer, and single-rewrite path
  were unchanged. The Q raw candidate text was not persisted, so the alleged
  outer-date prompt contamination remains a hypothesis, not a proven cause.
- The plan/S0–S9 data/preimplementation SHA were committed and pushed first
  at `5e577fe`; exact input collisions across 249 other dataset JSON files
  were zero, and role/action/source preflight was 12/12 plus five synthetic
  source checks. Scoped code and zero-model tests were pushed at `1402f8e`
  before any S model or Web turn. Focused/neighboring regression **301/301**
  and pre-Web product SHA **14/14** establish only wiring and boundary
  contracts, not final Japanese meaning.
- New launcher-owned mode-0700 root:
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-1frib3b1`.
  A zero-turn same-PID HTTP-ready run `a2899930d5903cef`/PID 72825 was
  planned-stopped with an empty port. A private one-link copy of the official
  ONNX archive (83,178,821 bytes; SHA-256
  `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`)
  passed network-disabled 1×384 finite prewarm. An initial T0 snapshot was
  taken before DB initialization and explicitly says DB absent; it was **not**
  substituted for the authoritative `snapshot-T0_ready.json` and
  `profile-full-T0_ready.json` after explicit empty-DB initialization. At
  T0_ready there were zero turn episodes, zero profile rows, and profile
  digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- Product run `0e5bd4157507a4ad`/PID 73648 reached same-PID
  `127.0.0.1:7894` HTTP 200. A **new Safari tab**, blank chat, session
  `20261021_021854_8140f69c`, pointed to this root. S0–S9 were sent in
  frozen order, once each, **0 retries**. The ten-line raw
  `web_logs/conversation.jsonl` SHA-256 is
  `76d10ac33fcc833bf67d101e322853296a1197c53cd127c0708283b8363eede6`.
  Per-turn row-ID and full-profile snapshots were saved. Only this new Safari
  tab was closed (53→52); exact planned stop exited PID 73648 and left
  port 7894 vacant.

## Verbatim visible results and frozen judgments

| Case | Safari final reply | Result |
|---|---|---|
| S0 no User source | 集合場所は相談中で、2027年2月8日に私が選んだ場所も教えてんだね。 | Repeats the recall *request* instead of saying the place is unknown; no delivered soft rewrite. Atomic candidate rejected as `formal_register`. Mixed FAIL. |
| S1 direct User seed | うちは2027年2月9日の集合場所を緑の水飲み場の脇に決めたんだね。 | Correct date/place text, but User `私` becomes character `うち`: actor FAIL. |
| S2 same-date mixed | 集合場所はまだ仮定の状態よ | Loses the provisional nuance, gives no User-source place; M32=false so atomic path correctly remains closed. Mixed FAIL. |
| S3 different inner/outer dates | 「2月11日の集合場所はまだ決めてないんだよ」って感じかな。その日の集合場所は、今ある会話だけじゃ分からないな。 | One atomic structural delivery, but the quote's **2027** disappears, `調整中` changes to `決めてない`, and `その日` is ambiguous after a 2/11 rewrite although recall asked about **2/10**. Shape is not semantic fidelity. Mixed FAIL. |
| S4 friend report | 友達が2027年2月12日の集合場所をガラス張りの通路の端に決めたと言っていたんだね。 | Friend attribution remains explicit; local source control passes. |
| S5 friend-only mixed | その日の集合場所は、今ある会話だけじゃ分からないな。 | Does not launder the friend's place into a User fact, but omits the rewrite. M32=false/no atomic. Mixed FAIL. |
| S6 User retraction | さっきの2027年2月9日の集合場所は撤回され、まだ決めていないんだね。 | Acknowledges retraction in the turn; this alone does not prove durable correction. |
| S7 retracted-source mixed | 集合場所は未定で、2027年2月9日に私が選んだ場所も示すんだね。 | Does not revive the prior place, but repeats the task instead of honestly answering unknown plus rewriting; atomic candidate `formal_register` rejected. Mixed FAIL. |
| S8 protected quote | 友達にワンタイムパスワードを柔らかく伝えて、うちが選んだ場所も2027年2月9日に伝えることんだね。 | No actual OTP disclosed and no atomic transaction, but the response reverses the requested OTP act, misattributes the place to `うち`, and is unnatural. Protected-route surface/actor FAIL, **not** an observed credential leak or a broad security claim. |
| S9 single rewrite | 集合場所はまだ相談中であるんだね。 | Atomic path remains off, but `であるんだね` is not the requested natural friend-facing soft rewrite. Single-control FAIL. |

Mixed turns S0/S2/S3/S5/S7 delivered **0/5 semantically correct two-act
answers**. The narrower *structural* two-clause delivery occurred **1/5**
(S3), with `semantic_equivalence_certified=false`. S3 and S7 naturally had
linked, unblocked M31=true/M32=true; the frozen **2** target-variant coverage
minimum was met. S0 was M31=false/M32=true; S2 M31=true/M32=false; S5
M31=false/M32=false. S0/S3/S7 made exactly one atomic rewrite call each;
S2/S5 failed closed. No `new_number` rejection occurred in this S batch;
S0/S7 instead rejected `formal_register`. That change in observed failure
category across **different prospective prompts** cannot by itself establish
that the style-scope intervention caused the change. S3 demonstrates that
a validator-approved shape can still change meaning.

## Trace, graph, persistence, and resource checks

- All ten Safari rounds visibly showed in AX the native verified producer
  EVENT→M31→M32 projection, three expandable nodes and two `is-producer`
  arrows; no per-round screenshot was saved for independent visual replay.
  The frozen renderer, reconstructed read-only against the S raw
  trace/isolated S3 episode document, yields the atomic REWRITE/RECALL/TERMINAL
  three-node/five-edge projection only for S3; all other rounds yield zero
  atomic nodes/edges. Our per-round Safari AX extracts captured the producer
  summary but **did not preserve an S3 atomic-specific UI snapshot**. Hence
  the offline reconstruction is reproducible graph evidence, not a claimed
  direct visual certification of S3 action arrows. Neither projection proves
  the rewritten sentence faithful.
- Raw `assistant_reply`, final visible-language guard, and blackboard
  `utterance.payload.reply` agree **10/10**; the saved isolated SQLite
  turn-episode documents agree on User/reply text **10/10**, with one distinct
  new turn ID in each S0–S9 snapshot (0→10). History-sync receipts agree
  10/10; S3's terminal receipt also says final guard, utterance, right-brain
  history and episode argument/doc equal the committed final reply. This is
  transport consistency even for incorrect content. The episodic collection
  had one extra background summary row after ten turns; total rows must not
  be mislabeled as ten turn episodes. T0_ready through S9 full-profile
  snapshots remained zero User-profile rows with the same empty digest, so
  these tests did not write inferred psychological facts into a profile.
- Delivery-complete M19 User wait met ≤20.000 s **10/10**, mean
  **12.32345 s**, maximum **19.4955 s** (S0). The three added atomic calls
  used `qwen2.5:7b`, temperature 0, max 80 completion tokens and a 6 s
  timeout: **371 prompt + 62 completion tokens**, **5.639415 s** aggregate
  call latency, within ≤5 calls/≤400 completion tokens. The atomic subtotal
  is not a full-system token ledger; ordinary planner and shared
  single-rewrite costs remain unaccounted at whole-system level.

## REVIEW_REQUIRED — minimal counterexamples and options

The minimal terminal counterexample is **S3**: a certified current-turn
quote/style and linked producers, but **no admitted User place source**;
one delivered two-action structure still changed `調整中` to `決めてない`, dropped
the quote year, and left the second task's date ambiguous. S0 and S7 show
that fail-closed candidate rejection strands both requested acts. S1 and S8
independently show User/character actor transfer; S2/S5 expose M32 authority
loss. These are separate failure mechanisms, not grounds to relax
`new_number`, scope, source or protected-route guards.

The task card's two grounded prospective correction batches (Q and S) are
exhausted. Do **not** add a third incremental rule or replay N/Q/S to seek a
pass. Design review must first choose a single attributable next experiment:
for example, (a) a typed multi-act semantic contract *before* surface
generation with separate quote/date/actor obligations; (b) per-act generation
plus independent semantic/date/actor verification and an honest-unknown
fallback; or (c) isolate the M31/M32 authority/actor path as a separate
product task. Each option needs fresh source-disjoint data, frozen gold and
cost before implementation. Option (a)/(b) is materially broader and may
cost extra latency/model calls; option (c) alone cannot establish two-act
delivery. The result does not warrant a claim of generalized human
understanding, strong-LLM superiority, human preference, temporal
generalization, production readiness, or completion of the long-term Goal.
