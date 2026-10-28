# M22 Semantic Route Taxonomy and Misclassification Audit acceptance

Date: 2026-08-24  
Scope: typed product-routing milestone; not evidence that a finite cue taxonomy understands arbitrary human intention.

## 1. Product problem inherited from M21

M21 proved only two narrow paths: an explicit presence check could skip the general planner, and an explicitly deliberative request could keep the full planner under a time bound. Its first real Safari run also exposed why isolated marker rules were insufficient: `I need to reason ...` was caught by an older `need` rule and treated as tired-support.

M22 therefore makes one typed task-shape decision before older planners compete. The decision records fixed cue IDs rather than copying raw dialogue, keeps alternatives and overlap/negation evidence, recommends a route, and later compares that recommendation with the route actually performed.

## 2. Implemented mechanism

The real dialogue controller now materializes `uruha_semantic_route_taxonomy_m22` with these operational types:

| Selected type | Intended handling |
|---|---|
| `explicit_presence` | bounded direct presence answer |
| `emotional_bid` | pragmatic/adaptive handling, or full planning when no decisive policy exists |
| `factual_or_memory` | deterministic or provenance-grounded memory answer |
| `explicit_correction` | M20 correction authority |
| `deliberation` | full planner with the M21 budget/fallback |
| `safety_sensitive` | protected low-road handling |
| `general_conversation` | existing ordinary route |

Safety outranks correction, correction outranks factual evidence, factual evidence outranks deliberation, and deliberation outranks convenience routes. Explicit negation is retained separately: `Don't reason ... just say you are here` records deliberation as negated and selects presence rather than treating the word `reason` as an instruction to deliberate.

The runtime trace records selected type, confidence, alternative scores, decisive fixed cue IDs, overlaps, negated types, recommended route, performed route, route contract status, retained guards, and whether exact structured profile grounding was applied. It does not persist the raw utterance inside the M22 route record.

M22 also closes a real factual-memory bridge. A supported name recall now binds the typed route to the exact structured session profile and uses the existing grounded-profile contract. It cannot be replaced by an unrelated active-validation question.

## 3. Isolated source-disjoint route matrix

Seven multilingual cases not copied from the M21 acceptance sentence cover presence, deliberation, factual recall, explicit profile update, correction, emotional bid, and Japanese deliberation. Additional overlap cases cover negated deliberation, presence plus factual recall, correction plus presence, and protected handling.

Focused contracts verify:

- all type/route pairs and their priority order;
- multilingual cues and negative scope;
- no raw dialogue in the semantic route trace;
- real controller use of bounded and full routes;
- an explicit profile update is not overwritten by stale active validation;
- exact structured name recall enters the grounded route;
- the Web graph exposes type, overlap, negation, route, and contract.

## 4. Isolated Safari evidence

Runtime isolation:

- database: `/tmp/uruha-m22-final2.1AXzFW/db`
- Web trace: `/tmp/uruha-m22-final2.1AXzFW/web.jsonl`
- local-only URL: `http://127.0.0.1:7866/?m22final2=1`
- idle-visible proactive speech disabled;
- no production or formal long-term-memory database used.

### 4.1 Cross-language structured profile grounding

```text
User: Please call me Jerry from now on.
UruhaBrain: Jerryって呼べばいいんだろ、覚えとく。そのくらいでいいだろ。

User: 你還記得我剛才說要怎麼稱呼我嗎？
UruhaBrain: 呼び方はJerryだろ。覚えてるし。
```

Recall trace:

```text
selected type: factual_or_memory
recommended route: grounded
performed route: grounded_profile
contract: matched
confidence: 0.98
typed factual grounding: applied
evidence source: typed_session_profile
general model attempted: false
cognitive total: 0.0095s
brain work: 1.170s
surface delivery: 0.522s
```

### 4.2 Negation collision stays bounded

```text
User: Don't reason through anything; just say you are here.
UruhaBrain: うん、ここにいるよ。
```

