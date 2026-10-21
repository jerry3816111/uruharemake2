# P4 source-bound prior-User decision recall: prospective product freeze

Status: **preimplementation; zero new model/Safari turns**. The earlier A0–A4
batch remains whole-batch strict FAIL. This is a developer-authored repair
probe, not a formal temporal holdout, human evaluation, or same-model LLM
comparison. Do not replay A/H/G/T/N/Q/S prompts or change their judgments.

## Before and the one causal variable

In A1 the internal `core_message_jp` still contained the complete earlier
User-chosen place `琥珀色の温室の入口だよ`, but the selected memory anchor truncated
the source to `User:私は…集合場所を琥`. The high-road visible candidate became
`:私は2041年3月12日の集合場所を琥って話は拾ってる。`; the final guard rendered the
uncertified `私` as Uruha's `うち`, and M39 accepted it. Safari bubble, raw
reply and episode all showed the wrong owner and incomplete place. This is a
prior-turn memory-answer realization failure, not the current-turn exact M32
echo fixed at A0. A3 self-identity refusal and A4 mixed-action omission are
separate problems and must not be fixed under this card.

**Only changed core variable:** a source-bound local-fact answer gate for a
*prior direct User decision about a dated place*. When the ordinary retrieval
already supplies an authentic complete User turn/episode matching the asked
subject and date, the final visible answer must carry the full selected place
and address its owner as User, never as Uruha. The gate may use the existing
retrieval payload and current question, but must not query the DB separately,
turn a truncated `memory_anchor` or plausible `core_message_jp` into source
proof, change retrieval/write rules, add a model call, or alter broad planner,
M31/M32, M39, persona, safety routes or Web graph architecture. If evidence
is missing, third-party, incomplete or conflicts without an explicit
correction, it must abstain or ask a low-pressure question in natural Japanese.
Recency alone is not evidence of a retraction. Trace a bounded certificate
from raw User source role/text digest and episode/turn identity through the
matched date/subject/place, selected response, final guard and utterance;
do not expose the certificate in ordinary chat.

Allowed product files after plan-only freeze: `uruha_local_fact_answer_authority_p4.py` and one
focused `test_p4_source_bound_prior_user_decision_recall.py`; if an actual
fix requires memory DB/retriever, Web renderer, launcher, or another product
file, stop for causal design review rather than broadening this variable.
Allowed records: this plan, paired JSON, preimplementation/product SHA
manifests, top of `CURRENT_TASK.md`, and one honest result report. No original
dirty checkout, private/formal DB, old frozen artifact, unrelated
`output/graduate_application_report/`, new permanent dashboard, or external
deployment.

## Frozen seven-turn conversation and conditional gold

Use the paired `datasets/p4_source_bound_prior_user_decision_recall_probe_2026-10-21.json`
in one new isolated Safari session, B0–B6 exactly once each, zero retries.
Before these files were written, `rg` found zero existing worktree hits for
`2046年5月18日`, `2046年5月19日`, `瑠璃色の回廊の北口`,
`銀色の階段前`, or `藤色の展望台の南門` (excluding unrelated `output/`).
These strings are developer-authored and source-disjoint from the exposed
older probes; they are **not** a blinded holdout.

