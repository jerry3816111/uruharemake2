# P4-AS product development smoke: preserved failure

Status: **development failure, not formal or holdout evidence**. The input is exposed and must never be rerun or relabelled as fresh evidence.

The isolated Safari turn at port `7880` produced the intended natural-Japanese clarification:

> 今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？

M39 reported `repaired_and_verified`, `calibrate_need`, a realized policy act, and zero unresolved violations. The product also already contained the exact P1 pending prediction. The causal chain still failed: M44 returned `existing_pending_preserved`; P4-AS required `no_existing_pending`; P4-AR consequently did not receive P4-AS plan authority and blocked on `plan_applied`, `plan_identity_exact`, and `plan_policy_exact`. The binding was reduced to `not_available/0`, and the temporal graph honestly showed no future commitment.

This is an integration failure rather than a visible-reply failure. The informed correction is deliberately narrow: an existing event is acceptable only when prediction ID, policy, turn, and input digest all match. That event and its ledger are preserved verbatim; only the missing verified-surface receipt may be appended. Any mismatch remains fail-closed.

Evidence: one log row, SHA-256 `ee26985953f9fd1606b534dc30292a4e143ac4abb6d5a59bc8ee167b5d06b0e5`; one durable Chroma embedding; semantic-authorization elapsed time `13.6936s`. The graph contains P4-AS / P4-AR / binding / temporal / utterance at zero-based indices `64/65/67/68/69`; M44 is subsequently materialized at `77`.

This result does not establish user preference, prediction correctness, felt understanding, a human equation, or superiority over a strong LLM.
