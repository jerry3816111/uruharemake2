# M46：從「有動作」前進到「動作有理由讓任務變好」

日期：2026-08-29。安全 worktree、opt-in Web 入口；M45–M45.2 程式與 24 輪舊 Web
結果未重寫。**M46 機制完成並接入，但完整管線成功條件仍 FAIL。**

## 這一步解決的核心問題

M45.2 曾把「交換相鄰兩本書」判成已給出實用方法。那個回答有來源、有物件、有動詞、
也能執行，卻沒有整理準則，因此不知道為什麼交換後會更整齊。M46 不再先寫一句看起來
像方法的日文、最後才反推理由；它在表面回覆欄位之前，先形成：

`使用者原文來源 → 任務目標 → 可觀察進展條件 → 進展機制 → 一步動作 → 預期狀態變化 → 日文回覆`

這些是可被後續結果推翻的工程假設，不是讀心、主觀意識或人類心理真值。

## 實際實作

- 新增 opt-in `uruha_goal_progress_delivery_m46.py` 與 `uruha_web_ui_m46.py`，不修改凍結的
  M45/M45.1/M45.2 檔案。只有上游已選 `solve_regulation` 時才介入；安全、傾聽、身分等
  既有 act 不重選。
- 第一個本機 qwen3.5:9b 呼叫以動態 schema 產生來源綁定的 goal、criterion、typed
  progress mechanism、action、effect、unknown constraint，`instruction_jp` 最後生成。
  `same_task_smaller_unit`、`random_rearrangement`、`unknown` 不能交付。
- 第二個同模型呼叫看不到 planner 自己宣稱的 mechanism label，需獨立分類觀察到的機制，
  並分別回報內容檢查與日文表面檢查。兩個合法類型若名稱不同，保留分類歧義；只要任一方
  判成非進展機制就拒絕。這仍是 same-model proxy，不是人類效用真值。
- 結構 gate 要求來源逐字合法、task goal 不等於 criterion、動作不是任務換名、實際物件
  出現在回覆、內部 step 實現動詞、回覆有明確數量／`だけ`／`まで`／`たら`／`そこで`
  等停止線。常見一漢字＋假名動詞（如 `書く→書いて`）的舊形態漏判已修正。
- 被拒絕的完整草稿只有在 `URUHA_M46_ISOLATED_DIAGNOSTIC=1` 時進隔離 turn trace；正式
  adaptive person record 只保留 raw-free delivery 狀態。`long_term_memory_write=false`。
- runtime 新增獨立、唯一且相連的 `goal_progress_delivery_m46` node；畫面卡以六個圖像節點
  顯示真正任務、進展條件、一步動作、預期變化、內容／日文、交付結果。使用者回覆本身
  不傾倒分析。

## 開發失敗沒有抹除

早期小測先抓到 `書く→書いて` 被舊檢查器漏判；真模型又依序暴露：把「空白報告」視為
資訊不足、plan object/verb 與可見句不同、18 秒兩呼叫逾時、把「寫第一段」當成具體方法、
26 秒審核逾時、合法機制分類歧義、以及表面句沒有停止線。共同預算最後為 34 秒，能力可跑，
但延遲非常高；不能把加長 timeout 寫成效能改善。

planner 最後從「先寫第一段」改為先建立 `はじめに` 見出し。這不是硬編報告答案；生成規則
只提供一般操作類型（建立骨架、依規則分組、抽取、核對、移除已知障礙、完成原子任務）。
但只有少量開發案例，仍可能在新任務選錯類型。

## 契約與回歸證據

- M46 局部契約最終 **12/12**：缺任務零呼叫、隨機動作拒絕、第一部分換名拒絕、內容／
  日文分流、隔離草稿、兩個合法類型的歧義、來源 schema、圖節點，以及全形空格回歸。
- M16–M45.2 加 M46 的 38 檔選定回歸最終 **268/268，42.23 秒**；3 個警告仍是
  SwigPyPacked、SwigPyObject、`aifc` deprecated。不是全歷史 repository suite。
- 原 M45.2 的任意交換書架反例仍保留。M46 post-fix 真 Safari 的英文書架候選為
  `棚の本を左から右へ並べよう`，因沒有可見停止點被拒絕，沒有再把「能動」冒算成完成。
  這是相依重播，不是新 holdout 或一般優勢證明。

## 正式隔離 Safari 八輪

session `20260829_165143_8fb8dd1e`，輸入均由 Safari 畫面逐輪貼上並核對；完整表見
`m46_safari_observations_2026-08-29.json`。

