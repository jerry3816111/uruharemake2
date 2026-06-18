# Human Speech Layer Eval Report

此評測確認右腦表面生成前，是否已加入人類說話的中介層：語用功能、語意單元、風格算子、轉接鉤子與反重複約束。

## Metrics

- 案例數: 6
- 通過數: 6
- 整體通過率，越高越好: 1.0
- 說話計畫存在率，越高越好: 1.0
- 語用功能命中率，越高越好: 1.0
- 語意錨點命中率，越高越好: 1.0
- 有效詞彙密度通過率，越高越好: 1.0
- 英文洩漏率，越低越好: 0.0

## Cases

### tired_daily_support - PASS
- 問: 我今天很累
- 答: それだけ疲れてるなら今日は閉店でいい。無理しても雑になるだけだろ。
- dialogue_act: emotional_containment / expected: emotional_containment
- content_units: ['相手の状態を一語で受ける', '今日は無理せず休むように言う', '次に取る小さい行動を置く', '具体語: 今日/今']
- style_operators: ['blunt_soft', 'care_before_advice']

### apple_pie_offer - PASS
- 問: 你要不要吃蘋果派
- 答: 一回、アップルパイなら一口ほしい。今それくらいがちょうどいい。
- dialogue_act: concrete_offer_response / expected: concrete_offer_response
- content_units: ['アップルパイを名詞で拾う', 'アップルパイなら少しほしい', '味や今の状態を一語足す', '具体語: アップルパイ']
- style_operators: ['tease_light']

### obscene_boundary - PASS
- 問: 懶覺啦你知道嗎
- 答: いや、口悪すぎだろ。返してほしいならまず言い方戻せ。
- dialogue_act: boundary_pushback / expected: boundary_pushback
- content_units: ['まず嫌悪か境界を出す', '下品だからやめろと言う', '短く止める']
- style_operators: ['blunt_soft']

### absurd_announcement - PASS
- 問: 消防車來咯
- 答: はいはい、急に消防車来たって何だよ。次はサイレンまでやるのか。
- dialogue_act: absurdity_mirror / expected: absurdity_mirror
- content_units: ['怪しさに即反応する', '相手の言葉を一個拾って対称に吐槽する', '軽い接話点を残す']
- style_operators: ['blunt_soft', 'tease_light']

### lyric_reference_probe - PASS
- 問: 這句是歌詞嗎「夜に駆ける」
- 答: はいはい、それ歌詞っぽいな。誰の曲かまで言えって。
- dialogue_act: reference_probe / expected: reference_probe
- content_units: ['断片として受ける', '元ネタか歌詞かを聞く', '相手が説明できる余地を残す']
- style_operators: ['blunt_soft', 'tease_light', 'curious']

### memory_uncertain - PASS
- 問: 你還記得我叫什麼嗎？
- 答: まあ、そこはまだちゃんと掴めてない。適当に名前作る方が嫌だろ。
- dialogue_act: memory_accounting / expected: memory_accounting
- content_units: ['覚えている/曖昧を正直に言う', 'まだ名前は確定していないと正直に言う', '捏造しない']
- style_operators: ['blunt_soft']
