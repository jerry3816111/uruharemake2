# P4-D-G 新隔離 Safari：D 權限圖表投影結果

日期：2026-10-23。這是對 `research/p4_current_decision_graph_authority_projection_design_2026-10-23.md` 的單變因產品驗收。設計／題本 `8c17b68`、產品／零模型證據 `9261ed8` 都在 Safari 送題前推到 PR #435 並核遠端 exact head。D0–D10 舊題沒有重跑或改判。

## 判定

**狹義 D 圖表權限投影符合凍結的零模型及新真 Safari 觀察：2/2 當輪、2/2 reload 的 D 與 selected-plan signal 正確；但整體「給旁觀者清楚展示」仍未通過。** 原生畫面是大量密集節點，D 卡的小框標籤仍被截斷，需點開或讀 AX 才明白；Safari screenshot/AX 僅在工具內目視，未能落成持久 PNG/AX artifact；全管線 token ledger 也仍缺。這些未達不可被 2/2 訊號代替。D 首批 D2 自然度、D5 衝突值等 strict FAIL 保留，不能把新 D-G 結果回填成 D 整批 PASS。

## 隔離與執行

- 新 controller-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-w2l5c6o1`。官方 ONNX 83,178,821 bytes／SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 的私有 0600 複本，inode `48805504` 與主機 `4160298` 不同；封住 Chroma download entrypoint 的 fresh HOME/TMPDIR 預熱產生 1×384 有限向量，觀察下載呼叫 0（不聲稱 OS 層完全斷網）。
- Zero-turn 首啟 run `b6b796694b99592a`／PID 88049：同 PID 7894 HTTP ready，兩個隔離 DB embeddings 0、stderr 無 download/error；planned stop，原 PID 退出與 port vacant。產品重啟 run `1e38de2ff37c8b59`／PID 88414 同 PID ready。T0 profile/episode 均 0。
- 原生 Safari **只新開 1 tab**，53→52 tabs 收尾。實際 session `20261023_013453_8090f27b`，凍結 `dg0`、`dg1` 各送一次／0 retry；中途 reload `dg0` 一次、最後 reload `dg1` 一次，均還原當輪圖。reload 後側欄一度顯示啟動時 session ID，但下次送出及私有 raw 記錄仍為同一實際 session；沒有據此宣稱一般跨瀏覽器 session 正確。服務 exact planned stop（PID 88414 exited、7894 vacant），只關本次分頁；私有 root 留存未刪。

## 逐輪可見結果與獨立核對

| 題 | User 來源摘要 | Safari 日文泡泡 | Safari 原生圖 signal | 私有 raw/DB | 等待 |
| --- | --- | --- | --- | --- | ---: |
| dg0 | 本人說 2081-06-14 地圖箱交接地點為銀色資料室西窗 | `そっちが2081年6月14日に木製の地図箱を受け取る場所を銀の資料室の西窓に決めたんだな。` | `使用者本人決定｜來源與回覆核對`；`已選：當輪決定承接（D）`，reload 仍在 | D cert `ordinary_decision_reported`、terminal match；泡泡＝raw＝guard＝utterance；T1 episode 1、profile 0 | 17.0986 s |
| dg1 | 明示訂正同一地點為綠色溫室東口 | `訂正ね。そっちが2081年6月14日に木製の地図箱を受け取る場所を緑の温室の東口に決めたって話な。` | `使用者本人訂正｜來源與回覆核對`；`已選：當輪訂正承接（D）`，reload 仍在 | D cert `correction_reported`、`correction_supersession=unresolved`，不宣稱舊事實已撤銷；泡泡＝raw＝guard＝utterance；T2 episode 2、profile 0 | 11.4951 s |

兩輪均在 frozen ≤20 秒門檻內，均值 14.29685 秒。獨立 SQLite 查 `session_db` 的 `chroma:document`：dg0 與 dg1 的各自來源地點＋回覆各 1 筆；T0/T1/T2 episode 0→1→2，user_profile 0→0→0，其他 collections 0。零模型契約 2/2 合成正例、13/13 凍結負控與新增低路由／guard/history 等負控、178/178 受影響回歸通過；歷史 P4-AB 固定舊 SHA 測試 3 pass/1 pre-existing stale fail，詳見 zero-model 報告。

私有 raw log `web_logs/conversation.jsonl` 2 行／3,434,242 bytes／SHA `09b02eb9302c116201bd5d4007a1c7c2bb3a640a8033c86c7ae07ee5dddcf51d`。產品 stderr 無 download/traceback/error；raw 裡有 latency，但沒有完整 prompt/completion token ledger。完整認知 trace 含 source 原文，只在 0700 私有 root，未加入 Git。

## 證據界線與下一步

同一合成來源的**零模型** before/after graph 比較中，只變兩個 signal，node/edge/detail/trace_id/budget 不變；Safari 是**不同於 D0–D10 的新來源真輪次**，支持產品上確實可見且 reload 可還原，不能拿舊 D 題的 4/4 與新題的 2/2 當嚴格同題 A/B。來源由開發者寫並已進契約測試，**不是 blind holdout**。無持久原生視覺、人評或同模型 baseline，不能宣稱旁觀者「一眼懂」、比強 LLM 更會理解人、或人腦方程式已成立。

下一個必要交付與本次分因：圖像展示需另設單變因可讀性／截圖保存 gate（不能靠替換 signal 宣稱解決），D2 日文自然度與 D5 互斥值是獨立可見回覆缺口，完整 token 成本是獨立測量缺口。先選阻擋產品展示的最高價值一項，保留 D-G 狹義效果與總 FAIL，不重播本批題追分。正式同模型公平比較、人評、temporal holdout、VRM/Function Calling 統一驗收及長期 Goal 仍 pending。
