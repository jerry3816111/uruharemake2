# P4 混合請求中的過去地點來源授權：前瞻工作卡

2026-10-20；本卡在新程式及新產品輪次前凍結。前批 A1–A7 的 raw、gold、strict FAIL 不改，也不重送。這是對 `CURRENT_TASK.md` 頂部「先設計審查」的結果；不是改寫品質修復。

## Before 與單一變因

前批 A1 的外層同時要求改寫與回想昨天地點；來源角色正確為 `mixed_request`，但舊 `emit` 在不適用單一改寫時直接交給一般 planner。`core_message_jp` 已無來源地寫出「昨日は公園で待ち合わせしたよね」；檢索／通過的記憶與 `memory_recall_contract` 均空，M39、最終 guard 放行，assistant episode 隨後保存該句。這是規劃→發話→寫回的事實授權缺口，不是 graph 排版問題。

只加入一個可歸因的能力變因：**對可辨識的「引述改寫＋回想自己過去選的集合地點」混合請求，具體地點只能由同輪已交付、型別可核的直接 User 原話授權；沒有來源、相對日期不穩、矛盾、撤回或第三者話語時，最終日文只能承認不能確認。** 現階段只覆蓋日文、單一引述、明確本人選擇與絕對日期；`昨日／一昨日` 只可進未知分支，不把跨午夜的相對時間錯配。來源證明「使用者曾這樣說」，不證明世界事實。不得從 current query 的預設、引號內容、summary、Uruha/assistant 輸出、未交付候選、私人狀態抽取答案；已知來源只用已交付 `recent_turns.user` 或 metadata 型別可核的 `direct_episode` User 欄位。來源值要保留日文主體／日期／選擇行動／地點，不以字詞相似度授權。

現有 `local_fact_answer_authority_p4._handed_user_sources` 可用作來源 transport 驗證，但其 standalone time/place grammar 不涵蓋混合請求。新 opt-in 模組只在隔離產品入口安裝於現有改寫 wrapper 之外；在 `cognitive_tick` 後、`emit/speak` 前建立憑證並選定來源限定 core；在最外層可見 guard 再算同一憑證，避免 M39/P4-W 或其他表面修復重新插入無來源過去事實；episode 寫入前完成，不做 post-emit 文字補救。若 M31/M32 已有 authoritative surface、protected route 或憑證不完整，保留原權限並記錄 abstain，不憑同一 input digest 宣稱 event/parent lineage。回傳後只同步 digest、graph 節點與歷史鏡像，絕不改 reply。

這個 gate 可能只回答事實子任務而未完成改寫；那是**明示的產品限制／完整 mixed-act 失敗**，不得把 factual-source pass 當整輪產品 PASS。A2/A3 候選自然度、A6 句型、A7 身份與真 graph event-parent edges 分卡處理。

## 凍結驗收

新題見 `datasets/p4_mixed_past_place_source_authority_probe_2026-10-20.json`。先做零模型契約，覆蓋同 session 直接 User、typed episode 跨重啟、未知、相對日、不同值矛盾／撤回、第三者引述、assistant/summary 污染、current presupposition、未交付來源、M31/M32 authoritative 與保護路由。不得把新題答案或原文硬編進 matcher；正式程式只能用泛用 typed grammar、source transport 與保守 abstention。

再用全新 0700 root、私有模型 cache／空 profile、0-turn same-PID ready/stop、真 Safari 新 session 做未曝光序列各句一次、零 retry；每輪在下一輪前核可見泡泡、raw JSONL、`visible_language_guard.final_reply`、graph `utterance` 與來源憑證，核 episode 是否只保存最後可見句。需要時同 DB planned restart 測直接 episode。先凍結來源 seed，再送 mixed query；不可用前批 A1 重播。產品必要門檻：所有覆蓋的地點斷言都有可核 User trace ID，無來源／矛盾／撤回 0 假地點，負控 0 接管，visible 日文、final/graph/episode 一致，逐輪 user-wait ≤20 秒；新 gate 0 額外模型呼叫，另列全路徑可得 token／耗時。若任何硬 gate 失敗整批 strict FAIL，原件／成本／反例保留；若 mixed rewrite 未完成，即使本 gate 局部通過，整體產品仍 FAIL。

允許檔案：本 plan/dataset、`uruha_mixed_past_place_source_authority_p4.py`、聚焦 test、薄 Web entry/controller、相應 SHA manifest、`CURRENT_TASK.md` 與結果報告。其餘既有 core、歷史 freeze/result、正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 不動。先小測再受影響回歸與真 Safari；至多兩個有根據修正批次，不修改曝光 gold 追分。成果只推現有 branch／PR #435，review diff 與 PR head。正式同模型、人評、temporal holdout、VRM／Function Calling pending。