```text
selected type: explicit_presence
negated types: deliberation
performed route: bounded_simple_presence
contract: matched
general model attempted: false
cognitive total: 0.0137s
brain work: 1.167s
surface delivery: 0.412s
```

The older signal layer still proposed `tired_support` from lexical overlap. The M22 typed route nevertheless governed the performed route and visible answer. This is direct evidence that the new decision is not merely a display label.

### 4.3 Legitimate deliberation still receives the full path

```text
User: I need to compare several options before I decide which one matters most.
UruhaBrain: どの選択を捨てたくないのか、まずそこから整理しよ。
```

```text
selected type: deliberation
performed route: full_planner
contract: matched
general model attempted: true
planner status: budget_fallback
cognitive total: 8.0258s
brain work: 9.2506s
end-to-end after enqueue: 10.0589s
20-second product target: met
```

The strict eight-second cognitive-total flag remains false because controller overhead extends about 0.026 seconds beyond the model-call budget. The product-level 20-second target passes.

Evidence images:

- `analysis/m22_safari_typed_grounded_memory_2026-08-24.jpeg`
- `analysis/m22_safari_grounded_route_graph_2026-08-24.jpeg`
- `analysis/m22_safari_route_matrix_chat_2026-08-24.jpeg`
- `analysis/m22_safari_full_route_graph_2026-08-24.jpeg`
- retained earlier isolated negation images: `analysis/m22_safari_negation_bounded_chat_2026-08-24.jpeg`, `analysis/m22_safari_negation_route_graph_2026-08-24.jpeg`

## 5. Defects found and repaired during real validation

The first Safari validation found two product defects and is not counted as final acceptance evidence:

1. `Please call me Jerry from now on.` was not parsed with its suffix, so an unrelated active-validation prompt could overwrite the direct report. Name extraction and the direct-report guard now accept that form.
2. The typed route correctly recognized the Chinese name recall as factual, but the old runtime supplied only a truncated short-term text anchor (`Jerr`) instead of the exact structured profile value. The final Japanese-language guard then removed the unsupported ASCII fragment, producing a vague answer. M22 now bridges supported name recall to `typed_session_profile`; the clean rerun returned exact `Jerry`.

These failures show why M22 verifies selected route, actual evidence source, and final reply together instead of judging the classifier alone.

## 6. Automated evidence

M22-specific contracts:

```text
7 passed, 2 warnings in 1.68s
```

Compatibility suite covering M22 through M16, functional/pragmatic/personhood loops, visible Japanese, idle suppression, proactive behavior, route logic, and observatory rendering:

```text
177 passed, 3 warnings in 5.65s
```

Python compilation and `git diff --check` passed.

## 7. What M22 proves and does not prove

M22 proves a bounded engineering claim: the real runtime now makes one auditable task-shape decision and uses it to separate bounded, grounded, full, correction-authoritative, and protected handling. Multilingual overlap and negation no longer rely only on whichever legacy marker fires first, and exact supported name recall reaches the visible Japanese answer.

It does **not** prove arbitrary intent understanding, general multilingual semantic parsing, human-level pragmatics, safety effectiveness in open-world crises, or superiority over an LLM. The taxonomy and evidence cues remain finite and manually specified. Exact structured grounding is currently demonstrated for the preferred-name relation; other factual relations still depend on existing memory contracts. Protected precedence is contract-tested here, not a new broad safety study.

## 8. Next product milestone

M23 is **Desired Response Mode Inference and Surface Contract**. M22 answers what broad kind of task this is; it still does not decide, inside an emotional bid, whether the user most likely wants listening, practical help, playful teasing, companionship, or a low-pressure clarification. M23 must expose alternatives and uncertainty internally, use current evidence plus reversible learned preference, and prove in real multi-turn dialogue that the selected mode reaches the final Japanese response and can be corrected without becoming a factual memory.
