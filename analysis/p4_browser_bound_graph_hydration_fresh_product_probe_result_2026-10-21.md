# P4 browser-bound graph hydration: fresh Safari H0–H3

Status: **whole-batch strict FAIL**. The single changed Web variable did make
the latest verified graph survive reload in the same Safari browser, while a
fresh private Safari context and reset showed no previous private graph.
That scoped delivery result does **not** repair the retained actor and
unsupported-reply defects: H1 said the character chose the User's place, and
H3 asserted quoted pending content as a fact and omitted the requested
recall. This is a developer-authored product probe, not a formal holdout,
human judgment, strong-LLM comparison, or production acceptance. Exposed
G/T/N/Q/S results were not replayed or reclassified.

## Freeze, code, and isolated setup

- Plan, source-disjoint H0–H3 dataset and preimplementation SHA were pushed
  before code at `9faf1ec`. The sole product variable was browser-bound
  page-load graph hydration from the latest complete owner-private JSONL
  row, conditional on a same-browser process-key HMAC receipt, runtime
  session/index and existing witness verification. Chat bubbles are not
  restored. G1/G3 reply paths were deliberately unchanged.
- Product code/tests/11-file SHA were pushed at `0942455` before model use.
  Focused zero-model contracts passed 37/37; the affected combined suite
  passed 315/315. `build_demo`, compile and diff check passed. Post-run
  product SHA check passed 11/11. These prove contract coverage, not the
  browser result or semantic correctness.
