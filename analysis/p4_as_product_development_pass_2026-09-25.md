# P4-AS product development smoke: pass after one informed correction

Status: **development smoke pass, not formal or holdout evidence**. The input is exposed and must not be rerun or relabelled as fresh evidence.

Safari at isolated port `7881` showed the visible reply:

> 今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？

The expanded graph showed `selected_action_surface_execution_p4 = executed_and_committed`, `executed_action_identity_gate_p4 = authorized_executed_product_event`, and `過去 0｜現在 6候選/選択 calibrate_need｜本輪未來 已封存`. M39 verified the Japanese policy act with zero unresolved violations; M44 registered an exact receipt; P4-AR authorized the same P1 event. P4-AS added no model call and no factual-memory write.

This follows one preserved informed correction. The first smoke had already committed the exact P1 pending event, while P4-AS incorrectly required an empty slot. The correction permits only absent-or-exact pending state and preserves an exact pending event plus ledger verbatim; mismatched events remain fail-closed. The focused suite is `14 passed`. The prospective offline gate is `13/13`, including `6/6` new positives, `6/6` controls, and zero false execution.

The broad P4-AD–AS collection reported `148 passed, 1 failed`. The single failure is a historical P4-AR real-freeze novelty assertion that scans every future `p4_a*.json`; it now sees the intentionally reused, already-exposed P4-AR input in the later P4-AS development partition. The frozen historical test was not rewritten and this is not a product behavior regression.

Runtime evidence: one log row, SHA-256 `abcbc7e0c109adef0966a00efb36687626aecd8868258d112acc72ed9a0c1dff`; one durable Chroma embedding; end-to-end `16.471s`. Safari visibly expanded the P4-AS, P4-AR, and temporal nodes; zero tabs were closed.

This pass proves only one bounded mechanism path from typed signal to visible action, receipt, exact event authority, and later-verifiable commitment. It does not prove that the user preferred the reply, that the next-turn prediction is correct, natural-distribution generalization, felt understanding, a recovered human equation, or superiority over a strong LLM.
