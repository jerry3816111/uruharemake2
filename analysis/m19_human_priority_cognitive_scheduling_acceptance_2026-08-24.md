# M19 Human-Priority Cognitive Scheduling

Date: 2026-08-24  
Status: bounded product-development milestone complete  
Scope: local scheduler, runtime trace, isolated Safari stress test; not production readiness or a total-latency claim

## 1. Product problem

M18 could make a guarded response decision in roughly 1.2 seconds, but the Web application still placed autonomous polling, memory maintenance, and human messages behind one shared Gradio queue. A person could therefore wait tens of seconds before the brain even received the message. Reporting only cognition time hid that product failure.

M19 is complete only if the real Web runtime can:

1. register a human message before it enters queued cognition;
2. prevent background work from waiting in front of that message;
3. make background admission non-blocking and bounded;
4. retain non-idle proactive behavior and silence-visible suppression;
5. separate frontend queue wait, brain-lock wait, brain work, and surface delivery in the real trace;
6. preserve the M16-M18 adaptive/person-model path and natural-Japanese visible-output guard.

## 2. What changed

### 2.1 Human-first admission

The Web submit path now has a queue-free admission marker. It increments the count of waiting human turns before the queued handler begins. The marker and the actual turn share a dedicated human concurrency lane, while proactive polling remains queue-free.

The runtime always clears the marker in `finally`, including an exception path. Human turns themselves remain serialized so two people cannot mutate the same single-session brain concurrently.

### 2.2 Background work never queues in front

Background work now follows this admission contract:

```text
human waiting?       -> skip
brain not ready?     -> skip
brain lock busy?     -> skip, never wait
human appeared?      -> recheck and skip
otherwise            -> run one bounded cycle
```

Web background memory consolidation is explicitly called with model maintenance disabled. The default CLI/runtime behavior is unchanged. This prevents a locally scheduled background turn from starting a long model call inside the Web interaction path.

### 2.3 Honest end-to-end timings

The M19 trace exposes:

```text
frontend_queue_wait_seconds
runtime_lock_wait_seconds
cold_brain_initialization_seconds
brain_work_seconds
surface_stream_seconds
handler_total_seconds
end_to_end_after_enqueue_seconds
delivery_complete
```

The final surface time is recorded only after the last visible chunk has been yielded. The node graph begins with `human_priority_scheduler_m19` and ends with `runtime_latency_m19`, so the displayed numbers are part of the same real turn rather than a separate benchmark.

### 2.4 Compatibility boundary

M17 and M18 trace aliases remain available. The hierarchical reuse, negative-transfer gates, six adaptive response dimensions, feedback persistence, Japanese surface guard, proactive non-idle behavior, and idle-visible suppression remain in the path.

## 3. Automated evidence

M19 adds six focused contracts:

1. a waiting human blocks background admission;
2. a busy brain causes background skip instead of queueing;
3. Web background consolidation cannot invoke model maintenance;
4. a turn records queue, lock, brain, and final surface timing;
5. the runtime graph and comparison card use actual M19 values;
6. Gradio uses a queue-free human marker, isolated human lane, and queue-free proactive poll.

Focused compatibility suite:

```text
106 passed in 4.92s
```

It covers M19, M18, M17, M16, functional understanding, personhood/pragmatic loops, visible Japanese, idle suppression, and proactive dialogue. Python compilation and `git diff --check` also passed.

One additional historical consolidation test was kept outside the M19 pass count because its fixed 2026-07-18 timestamp is no longer inside its hard-coded 24-hour window on 2026-08-24. M19 did not rewrite that historical fixture to manufacture a green result.

## 4. Isolated Safari stress test

Runtime isolation:

```text
memory DB:     /tmp/uruha-m19-final.gemFJz/db
adaptive:      /tmp/uruha-m19-final.gemFJz/adaptive.json
conversation:  /tmp/uruha-m19-final.gemFJz/web.jsonl
```

Visible proactive speech was disabled, while the autonomous loop ran once per second. The formal database and external deployment were not used. Safari kept the existing 15 unrelated tabs untouched.

