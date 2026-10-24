# P4 f7d：雙 root 真 Safari 入場通過，來源事件回覆 strict FAIL

日期：2026-10-24。事前題、visible gold、雙 root 協定及四 SHA 已在 `8f65c08` 凍結推 PR #435；產品 f7 程式不變。**整體 strict FAIL**：本次克服了 f7c 的跨進程 journal 入場問題，但真實回覆把「自己種下香草苗」說成「播種」，沒有達到事前可見語義 gold。不得把 protocol PASS、自然日文字元或 60/60 零模型機制契約寫成產品品質 PASS。

## 可見的實際一輪

| 來源 | 真 Safari 最終泡泡 | 事前判定 |
|---|---|---|
| `初めて自分でハーブの苗を植えた。今は一言だけ励まして。` | `種をまいただけでもすごい！そのくらいでいいだろ。` | **FAIL**：`苗を植えた` 被改成 `種をまいた`，也沒承接 `初めて自分で`；日文短句本身不等於來源忠實。 |

原生 Safari 在 7937 的新 tab 上 1 次 Send／0 retry；AX 直接看到同 session `20261024_124228_755cec94` 的 User、最終泡泡及下方 runtime graph。圖的 `source_event_core_utility_p4` 節點展開顯示 `eligible=true/status=no_grounded_candidate`，`UTTERANCE` 節點與泡泡同句；原生畫面上可見節點與箭頭。**未能落盤 Safari PNG/AX 原件**，所以 saved-visual/full graph gate 不稱通過；私有 JSONL/圖內容不能代替圖像原件。只關本次新 tab，Safari 53→52，其他舊頁未關。

## 入場、持久化與成本

- 兩個不同 controller-owned 0700 roots，A `uruha-product-spy1v1m0`、B `uruha-product-oq92tck4`，各自 private ONNX copy（官方 SHA `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`）及 1×384 離線 warm／0 download；正確 product venv、同一 port 7937、同一 f7 child flags。A PID77445 初次 `verify-ready` 在 listener 建立前回 `product_listener_not_same_pid`，同 PID 啟動完成後再讀取得 HTTP 200、Brain ready；2 完整 background pairs（0 model/token/write），exact planned stop、port vacant。B 為**新** root，PID77818 僅啟動一次；same-PID HTTP ready、Brain ready、private `memory_db` available，未重啟或重送題。B T0 snapshot 記 `reset0/tick0/finish0`；同時間另作只讀檢查得 Chroma 0 embeddings、profile 0 learned/scoped atoms、Web log 0 行，後三者不是單靠 T0 snapshot schema 可重建。
- B T0→Tpre 同 session/PID、reset0/finish0，**持久 Chroma SQLite** SHA 同為 `772783bb32ea667f832f4bfca5d229ca49d24258d6c95b441ac247592b678ad8`；這不代表整個記憶狀態未變，背景的 in-memory `memory_sha/runtime_sha` 有變，journal 亦記 `memory_diff_nonempty=true`。背景 tick 0→4，Tpre 前 11 組完整背景 pair：4 completed passive-decay、7 idle-noop、20 vector ops、0 model token／reported write。Tpre snapshot end→human arrival **2.755442625s**，前一 pair end→arrival **2.960548s**，中間 **0** background interleave；同 opaque ID seq23–27 `arrival→admission_snapshot→cognition_start→cognition_end→terminal delivered`。arrival→terminal **10.606700875s**。B Tpost `finish1`；隔離 Chroma embedding 0→1、episode 文檔的 User/Uruha 和 Web log 對齊，SQLite `user_profile` 0 row；`adaptive_person_model_m16.json` 已建立，但 learned/scoped atoms/revision 仍 0，raw dialogue 未寫為 fact profile。B PID77818 exact planned stop、PID exited、7937 vacant。
- 真 user-turn compute receipt：**1** qwen2.5:7b generation、1041 prompt＋77 completion＝**1118 provider tokens**；11 vector ops、0 失敗，attribution complete。M21 full compact completed、3 candidates、0 fallback；M19 `user_wait_seconds=10.4193`（≤20s，量測邊界不同於 arrival→terminal）。背景全程至停止共 21 組完整 pair／40 vector ops（Tpre 前 20、Tpost 後 20）；啟動/ONNX、embedding tokens、Web rendering、CPU/RSS/energy 未完整 instrument，不能說全系統只花 1118 tokens 或 11 次操作。

## 失敗歸因與下一個必要變因

當輪 M29 是 control/direct `brief_encouragement`、M33 not-applicable，M21 1 真模型呼叫完成。f7 事件證書 `eligible=true`，但三個原始核心在**有限字面關係驗證**中皆 `event_relation_unverified`；`old_index=1→new_index=1`、`manipulation_status=no_grounded_candidate`、winner/final core hash 同 `3c62832b6c65e4c5a24c78023c0adf0c7c1b251fc6f09f3c41f0cac62695f7fd`，無後續 planner revision。故**本真輪沒有實際操弄選擇效用**，不能由此判它在「已有來源候選」的條件下有效或無效。其他兩候選只留 hash，不能獨立重算三者語義，也不能斷言語義皆錯。

可觀測的已選 compact core 已是 `種をまいただけでもすごい！`；最後只加角色尾句，visible guard `changed=false`，M39 `observable_concepts=[]/action=accept`，`post_check.did_reply_cover_focus=false` 只記錄未修。首次可定位的錯誤在**候選核心形成／選出**，不在後段把一個正確核心改錯。下一單一前瞻變因應是「compact 候選對當輪來源事件的保全／缺證棄權」，而非再調 f7 排序或只改日文字元 guard；先凍結 source-disjoint 正負例與 no-grounded failure branch，再決定如何讓來源事件進入候選形成且保留 User actor／動作／受詞，不硬寫測題答案。這仍不能保證一般日文、跨語、人評或同模型 LLM 優勢。

## 原件及界線

私有 B root 未複製 raw trace 到 repository。SHA-256：`evidence/db-t0.json` `5f9b2cf72128e1c63aa27e610fd1bdcafe44926ab69171490387e8787b159137`；`db-tpre.json` `574ba05fff6fcab82c80874a1a1bb32b032957f808b513ea48656dfb5f98c888`；`db-tpost.json` `e5da2d4ec569986a7c4a3252670af793cf591c8581b742948953fbf514c1c365`；最終 `turn_admission_journal.jsonl` `7d8ef4e4a14fd70e4f8e74f6d645f153f5e7d381a2f0aac4f06180d8c511764b`；`web_logs/conversation.jsonl` `f720c0a33d3075ef74a953a560d71be9def90f9cd23e18825b1bdffd87fbb207`；正式 `.stop.json` `53091ac3e4e9d67b4e49d7266b2606ee5e2c2cb2a383018daee88f986d64a72a`。停止後 journal 尚含背景事件，故它的**最終** SHA 與 Tpost 中 journal SHA 不同，兩者各自按時間點使用。正式資料、原始 dirty checkout、無關 `output/graduate_application_report/` 未動。
