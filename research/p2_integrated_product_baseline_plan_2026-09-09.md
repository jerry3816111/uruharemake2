# P2 integrated product baseline：收斂計畫

日期：2026-09-09
狀態：不新增產品機制；只對目前共同安裝的 P1/P2 adapters 做整批 gate 與版本凍結。

## 為什麼需要這一步

前四個 P2 修正各自有 before/after，但它們都包在同一個產品入口。若直接進 P3，比較時無法區分「某個修正單獨通過」
與「目前整體版本真的同時保留全部行為」。因此先以最新九輪本機控制作 integrated gate，再把 product source、run JSON、
graph HTML 與成本帳本的 digest 凍結為 P3 system baseline。

## 唯一驗收變因

不改任何回答、route、prompt、模型、temperature、token budget、memory、graph 或正式研究檔案。只判讀已完成的
`analysis/p2_speaker_attribution_recall_local_run2_2026-09-09.json`／HTML，並保存不可混淆的 baseline manifest。

## Gate

1. repeated refusal：第二次婉拒保留低干預模型 core，沒有新 pending，圖有 arbitration 節點。
2. current help request：中文當輪求助取得 `solve_regulation`，不被前輪 listening 蓋掉，圖有 current-request 與 task handoff。
3. explicit space：修正後尊重獨處，沒有把錯誤二選一保存為 pending，圖有 explicit-space authority。
4. speaker-qualified recall：已選 episode 的 user role 接到自然日文回答，走 deterministic factual/memory route，圖有 source node。
5. no-context deixis：`那個。` 沒有可辨識指稱時只做低壓追問，不保存臆測；這是 bounded abstention，不是理解成功。
6. 全局：5 sessions／9 turns、持久化與 calibration checks 4/4、正式 DB/holdout/human rating 未使用、graph HTML 與 JSON
   對應、OpenAI-compatible call ledger 不含 raw prompt/reply。

任一項失敗只定位第一個交互作用，不新增第二個回答規則。全部通過時只能稱「P2 bounded product baseline frozen」，
不能稱 open-world P2、長對話理解、人類偏好、正式優勢或人類方程式完成。

## P3 交接條件

P3 必須以 manifest 所列 product commit 與 artifact digest 為 system side；baseline side 使用相同 qwen2.5:7b、同輸入、
同 persona surface 條件與可稽核 token budget。開發案例不得改名 holdout；正式比較前先凍結 measurement、失敗條件與新資料來源。
