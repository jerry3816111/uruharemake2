# P3-B66 future-outcome scoring acceptance

日期：2026-09-20

## 結論

`POSITIVE ONE-ROW PROXY FOR SYSTEM / NEITHER CONDITION TOP-1 CORRECT`。B65 prediction pair以immutable hash綁定後，
B66才取得同一公開來源`3181.0..3241.0s`的日文automatic captions。依事前freeze，評分target是第一個cue起12秒內、
最多3個cues；實際是`3182.520..3190.559s`，proxy marker為`?`，因此actual proxy label是
`ask_clarification`。

這個label是固定規則從automatic captions得到的observable proxy，不是真人人評的語意ground truth。

## 公平結果

| condition | top-1 prediction | actual-label probability | selected hit | Brier ↓ | log loss ↓ | char-bigram Jaccard |
|---|---|---:|---|---:|---:|---:|
| baseline literal | accept_support_and_continue | 0.05 | false | 1.360 | 2.9957 | 0.0247 |
| system pragmatic state | acknowledge_then_continue | 0.10 | false | 1.235 | 2.3026 | 0.0294 |

依凍結的primary rule（actual-label probability較高）與secondary Brier，winner是`SYSTEM_PRAGMATIC_STATE`。system把真實
proxy label的機率從0.05提高到0.10，Brier與log loss也較低；但兩組top-1都不是`ask_clarification`，所以不能說system
「猜對了」。較準確的陳述是：這一列中，pragmatic condition對後來發生的可觀察問題行為保留了較多機率。

actual evidence excerpt（automatic caption，僅保存短片段）：

> ドリルを入れてみます。…これで壊せんのか。…壊せんの?

## 資料與執行證據

- B66 freeze前9項合成邊界測試、B65–B66 affected suite 21項通過。
- native caption download=`1`、return code=`0`、2.147527s；private full caption=`1,483,058 bytes`。
- private full caption與temporary runtime在public scoring前刪除；只發布23個`3182.520..3240.720s` future cues。
- fresh future-only reader=`1`、exit code=`0`；future access=`1`、scores=`2`。
- prediction mutation / model or judge call / retry / fallback / production write=`0`。
- frozen prediction result hash=`379e0cd852cb3101bc03b593928f2201324e2ee4dd358c749dc1ecba22906abe`。
- scored result hash=`9b2c51db62cff73dd24ea15b875d49eafab0fb727929ff3114657ad63873e754`。

## 能與不能證明

這是專案第一個「先封存真實預測、再揭盲公開未來」且system在凍結proxy metric勝出的完整temporal row。它支持繼續做
多列前瞻比較，不支持全面優勢：樣本只有1、同一支影片、automatic captions可能錯、keyword proxy可能錯，且system top-1也錯。
下一個必要階段是事前選定多個未讀窗口，先全部封存prediction，再一次揭盲aggregate；不能用這個已曝光row調marker、prompt或門檻。