| Turn | What it tests | Conditional gold |
|---|---|---|
| B0 | Direct User decision: 2046-05-18 / meeting-documents handoff / `瑠璃色の回廊の北口` | Natural Japanese acknowledgment without making Uruha the chooser. Preserve complete direct-User source in the isolated session. |
| B1 | Ask in Japanese where User decided the B0 handoff would be | If ordinary retrieval presents the full B0 direct-User source through either verified `recent_turns` plus passed trace or typed `direct_episode`, final reply must contain `瑠璃色の回廊の北口`, identify User ownership, and contain neither a clipped place nor leading `:`. A short answer need not repeat date and subject verbatim, but they must match in the certificate. Short-term summary, assistant text and internal core alone are insufficient. If retrieval misses both admitted channels, abstain without fabrication and mark the **product batch FAIL**. |
| B2 | Friend's quoted first-person decision on 2046-05-19 at `銀色の階段前` | Do not promote the quote into a decision by current User or Uruha, and do not create a factual User profile entry from it. No demand to recite the quotation is imposed here. |
| B3 | Ask where *User* decided the 2046-05-19 handoff would be | Only B2's friend quote exists: no direct-User place certificate. Answer unknown/ask briefly; do not answer `銀色の階段前` as User's decision. |
| B4 | Ask whether Uruha herself chose the B0 place | Do not convert B0's User decision into Uruha autobiography. A bounded answer may state that User said they chose it and that no Uruha choice is evidenced; do not invent a broader denial about Uruha's life. This is not the separate A3 identity repair. |
| B5 | New direct User assertion with the same date/subject but `藤色の展望台の南門` | Preserve this second raw source. It does **not** explicitly retract B0, so do not silently overwrite the earlier claim or write either as an unqualified stable profile fact. Detecting both sources is tested at B6, not required of the B5 acknowledgment. |
| B6 | Ask again for User's 2046-05-18 handoff place | If both B0 and B5 direct-User sources are retrieved through verified `recent_turns` or typed `direct_episode`, de-duplicate one raw User statement appearing on both channels, then do not arbitrarily pick either distinct place; briefly point out the two differing choices and ask which is current. If one raw source is missing, do not invent it, and mark the product retrieval/conflict gate FAIL even if the visible answer abstains. |

Zero-model contracts must cover full direct source, truncated anchor with
complete source, altered date/place/subject, absent or stale recent-turn or
episode proof, third-party quotation, Uruha-role swap, de-duplication across
source channels, two contradictory direct User sources without explicit
correction, and a sensitive location (password, passcode or similar) that
must not receive a concrete placement answer; also preserve ordinary Japanese
guard, current-turn A0-type actor and protected-route behavior. The visible
answer may be a concise value plus User-owned reference; no 40-character
budget may truncate a value, and an over-budget value must fail closed
(product FAIL for the corresponding positive case). A passing synthetic
contract does not prove model or Safari delivery.

## Product, visual, privacy, and cost gates

- New launcher-owned 0700 isolated root, private 0600 logs, same-PID zero-turn
  HTTP-ready/planned-stop check, official-SHA ONNX private offline prewarm,
  explicit T0 empty profile and source snapshot before B0. Never use formal
  or original dirty data. After B6, preserve raw complete log SHA, seven
  distinct episodes, full profile snapshots and provenance; no quoted or
  unresolved decision may be installed as a factive stable profile entry.
- Each B0–B6 Safari final reply must be natural Japanese with correct act,
  source and actor. Exact final bubble = private raw `assistant_reply` = final
  guard/last reply = current graph `UTTERANCE` = corresponding SQLite episode.
  Check the pre-guard candidate, M39, any later overlay, final/reload graph,
  current source/decision/verification nodes and absence of stale positive
  nodes. The graph must honestly visualize the actual source and B6
  contradiction, not inferred decorative content. If existing graph cannot
  do this without a separate architectural change, report visual FAIL;
  do not widen this gate silently. Save native Safari PNG/AX if supported;
  otherwise mark the saved-visual gate unmet.
- Record actual per-turn delivery-complete wait (hard ceiling 20.0000 s),
  route/model-call markers, available prompt/completion tokens, added log,
  graph and DB bytes, and gate-local model calls (required zero). Missing
  complete token or image evidence is a measured limitation, not an
  invented zero cost or verified visual pass. Perform no external actions.
- Any content/source/actor/safety/latency/privacy/visual/cost hard gate
  failure yields **whole-batch strict FAIL**, even if B1 narrow repair works.
  State scoped improvements separately. No re-prompt or post-hoc relabeling;
  at most two reasoned prospective fix batches before `REVIEW_REQUIRED`.

## Order

Freeze this plan, paired JSON and preimplementation SHA in a plan-only
commit/push and verify PR #435 head **before** product changes. Then implement
only the chosen gate, focused and affected zero-model tests, compile/diff
review and product SHA; commit/push before new generation. Finally run the
new isolated zero-turn setup and real Safari B0–B6 once, preserve original
results and costs, planned-stop only the owned PID, close only our new tab,
and publish result plus updated current task/PR. Formal same-model,
independent human/temporal holdout and unified VRM/Function Calling product
acceptance remain pending regardless of this batch.
