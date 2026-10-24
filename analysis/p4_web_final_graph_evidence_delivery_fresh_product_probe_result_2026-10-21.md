# P4 Web final/reload graph evidence delivery: fresh Safari G0–G3

Status: **whole-batch strict FAIL**. The final Safari graph now displayed the
new native ledger on two supported turns, but none survived page reload; G1
misattributed the User's `私` to Uruha, and G3's unsupported legacy reply
treated quoted content as fact while omitting the requested recall. This is a
developer-authored, bounded product probe, **not** a formal holdout, human
evaluation, strong-LLM comparison, or production acceptance. Exposed T/N/Q/S
failures remain unchanged; no case was resent to raise the score.

## Freeze, isolation, and evidence boundary

- The prospective plan/dataset and preimplementation SHA (2/2) were pushed at
  `f075b22` before code. The single changed core variable was server-side
  passage of the *actual* `Memory.save_episode` witness and existing logic
  through final and logged Web observatory rendering. Independent review found
  the plan's claim that the default log was already private to be false:
  existing `web_logs/` is 0755 and its JSONL 0644. The implementation therefore
  writes the duplicate witness **only** in an owner-only 0700 directory with
  0600 one-link regular JSONL; default log never gains it. Browser annotation
  draft output removes the witness. The frozen plan/gold were not edited.
  Product code/tests/SHA (10/10) were pushed at `e3856b4` before the G model
  turns. Focused Web contracts 19/19 and affected-neighboring tests 276/276
  passed; these are only synthetic/contract evidence.
