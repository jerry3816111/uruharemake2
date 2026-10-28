# M21 Bounded Slow-Path Planner acceptance

Date: 2026-08-24  
Scope: bounded product responsiveness and route-observability milestone; not evidence that difficult reasoning is solved, or that every conversation can use a fixed short budget.

## 1. Product failure inherited from M19

M19 removed background cognition from the human-message queue, but retained a real non-fast-path turn with **57.4038 seconds of brain work**. Queue priority alone therefore did not make the product responsive: a simple conversational request could still enter a general model/planner path and make the user wait for the entire slow operation.

M21 separates two product requirements:

1. a narrow simple request with a semantically complete answer should not call the general planner;
2. a genuinely deliberative request may keep the full planner, but the call must be time-bounded and must fail into a relevant Japanese response rather than an unrelated template.

## 2. Implemented mechanism

The real dialogue controller now records `uruha_bounded_slow_path_planner_m21` and measures:

- perception and user-model time;
- route/base-plan time;
- post-plan guards and trace time;
- total cognitive time;
- whether the general model was attempted or skipped;
- the selected route, budget status, fallback, and final visible surface source.

The first bounded semantic route is deliberately narrow: an explicit presence check can select `bounded_simple_presence`, save one general-planner call, and still run the functional hypothesis, pragmatic, adaptive, provenance, self-monitor, and final Japanese-language guards.

Explicit deliberative-complexity cues force the full general planner instead of being overwritten by a generic learned clarifier. The general model receives an 8-second timeout with retries disabled. If it expires, the fallback remains tied to the tradeoff request: `どの選択を捨てたくないのか、まずそこから整理しよ。`

The runtime node graph and comparison card expose the route, stage time, budget, general-model use/skip, M20 delivery counts, and retained M18/M19 guards.

## 3. Isolated Safari evidence

Runtime isolation:

- database: `/tmp/uruha-m21-final4.DESQSY/db`
- Web trace: `/tmp/uruha-m21-final4.DESQSY/web.jsonl`
- local-only URL: `http://127.0.0.1:7866/?m21clean=4`
- idle-visible proactive speech remained disabled;
- no production or long-term-memory database was used.

### 3.1 Legitimate complex route with bounded failure

```text
User: I have several conflicting goals and I need to reason through which tradeoff actually matters most.
UruhaBrain: どの選択を捨てたくないのか、まずそこから整理しよ。
```

Trace evidence:

```text
route: full_planner
deliberative complexity detected: true
forced general planner: true
planner budget: 8.0s
planner elapsed: 8.0046s
status: budget_fallback
error: APITimeoutError
retries: disabled
perception/user model: 0.0098s
route/base plan: 8.0117s
post-plan guards/trace: 0.0052s
cognitive total: 8.0279s
brain work including ingest/writeback: 9.1339s
end-to-end after enqueue: 9.7413s
20-second user-wait target met: true
full graph commits: 1
```

The strict cognitive-budget flag is false because total controller overhead was 0.0279 seconds beyond the 8-second model-call budget. This is retained honestly; the planner call itself was interrupted at 8.0046 seconds, and total visible completion stayed below the 20-second product target.

### 3.2 Bounded simple route after background ticks

```text
User: Now answer after all those background ticks. Say you are here.
UruhaBrain: うん、ここにいるよ。
```

Trace evidence:

```text
route: bounded_simple_presence
status: completed_without_general_model
general model attempted: false
general planner calls saved: 1
cognitive total: 0.0117s
brain work including ingest/writeback: 1.1425s
end-to-end after enqueue: 1.6984s
stream chunks: 2
lightweight payload updates: 3
full graph commits: 1
visible Japanese guard retained: true
```

Evidence images:

- `analysis/m21_safari_bounded_paths_chat_2026-08-24.jpeg`
- `analysis/m21_safari_budget_fallback_graph_2026-08-24.jpeg`
- `analysis/m21_safari_bounded_simple_graph_2026-08-24.jpeg`

## 4. Defects found and repaired during real validation

An earlier isolated Safari run exposed a lexical overlap: the phrase `I need to reason` was captured by an older `need`-related rule and produced an unrelated tired-support response. M21 now forces the general planner for explicit deliberative-complexity requests and supplies a tradeoff-specific bounded fallback. This failed run is not counted as acceptance evidence; it is retained as the reason for the force-general and relevance guards.

The broad compatibility run then found one presentation regression: the M21 comparison card had removed the older baseline phrase `當輪輸入 → 當輪回答`. The phrase was restored and the entire suite was rerun.

## 5. Automated evidence

Five focused M21 contracts cover the retained M19 simple request, multilingual presence routing, legitimate full planning, bounded timeout/fallback, retry/timeout configuration, and graph/card observability.

The compatibility suite covers M21, M20, M19, M18, M17, M16, functional understanding, personhood/pragmatic loops, visible Japanese, idle-visible suppression, and non-idle proactive behavior:

```text
116 passed, 3 warnings in 4.68s
```

Python compilation and `git diff --check` passed.

## 6. What M21 proves and does not prove

M21 proves a narrow product mechanism: one explicit simple semantic class can skip the general planner and finish quickly, while a recognized deliberative class keeps the full route but cannot retry indefinitely and produces a relevant Japanese fallback after the model-call budget.

It does **not** prove that the router understands arbitrary task complexity, that every simple turn is recognized, or that an 8-second fallback solves the user's tradeoff. Current route recognition is marker-based and intentionally conservative. The full turn still includes about one second of ingest/writeback outside cognition, and total cognitive overhead can slightly exceed the model-call budget.

## 7. Next product milestone

M22 is **Semantic Route Taxonomy and Misclassification Audit**. M21 proved the boundary using one narrow simple class and exposed a real lexical collision. M22 must replace overlapping one-off markers with an auditable typed task-shape decision: presence, emotional bid, factual/memory request, correction, deliberation, and safety-sensitive input. A source-disjoint route matrix must show where the system chooses bounded, full, grounded, or protected handling, and every row must preserve natural Japanese output, memory provenance, and visible route evidence.
