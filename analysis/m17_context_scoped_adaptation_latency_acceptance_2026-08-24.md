# M17 Context-Scoped Adaptation + Latency Budget

Date: 2026-08-24  
Status: bounded product-development milestone complete  
Scope: local runtime and isolated Safari acceptance only; not production readiness or a claim of human-equivalent understanding

## 1. Product problem

M16 proved that an explicit correction could change named desired-response variables and a later visible reply. It still had two product defects:

1. learned interaction preferences were global, so one correction could contaminate unrelated topics;
2. the runtime still called the general LLM planner even when the adaptive model had already selected a decisive policy and would overwrite that plan, causing roughly 65–85 seconds of observed local wait in the earlier acceptance.

M17 is complete only if the real Web runtime can learn a response preference inside a bounded context, avoid applying it to an unrelated context, reuse it when the original context returns, keep it across a restart, render the complete graph in Safari, and do so within the 20-second warm-turn budget.

## 2. What was implemented

### 2.1 Context-scoped adaptive state

`uruha_adaptive_person_model.py` now persists M17 state under categorical scope IDs:

```text
domain : interaction_kind : relationship_band
```

Current bounded domains are `arousal_regulation`, `physical_wellbeing`, `task_execution`, `positive_anticipation`, `emotional_support`, `relationship_play`, and `general_conversation`. Raw dialogue is not part of the scope or adaptive store.

Each scope has its own learned atoms and policy reliability. Exact-scope atoms are revision-aged, confidence-decayed, and rejected after the configured TTL. Legacy M16 global atoms remain readable for diagnostics but are not silently consumed by M17 decisions.

### 2.2 Feedback linkage rather than next-turn assumption

The next user turn is no longer automatically treated as an evaluation of the previous reply. It updates the previous context only when it is linked by one of these bounded signals:

- it directly answers a `calibrate_need` question with an explicit desired response;
- it contains an explicit reference such as “I didn't want… / I wanted you…”;
- it directly confirms or corrects the previous response.

A new task request after a playful reply is recorded as `uncertain`, `feedback_linked=false`, and creates no atom changes in the previous relationship-play scope.

### 2.3 Guarded planner fast path

When M17 has an active decision with sufficient margin, the runtime builds a complete guarded base plan and skips the general LLM plan that would immediately be overwritten. The normal hypothesis, pragmatic, longitudinal user model, public-persona appraisal, adaptive application, self-monitor, and final Japanese guard still run.

The fast path is denied for low-road safety cases, boundary/protected intents, grounded factual profile or memory recall, inactive decisions, and insufficient margins. A previously verified exact scope may use a lower margin threshold because the source is explicit interaction feedback rather than an unverified global guess.

### 2.4 Visible commitment and graph reliability

An explicitly requested or previously verified response policy must reach the user-visible Japanese surface. A selected `playful_tease` can no longer remain only in the trace while the final reply asks another generic clarification.

The Safari graph now:

- shows context scope, learned/rejected atoms, candidates, prediction, feedback linkage, persistence, fast-path decision, visible commitment, and latency;
- maps new and unknown runtime stages to valid lanes instead of failing after a successful brain turn;
- accepts both full and compact historical trace payloads.

Web startup prewarms the brain in the background. The cold initialization cost still exists (about 45 seconds in this local acceptance), but after prewarm it is not paid by the first user turn.

### 2.5 Additional runtime defects found by real Safari acceptance

The acceptance run exposed and repaired four defects that isolated function tests alone did not reveal:

1. a new `plan` stage fell through to a non-existent graph lane and caused `KeyError: 'reason'`;
2. compact candidate traces could contain strings and caused an `AttributeError` during graph rendering;
3. compact English matching joined `finish it` into `finishit` and falsely detected the abuse word `shit`;
4. a correct internal `playful_tease` decision could be paraphrased away before the visible reply.

The false English abuse match is now prevented without disabling actual Chinese, Japanese, or explicit English abuse detection.

## 3. Isolated Safari acceptance

Runtime isolation:

```text
memory DB:     /tmp/uruha-m17-final.TVE9Lt/db
adaptive:      /tmp/uruha-m17-final.TVE9Lt/adaptive.json
conversation:  /tmp/uruha-m17-final.TVE9Lt/web.jsonl
```

No formal long-term database or external deployment was used.