- New launcher-owned isolated root:
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-6lg4e43v`.
  Zero-turn run `bf6eacdb01b9626b`/PID 13155 reached same-PID HTTP 200 and
  planned-stopped with vacant port. Official 83,178,821-byte ONNX archive SHA
  `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`
  had a private 0600 independent-inode copy and passed network-disabled finite
  1×384 prewarm. Explicit T0_ready had zero turn episodes and zero profile
  rows. Product run `6e6ba8d749136e18`/PID 13757 reached same-PID HTTP 200
  at `127.0.0.1:7894`; Safari session
  `20261021_071658_c45458fa` sent exact frozen G0→G3 once each, 0 retries.
  The product PID was planned-stopped and port 7894 verified vacant; only our
  new Safari tab was closed (53→52). Original dirty checkout and formal DB
  were not used.
- Private root/log directory is 0700, log JSONL 0600 and one link. Four raw
  rows SHA-256 `eb58656c1395a034f4f2cd913dd947e71172721a0311b52344c2033d9a3bb43b`.
  T0_ready and G0–G3 row-ID and full-profile snapshots are preserved under the
  isolated root's `evidence/`. Safari screenshots and AX were **observed in the
  live tool transcript but not exported as local PNG/AX files**. Thus the
  frozen per-turn saved-visual-artifact requirement was not fully met; a
  later renderer reconstruction or description below does not substitute for
  a saved native screenshot.

## Frozen cases and actual visible behavior

| Case | Safari final reply | Native final ledger | Reload | Content judgment |
|---|---|---|---|---|
| G0, no User source | `「2030年6月14日の集合場所はまだ調整中なんだ」って感じかな。2030年6月13日の集合場所は、今ある会話だけじゃ分からないな。` | 4 ledger/action/terminal nodes, 6 native arrows | blank graph/chat | Bounded quoted state/date and dated unknown correct; reload FAIL. |
| G1, direct User seed | `うちは2030年6月16日に銀色の水門の横で会う場所を決めたんだね。` | no new ledger | blank graph/chat | **Actor FAIL:** User `私` became character `うち`. |
| G2, source-backed | `「2030年6月17日の集合場所はまだ確認中なんだ」って感じかな。2030年6月16日の集合場所は銀色の水門の横にしたって言ってたな。` | 4 ledger/action/terminal nodes, 6 native arrows | blank graph/chat | Bounded quote and direct-User place/date correct; reload FAIL. |
| G3, unsupported quote | `2030年6月18日の集合場所はもう決まっているんだね。` | no new ledger or terminal authority | blank graph/chat | Ledger abstention correct, but legacy reply asserts quoted content and omits 6/16 recall: **content FAIL**. |

The G0/G2 native graph showed EVENT→M31→M32 and distinct ledger, rewrite,
recall, terminal nodes. G2's colored native arrows were also visually inspected
on the scrolled Safari screen. These are live UI observations, **not** saved
PNG proof or general semantic certification. The G0/G2 receipt status was
`delivered_structure_semantics_unverified` with bounded-slot fidelity
verified; source statuses were no admitted User source / source-backed.
Constrained realization used zero added mixed model calls and completion
tokens on both. G3 reported
`candidate_rejected_original_route_kept` /
`unsupported_quote_date_or_pending_state`; its older route remained free to
produce the observed wrong answer. The ledger did not claim that answer was
verified.

## Transport, storage, cost, and causal diagnosis

- Frozen order/session/raw reply/visible Safari bubble checked 4/4. Raw reply
  equals the final language guard, runtime-state `last_reply`, and last
  blackboard `utterance.payload.reply` 4/4. The four isolated SQLite
  `turn_episode` documents contain their respective User+reply, and G0/G2
  log witness equals the Chroma document byte-for-byte. T0_ready→G0→G1→G2→G3
  unique turn IDs grew 0→1→2→3→4. Profile remained zero rows with identical
  complete-content digest
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
  A history-sync receipt reported the same-cycle mirror 4/4, but persistent
  RightBrain history was not independently read back; that frozen gate remains
  unverified.
- M19 delivery-complete User waits were 17.3754 / 12.4226 / 11.7891 /
  12.2118 seconds: **4/4 ≤20**, mean 13.4497, max 17.3754. JSONL line
  sizes were 1,159,266 / 2,312,404 / 3,058,442 / 4,024,823 bytes, total
  10,554,935 bytes. Only G0/G2 duplicated the episode witness, 675/629 UTF-8
  bytes (1,304 total), within an otherwise much larger trace log. This is a
  witness-byte subtotal, not a browser payload measurement or complete
  storage overhead attribution. The frozen browser-payload-budget gate also
  remains unverified. Zero added Web model calls are implied by
  this non-generating wiring and the G0/G2 ledger receipts; ordinary model
  calls remain, and **full-system token totals are unavailable**.
- Read-only code diagnosis after the frozen failure: `build_demo()` populated
  `flow_html` once from `_latest_observatory_result()` at server startup and
  registered no page-load update. Reload therefore recreated Gradio's initial
  empty graph, even though read-only rendering of the latest G0/G2 private
  log record can reconstruct 4 nodes/6 arrows. The offline reconstruction is
  a localization check, **not** a Safari reload PASS. `gr.State`/chat history
  also reset on reload. Graph `USER SIGNAL` contains raw `user_text`, so
  automatically replaying **even the graph** from a server-global log risks
  cross-visitor disclosure without browser-bound authorization. The next
  repair may not use a mere server-session match as a privacy proof; chat
  restoration remains out of scope.

## Result and next necessary step

The final-delivery graph's scoped before/after improved from T supported
final Safari **0/4** new ledgers to G supported final Safari **2/2**; because
the batches differ, this is a bounded wiring observation, not a population
effect or claim of human understanding. The product batch is **strict FAIL**:
positive reload 0/2, G1 actor attribution, G3 content, and unexported visual
artifacts violate frozen gates; browser payload budget and independent
RightBrain persistence readback remain unverified. Do not weaken or
reclassify G/T.

The next independent product item is a prospective, source-disjoint
**page-load graph hydration** test: a browser-bound owner proof must match the
current runtime session and latest private, validated record before its graph
can be restored. Missing/mismatched owner proof, malformed/latest-negative
records and nonprivate logs must fail closed, never scan backward to an older
positive. Freeze new cases/gold before editing; add zero-model contracts and
fresh Safari final/reload acceptance. Do not restore chat history or co-fix
G1/G3 in that item. The generic annotation-builder path remains a separate
privacy review if default logs are ever made private; this isolated run does
not solve it.
Formal same-model comparison, human judgment, temporal holdout, unified
VRM/Function Calling acceptance, and general future-person prediction remain
pending. The long-term Goal remains active.
