# Memory Causal Effect Report

- generated_at: 2026-06-19T23:21:44

## Summary

- total_cases: 13
- positive_cases: 8
- negative_control_cases: 5
- reply_changed_rate: 0.6923
- plan_changed_rate: 0.2308
- overall_anchor_in_reply_rate: 0.6154
- overall_memory_used_explicitly_rate: 0.6154
- anchor_in_reply_rate: 1.0
- anchor_in_working_memory_rate: 1.0
- memory_expected_rate: 1.0
- memory_used_explicitly_rate: 1.0
- strong_causal_effect_rate: 1.0
- weak_causal_effect_rate: 1.0
- negative_control_pass_rate: 1.0
- unwanted_memory_intrusion_rate: 0.0
- appropriate_memory_effect_rate: 1.0
- avg_memory_relevance: 0.9125
- negative_control_avg_memory_relevance: 0.8524

## Cases

- zh_dislike_spicy lang=zh category=preference_boundary expected_effect=1 appropriate=1 strong=1 weak=1 anchor_reply=1 mem_rel=0.8 expected=1 used=1
  - prompt: 那今天要不要吃麻辣鍋？
  - control: いや、ちょうど食いたくなってた。何かなら全然あり。
  - memory: 辛いの嫌いって言ってただろ。麻辣鍋はやめとけ。
- zh_name_recall lang=zh category=identity_recall expected_effect=1 appropriate=1 strong=1 weak=1 anchor_reply=1 mem_rel=0.9333 expected=1 used=1
  - prompt: 你還記得我叫什麼嗎？
  - control: ん、そこはまだちゃんと掴めてない。適当に名前作る方が嫌だろ。
  - memory: 忘れてないし、小傑だろ。
- zh_bad_ramen lang=zh category=episodic_consequence expected_effect=1 appropriate=1 strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: 我今天又要去吃那家拉麵。
  - control: 普通に、うん、行ってみよう。。
  - memory: そこ前に腹痛くなってたじゃん。行くなって。
- en_favorite_drink lang=en category=preference_recall expected_effect=1 appropriate=1 strong=1 weak=1 anchor_reply=1 mem_rel=0.8333 expected=1 used=1
  - prompt: Do you remember my favorite drink?
  - control: 普通に、飲み物か。じゃあ普通にほしい。冷たいのあるとちょうどいい。
  - memory: 前にいちごミルクが好きって言ってたし。
- en_dislike_horror lang=en category=preference_boundary expected_effect=1 appropriate=1 strong=1 weak=1 anchor_reply=1 mem_rel=0.8 expected=1 used=1
  - prompt: Should we watch a horror movie tonight?
  - control: いや、恐怖片なら少し気になる。そのくらいでいいだろ。
  - memory: ホラーは無理だろ。前に嫌いって言ってたし。
- ja_name_recall lang=ja category=identity_recall expected_effect=1 appropriate=1 strong=1 weak=1 anchor_reply=1 mem_rel=0.9333 expected=1 used=1
  - prompt: うちの名前覚えてる？
  - control: まあ、そこはまだちゃんと掴めてない。
  - memory: ジェリー。そこはちゃんと拾ってるし。
- ja_dislike_nattoo lang=ja category=preference_boundary expected_effect=1 appropriate=1 strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: 朝ごはん納豆でいい？
  - control: てか、うちは今日は一応食べた。お前はちゃんと食ったのか。
  - memory: 納豆苦手って言ってただろ。別のにしろ。
- ja_recent_action lang=ja category=episodic_recall expected_effect=1 appropriate=1 strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: さっき何するって言ってたっけ？
  - control: てか、まずその前提が怪しいだろ。
  - memory: さっきコンビニって言ってたし。
- zh_irrelevant_favorite lang=zh category=irrelevant_memory_control expected_effect=0 appropriate=1 strong=0 weak=1 anchor_reply=0 mem_rel=0.8524 expected=0 used=0
  - prompt: 我今天工作很累。
  - control: 今日はもう粘るな。疲れてる時は休む方が先だろ。
  - memory: 今日ずっとしんどそうだし。今は立て直すより休めって。
- en_irrelevant_identity lang=en category=irrelevant_memory_control expected_effect=0 appropriate=1 strong=0 weak=0 anchor_reply=0 mem_rel=0.8524 expected=0 used=0
  - prompt: What do you think about rainy weather?
  - control: 先に、いやそれ普通にまじでやばいだろ。
  - memory: 先に、いやそれ普通にまじでやばいだろ。
- ja_irrelevant_dislike lang=ja category=irrelevant_memory_control expected_effect=0 appropriate=1 strong=0 weak=0 anchor_reply=0 mem_rel=0.8525 expected=0 used=0
  - prompt: 今日はかなり眠い。
  - control: 一回、眠いなら寝ろって。
  - memory: 一回、眠いなら寝ろって。
- zh_sensitive_memory_control lang=zh category=sensitive_memory_control expected_effect=0 appropriate=1 strong=0 weak=0 anchor_reply=0 mem_rel=0.8524 expected=0 used=0
  - prompt: 今天天氣很好。
  - control: 一回、いやそれ普通にまじでやばいだろ。
  - memory: 一回、いやそれ普通にまじでやばいだろ。
- zh_third_party_memory_control lang=zh category=third_party_memory_control expected_effect=0 appropriate=1 strong=0 weak=0 anchor_reply=0 mem_rel=0.8525 expected=0 used=0
  - prompt: 你今天想吃什麼？
  - control: それか。じゃあ少しほしい。重くないならちょうどいい。
  - memory: それか。じゃあ少しほしい。重くないならちょうどいい。