### 4.1 Four warm turns

| turn | input language | visible reply | queue | brain lock | brain work | surface | end to end |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | English | `そりゃ頭止まんねえわ。結果来るまでうちも一緒にそわそわしとく。` | 0.0177s | 0.0000s | 1.1451s | 2.2107s | 3.5267s |
| 2 | Chinese | `寝てないのか、考え事で止まんないのか、まずそこだけどっち？` | 0.0149s | 0.0000s | 1.1454s | 2.5528s | 3.8429s |
| 3 | English | same incorrect clarification | 0.0175s | 0.0000s | 1.2165s | 3.1301s | 4.5087s |
| 4 | English correction | same incorrect clarification | 0.0132s | 0.0000s | 1.2816s | 3.8951s | 5.3607s |

All visible replies remained Japanese. Queue and brain-lock waits stayed near zero while autonomous ticks continued. Surface cost increased every round; this was retained as a real failure rather than hidden.

### 4.2 Post-background stress turn

After 49 autonomous ticks:

```text
Input:  Now answer after all those background ticks. Say you are here.
Reply:  うん、ここにいるよ。
```

Actual trace:

```text
frontend queue wait     0.0933s
runtime brain-lock wait 0.0000s
brain work             57.4038s
surface delivery        1.9941s
end to end             59.8518s
```

The scheduler node recorded `human_waiters=1`, `background_status=skipped`, `admission=human_first`, and `poll_is_nonblocking=true`. This is a successful M19 scheduling result and a failed total-latency result: background work did not delay admission, but a non-fast-path brain turn itself took 57.4 seconds.

## 5. New defects revealed by M19

### 5.1 Explicit correction was not authoritative

The user stated three times that they only wanted the system to wait for the result together, including `You misunderstood again`. The adaptive fast path still repeated an old sleep/thought clarification. The trace had already stored the current goal `希望先被傾聽或陪伴`, but that known current evidence did not override the stale clarification surface.

This is not an M19 scheduler failure. It is a correction-priority and surface-commitment defect and becomes the first half of M20.

### 5.2 Streaming resent the full cognitive payload

Every partial Japanese chunk also resent the growing graph, trace, memory view, and debug payload. Surface delivery rose from 2.21 to 3.90 seconds across four short replies, and the fifth turn temporarily left Safari in `streaming_reply` with the visible response area blank even though the JSONL had finalized.

This is the second half of M20. A partial visible reply should update only the chat/status surface; the complete graph should commit once at the end.

## 6. Visual evidence

- `analysis/m19_safari_human_priority_timing_2026-08-24.jpeg`: the real post-49-tick Safari submission with loaded brain, autonomous tick count, isolated log, and streaming stage.
- `analysis/m19_safari_scheduler_graph_2026-08-24.jpeg`: the same final stress window retained as evidence of the oversized surface-commit problem rather than presented as a successful final graph render.

The definitive numeric evidence is the isolated JSONL trace above. M20 must produce a clean final Safari graph after eliminating repeated full-payload streaming.

## 7. Honest completion boundary

M19 proves a bounded product mechanism: waiting human messages no longer sit behind queued Web background cognition, and the system can distinguish admission delay from brain and surface delay.

It does not prove that every human turn is fast, that an already-running arbitrary external model call can be preempted, that multiple simultaneous users are supported, or that the Gradio page is production ready. The fifth turn missed the 20-second budget because brain work itself took 57.4 seconds. The correction failure and surface-update growth are explicitly unresolved.

## 8. Next product milestone

M20 is **Correction-Aware Surface Commit**:

1. treat explicit user correction and stated desired response as authoritative current evidence;
2. suppress a contradicted/repeated clarifier instead of asking it again;
3. record correction, revoked assumption, selected repair, and Japanese surface in the runtime graph;
4. stream only lightweight chat/status updates, then commit the full trace and graph once;
5. expose stream chunk count and full-payload update count;
6. verify with a multi-turn correction case and a post-background Safari turn.

M20 directly connects the user's correction to a changed reply and makes that change visible without allowing the visualization itself to block conversation.