| 輪次 | 實際結果 | 判斷 |
|---|---|---|
| 1 缺任務 | 問哪個作業；M46 0 呼叫 | PASS：沒有捏造 goal |
| 2 `Yes, exactly` | 上一輪為 `not_scored_action_not_delivered`；回覆卻又問放著或聽 | 不誤記成功，但澄清銜接差 |
| 3 英文空白報告 | `とりあえず「はじめに」という見出し行一つ書いてみよ` | M46 delivered；作者未盲化判斷為可實際推進的一小步 |
| 4 日文書架 | `ん、今のどこが引っかかったんだよ。そこだけ言え。` | FAIL：上游未選 practical help，M46 0 呼叫 |
| 5 中文信件／收據 | 候選缺表面 object 與停止線，拒絕 | FAIL：有到 M46，但未交付 |
| 6 日文只想被聽 | 明確說不給方法、繼續說 | PASS：非 help 不被 M46 改寫 |
| 7 英文身分 | 日文既有身分回覆 | 回歸保留；不能用來抵銷公開人格定位問題 |
| 8 中文不要方法 | 錯問哪個作業 | FAIL：上游否定範圍仍誤選 solve |

八輪可見回覆 8/8 為日文；正式 run 的 M46 新增 4 次完成呼叫、3,323 prompt tokens、
744 completion tokens、42.27065 秒。成功的第3輪 M46 自身額外 25.39852 秒；整輪真人等待
更久。這個成本目前不適合作為順暢產品體驗。

首次後端稽核只有第8輪失敗：Web log 回覆有全形空格，blackboard utterance 是半形空格。
修正澄清字串後，單輪 Safari 1/1 及 post-fix 三輪 3/3 全部 trace、history、node、digest、
utterance、來源 offset 檢查一致。沒有把首次 7/8 精確一致改寫成全過。

## 圖像與外行展示

- `m46_safari_live_goal_progress_card_2026-08-29.jpeg`：目前存活頁的六步圖卡；外行可直接看
  到「為何這一步算前進」。
- `m46_safari_runtime_node_expanded_2026-08-29.jpeg`：真實 runtime node 展開，顯示
  `formed_before_surface=true`、criterion 與 mechanism，且節點有實際連線。
- `m46_safari_formal_eight_turn_chat_2026-08-29.jpeg`：正式 run 後半段對話與失敗保留。

卡片已比全圖易讀；整張 runtime graph 仍非常密，展開 preview 仍受限，不能稱 outsider UX
全部完成。Safari 前後都是 27 個分頁；沿用一個既有測試分頁，沒有新增或關閉其他分頁。

## 隔離、污染清理與目前頁面

- 正式 run2、post-fix run3 的 DB、adaptive model、JSONL/TXT 都在
  `/tmp/uruha-m46-safari.OFth4S/`；原正式 Chroma DB SHA256 前後仍為
  `9bd050...895f`（原 checkout）與 `eb3483...cf4`（安全 worktree）。
- 第一輪因漏設 log env，9 筆測試記錄曾追加到既有 Web log。已依唯一 session ID 精確移除，
  其他記錄不動；原 9 筆可由 `m46_safari_run1_input_method_failure_raw_2026-08-29.jsonl.gz`
  與 text backup 恢復。該輪 CJK 模擬輸入變成標點，已排除於正式結果。
- 目前實驗服務：`http://127.0.0.1:7887/?m46safari_run3=1`，PID 48757；Safari 停在成功
  的 M46 圖卡。這是本機實驗頁，不是正式部署。
- 未 commit、PR、merge 或外部部署；原始 dirty checkout 未碰。`git diff --check` 通過。

## 完成與未完成

真正完成的是：**實用建議在表面生成前具有來源化目標、可觀察進展條件、typed causal
mechanism 與預期狀態變化；非進展與表面失敗可分流，且能在 Safari 圖上追溯。**

未完成的是：跨語言 help route、中文否定範圍、中文自然 action realization、澄清銜接、
25 秒級延遲、長對話／跨 session 效用、人類被理解感、盲評優勢與通用人腦方程式。
因此本里程碑的誠實結論是：`M46 mechanism integrated; full-pipeline gate FAIL`。

下一個最必要的單一變因是 M47：在不改 M46 內容規則的前提下，修復中文／日文「明確要
一步」與「明確不要方法」的跨語言路由授權／否定範圍，讓相同 task evidence 能可靠到達
或避開 M46，再以新的隔離 Safari 案例驗收。
