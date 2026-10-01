# P3-B68 multiwindow future aggregate acceptance

日期：2026-09-20

## 結論

`POSITIVE SAME-SOURCE DEVELOPMENT PROXY / WEAK TOP-1 ACCURACY`。四個future windows是在B67八條prediction全部封存後，
才以一次private acquisition同時投影；B66的target、marker order、metrics與winner rule完全不變。

逐列winner為system `4`、baseline `0`、tie `0`。但這個4–0必須配合細節解讀：r0600與r1200兩組對actual label
給相同機率，只是system Brier稍低；兩組top-1都只有`1/4`。

## Aggregate

| metric | baseline literal | system pragmatic |
|---|---:|---:|
| mean actual-label probability ↑ | 0.2625 | 0.2875 |
| mean multiclass Brier ↓ | 1.17095 | 1.01340 |
| mean log loss ↓ | 9.82662 | 1.83949 |
| top-1 hits | 1/4 | 1/4 |

log loss差距很大，主要因r1800 baseline對actual proxy label `ask_clarification`給`0.00`，經事前floor形成
`34.5388`損失；system給`0.05`。它顯示baseline過度自信的風險，不代表system具有人類等價理解。

## 逐列

| row | proxy label | baseline p | system p | winner | top-1 hit (B/S) |
|---|---|---:|---:|---|---|
| r0600 | acknowledge_then_continue | 0.85 | 0.85 | system（Brier 0.0338 vs 0.0336） | true / true |
| r1200 | acknowledge_then_continue | 0.10 | 0.10 | system（Brier 1.38 vs 1.22） | false / false |
| r1800 | ask_clarification | 0.00 | 0.05 | system | false / false |
| r2400 | acknowledge_then_continue | 0.10 | 0.15 | system | false / false |

## 執行完整性

- prediction batch hash=`f51399ee1e226a7c92f1a547f9b6974577fdc8ab7efbf76d744baaa19a6dcb82`。
- future access=`4`、scores=`8`；prediction mutation/model/human/LLM judge/retry/fallback=`0`。
- private full caption `1,483,058 bytes`在public scoring前刪除；只發布四個future-only artifacts。
- scored result hash=`3593e9bf85a6efbfdf8c290864729708a7263807c3bea9ed3b88da6a73b10f6b`。

## Claim boundary與下一步

目前可以主張：在同一支公開影片的四個事前固定development windows，加入pragmatic state的同模型condition，在固定caption
keyword proxy上得到較好的機率校準；這是「值得繼續」的可重現訊號。不能主張獨立holdout、真人偏好、跨人物泛化、全面優於
強LLM、真正理解或人類方程式。

下一個必要gate不是再切同影片追分，而是凍結一個新的公開來源／影片與窗口，在不改B65介面和B66評分的前提下做source-level
replication；若跨來源結果不收斂，必須保留失敗並回頭檢查proxy validity。
