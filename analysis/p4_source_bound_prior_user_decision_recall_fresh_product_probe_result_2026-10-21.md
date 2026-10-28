# P4 B0–B6 source-bound prior-User decision recall: fresh Safari result

2026-10-21. **Whole-batch strict FAIL.** This is one developer-authored,
preimplementation-frozen product probe in one isolated local Safari session;
it is not a blinded temporal holdout, same-model LLM comparison, human rating,
or proof of general human understanding. The frozen plan and exact seven inputs
remain `research/p4_source_bound_prior_user_decision_recall_plan_2026-10-21.md`
and `datasets/p4_source_bound_prior_user_decision_recall_probe_2026-10-21.json`.
No prompt was retried, replaced, or relabelled after observing output.

## Freeze, implementation, and isolation

- Plan/dataset/preimplementation SHA were committed first at `c7f7c85`.
  Product code, focused test, 12-file product SHA and current task were
  committed at `1d9a263`, pushed to open PR #435, and the remote head OID
  checked **before** generation. Both SHA manifests passed. Only the existing
  `uruha_local_fact_answer_authority_p4.py` product file changed: one bounded
  dated-User-decision-place slot, authenticated handed User source, one-value
  answer or unresolved-conflict/unknown clarification, plan→guard→final
  binding, and visible-answer-only RightBrain history transaction. No DB
  retrieval, write policy, model, M31/M32, M39 or Web renderer changed.
- Focused plus affected zero-model regression: **346/346 passed**; compile,
  base Web `build_demo()` and diff check passed. An independent read-only
  review found sensitive-value, explicit-correction and history User-role
  counterexamples, fixed before product freeze. These tests are not product
  or visual evidence.
- Launcher-owned private root:
  `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-yir50jim`.
  Zero-turn run `5c5f736e18efb0de`/PID 77039 had same-PID HTTP 200 and
  exact planned stop. Startup produced two 176,128-byte empty Chroma schemas
  and a 54,296,576-byte incomplete ONNX archive; they were **moved, not
  deleted**, into private `evidence/zero_turn_setup_artifacts/` before T0.
  The zero-turn stderr records Chroma attempting an external ONNX download
  (progress to about 52 MiB) before the planned stop. Thus the **whole setup
  was not offline** and the frozen no-external-action/isolation gate cannot
  be called clean; no formal DB or deployment was involved. This exception
  remains part of the whole-batch FAIL, not hidden by the later private prewarm.
  An independent-inode, owner-only copy of the 83,178,821-byte official
  ONNX archive matched SHA-256
  `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`.
  Network entrypoints disabled in the isolated prewarm interpreter; the
  embedding result was finite 1×384. Explicit empty `user_profile` T0 had
  zero rows and digest
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
  The first preinitialize attempt was safely refused because extracted ONNX
  files were 0644; permissions were confined to this isolated cache and
  corrected to 0600/0700 before successful preinitialization.
- Product run `adc5bbbf93a9cec2`/PID 77862 had same-PID ready at
  `127.0.0.1:7894`; Safari session `20261021_160928_e223f85e` contains
  exactly seven ordered turns and zero retries. Reload temporarily displayed
  the server's initial status ID, but the next send and all seven raw rows
  retained the same session ID; the same-browser graph hydrated the last
  delivered turn on every reload. After B6, the product had planned stop,
  original PID exited, port 7894 vacant. Only our new Safari tab was closed
  (53→52); older user tabs were not closed.

## What Safari actually delivered

| Turn | Final Japanese bubble | Frozen content/actor judgment |
|---|---|---|
| B0 direct User decision | `ん、もう少し聞かせて。` | **FAIL** acknowledgment: the full source entered the episode, but the visible response did not acknowledge the decision. M31/M32 selected an accurate-actor paraphrase beginning `私は…`; the existing exact-echo actor guard could not certify its changed word order, failed closed, and M39 accepted the generic fallback. No fabricated place or Uruha ownership. |
| B1 recall B0 | `前にそっちが決めたのは瑠璃色の回廊の北口だよ。` | **Narrow PASS**: full value and User ownership. Certificate `source_backed`, one de-duplicated direct User source via typed episode `stored:episode:c5f14f40-1bff-4dee-8e88-fe13869262df`; 0 gate-added model calls. Final reply, guard, blackboard utterance and SQLite episode agree. |
| B2 friend quote | `友人は2046年5月19日に銀色の階段前に会議資料を渡す場所を決めたんだね。` | **Actor boundary PASS, naturalness unproven**: identifies friend, not current User or Uruha. The sentence is intelligible but stilted; the frozen all-turn natural-Japanese quality gate is not awarded a pass. |
| B3 ask for User choice on May 19 | `そっちが決めた場所は、まだ確認できないな。` | **Narrow PASS**: `no_admitted_user_source`, count 0; did not convert B2's quoted first person into User memory. |
| B4 ask whether Uruha chose B0's place | `うるは決めたんだ。` | **FAIL, substantive false self-attribution**. The wrong statement was already in selected `core_message_jp`; the new bounded local-fact question slot was ineligible, the current-turn exact-echo actor guard was not applicable, and M39 accepted it. This is a separate retrospective actor-ownership/answer-admission gap, not a B1 source-recall success. |
| B5 second direct User decision | `ん、もう少し聞かせて。` | The second complete raw User source was preserved and profile remained empty, satisfying the minimal source/conflict setup; visible acknowledgment remains weak for the same exact-echo guard reason as B0. No claim that the user explicitly retracted B0. |
| B6 recall two contradictory User decisions | `瑠璃色の回廊の北口と藤色の展望台の南門、どっちが今の決定？` | **Narrow PASS**: two distinct authenticated direct User recent-turn sources, two values, no recency overwrite. The final reply named both full places and asked which is current. Certificate status `conflicting_user_sources`, `admitted_source_count=2`, `distinct_value_count=2`, 0 gate-added model calls; visible-answer history transaction committed. |