| Turn | User input | M17 result | Visible Japanese reply | Warm user wait |
|---:|---|---|---|---:|
| 1 | `I can't sit still and my mind won't stop.` | scope=`arousal_regulation`; learned=0; policy=`calibrate_need` | `いや、寝てないのか、考え事で止まんないのか、まずそこだけどっち？` | 1.1033 s |
| 2 | `No, I didn't want advice. I wanted you to tease me like we usually do.` | previous feedback=`contradicted`, linked=true; current policy=`playful_tease`; visible=true | `朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。` | 1.1467 s |
| 3 | `My report deadline is tomorrow and I cannot finish it. What should I do first?` | previous feedback=`uncertain`, linked=false; scope=`task_execution`; learned=0; policy=`solve_regulation` | `今すぐなら、頭の中を一回メモに全部出して、五分だけ呼吸整えよ。` | 1.1766 s |
| 4 | same ambiguous arousal input as turn 1 | exact arousal scope; learned atoms=`humor_invitation`, `relationship_familiarity`, `solution_request`; policy=`playful_tease`; visible=true | `いや、朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。` | 1.2135 s |

Measured cognition time for these four turns was 0.0139, 0.0131, 0.0147, and 0.0161 seconds. All four used the guarded fast path. The remaining roughly 1.1 seconds is Web/queue/rendering overhead rather than the skipped general LLM planner.

After stopping and restarting the full local Web process with the same isolated adaptive store, the same ambiguous arousal input immediately produced `playful_tease`, `learned 3`, `visible true`, and the full Japanese tease. Restarted warm user wait was 1.1814 seconds and cognition time was 0.0202 seconds.

The persisted adaptive JSON contained none of the five acceptance inputs, and its `raw_dialogue_persisted` contract remained false. The one decisive correction produced one adaptive revision; unrelated topic shifts did not add revisions.

## 4. Visual evidence

- `analysis/m17_safari_context_isolation_2026-08-24.png`: chat sequence showing teasing, an unrelated task solution, and same-context teasing reuse.
- `analysis/m17_safari_comparison_graph_2026-08-24.png`: comparison card plus the live M17 graph entrance.
- `analysis/m17_safari_scope_graph_2026-08-24.png`: dense runtime node graph with actual memory, pragmatic, context, prediction, verification, decision, surface, and writeback connections.

Safari kept one existing local UruhaBrain tab active. The other 15 user tabs were not closed or modified.

## 5. Automated evidence

Final focused command covered M17, M16 compatibility, desired-response equation, functional understanding, personhood/pragmatics, Japanese surface guard, idle suppression, routing, and graph rendering:

```text
Ran 150 tests in 0.587s
OK
```

`py_compile` for the four changed runtime modules and `git diff --check` also passed.

Important M17-specific regressions include:

- correction binds to the previous prediction's context rather than correction wording;
- same context reuses an explicit correction;
- unrelated task and physical contexts do not consume arousal-play atoms;
- a plain topic shift is not mislearned as feedback;
- withdrawal revises only the original scope;
- scope expiry and confidence decay;
- restart persistence without raw dialogue;
- legacy global atoms are ignored for M17 decisions;
- decisive adaptive turns skip the redundant general planner;
- new/unknown graph stages and compact candidate traces cannot crash Safari;
- `finish it` cannot become an English abuse token.

## 6. Honest completion boundary

M17 is complete as a bounded engineering milestone. It demonstrates a real product loop, not only a replay or dashboard:

```text
current signal
→ categorical context
→ desired-response candidates
→ visible Japanese action
→ linked next-turn feedback
→ scoped update
→ unrelated-context isolation
→ same-context reuse
→ restart persistence
```

It does not prove mind reading, consciousness, a biological human equation, universal pragmatic understanding, or superiority to strong LLMs. It also does not prove production durability.

Remaining limits:

- seven domains and six response policies are still a narrow manually designed vocabulary;
- the scope hierarchy is exact-match only; there is no audited domain-level fallback or transfer between similar situations;
- explicit feedback linkage is marker-based and will miss indirect or culturally varied corrections;
- cold initialization still takes about 45 seconds, although prewarm hides it from warm interaction;
- fixed Japanese policy cores make surface behavior reliable but less varied;
- no broad real-user distribution, adversarial long-run test, or independent human rating was performed for M17.

## 7. Next product milestone

M18 should be **Hierarchical Context + Adaptive Policy Coverage**:

1. replace exact-only scope reuse with auditable exact/domain/relationship fallback and negative-transfer gates;
2. represent desired response as composable dimensions (care, directness, humor, listening, actionability, distance) so the system is not limited to six fixed policies;
3. generate varied Japanese surfaces from the selected dimensions while retaining commitment and language guards;
4. validate indirect corrections, near-context transfer, conflicting preferences, long-run decay, and latency in isolated Safari sessions.

M18 should remain development-first: it must change real replies and the live graph before any extra research packaging is considered.