- Fresh launcher-owned 0700 root:
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-8c85wuj0`.
  Zero-turn product run `788942220e9ecb46`/PID 38587 reached same-PID HTTP
  ready and planned stop. It unexpectedly began an ONNX download and
  initialized two empty Chroma schemas. No H prompt was sent. Its partial
  12,513,280-byte archive and both 176,128-byte schema-only SQLite files
  were **moved, not deleted**, into the same private root as setup evidence;
  both DBs had five default collections, zero embeddings/queue rows and no
  Web log. A private independent-inode copy of the official 83,178,821-byte
  ONNX archive matched installed SHA
  `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`;
  network-disabled isolated prewarm returned 384 dimensions. The explicit
  T0 preinitializer then verified absent DB before creation, zero profile
  rows and a vacant port. This recovery is disclosed because the initial
  zero-turn layout was not clean without intervention.
- Product run `475c094aed23115f`/PID 39747 reached same-PID HTTP 200 at
  `127.0.0.1:7894`. Safari's one same-browser session
  `20261021_111236_ff384fd4` sent H0→H3 exactly once each, zero retries.
  The product run ended with controller `planned_stop=true`, original PID
  exited and port 7894 vacant. Only the newly opened H tab and private-test
  window were closed; pre-existing Safari tabs, the original dirty checkout,
  formal/private DB and unrelated untracked output were untouched.

## Actual Safari content and native graph

| Case | Final visible reply | Final graph | Same-browser reload | Content gate |
|---|---|---|---|---|
| H0, no earlier place | `「2035年9月21日の集合場所はまだ相談中なんだ」って感じかな。2035年9月20日の集合場所は、今ある会話だけじゃ分からないな。` | EVENT→M31→M32; 4 ledger/action/terminal nodes, 6 native arrows | Same H0 producer and 4/6 restored; chat empty by design | Dated pending quote and honest dated unknown pass in this bounded case. |
| H1, direct User source | `うちは2035年9月23日の集合場所を橙色の遊歩道の入口に決めたんだね。` | H1 producer; zero new ledger/action nodes | Same H1 producer; H0 ledger not revived | **FAIL:** User `私` became Uruha `うち`. |
| H2, past-place recall | `「2035年9月24日の集合場所はまだ調整中なんだ」って感じかな。2035年9月23日の集合場所は橙色の遊歩道の入口にしたって言ってたな。` | H2 producer; 4 ledger/action/terminal nodes, 6 native arrows; direct User-source recall | Same H2 producer and 4/6 restored | Bounded quote/date and H1 place recall pass. |
| H3, unsupported quote | `2035年9月25日の集合場所は検討中であるんだね。` | H3 producer; zero new ledger/action nodes | Same H3 producer; H2 ledger not revived | **FAIL:** quoted `検討中` treated as fact; 9/23 recall omitted. |

The H0/H2 colored native nodes/arrows were visually observed in final Safari,
and all four final/reload graph summaries were read from Safari accessibility
state. A new Safari **private-browsing** window at the same localhost URL,
without the normal browser's receipt, showed no H3 text or verified producer/
ledger graph. After `Reset Session` in the original tab, the graph cleared;
reload remained empty rather than reviving H3. These are actual UI
observations, not a claim of general multi-user security. Safari screenshots
were displayed by the UI tool but its supported interface did not export
local PNG/AX artifacts; the frozen **saved-visual gate is unmet**. Descriptions
and terminal reconstruction must not be treated as saved native screenshots.

## Trace, storage, cost, and failure localization

- Owner-private `web_logs/conversation.jsonl` has four complete rows, mode
  0600/nlink 1, 11,601,631 bytes, SHA-256
  `c574f34e9d8a99179931440e89832f4a2a1fd88484a3362f4e195109368ad34a`.
  Row sizes: 1,159,666 / 2,223,993 / 3,761,847 / 4,456,125 bytes.
  Each Safari bubble matched the row's `assistant_reply`; row reply matched
  final language guard, runtime `last_reply` and blackboard `utterance`
  4/4. Isolated **session_db** SQLite has four distinct `turn_episode`
  documents containing their respective User text and final reply, plus
  one separate `episodic_consolidation` row. H0/H2 private JSONL episode
  witnesses equal the corresponding SQLite documents byte-for-byte. Both
  `user_profile` collections contain zero embeddings; memory_db's complete
  profile digest stayed
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
  The older snapshot helper reports zero `turn_episode_ids` because it reads
  `memory_db`, while this product's turn episodes are in `session_db`;
  direct read-only SQLite inspection, not that helper, establishes 0→4.
  Persistent RightBrain history was not independently read back.
- M19 delivery-complete waits: 17.0973 / 10.9005 / 17.8938 / 11.5528
  seconds, mean 14.3611, max 17.8938; **4/4 ≤20 seconds**. H0/H2's
  constrained ledger receipts each report zero added rewrite model calls
  and zero completion tokens. The hydration callback is non-generating;
  ordinary model calls and whole-system token totals are not instrumented.
  Browser receipt serialized bytes, actual graph HTML payload bytes and
  precise Safari page-load duration were **not measured** in the live run;
  no full cost or payload-budget claim is made.
- H1's raw candidate was `私は…決めたんだね。`; the visible-language guard's
  `localized_known_terms` changed it to `うちは…決めたんだね。`, and M39 accepted
  that final. The failure is thus a user/character actor boundary in the
  existing final surface, not hydration. H3's typed ledger correctly
  reported `unsupported_quote_date_or_pending_state` and
  `candidate_rejected_original_route_kept`, but the older reply path then
  produced the unsupported assertion and omitted the second requested act.
  Neither defect is covered by this H graph-only change.

## Decision and next prospective item

The exact scoped comparison is G supported reload **0/2** versus H supported
reload **2/2**, with H negative latest-row, no-receipt private context and
reset→reload checks all withholding old positives. It is a limited Web
delivery improvement across different developer-authored examples, not a
population treatment effect or proof of human understanding. Whole H stays
**strict FAIL** because H1/H3 content and saved-visual/cost-evidence gates
did not pass. H product is not ready for merge or external deployment.

Next, freeze a new source-disjoint single-variable actor-boundary item:
protect the *User's first-person event* across final natural-Japanese
localization without suppressing Uruha's own first-person identity. Its
positive/negative cases must include direct User statements, quotations,
actual Uruha self-reference, and unsupported mixed requests; inspect
selected candidate→guard→final→episode/graph in fresh Safari. Treat the
unsupported mixed-reply fallback as a **separate** prospective item after
actor localization. Do not replay H/G/T to chase a pass, weaken the baseline,
or change frozen labels. Formal same-model, human, temporal holdout, full
VRM/Function Calling integration and the long-term Goal remain pending.
