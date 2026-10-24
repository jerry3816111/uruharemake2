# P3-B69B source2 multiwindow prediction acceptance

日期：2026-09-20

## 結論

`TERMINAL INCOMPLETE BATCH / 7 MODEL CALLS / FUTURES LOCKED`。第二公開來源`Mlk5e3hBnb8`的context-only
取得與隔離成功，但原樣重用的B65預測介面沒有完成8條prediction，因此B69B不是跨來源效果證據，B69C不得揭盲。

## 實際證據

- yt-dlp唯一一次下載成功（`1.732784s`）；private full caption為`1,542,085 bytes`，投影四段context後刪除。
- fresh reader只看到四段context；cue counts=`69/66/77/55`，future content returned=`false`。
- qwen3.5:9b完成7次provider call；prompt/completion tokens合計=`15,429/1,650`，model latency=`133.887876s`。
- 前六call涵蓋前三列paired conditions；第七call是`s2r2400 / BASELINE_LITERAL`，provider已回傳，但B65 parser以
  `prediction/schema`拒絕。raw response依事前規則未保存，只保留hash，所以不能事後斷言是哪一個schema子欄位失敗。
- 第八個`SYSTEM_PRAGMATIC_STATE` call未執行；retry/fallback=`0/0`。
- prediction-side future access / outcome score / training / formal M56 / production write=`0/0/0/0/0`。

## 能與不能主張的內容

這證明第二來源的公開字幕可以安全投影為四個context artifacts，也證明目前介面在跨來源完整批次的可靠性不足：
事前要求8/8，實際只有7 calls且沒有完整prediction batch。不能以六個已完成prediction、第一來源的正結果，或這次未揭盲資料
推算勝負；更不能宣稱系統優於baseline。B69B已terminal，禁止在同一來源／row重跑、調prompt或放寬gate。

## 下一個必要設計審查

下一步不是B69C，而是建立新的、資料不重疊的prediction-interface reliability gate：先把schema失敗原因做成不含原文的
allowlisted可觀察分類，並在已曝光開發fixture上證明每個condition能一次完成。之後必須另選、另凍結未讀內容的新來源，才可測
修正版；B69第二來源保留為未完成反例，不得補跑追分。
