# P4 第三者偏好真問句：新六輪 Safari 產品驗收契約

狀態：2026-10-17，**未送新六輪模型／Safari**。單一變因、原六輪負結果和開發期 4/5→5/5 修訂見 `research/p4_third_party_preference_question_evidence_design_2026-10-17.md`。新 input／gold／逐輪 20 秒／0 retry 已事前寫於 `datasets/p4_third_party_question_evidence_fresh_probe_2026-10-17.json`。六輪有**五個不同字串、六次前瞻操作**：T4 的 T1 重複是首輪前凍結的跨重啟「先前問句不是證據」測量，不是看到答案後重試。每個不同字串在寫入前 repository `rg -F -l` exit 1；開發者題，不是獨立 holdout。

## 已完成的首輪前門檻

新 `uruha_third_party_question_evidence_p4.py` 僅產品入口 `__main__` 接入，舊 import-only launcher preflight 不改；RightBrain／writer／M31/M32 核心均未改。先前聚焦＋受影響既有 source／question／owner／launcher 相鄰 112/112（8 個依賴警告，142.91s）。其後首輪前 preflight 發現兩項稽核完整性反例：unknown core 後續接矛盾命題會誤報保留、episode 原話嵌入未跳脫欄位標籤會誤報無證據。修成有限無新命題表面語法與歧義來源 fail-closed，加入對抗測試與真實兩輪重複問句零模型回歸；修訂後最新聚焦 6/6（41.66s）、受影響既有 source／statement／detached-control 相鄰 31/31（45.05s），沒有重跑無關長套件。原 112/112 發生於這兩項修訂前，**不代替修訂後證據**。純規則預檢五個新字串：四個不同直接第三者問句為 `chat`／新 gate，真正 food offer 是原 `food_offer_generic`；T4 與 T1 同字串，總計五個 gate 輪次。隔離產品入口 0-turn 啟停：第一次 verify-ready 在啟動競態時 false、第二次 HTTP 尚未 ready；其後同一 final PID 87348／run `cf8fa3a2d23f63c9`、127.0.0.1:7894 HTTP 200 verify-ready 成功，planned stop 退出且埠空。這些只是發題操作前提，不是 Safari 回覆證據；暫時 ready 失敗已保留，不隱藏。

## 首輪前凍結與真實程序

在第一輪前將新 overlay、入口、聚焦測試、修訂設計、本 plan、逐字 dataset 與依賴 SHA-256 manifest 一起 commit 並推送既有 branch／PR；核 manifest。看到回答後不得改 gold／門檻／原程式或重送已曝光題。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 不碰。

以全新 0700 隔離 root，既有 detached controller `start --mode product --python .venv/product_checks/bin/python`，`verify-ready` 必須核 final Python 同 PID、唯一 loopback listener、HTTP 200，未 ready 不送。Safari 新測試 tab 逐字 T1–T6 各一次；舊分頁不任意關閉。每輪 before/after 用 `p4_preference_fallback_snapshot.py` 留 0600 profile row-ID 與 episode-ID 快照，核原始 JSONL、真 early signal、M21/M29/M31、selected、source evidence 節點、graph UTTERANCE 與 Safari bubble。若可用 Safari 操作介面封存畫面影像，標註輪次及可見範圍；否則只寫目視觀察，不冒稱有 screenshot。

T1/T3/T4/T5/T6 必須真選 `third_party_question_evidence_p4`，早期 chat，M21 deterministic、M31/full planner 皆未完成模型呼叫；graph evidence 狀態是 available-context unknown、selected 與最後可見日文保留 X/Y、真正未知，沒有肯定、無來源 `も`、已知記憶承諾或技術分析。T4 重新問 T1 同題時可說剛才問過，但前問不能變成第三者偏好事實。T2 不得有新 gate node，須保留真食物邀請路徑並回答邀請。六輪都不應寫本人偏好，profile row-ID delta `[0,0,0,0,0,0]`，六個不同 turn episode。Graph node 的布林／`frame_shadow` 不能代替逐輪人工核實語義；若表面保留語義但新節點因保守字串門檻 false，也必須報 graph gate FAIL，不偷偷重命名成 PASS。

T3 後恰一次 planned stop，核舊 PID 退出、埠無 LISTEN、controller 原 metadata `planned_stop=true`；同一 root／DB 重啟一次，核新 PID/run ID/session、T4 前 row-ID 集合不變；T6 後 planned stop。任何意外停機、額外重啟、漏輪、無 before/after row-ID、結果驅動 retry 均程序 strict FAIL。逐輪 user wait（含冷啟）≤20.0s；記真模型呼叫、可得 total tokens／價格／延遲，缺完整 ledger 標 unavailable，不以局部零呼叫推總成本，也不跨不同題目聲稱因果加速。任一語義、來源、記憶、graph、安全、成本、程序 gate 不達，**整批 strict FAIL** 並保留最小反例。

結果及 raw SHA 封存後更新 `CURRENT_TASK.md`，diff review，只提交本項，push、核對既有 PR #435。即使 strict PASS，只證明窄日文無可辨識證據第三者問句在這批本機產品輪次可保留未知；不代表一般語用理解、有效全庫檢索、同模型強 LLM 優勢、人類被理解感、正式 temporal holdout、長對話泛化、VRM／Function Calling 完整交付或人腦方程式。
