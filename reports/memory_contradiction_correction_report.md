# Memory Contradiction / Correction Report

- generated_at: 2026-06-18T23:21:22

## Summary

- total_cases: 5
- case_pass_rate: 1.0
- current_negative_profile_rate: 1.0
- stale_positive_profile_rate: 0.0
- correction_intent_rate: 1.0
- current_anchor_rate: 1.0
- reply_correction_rate: 1.0

## Interpretation

- This eval checks whether explicit negation updates the current profile state without deleting historical episodes.
- Passing means the system can keep old memories as history while answering from the newer current-state memory.

## Cases

| id | lang | category | current_negative_profile | stale_positive_profile | intent | anchor | reply_correction | pass | reply_text |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zh_like_then_not_like | zh | preference_negation | 1 | 0 | 1 | 1 | 1 | 1 | 前のままじゃない。今は咖啡じゃない方で覚えてる。 |
| en_like_then_not_like | en | preference_negation | 1 | 0 | 1 | 1 | 1 | 1 | コーヒーはもう違うって更新してるし。 |
| ja_like_then_not_like | ja | preference_negation | 1 | 0 | 1 | 1 | 1 | 1 | 今はコーヒーじゃないって言ってただろ。 |
| zh_food_then_cannot_eat | zh | capability_negation | 1 | 0 | 1 | 1 | 1 | 1 | 前のままじゃない。今は拉麵じゃない方で覚えてる。 |
| en_food_then_cannot_eat | en | capability_negation | 1 | 0 | 1 | 1 | 1 | 1 | 今はラーメンじゃないって言ってただろ。 |
