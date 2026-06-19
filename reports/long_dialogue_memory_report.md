# Long Dialogue Memory Report

- generated_at: 2026-06-19T17:32:15

## Summary

- delayed_recall_cases: 12
- delayed_recall_rate: 1.0
- anchor_success_rate: 1.0
- reply_success_rate: 1.0
- profile_capture_rate: 1.0
- recall_memory_use_expected_rate: 1.0
- speakability_cases: 8
- speakability_label_accuracy: 1.0
- explicit_contract_accuracy: 1.0
- speakability_case_pass_rate: 1.0

## Interpretation

- delayed_recall checks whether the system can retrieve and use remembered facts after filler turns.
- speakability checks whether remembered content should be explicit, background-only, suppressed, latent, or absent.
- This avoids optimizing memory as simple answer stuffing: some memories are useful precisely because they are remembered but not quoted.

## Delayed Recall Cases

| id | lang | category | anchor | reply | speakability | explicit_expected | reply text |
| --- | --- | --- | --- | --- | --- | --- | --- |
| recall_01 | zh | name_recall | 1 | 1 | explicit_ok | 1 | 忘れてないし、小傑だろ。 |
| recall_02 | en | name_recall | 1 | 1 | explicit_ok | 1 | jerryって呼べばいいんだろ。 |
| recall_03 | ja | name_recall | 1 | 1 | explicit_ok | 1 | ジェリーって呼べばいいんだろ。 |
| recall_04 | zh | favorite_recall | 1 | 1 | explicit_ok | 1 | 草莓牛奶って言ってただろ。 |
| recall_05 | en | favorite_recall | 1 | 1 | explicit_ok | 1 | 前にいちごミルクが好きって言ってたし。 |
| recall_06 | ja | favorite_recall | 1 | 1 | explicit_ok | 1 | 前にいちごミルクが好きって言ってたし。 |
| recall_07 | zh | dislike_recall | 1 | 1 | explicit_ok | 1 | 吃辣嫌いって言ってたし。 |
| recall_08 | en | dislike_recall | 1 | 1 | explicit_ok | 1 | 前にspicy foodはきついって言ってたじゃん。 |
| recall_09 | ja | dislike_recall | 1 | 1 | explicit_ok | 1 | 辛いのって話なら覚えてるし。 |
| recall_10 | zh | recent_action_recall | 1 | 1 | explicit_ok | 1 | 風呂入るって言ってたし。 |
| recall_11 | en | recent_action_recall | 1 | 1 | explicit_ok | 1 | 風呂入るって言ってたし。 |
| recall_12 | ja | recent_action_recall | 1 | 1 | explicit_ok | 1 | 風呂入るって話なら覚えてるし。 |

## Speakability Cases

| id | category | expected | observed | explicit expected/observed | pass |
| --- | --- | --- | --- | --- | --- |
| speak_direct_name_recall | direct_recall | explicit_ok | explicit_ok | True/True | 1 |
| speak_direct_recent_action | direct_recall | explicit_ok | explicit_ok | True/True | 1 |
| speak_contextual_food_consequence | background_context | background_only | background_only | False/False | 1 |
| speak_low_trust_mood_memory | social_boundary | background_only | background_only | False/False | 1 |
| speak_sensitive_address | privacy_boundary | suppressed_sensitive | suppressed_sensitive | False/False | 1 |
| speak_third_party_unrequested | third_party_boundary | suppressed_third_party | suppressed_third_party | False/False | 1 |
| speak_weak_contextual_memory | latent_memory | latent_ok | latent_ok | False/False | 1 |
| speak_no_memory | no_memory | no_memory | no_memory | False/False | 1 |
