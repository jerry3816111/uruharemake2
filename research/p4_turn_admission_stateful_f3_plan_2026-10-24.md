# P4 stateful admission f3：wrapper 修正後新產品輪的事前計畫

狀態：**source-only freeze，尚未執行 f3 fake full-turn、真模型或 Safari Send。** 這是作者診斷題，非正式 holdout、人評或同模型 LLM 對照。f0 pre-Send、f1 原始 route、f2 Web wrapper 各自 strict FAIL；不得重送或重判。f2 後的單變因 wrapper 修正及其零模型結果見 `analysis/p4_admission_token_function_wrapper_zero_model_result_2026-10-24.md`，未有修後真產品證據。本次僅檢查已修產品在**實際 pre-state**下的一輪可歸因 user turn，不稱 pristine tick0。

## 問題與事前判準

唯一新產品刺激是 `datasets/p4_turn_admission_stateful_f3_probe_2026-10-24.json` 的一次使用者輸入：「初めて自分で自転車のパンクを直せた。今は一言だけ励まして。」情境為首次自己修好腳踏車破胎，和 f2 家具配置、f1 庭院、f0 小說不同。凍結前 `rg -F` 對整句及 `自転車のパンク` 在 tracked project source/datasets（排除無關 `output/`）均 0 命中；source-only classifier 為 `direct / brief_encouragement`，input SHA-256 `c9b992d1a8dab34e3e7de4f8dc67bd56be5925b64a2bbc824d7e17e3038babf1`。它仍使用已知的明示鼓勵格式；**不宣稱語義全面未見或 open-domain 泛化**。

可見 gold：短而自然的日文，承接「第一次自己修好腳踏車破胎」這個可觀察事實，給一言鼓勵；不要轉成修車教學、泛用休息句、追問、憑空猜測睡眠、疲憊、心理或私人經驗。語氣在公開資料人格界線內，不冒稱真人；本題只能排除錯誤身分聲稱，不能正向證明身份認知。句末不得有 `！。`／`？。`／`。。`；若沒有觸發該接合分支，該狹義 punctuation gate 標 not_exercised，不能算成功。

## 唯一變因、資源與執行順序

- 產品 code、模型、prompt、planner、guard、Web、背景週期、journal、正式資料及 baseline 不改；本次產品變因只有新輸入及新隔離 session/root。此測例也提供上一批 wrapper 修正的前瞻產品驗證，不可用舊 f2 再試。固定 `qwen2.5:7b` digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`、原產品生成參數；官方 ONNX archive SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`。上限：3 completed Brain user-turn generations、2,000 provider tokens、20 秒 user wait、Safari Send **一次、0 retry**。Web delivery 額外 Chroma 成本若無 ledger，必列 unknown，不宣稱 full production-cost PASS。
- 先提交／push 本計畫、題本、preimplementation SHA、任務卡，核 PR #435 exact head。其後才跑隔離真 RightBrain＋假 LeftBrain 的 zero-provider full-turn route test：M29 `brief_encouragement`、M33 `not_applicable`、M18 不接管、M21 `full_planner` 且 compact completed、scene `support`、act `direct_chat_answer`、final＝episode、1 fake model call。若未過，f3 真產品不啟動，保留 FAIL；不得改 gold 追分。Web-level wrapper 正負控沿用修正批契約。
- port 7930 起初必空。新 launcher-owned 0700 私有 root、loopback-only，官方 ONNX 私有封網預熱；無 journal／無對話 zero-turn rehearsal 同 PID HTTP ready 與 exact planned stop，port 再度 vacant。正式 `p4_direct_reply_act_m29_priority_detached_control.py --direct-act-arm control --repair-cue-boundary --turn-admission-journal --product-port 7930 start --mode product`；同 PID ready、model digest、active `memory_db`、reset0、human finish0、brain ready、episode/profile 0。readiness race 僅同 PID 重查，不重啟同題掩蓋。
- T0 ready 與 Send 前 Tpre **各自落盤**為私有 0600、fsync、不可覆寫的 regular-file DB tree 原件：相對路徑、size、SHA-256、mode、取樣 `monotonic_ns` 前後、PID/session/reset/DB 與 journal end-seq。只讀掃描且拒絕 symlink、root escape、取樣時漂移；兩 tree 必須 byte-equivalent，並在原件上可重算 SHA。任何取樣失敗或 DB 變更，**不 Send**。這補足 f2 僅有工具輸出而無持久 snapshot 的缺證。`tick > 0` 明列 pre-state，不能說背景沒影響。
- Tpre 之前 journal 只可為完整、序號連續且同 PID/session/reset/DB 的 background start/end pairs；ledger coverage complete，0 unknown worker、0 error、0 wrapped vector mutation returned/error。in-memory fingerprint/`passive_decay` 變化如實揭露。原生 Safari 新 tab 確認 exact input/session/未送；Tpre 取樣後目標 10 秒內點一次 Send，保存 click wall time、server arrival monotonic。Tpre 不合格或無可核 click→arrival 時序，嚴格 FAIL；Tpre 取樣不確定窗口至 arrival 若有任何背景 event／次序不明，已送也 strict FAIL、不得重試。
- 同 opaque ID 的 browser `arrival → admission_snapshot ready → cognition_start → cognition_end completed → terminal delivered` 必連續、同 PID/session/reset/DB、無 background/proactive interleave、無 timeout/error/state drift。`delivered` 不是 DOM ACK；Safari 真 user bubble、visible reply、當輪 node graph input→retrieval→decision→utterance→writeback 的節點／連線與來源、raw＝guard final＝graph utterance＝isolated episode 都需逐一核。保存可重核原生 PNG/AX 或同等原生視覺證據；若工具無法落盤，visual-evidence gate 不過，不能用 HTML replay 充當。
- 取 Brain user-turn actual model calls/tokens/wait/vector ops、背景 pair/read/gen、journal bytes/events、隔離 DB episode/profile 前後與完整性；Web delivery 額外 Chroma cost 獨立揭露 unknown。超資源或缺帳、visible quality/source/graph 任一 gate 不符即本批 strict FAIL，局部成功另列。只停本次 exact PID，核 7930 vacant；只關本次新 Safari tab，保存私有原件及其 SHA。UI 工具拒絕時 Web gate pending，不繞過。

即使 f3 narrow product PASS，也不能外推同模型 LLM 優勢、長期記憶／預測、真人被理解感、temporal holdout、VRM＋Function Calling 統一驗收或人腦方程式；f0–f2 FAIL 原樣保留。
