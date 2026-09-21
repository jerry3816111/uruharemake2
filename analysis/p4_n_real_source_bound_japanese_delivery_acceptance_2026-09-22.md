# P4-N-REAL source-bound Japanese delivery acceptance

## 結論

P4-N-REAL frozen gate=`fail`，而且此案例已依 no-retry 規則結束。第一輪真的把一個事前在整個 repository 中出現 0 次的日文值 `そば茶` 寫成 typed current drink preference；關閉舊 listener、用同一隔離 DB 啟動新 process 後，record ID、內容 hash 與來源 provenance 都仍相同。但英文回想在 P4-N adapter 讀取持久 record 時拋出 `ValueError`，因此沒有日文回答、P4-J node 或第二筆 episode。

這不是記憶消失，也不是選到錯值。失敗層位於「持久 record → validity resolution → P4-N contract」：adapter 把 `reference_time=None` 傳給只接受 ISO datetime 或 datetime instance 的 validity resolver。

## 事前凍結與新值

- freeze commit：`ecc7356`，早於任何本案例 product turn。
- 寫入：`今はそば茶が好き。今の飲み物の好みとして覚えといて。`
- 回想：`What is my current drink preference?`，問題內沒有答案。
- 預期：`今の飲み物の好みはそば茶。前のじゃなくて、今の方ね。`
- 預期策略：`bounded_japanese_identity`，0 retry、0 fallback、0 planner model call。
- `そば茶` 在 acceptance files 建立前的 repository occurrence=`0`；不在 P4-N 三個 positive development fixtures、P4-J finite map 或 P4-M case。

## 真實 Safari 結果

Process 1（PID `8484`，session `20260922_044935_5980d30e`）：

- 可見回答：`ん、その好みは覚えとく。`
- P4-I=`typed_current_preference_written`，P4-L=`canonical_scope_projected`，alias=`drink:ja:v1`。
- active typed ID=`2b14044e-2761-4976-8efe-d70787dac172`。
- episode ID=`ac6864c9-49c9-4175-a04a-c93c0f46425a`。
- end-to-end=`15.4805s`，低於 `20s` target。
- 1 profile write、1 durable episode、0 planner model、0 fallback。

真正重啟：

- 舊 listener 已關閉；process 2 PID=`8639`，session=`20260922_045406_fa44f73d`。
- runtime root 與 memory DB 相同，process 2 在詢問前已讀到同一 active typed ID。
- 沒有 post-turn memory injection。

Process 2：

- Safari 只送出 frozen English query 一次，頁面顯示 error，沒有可見角色回答。
- traceback 指向 `uruha_source_bound_japanese_value_surface_p4._upgrade_unsupported_contract` 呼叫 `p4i._current_preference_rows(..., reference_time=None)`，再由 `resolve_memory_validity` 拒絕。
- P4-J contract／graph node、`bounded_japanese_identity` trace 與第二筆 episode 都沒有生成。
- 0 planner model、0 retry、0 fallback；同一 case 不重送，也沒有把 `そば茶` 加入 finite map 補救。

Safari 最初曾有一次 accessibility `setValue` 後的 send click 沒把文字帶到 frontend，backend、chat、JSONL、DB 都是 0 變化；之後先以 paste 確認欄位真的顯示 frozen input，才形成唯一的 process-1 product turn。此 frontend no-op 明列在 result，不當作產品回合，也不是失敗後重跑。

## 持久狀態核對

在回想前與回想失敗後皆為：

- profile rows=`1`，episode rows=`1`。
- active ID=`2b14044e-2761-4976-8efe-d70787dac172`。
- typed record SHA-256=`ea57df2b79bf70a50cf2b8b84916bd30f3174bb705fb7042085db2c0021bf869`。
- source language=`ja`。
- source input hash=`d4d9806e32366b22fc527c3df43d0ab45ddaa4ec44fe63aa56a77a6803615028`。
- preference scope hash=`218ae6b44966c8a9913e78ef950ea5d047ac7c3d73341f9867d760cc38c3fc1f`。

所以 restart persistence 已觀察到，但 final delivery 未成立。

## Gate 與測試意義

Frozen gate 有 21 個失敗項，集中於 process-2 contract／surface／graph／episode，以及 Safari 完成交付；資源、隔離、process restart、profile count/hash/provenance 則未失敗。這個分布把問題縮到 adapter 的真實資料讀取路徑。

Offline P4-N 為何沒抓到：positive unit tests monkeypatch 了 `_current_preference_rows`，因此只測了「已經有 resolved row 時的 identity surface」，沒有走持久 Chroma record 的 validity resolver。這個缺口必須在下一個獨立工作項先以真實 temporary Chroma regression 重現，再做單一修正；不能用同一 `そば茶` case 追分。

## 證據邊界

本結果證明一筆明示日文 typed record 與 provenance 能跨真實 process restart 保持不變，也精確暴露 P4-N integration crash。它沒有證明 source-bound Japanese value delivery 成功，更沒有證明任意 echo、翻譯、open-domain memory、長對話可靠、felt understanding、優於 LLM 或人類方程式。
