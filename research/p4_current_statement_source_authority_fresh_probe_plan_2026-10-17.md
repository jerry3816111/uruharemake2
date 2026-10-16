# P4 當輪陳述來源優先權：新六輪 Safari 產品驗收契約

狀態：2026-10-17，**未送模型／Safari**。逐字 input、gold、20 秒每輪上限、0 retry、T3 後同庫重啟已事前寫入 `datasets/p4_current_statement_source_authority_fresh_probe_2026-10-17.json`。六句全文寫入前 repository `rg -F -l` 均無命中（exit 1）；這仍是作者開發題，**不是獨立 holdout**。舊曝光五輪及其 strict FAIL 不改、不重播。單一變因與已知 M18／prediction-error 邊界見 `research/p4_current_statement_source_authority_design_2026-10-17.md`。

先以 `.venv/product_checks/bin/python -m pytest -q test_p4_current_statement_source_authority.py` 驗證零模型來源證書、early signal、plan、M29、writer、graph、正反控制；接著只跑受影響的既有 source/owner/question/statement-act/launcher 回歸，並跑 `compileall`、`git diff --check`。新 overlay 的獨立無模型安裝契約須另驗，因舊 launcher 匯入式 preflight 在既有入口的 `__main__` 前，不應被新安裝改變。再跑 `p4_preference_fallback_detached_control.py` 的全新 root 0-turn start／verify-ready／planned stop；此為操作前提，不是回覆驗收。任一前提失敗不送新六輪。

**首輪前**凍結實作、入口、測試、此 plan、逐字資料與 SHA-256 manifest 並提交 Git；核 manifest。看到回答後不能改金標、門檻或重送曝光題。新 0700 私有 root，單一 `127.0.0.1:7894` listener，正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 不碰。以既有 detached controller `start --mode product --python .venv/product_checks/bin/python` 和獨立 `verify-ready` 核同一 final Python PID、loopback 與 HTTP 200；Safari 開新測試 tab，舊分頁不隨意關閉。

六輪各逐字送一次。每輪 before/after 用 `p4_preference_fallback_snapshot.py --runtime-root <root> --save before-tN|after-tN` 留 0600 row-ID 和 episode-ID 快照；root／DB 僅隔離開發資料。逐輪核原始 JSONL、真 `actual_signal`／M29／M31／M21／selected plan、source certificate／graph node／utterance 與 Safari 泡泡。T1/T2/T3/T6 必須真選 source-rule chat、早期 signal 不誤當 food offer，M31/full planner 均未完成模型呼叫；保留逐字 X/Y 與肯定 speech act、自然日文、沒有未證實的早知／記憶承諾。T1/T3 第三者 profile 0；T2/T6 本人各恰一筆，只記本人。T4 真問句、T5 真食物邀請不得獲來源證書；T4 不冒充知道未確認的第三者偏好，T5 應答邀請。預期 profile row-ID 差 `[0,1,0,0,0,1]`，六個不同持久 turn episode。graph 需從 bubble/raw/selected 的來源、owner、act、物品與最後 utterance **語義一致**，不能只看文字泡泡是否一致或 `frame_shadow=0`。

T3 後恰一次 planned stop，核 PID 退出、port 無 live LISTEN、controller 原 metadata `planned=true`；同一 root/DB 重啟一次，新 PID/run ID/session 不同、T4 前 row-ID 集合不變，再送 T4–T6。最後 planned stop、保留隔離 root。任何意外停機、額外重啟、漏輪、未留 before/after ID 或重播，程序 strict FAIL。記每輪實際 user wait（含冷啟，均 ≤20.0s）、M31/full-planner/其他真模型呼叫、可得的完整 token／價格／延遲；缺值記 unavailable，不以某一局部 ledger 推總成本，也不跨不同題目宣稱因果加速。六輪任一語義、route、source boundary、profile、graph、安全、成本、程序不達，整批 strict FAIL 並保存反例；不得改已曝光題追分。

結果及 raw SHA 封存後更新任務卡、diff review、僅提交本項、push 並核對既有 PR #435。即使 strict PASS，只可稱窄日文單句 source-act 的本機產品證據；不代表一般語用理解、同模型強 LLM 優勢、人評、正式 temporal holdout、長對話能力、VRM/Function Calling 完整交付或已推得人腦方程式。
