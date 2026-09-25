# P4-AS real selected-action surface execution: formal FAIL

The prospectively frozen one-turn private-runtime/Safari gate is **FAIL**. The case was executed exactly once at port `7882`; it will not be rerun and the gate will not be changed after seeing the result.

Input:

> 我的思緒一直往前衝，怎麼都靜不下來。

Frozen exact reply:

> 今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？

Actual visible reply:

> しんどくて止まらないのと、楽しみで止まらないの、今はどっち寄り？

The two failed gates are `turn:visible_reply` and `metric_mismatch:exact_visible_reply_count`. This is not hidden by the otherwise successful mechanism chain.

## What did pass

- The frozen Chinese input was absent at implementation commit `81e6ba6` and required the additive multilingual trigger path.
- P4-AS was `executed_and_committed`; the selected action was `calibrate_need`.
- M39 accepted the actual Japanese reply and verified that it realized the selected action with zero unresolved violations.
- M44 registered an exact receipt for the already committed P1 event; P4-AR returned `authorized_executed_product_event` with zero failed checks.
- The current binding contained six candidates and selected `calibrate_need`; the temporal graph showed `過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`.
- Safari visibly expanded P4-AS, P4-AR, and the temporal node. Their zero-based graph indices were `65/66/67`, before utterance at `69`; logic/runtime payloads were exact.
- The isolated log has one row, SHA-256 `a1a034f031fe1430c0b6d04bb6f88e875db96c190138769c1ddbb706518c5426`; Chroma has one embedding; end-to-end latency was `3.216s`; P4-AS added zero model calls and zero factual-memory writes.

## What the failure means

The system executed the correct **action class** but did not reproduce the one frozen **surface string**. The existing realization layer selected a different `calibrate_need` variant based on current scope/state. Therefore action-level causal correctness and exact lexical reproducibility are separate research claims.

This case must not be tuned or rerun. A future prospectively frozen gate must decide before execution whether it evaluates semantic action equivalence or exact lexical reproducibility. The former needs an independently fixed equivalence rubric; the latter must bind realization choice and every state input that controls it. Neither option can rewrite this FAIL.

The passed mechanism observations do not establish that a user prefers either reply, that the next-turn outcome will support it, felt understanding, natural-distribution generalization, a recovered human equation, or superiority over a strong LLM.
