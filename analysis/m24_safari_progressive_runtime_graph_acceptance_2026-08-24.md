# M24 Safari-Scale Progressive Runtime Graph and Trace Payload Budget acceptance

Date: 2026-08-24  
Scope: browser payload and graph-retention engineering for the live Web runtime. This is not evidence that the cognitive interpretation is always correct.

## 1. Product failure inherited from M23

M23 made the desired-response decision and its causal path visible, but a real four-turn Safari run retained about 5.37 MB of cognition in the final turn, duplicated most of it in browser state, and rendered about 335 KB of graph HTML. Scrolling the full graph triggered Safari's high-memory reload and removed the visible chat state.

The dominant duplication was runtime history: `recent_turn_traces`, `recent_autonomous_traces`, `last_autonomous_result`, `last_state_diff`, and blackboard/state aliases were repeatedly copied into the current browser payload. This was a product defect, not a cognition result.

## 2. Implemented M24 contract

M24 separates three representations:

1. **complete local record** — the original full turn and research trace are still appended to the isolated local Web JSONL;
2. **progressive browser cognition** — Safari receives current decision-bearing M18–M23 contracts, a bounded blackboard/state preview, and counts for retained histories instead of the histories themselves;
3. **progressive node graph** — every causal node and edge remains renderable, but each inspector detail is capped at 2,200 bytes and the aggregate graph detail budget is 160,000 bytes. Oversized content is marked as a bounded preview whose full source remains the local JSONL.

The text and audio submission paths both use the bounded browser payload. Full local logging occurs before browser compaction, so reducing Safari memory does not delete the research record.

## 3. Measured real-turn effect

The clean isolated Safari session used six turns. The complete local turn grew as history accumulated, while the browser turn stayed bounded:

| Turn | M23 selected mode | Full local turn | Browser turn | Graph HTML | Graph detail |
|---:|---|---:|---:|---:|---:|
| 1 | low-pressure clarification | 872,729 B | 120,666 B | 98,945 B | 34,971 B |
| 2 | playful tease | 1,908,613 B | 221,338 B | 115,419 B | 45,002 B |
| 3 | practical help | 3,147,734 B | 278,986 B | 125,070 B | 49,850 B |
| 4 | practical help, verified reusable preference | 4,020,457 B | 291,510 B | 131,357 B | 52,589 B |
| 5 | handled by correction-aware listening surface; M23 mode inactive | 4,778,148 B | 300,281 B | 133,375 B | 52,500 B |
| 6 | low-pressure clarification | 5,566,394 B | 316,590 B | 133,705 B | 52,320 B |

At turn 6, the browser turn is 94.3% smaller than the complete local turn. The graph keeps 65 nodes, all causal edges, and a largest node inspector of 1,857 bytes, below both explicit budgets.

The browser kept all six user/assistant messages while the graph was scrolled and the desired-response node was expanded. The prior high-memory reload did not recur during this bounded acceptance run.

## 4. Traceability evidence

The graph card still exposes task type, response-mode alternatives, evidence authority, uncertainty, performed route, surface match, timing, and M18–M23 causal stages. Clicking `desired_response_mode_m23` showed the selected mode, policy, task type, reason, and runner-up while retaining the trace identifier.

Automated contracts also inject multi-megabyte synthetic history and verify that:

- the graph stays under per-node and aggregate budgets;
- the selected M23 decision and M22 route remain in browser cognition;
- repeated full histories are replaced by auditable counts;
- the complete source record still contains the omitted evidence;
- text and audio final updates both use the progressive payload.

The adaptive persistence file contains none of the six raw test utterances. The entire Safari run used `/tmp/uruha-m24-safari.4Zvlek` for DB, adaptive state, and logs.

## 5. Validation evidence

M24-specific contracts:

```text
4 passed
```

Compatibility suite spanning M16–M24 plus functional understanding, personhood/pragmatic comparison, Japanese output, proactive behavior, route logic, and observatory rendering:

```text
198 passed, 3 warnings in 5.59s
```

Python compilation and `git diff --check` pass.

Safari evidence:

- `analysis/m24_safari_six_turn_chat_retained_2026-08-24.jpeg`
- `analysis/m24_safari_progressive_graph_2026-08-24.jpeg`
- `analysis/m24_safari_node_detail_2026-08-24.jpeg`

## 6. Newly retained product failure and M25

The sixth turn deliberately used English: `I still cannot settle down. Just stay with me for a minute, okay?` The page remained stable and the output remained Japanese, but the controller selected low-pressure clarification rather than companionship/listening. Turn 5 also reached a reasonable listening surface through the older correction mechanism while the M23 typed mode was inactive.

This is not hidden by the M24 performance result. It shows that the response-mode contract still relies on incomplete multilingual explicit-request cues and that M22 `general_conversation` can prevent M23 from owning an otherwise explicit desired-response request.

The next single product milestone is **M25 Cross-Lingual Explicit Desired-Response Authority**: make explicit Chinese, English, and Japanese requests for listening, companionship, practical help, teasing, or clarification enter one typed current-turn authority contract; handle negation and mixed cues; let that contract override stale learned preference; and verify final natural Japanese in a fresh isolated Safari sequence.

## 7. Claim boundary

M24 proves a bounded browser-engineering result: multi-turn trace growth no longer has to be copied wholesale into Safari for the graph to remain causally inspectable. It does not prove indefinite-session memory stability, absence of all Safari memory defects, semantic correctness of every node, full-trace retrieval from the graph UI, or superiority over a general LLM. The full local JSONL still grows with every turn; disk retention and long-duration compaction remain separate future work.
