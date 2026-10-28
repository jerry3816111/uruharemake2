# M29 Generalized Literal-Topic Grounding and Translation Contract

Status date: 2026-08-25  
Status: bounded product mechanism accepted  
Claim boundary: observable literal-topic projection with checked source and visible anchors; not proof of hidden-intent understanding, translation equivalence, or human preference superiority

## 1. Problem closed

M28 could safely rebase a stale desired-response prediction only for a small typed weather set. Other self-contained topic shifts could still fall through to an old response mode and answer the previous uncertainty instead of the current sentence.

M29 adds a generalized but fail-closed route:

```text
unlinked self-contained current topic
→ deterministic candidate gate
→ local Japanese literal projection
→ exact source-span checks
→ subject / predicate / time / polarity representation
→ visible Japanese-anchor checks
→ casual-register check and bounded sanitation
→ final visible Japanese authority
→ suppress stale pending desired-response prediction
```

This is not an infinite phrase inventory. The model proposes the observable semantic projection, but it receives no surface authority unless every deterministic contract check passes.

## 2. Implemented contract

- Stores an input digest and source-anchor digests, not the raw current utterance, in the M29 trace.
- Requires one or more exact source spans from the current input.
- Requires Japanese subject, predicate, literal summary, and response fields.
- Requires every declared Japanese surface anchor to appear verbatim in the visible reply.
- Rejects foreign-script leakage at the final Japanese surface.
- Rejects polite service register (`です`, `ます`, `ください`, `なさい`, and related forms).
- May remove a non-casual trailing sentence only when all validated topic anchors remain in the retained casual surface.
- Removes empty generic understanding prefaces such as `了解だ` only when the remaining surface still contains every anchor.
- Retains M27 unknown/unlinked exclusion and M28 typed weather authority.
- Cannot override protected safety, boundary, or factual-memory plans.
- Does not store the local model's raw response.

## 3. Automated evidence

M29-specific:

- `test_generalized_literal_topic_projection_m29.py`: **8 passed**.
- Covers non-weather candidate gating, M28/incomplete-turn exclusions, exact source and visible anchors, fabricated-anchor fail-closed behavior, protected-plan priority, formal-tail sanitation, generic-understanding-prefix sanitation, and real runtime/graph integration.

Focused V2.11–M29 compatibility:

- **237 passed**, 3 dependency deprecation warnings.
- Includes visible Japanese output, functional/pragmatic/personhood loops, idle suppression, core routing, memory observatory, and M16–M29 contracts.
- Python compile and relevant `git diff --check` passed.

Broader historical combination:

- **242 passed, 2 failed**.
- Both failures are retained V2.15 evidence locks, not M29 behavior failures: one frozen-source integrity hash no longer matches the accumulated development tree; one test requires the retired `V2.15 Evidence` tab to appear before `Chat`, while the accepted product direction now makes Chat the main entry. These locks were not rewritten to manufacture a green result.

## 4. Actual isolated Safari acceptance

Isolation root: `/tmp/uruha-m29d-safari.zjh4cT`  
Local page left open: `http://127.0.0.1:7871/?m29rerun=1`  
Official long-term memory database: untouched

| Turn | Input | Visible reply | M29 evidence |
|---|---|---|---|
| 1 | `我今天又從早上就一直坐不住，腦子停不下來。` | `一回、寝てないのか、考え事で止まんないのか、まずそこだけどっち？` | creates the prior bounded prediction |
| 2 | `明天要考試。` | `明日の試験、頑張ろうね。` | zh; subject `明日の試験`; predicate `ある`; 2/2 anchors visible |
| 3 | `我今天又開始坐不住，腦子停不下來。` | `一回、今ほしいの、止め方と、ただ聞いてほしいのと、どっちに近い？` | creates another bounded prediction |
| 4 | `My train leaves at seven tomorrow.` | `明日の電車は七時に出発ね。` | en; subject `電車`; predicate `明日出発`; 3/3 anchors visible; formal tail removed |
| 5 | `我今天又開始坐不住，腦子停不下來。` | `しんどくて止まらないのと、楽しみで止まらないの、今はどっち寄り？` | creates another bounded prediction |
| 6 | `来週から新しい授業が始まる。` | `来週から新しい授業始まるね。` | ja; subject `授業`; predicate `始まる`; 3/3 anchors visible; generic `了解だ` prefix removed |

For turns 2, 4, and 6, all seven validation checks passed, M27 recorded `resolved_unknown_excluded`, `surface_status=matched`, the final pending prediction was null, and `raw_dialogue_persisted=false`.

Retained failures found through real Safari testing:

1. The first Chinese topic run produced `...` because the local model copied the schema's placeholder confidence and omitted surface anchors. The schema and numeric parsing were repaired, then rerun in a new isolated process.
2. The first English run ended in `なさい`; the register guard now removes a bad sentence only when all semantic anchors survive.
3. The first Japanese run began with unnatural `了解だ`; the bounded generic-prefix sanitation now removes it without deleting topic content.

## 5. Visual evidence

- `analysis/m29_safari_cross_lingual_literal_topics_2026-08-25.png`: final visible Japanese turns in Safari.
- `analysis/m29_safari_literal_projection_graph_2026-08-25.png`: retained progressive runtime graph.
- `analysis/m29_safari_projection_node_detail_2026-08-25.png`: expanded live M29 decision node with projected status and raw-free contract fields.

## 6. What M29 does and does not establish

Established:

- A self-contained unrelated current topic can outrank a stale desired-response prediction without a manually enumerated topic phrase row.
- The visible reply can be tied to exact source evidence and explicit Japanese surface anchors.
- Chinese, English, and Japanese actual Web turns reach Japanese output through the same traceable contract.
- Common non-casual and empty understanding surfaces found during real execution no longer pass unchanged.

Not established:

- Exact source-span presence does not independently prove that the Japanese projection is semantically equivalent.
- The model's confidence is an operational contract field, not an externally calibrated probability.
- Three successful live topics do not establish open-domain robustness, Uruha persona fidelity, or superiority over a same-model baseline.
- No blinded human naturalness or felt-understanding preference evidence was collected in M29.

## 7. Next milestone

M30 should evaluate cross-lingual semantic fidelity rather than add another surface feature: a frozen isolated holdout covering entity, time, negation, quantity, and relation changes; blinded source-to-projection checks; fail-closed error accounting; and protected-route non-regression. This is necessary before generalized literal grounding can be called reliable rather than demonstrable.
