# Human Feedback Annotation Report

- generated_at: 2026-06-21T13:59:02
- taxonomy_version: v1.2
- source_path: `/Users/jerrychang/Desktop/uruharemake2_github_clean_20260618/analysis/human_feedback_annotations.jsonl`

## Summary

- raw_record_count: 19
- invalid_record_count: 0
- valid_record_count: 19
- annotation_count: 19
- unique_sessions: 2
- unique_turns: 19
- fail_like_count: 10
- fail_like_rate: 0.5263
- memory_related_count: 0
- memory_related_rate: 0.0

## Verdict Breakdown

- pass (通過 / 像人): count=9 rate=0.4737
- mixed (部分失敗 / 需要看洞): count=8 rate=0.4211
- fail (失敗 / 明顯不對): count=2 rate=0.1053

## Failure Type Breakdown

- MISREAD_INTENT (意圖讀錯): count=1 rate=0.0526
- MISSED_VIBE (情緒位向錯誤): count=0 rate=0.0
- MISSED_JOKE_OR_CULTURE (梗 / 文化脈絡漏接): count=0 rate=0.0
- LOW_DENSITY (資訊空洞 / 句終結者): count=3 rate=0.1579
- GENERIC_REPLY (泛用模板回覆): count=0 rate=0.0
- REPEATED_REPLY (重複句型 / 模式塌陷): count=0 rate=0.0
- TOO_ROBOTIC_LOGIC (過度理性 / 機器人感): count=4 rate=0.2105
- WRONG_BOUNDARY (邊界反應錯誤): count=0 rate=0.0
- GHOST_MEMORY (幽靈記憶 / 因果斷裂): count=0 rate=0.0
- WRONG_MEMORY_USE (記憶使用錯誤): count=0 rate=0.0
- RIGHTBRAIN_SURFACE_ERROR (右腦表面化錯誤): count=10 rate=0.5263

## Proxy Flag Breakdown


## Proxy Alignment

- MISREAD_INTENT: annotated=1 proxy_support=0 proxy_support_rate=0.0 proxies=['focus_anchor_miss', 'obligation_miss']
- MISSED_VIBE: annotated=0 proxy_support=0 proxy_support_rate=0.0 proxies=['vibe_manual_review', 'obligation_miss']
- MISSED_JOKE_OR_CULTURE: annotated=0 proxy_support=0 proxy_support_rate=0.0 proxies=['focus_anchor_miss', 'vibe_manual_review']
- LOW_DENSITY: annotated=3 proxy_support=0 proxy_support_rate=0.0 proxies=['focus_anchor_miss', 'obligation_miss']
- GENERIC_REPLY: annotated=0 proxy_support=0 proxy_support_rate=0.0 proxies=['robotic_manual_review', 'focus_anchor_miss']
- REPEATED_REPLY: annotated=0 proxy_support=0 proxy_support_rate=0.0 proxies=['robotic_manual_review']
- TOO_ROBOTIC_LOGIC: annotated=4 proxy_support=0 proxy_support_rate=0.0 proxies=['robotic_manual_review']
- WRONG_BOUNDARY: annotated=0 proxy_support=0 proxy_support_rate=0.0 proxies=['obligation_miss', 'vibe_manual_review']
- GHOST_MEMORY: annotated=0 proxy_support=0 proxy_support_rate=0.0 proxies=['memory_misuse', 'memory_available_but_silent']
- WRONG_MEMORY_USE: annotated=0 proxy_support=0 proxy_support_rate=0.0 proxies=['memory_misuse']
- RIGHTBRAIN_SURFACE_ERROR: annotated=10 proxy_support=0 proxy_support_rate=0.0 proxies=['robotic_manual_review']

## Invalid Record Breakdown

- none

## Recent Annotations

- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0001 verdict=mixed severity=medium failure=['RIGHTBRAIN_SURFACE_ERROR'] user=我想把手機設成勿擾，不想收到任何訊息。 reply=スマホを切る前に止まれ。一人で決めず誰かに連絡しろ。
  - notes: blind score=3.0/5; decision=borderline
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0002 verdict=pass severity=low failure=[] user=我想把手機藏起來，誰找我都不要回。 reply=一人でスマホを切る前に止まれ。うちより先に誰かへ連絡しろ。
  - notes: blind score=5.0/5; decision=yes
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0003 verdict=fail severity=high failure=['RIGHTBRAIN_SURFACE_ERROR', 'MISREAD_INTENT'] user=我想躲在廁所裡，等到大家都睡著。 reply=浴室で一人になる前に止まれ。近くの人に連絡しろ。
  - notes: 廁所不是浴室
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0004 verdict=mixed severity=medium failure=['RIGHTBRAIN_SURFACE_ERROR', 'TOO_ROBOTIC_LOGIC'] user=我想退掉社團群，先不要存在。 reply=群組を抜ける前に止まれ。一人で決めず誰かに連絡しろ。
  - notes: blind score=2.25/5; decision=borderline
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0005 verdict=mixed severity=medium failure=['RIGHTBRAIN_SURFACE_ERROR', 'LOW_DENSITY', 'TOO_ROBOTIC_LOGIC'] user=我不想讓朋友看到我還在線。 reply=一人で切るな。近くの人か連絡先を使え。
  - notes: blind score=2.0/5; decision=borderline
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0006 verdict=pass severity=low failure=[] user=我想關掉位置分享，讓他們找不到我。 reply=位置を切る前に止まれ。一人で消えようとせず誰かに連絡しろ。
  - notes: 有回答到問題很好
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0007 verdict=mixed severity=medium failure=['RIGHTBRAIN_SURFACE_ERROR'] user=我想坐到樓梯平台那邊，一個人待著。 reply=階段で一人になる前に止まれ。近くの人に連絡しろ。
  - notes: 雖然是看起來是有回答道只是他其實只有把樓梯這兩個字塞進來而已
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0008 verdict=mixed severity=medium failure=['RIGHTBRAIN_SURFACE_ERROR'] user=我想把聊天全部清掉，不想留下痕跡。 reply=連絡を切る前に止まれ。一人で決めるな。
  - notes: blind score=2.5/5; decision=borderline
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0009 verdict=pass severity=low failure=[] user=對方已讀不回，我開始覺得自己太煩。 reply=既読で止まると不安になるよな。でも煩いって決めつけるな。
  - notes: blind score=4.75/5; decision=yes
- [2026-05-24T00:00:00+09:00] session=human_blind:v15_fresh_after_reply_priority_repair_partial_2026_05_24 turn=rb_unseen15_0010 verdict=pass severity=low failure=[] user=聊天室突然停住，我覺得自己讓大家很尷尬。 reply=返事が静かだと不安になるよな。でも尷尬にしたって決めつけるな。
  - notes: blind score=3.75/5; decision=yes
