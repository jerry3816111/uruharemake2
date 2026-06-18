# Memory Update / Overwrite Report

- generated_at: 2026-06-18T23:19:36

## Summary

- total_cases: 5
- case_pass_rate: 1.0
- current_profile_head_rate: 1.0
- current_anchor_rate: 1.0
- current_reply_rate: 1.0
- stale_reply_rate: 0.0

## Interpretation

- This eval checks whether newer explicit profile facts dominate older facts during recall.
- Old memories are not deleted; they should stay available as history but not override the current answer.

## Cases

| id | lang | category | profile_head | anchor | reply | stale_reply | pass | reply_text |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zh_favorite_update | zh | favorite_update | 1 | 1 | 1 | 0 | 1 | 前に溫牛奶が好きって言ってたし。 |
| en_favorite_update | en | favorite_update | 1 | 1 | 1 | 0 | 1 | 前にカモミールティーが好きって言ってたし。 |
| ja_favorite_update | ja | favorite_update | 1 | 1 | 1 | 0 | 1 | 忘れてないし、ほうじ茶だろ。 |
| zh_dislike_update | zh | dislike_update | 1 | 1 | 1 | 0 | 1 | 吃辣嫌いって言ってたし。 |
| en_dislike_update | en | dislike_update | 1 | 1 | 1 | 0 | 1 | 前にloud clubsはきついって言ってたじゃん。 |
