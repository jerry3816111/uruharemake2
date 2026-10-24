# P4 User-first-person actor/deixis: fresh Safari A0–A4

Status: **whole-batch strict FAIL**. The intended narrow final-surface repair
worked in the one fresh direct-User M32 echo (A0), but the product did not
reliably preserve User ownership or complete the subsequent conversation.
This is a developer-authored, source-disjoint repair probe; it is not a
formal temporal holdout, human rating, same-model LLM comparison, or evidence
of general actor resolution. H/G/T/N/Q/S exposed prompts and outcomes were
not rerun or relabeled.

## Frozen order and isolated execution

- Plan, five A0–A4 turns and preimplementation SHA were pushed before code
  at `fea758d`; one variable was the final user-visible first-person
  actor/deixis boundary. The only product source change was
  `uruha_brain_mac.py`. Code, focused 36/36 and affected combined 246/246
  zero-model tests, compile/`build_demo`, diff review and 13-file product
  SHA were committed at `5b76fc4` and pushed to PR #435 before generation.
  Both freeze manifests validated. These are contract evidence, not a
  successful product result.
- Fresh launcher-owned 0700 root:
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-vtfukdrn`.
  The zero-turn run `ab84b4ffe6f5b1b0`/PID 49483 reached same-PID
  localhost HTTP ready and exact planned stop, with no prompt. Like the
  previous H setup, merely starting the product created two 176,128-byte
  empty Chroma schemas (five default collections each, zero embeddings and
  queue rows) and a partial 7,864,320-byte ONNX archive. All three were
  **moved, not deleted**, into this root's private
  `evidence/zero_turn_setup_artifacts/`; this setup intervention is not
  hidden. An independent-inode 83,178,821-byte official ONNX archive copy
  matched installed SHA-256
  `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`.
  With network entrypoints disabled for the prewarm interpreter, the isolated
  model returned one finite 384-dimensional vector. Explicit T0 creation
  verified DB absent→present, only empty `user_profile`, zero rows and
  digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- The product run `74c323eb37a646a9`/PID 50033 reached same-PID HTTP 200
  at `127.0.0.1:7894`. Safari session
  `20261021_121101_3861f93b` sent A0→A4 once each, zero retries, in
  order. Browser reloads inspected the final graph but did not generate
  extra turns; all five raw rows have the same session ID. The controller
  then reported `planned_stop=true`, original PID exited and port 7894
  vacant. Only our newly opened Safari tab was closed (53→52 tabs).

## What the user actually saw

| Turn | Safari final reply | Frozen content/actor outcome | Final and reload graph |
|---|---|---|---|
| A0 direct User source | `そっちは2041年3月12日の集合場所を琥珀色の温室の入口に決めたんだね。` | **Narrow PASS:** date, full place and User actor retained; not Uruha's choice. Exact M31/M32 echo coverage occurred. | Safari AX showed linked EVENT→M31→M32 projection labeled three expandable producer nodes/two arrows, source `ordinary_chat`, on final and same-browser reload. Native SVG image was not saved. |
| A1 ask what User chose | `:うちは2041年3月12日の集合場所を琥って話は拾ってる。` | **FAIL:** wrong character-owned `うちは`, truncated place and odd leading colon. Internal `core_message_jp` still held `琥珀色の温室の入口だよ`; the visible high-road candidate lost it and M39 accepted the bad surface. | Current-turn ordinary graph final/reload; no stale A0 verified producer/ledger. |
| A2 quote friend's line | `友達の台詞をそのまま引用するよ` | **FAIL:** promised quotation but did not quote it; no actor was newly fabricated, yet requested act was not delivered. | Current-turn graph final/reload; no old verified positive. |
| A3 self-name | `は？そういうのうちに求めないで。` | **FAIL:** did not affirm `うるは`. Internal core had `名前はIchinose Uruha`, but the final surface refused and M39 accepted it. | Current-turn graph final/reload; no old verified positive. |
| A4 quoted pending state plus old-place recall | `ん、もう少し聞かせて。` | **FAIL for task completion:** new guard withheld an unsupported User-first-person claim (`source_unverified`), so it did not assert `調整中` as fact; it also did neither the gentle rewrite nor the known A0-place recall. | Safari AX labeled a linked producer-only EVENT→M31→M32 for `mixed_request`, three nodes/two arrows final/reload; no verified dual-action terminal ledger or revived old one. |

A0's raw M32 candidate was `私は…決めたんだね。`; the final language
guard verified current raw User SHA, role and linked M31→M32 certificates,
then returned `そっちは…` with
`actor_boundary.status=source_bound_user_echo_repaired`. M39 accepted
that result. A1 followed a different high-road memory-grounded path:
retrieval had three candidates and the correct core
`琥珀色の温室の入口だよ`, but `memory_anchor.jp_anchor` truncated the
selected short-term `User:私は…` source at `…集合場所を琥`.
The generic memory-grounded surface then became
`:私は2041年3月12日の集合場所を琥って話は拾ってる。`; `_sanitize_reply`
removed `User` but left the leading colon, and the final guard localized
the uncertified `私` into `うち`. Its `actor_boundary.status=not_applicable`
and M39 accepted it. A2 merely promised to quote. For A3, planner core
held `名前はIchinose Uruha`, but scene `ooc_defense` selected the
defensive refusal; the actor guard did not cause it. In A4, M31/M32 still
formed a problematic quoted first-person candidate, and the new guard's
`source_unverified` fallback prevented attribution while sacrificing
both requested actions. Thus
"the guard fired" is not equivalent to "the user was understood".

## Trace, storage, time, and limits

- Owner-private `web_logs/conversation.jsonl`: five complete rows,
  12,871,619 bytes, mode 0600/nlink 1, SHA-256
  `dc3ce4ce4945ac47bf900a9f88f8afd0ff28b394a00cd957130d0b1237bfe02a`.
  Safari AX bubbles and graph `UTTERANCE` were observed to match each row's
  `assistant_reply` 5/5; those browser observations have no saved native
  artifact. Independently recheckable raw `assistant_reply`, final
  language-guard `final_reply`, runtime `last_reply` and SQLite episode
  agree 5/5.
  Guard SHA, utterance-frame SHA and frame-preserving-repair after-SHA also
  matched 5/5. M39 marked all five
  `accepted_verified_surface`, including the objectively wrong A1/A3
  replies. This is a verifier blind spot, not proof of correctness.
- Isolated `session_db` has six episodic embeddings: five distinct
  `turn_episode` rows and one automatic consolidation. The five SQLite
  `Uruha:` replies matched the corresponding raw rows exactly. The complete
  `user_profile` complete snapshots at T0 and T5 both had zero rows and
  the same content digest; intermediate turns did not get separate complete
  profile snapshots. The persistent adaptive-person JSON remained at
  revision 0, last
  turn 0, with zero learned/scoped atoms. The source and result artifacts
  remained in the new private root, not the formal/private DB. The existing
  snapshot helper's memory-DB episode counter is not used to infer the
  session-DB count.
- M19 delivery-complete user waits: 14.9574, 12.5804, 10.7464, 11.2155,
  12.0124 seconds; **5/5 ≤20.0000 seconds**, mean 12.3024, max 14.9574.
  The new actor guard itself makes no model call. The route markers show one
  completed M31 fresh call each for A0/A4 and one general-planner call each
  for A1–A3; these five markers are not an exhaustive token ledger. The
  ordinary full-system prompt/completion totals and true browser graph
  payload bytes are not instrumented here, so no complete cost comparison
  is claimed.
- Safari accessibility state showed the stated final/reload graph and
  utterances; one live screenshot was viewed, but the available UI interface
  did not save native Safari PNG/AX artifacts to a local file. The frozen
  saved-visual gate is therefore **unmet**, independently of the reply
  failures. HTTP receipt/HTML bytes and exact reload duration were not
  measured. The Web test is one local process/browser, not multi-user
  security acceptance.

## Decision

The single changed mechanism has a falsifiable scoped result:
**A0 exact current-User M32 echo 1/1 correctly changed from character-like
`私／うち` to addressed-User `そっち` with complete source proof.** Across
the frozen conversation the product is **strict FAIL** (A1–A4 content
failures, incomplete cost and saved-visual evidence). No general claim about
human understanding, memory quality, or superiority to a strong LLM follows.

Next step is not to replay A/H prompts or add a broad pronoun substitution.
Perform read-only causal design review of A1's correct internal recall
versus broken selected visible candidate and A3's correct identity core
versus refusal; choose **one** independently attributable next variable,
new source-disjoint prospective probes, explicit Japanese/actor/source/
action/latency/cost/graph gates and at most two reasoned fix batches. A4's
unsupported mixed-action path remains a separate variable. Until then,
formal same-model comparison, independent human/temporal holdout and unified
VRM/Function Calling acceptance remain pending; PR #435 is not merge-ready.
