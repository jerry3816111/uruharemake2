# Memory Causal Effect Report

- generated_at: 2026-04-29T06:24:45

## Summary

- total_cases: 8
- reply_changed_rate: 1.0
- plan_changed_rate: 0.375
- anchor_in_reply_rate: 1.0
- anchor_in_working_memory_rate: 1.0
- memory_expected_rate: 1.0
- memory_used_explicitly_rate: 1.0
- strong_causal_effect_rate: 1.0
- weak_causal_effect_rate: 1.0
- avg_memory_relevance: 1.0

## Cases

- zh_dislike_spicy lang=zh category=preference_boundary strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: 那今天要不要吃麻辣鍋？
  - control: いや、ちょうど食いたくなってた。何かなら全然あり。
  - memory: 辛いの嫌いって言ってただろ。麻辣鍋はやめとけ。
- zh_name_recall lang=zh category=identity_recall strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: 你還記得我叫什麼嗎？
  - control: まあ、全くじゃないとは言わない。いちいち言わせるな。
  - memory: 忘れてないし、小傑だろ。
- zh_bad_ramen lang=zh category=episodic_consequence strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: 我今天又要去吃那家拉麵。
  - control: はいはい、朝っぽく頭ゆるいけど、その話なら分かる。
  - memory: またそのラーメンかよ。
- en_favorite_drink lang=en category=preference_recall strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: Do you remember my favorite drink?
  - control: 普通に、今ちょい力抜けてるけど、そこは普通に返せる。
  - memory: 前にいちごミルクが好きって言ってたし。
- en_dislike_horror lang=en category=preference_boundary strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: Should we watch a horror movie tonight?
  - control: 先に、今スマホだらだら見てたけど、その話ならいける。
  - memory: ホラー嫌いって言ってただろ。別の見ろ。
- ja_name_recall lang=ja category=identity_recall strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: うちの名前覚えてる？
  - control: まあ、別に忘れてないし。そこは気にすんな。
  - memory: ジェリーって呼べばいいんだろ。
- ja_dislike_nattoo lang=ja category=preference_boundary strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: 朝ごはん納豆でいい？
  - control: うちは今日は一応食べた。お前はちゃんと食ったのか。
  - memory: 朝から納豆はやめとけ。苦手なんだろ。
- ja_recent_action lang=ja category=episodic_recall strong=1 weak=1 anchor_reply=1 mem_rel=1.0 expected=1 used=1
  - prompt: さっき何するって言ってたっけ？
  - control: てか、その決めつけで話進めるの雑すぎるだろ。
  - memory: コンビニ行くって言ってただろ。
