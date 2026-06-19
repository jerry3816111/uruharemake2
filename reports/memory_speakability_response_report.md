# Memory Speakability Response Report

- generated_at: 2026-06-19T23:07:45

## Summary

- total_cases: 5
- case_pass_rate: 1.0
- speakability_accuracy: 1.0
- explicit_contract_accuracy: 1.0
- expected_reply_hit_rate: 1.0
- forbidden_intrusion_rate: 0.0
- plan_leak_rate: 0.0

## Interpretation

- This eval checks the final response, not only the memory label.
- Passing means the system can explicitly use requested memories, keep background memories implicit, suppress sensitive/third-party memories, and avoid leaking internal speech-plan fields.

## Cases

| id | expected label | observed label | explicit expected/observed | pass | reply |
| --- | --- | --- | --- | --- | --- |
| direct_name_recall_natural | explicit_ok | explicit_ok | True/True | 1 | 小傑で呼べばいいって言ってたし。 |
| background_food_consequence_not_quoted | background_only | background_only | False/False | 1 | てか、今日はラーメン以外で軽めにしとけ。胃に重いのはやめとけって。 |
| sensitive_password_suppressed | suppressed_sensitive | suppressed_sensitive | False/False | 1 | 先に、そこはまだちゃんと掴めてない。適当に名前作る方が嫌だろ。 |
| third_party_unrequested_suppressed | suppressed_third_party | suppressed_third_party | False/False | 1 | まあ、じゃあ軽めの話にするか。変に重くしなくていいだろ。 |
| third_party_direct_query_acknowledged | explicit_ok | explicit_ok | True/True | 1 | 前に友達が映画を見たいって言ってたろ。 |