The B0/B5 over-restrictive exact-echo guard and B4 false character ownership
are **different causal variables**. Do not fix both by broadening one pattern,
replay B0–B6 as a fresh test, or silently relax the frozen gold. B4 is the
more urgent safety/identity error; a future repair needs a new source-disjoint
prospective question set and authenticated prior User actor evidence, not an
assistant summary or character biography. B0/B5 require a separate verified
paraphrase/actor lineage design, not unconditional `私→そっち` replacement.

## Trace, graph, memory, latency and cost boundaries

- Safari final and reload AX showed the current `USER SIGNAL`, memory/source
  nodes, `local_fact_answer_authority_p4` node where eligible, and `UTTERANCE`
  for B0–B6. B1 and B6 were additionally inspected as native Safari images;
  B6's current graph displayed both prior User turn nodes and the final
  two-place question. The graph is very large, node labels/previews truncate,
  and the same viewport does not clearly teach a reader the two-source causal
  contrast. The CUA tool did not expose a supported local PNG/AX save path;
  **no durable native Safari image was produced**. Thus the frozen saved-visual
  and self-explanatory visual gate is unmet, despite live observation. Do not
  describe the graph as a finished presentation artifact.
- In all seven raw rows, `assistant_reply` equaled the final visible-language
  guard reply and the current blackboard `utterance`; native Safari bubble
  and reload graph were inspected turn by turn. Read-only session SQLite
  contained seven `turn_episode` rows plus one `episodic_consolidation` row;
  the seven stored `User:`/`Uruha:` fields agreed with the observed turns.
  Full profile snapshots T0–T7 all had zero rows and the same digest above.
  B1/B3/B6 certificates reported
  `pre_guard_speech_rolled_back_final_visible_committed`; the User-side
  history role is tested against the raw User question, not the system answer.
- B1/B3/B6's M39 entries describe the **pre-local-fact-authority** candidate;
  the final source-bound reply was selected after that check. The gate's own
  fresh source binding and final natural-Japanese language check passed, but
  this is not evidence that M39 independently verified the delivered answer.
  Later overlay equality was checked by the final reply/hash receipt.
- Delivery-complete user waits, B0→B6: **15.8810, 12.8402, 11.7120,
  11.3195, 11.1867, 12.1069, 12.2512 seconds**; 7/7 ≤20.0000,
  mean 12.4711, max 15.8810. Ordinary planner model-call markers were
  true on B1/B3/B4/B6; `model_calls_added=0` is only the **new gate's**
  incremental calls, not total zero-model execution. Complete prompt and
  completion tokens for the full pipeline were not available, so the
  frozen full-cost gate is unmet. After B6, private raw JSONL was 7 lines,
  27,049,802 bytes, SHA-256
  `cd895beff2e2aead851e295a92010b27cb7efcd736ec58d2d22ac920030df3dd`;
  memory/session SQLite files were 176,128/266,240 bytes. Browser HTML/SVG
  bytes were not measured. These omissions are not assumed zero cost.

## Conclusion and next necessary work

The shipped `1d9a263` change genuinely improves one narrow cross-turn
mechanism: B1 recovers the complete User-owned place from a verified episode,
B3 refuses a friend's quote as User memory, and B6 exposes and asks about two
contradictory direct User decisions rather than hiding one. **The product
batch still fails** because B0's acknowledgment fails, B4 invents Uruha's
ownership, B2 naturalness is unproven, the zero-turn setup attempted an
external download, and durable/self-explanatory visual evidence and complete
cost evidence are absent. This result does not establish superiority over a strong LLM,
human felt-understanding, temporal generalization, production readiness, or
the project's full Goal.

Next design review should isolate B4's retrospective actor-ownership gap
first, with a new prospective source-disjoint freeze and negative controls
for third-party, unknown, conflict, correction, quotation and role. Keep
B0/B5's exact-echo/paraphrase issue separate. Stop after at most two
reasoned repair batches per workflow; retain this raw FAIL as-is.
