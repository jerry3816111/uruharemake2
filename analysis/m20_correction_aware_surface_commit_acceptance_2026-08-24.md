# M20 Correction-Aware Surface Commit acceptance

Date: 2026-08-24  
Scope: bounded product correction and Web delivery milestone; not evidence of mind-reading or general human-equivalent understanding.

## 1. Product problem retained from M19

The M19 Safari session exposed two actual product failures:

1. after the user explicitly said that the system had misunderstood and that the desired response was simply to wait together, the visible reply could repeat the stale clarification;
2. every partial reply chunk resent the full cognition/debug/graph payload, causing growing surface cost and a transient blank Safari state.

M20 treats the user's current explicit correction as stronger evidence than the prior provisional desired-response prediction and separates lightweight visible streaming from the final research payload.

## 2. Implemented mechanism

The real dialogue path now records an `uruha_correction_aware_surface_m20` directive containing only structured cues and a digest, not raw dialogue. When an explicit correction names a desired response, the runtime:

1. detects the correction and its explicit target;
2. records whether the previous prediction was contradicted;
3. revokes the stale policy;
4. selects a named repair policy;
5. adds the prior surface form to `must_avoid`;
6. verifies that the selected repair reached the final Japanese utterance.

The Web path batches reply text into useful chunks. Partial updates contain chat/status only; the complete planner, cognitive trace, graph, runtime state, and memory payload are committed once after the visible reply finishes. The trace records stream chunks, lightweight updates, full payload updates, and whether a full payload leaked into partial streaming.

## 3. Isolated Safari multi-turn evidence

Runtime isolation:

- database: `/tmp/uruha-m20-final.mhXNzo/db`
- adaptive model: `/tmp/uruha-m20-final.mhXNzo/adaptive.json`
- Web trace: `/tmp/uruha-m20-final.mhXNzo/web.jsonl`
- local-only URL: `http://127.0.0.1:7866/?m20clean=2`
- idle visible proactive speech remained disabled.

Turn 1 was intentionally ambiguous:

```text
User: 我從早上就一直坐不住，腦子停不下來。
UruhaBrain: 今は放っといてほしいのか、少し聞いてほしいのかだけ教えて。
```

The system retained uncertainty rather than turning sleep, anxiety, consolation, or teasing into a fact.

Turn 2 supplied an explicit correction and desired response:

```text
User: You misunderstood again. I only want you to wait for the result with me.
UruhaBrain: あー、そこ読み違えた。結果来るまでうちも一緒に待っとく。
```

Trace evidence for turn 2:

```text
correction detected: true
authority: current_explicit_desired_response
feedback: contradicted
revoked previous policy: calibrate_need
selected repair policy: share_arousal
repeated clarifier blocked: true
forbidden repetition detected: false
brain work: 1.2211s
surface stream: 0.7354s
end-to-end after enqueue: 2.1107s
stream chunks: 4
lightweight payload updates: 5
full cognition/graph payload updates: 1
full cognitive payload during partial stream: false
```

Safari remained responsive and showed the final graph. The visible reply was natural Japanese even though the correction was English.

Evidence images:

- `analysis/m20_safari_correction_chat_2026-08-24.jpeg`
- `analysis/m20_safari_correction_graph_2026-08-24.jpeg`

## 4. Automated evidence

M20 adds five focused contracts for correction authority, stale-policy revocation, surface repair, actual two-turn runtime nodes, and lightweight streaming with one final graph commit.

The compatibility suite covers M20, M19, M18, M17, M16, functional understanding, personhood/pragmatic loops, visible Japanese, idle-visible suppression, and proactive non-idle behavior:

```text
111 passed, 3 warnings in 4.78s
```

Python compilation and `git diff --check` passed.

## 5. What M20 proves and does not prove

M20 proves a narrow but product-visible mechanism: when the user explicitly corrects the expected kind of response, the current correction can revoke a contradicted provisional policy, change the final Japanese utterance, and appear as a causal change in the graph. It also proves that partial Web streaming no longer resends the full graph payload.

It does not prove that all implicit corrections can be recognized, that the system can infer an unspoken desired response without evidence, or that the selected repair is universally preferred. Detection is still marker/anchor based, and broad natural-dialogue and human preference validation remain future work.

## 6. Next product milestone

M21 is **Bounded Slow-Path Planner**. M19 retained a real non-fast-path turn with 57.4038 seconds of brain work. M21 must split that cost by stage, prevent simple conversational turns from entering an unbounded model/planner path, and provide a safe Japanese fallback before the user-facing latency budget expires without bypassing factual, correction, safety, or memory guards.
