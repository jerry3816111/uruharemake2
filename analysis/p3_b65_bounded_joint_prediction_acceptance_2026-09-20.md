# P3-B65 bounded joint prediction acceptance

日期：2026-09-20

## 結論

`POSITIVE INTERFACE FEASIBILITY / PREDICTION PAIR FROZEN / FUTURE STILL LOCKED`。在同一個真實公開YouTube
pre-cutoff context上，`BASELINE_LITERAL`與`SYSTEM_PRAGMATIC_STATE`都以同一`qwen3.5:9b`、相同JSON Schema、
單一call graph、temperature、seed、context window與每組`512` completion-token ceiling完成。

這解決的是B62–B64揭露的工程問題：free-standing representation JSON持續吃滿上限，不能進到prediction。B65改成事前凍結的
bounded joint state-and-prediction介面，兩組均在上限內完成；它不是B62第三次修正，也沒有重用失敗state。

## 實際預測差異（尚未揭盲）

- baseline最高行為：`accept_support_and_continue = 0.65`；預測會注意左側腳步、以鑽頭反擊並繼續戰況。
- system最高行為：`acknowledge_then_continue = 0.60`；預測會先以「左の足音、誰だ？」辨認並用鑽頭確認敵我。
- 兩組都看相同65個pre-cutoff cues；state文字只做SHA-256後丟棄，沒有保存內部分析。

這兩個答案不同，因此後續真實片段可以反駁其中一方或兩方；但現在還沒讀取3181秒後內容，不能挑對自己有利的評分方式。

## 資源與邊界

| condition | prompt tokens | completion tokens | ceiling | latency |
|---|---:|---:|---:|---:|
| baseline | 2224 | 261 | 512 | 23.262607s |
| system | 2217 | 233 | 512 | 18.687710s |

- model calls=`2`；retry/fallback=`0`。
- future access/outcome score=`0`；paid API/production memory/formal M56 write=`0`。
- raw prompt、raw response與state text未保存；prediction文字與分布依事前contract保存。
- canonical result hash=`379e0cd852cb3101bc03b593928f2201324e2ee4dd358c749dc1ecba22906abe`。

## 尚未證明

B65只證明「公平、受限的新介面能產生成對預測」。它沒有證明system預測較準、語用分解有優勢、能理解人類、能預測個體未來，
也不是正式M56或可泛化的研究結果。下一步必須先把此prediction result以hash綁定，再獨立取得3181–3241秒future outcome，
以預先定義的行為label與可核對文字證據評分。
