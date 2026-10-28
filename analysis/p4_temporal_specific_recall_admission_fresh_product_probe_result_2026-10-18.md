# P4 時間片語具體回憶准入：八輪前瞻 Safari 產品驗收

**整批 strict FAIL；不重播、不放寬門檻。** 新的有界准入在兩個直接來源回憶輪次確實進入最後日文回覆，但 T1 實際等待 **22.8402 秒**，超過事前 ≤20.0 秒 gate。T8 的「確かには言えない」也有日文自然度疑慮；沒有獨立母語人評，不把 8/8 可見日文等同 8/8 自然度通過。本批是同團隊撰寫的產品探針，不是正式 temporal holdout、真人被理解感或同模型 LLM 優勢證據。

## 首輪前凍結與隔離

- 先以 `2766bdc` 凍結 `research/p4_temporal_specific_recall_admission_plan_2026-10-18.md`、八句資料與 preimplementation SHA；再以 `f62e3e6` 凍結 opt-in 程式、薄 Web 入口、controller 與 product SHA，均已推既有 PR #435。兩份 SHA manifest 分別 **2/2**、**9/9** OK；本次重跑 temporal／episode-focus／relationship-authority／quote-scope 四組零模型／相鄰測試 **37/37**，8 warnings。這些不是 Safari 產品通過。
- 只改 `少し前に`／`ちょっと前に` 修飾的、未引述具體過去使用者發言查詢，進入既有來源限定 episode 回憶契約；原輸入仍供檢索，原文 SHA 綁在准入收據。未安裝此 opt-in 入口時舊行為不變。新 gate 的 raw 收據 `model_call_added=false`；不能據此說完整管線零模型呼叫。
- 全新 launcher-owned 0700 隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-s6y4nx7s`。0-turn readiness run `93b2501689757b47`／PID 71345 通過同 PID HTTP 後 planned stop。官方 Chroma ONNX archive 私有 0600 離線副本 83,178,821 bytes、SHA256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`，封鎖下載仍取得 1×384 finite embedding。T0 顯式空 `user_profile`、0 rows、完整內容 digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。
- Safari session A `20261018_202120_8708a46e`，run `16b27f7719ce2c3b`／PID 71877，T1–T4；T4 後 planned stop、PID exited、7894 vacant。同一 root／DB 重啟，session B `20261018_202944_fe82b494`，run `4da01c40b7d5d2e3`／PID 74139，T5–T8；終局 planned stop、PID exited、7894 vacant。重啟前四個 episode 在重啟後的 DB snapshot 仍存在；但 T7 檢索的是**重啟後才寫入的 T5**，本批沒有直接測「重啟後從 T1 舊來源作答」，不能稱跨重啟來源回憶已通過。兩個本批 Safari 分頁保留作畫面紀錄，但本機服務已停止，舊頁不可當作仍可用的網站。
- 每句一次、0 retry。原件 `web_logs/conversation.jsonl` 八行，SHA256 **`4a555de6ae4a0a4b26b3b84b01a332ac6e9a9b46a092feb4b992ca2632774683`**。T0–T8 九份 full-profile 收據與重啟前附加收據均 present／0 rows／同 digest；終局八個不同 `turn_episode` ID。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/` 未動。

## Safari 最終泡泡與原始等待

| 輪 | 凍結輸入 | 真 Safari 最終回覆 | user wait 秒 | 專用來源／控制觀察 |
|---|---|---|---:|---|
| T1 | `校庭の集合場所は銀色の門の前だよ。` | `了解した。` | **22.8402** | 直接 User episode 已存；**速度 FAIL**。 |
| T2 | `ねえ、まだ私のこと覚えてる？` | `まあ気にしてるし。お前はどうなんだよ。` | 3.1281 | 舊路徑 selected `ask_miss_me`，沒有回答「是否記得」；**直接問題忠實度疑似 FAIL**，不能算此負控完整通過。 |
| T3 | `少し前に言った校庭の集合場所、覚えてる？` | `「校庭の集合場所は銀色の門の前だよ」って言ってた。` | 3.0879 | 專用 focus 選 T1 直接 User episode；原候選 rank 6，普通 top-5 未選。 |
| T4 | `「少し前に言った校庭の集合場所、覚えてる？」って台詞、自然？` | `変ではないけど、前後の流れによっては少し唐突に聞こえるかも。` | 3.6398 | selected `quoted_line_feedback`；引號內查詢未執行。 |
| T5 | `図書室の待ち合わせ席は窓際の三番だよ。` | `図書室の待ち合わせ席は窓際の三番だね。` | 13.7760 | 同 DB 重啟後，第二個不同的直接 User episode 已存。 |
| T6 | `今日はちょっと眠いな。` | `ねむいならもう寝とけ。` | 2.5526 | 一般閒聊，非 T7 的事實來源。 |
| T7 | `ちょっと前に話した図書室の待ち合わせ席、覚えてる？` | `「図書室の待ち合わせ席は窓際の三番だよ」って言ってた。` | 3.1694 | 專用 focus 選 T5 episode；原候選 rank 6，普通 top-5 未選；沒有用較近的 T6。 |
| T8 | `少し前に言った屋上の看板の色、覚えてる？` | `そこは今、確かには言えない。もう一度教えて。` | 3.1360 | focus `unavailable`／`no_unique_direct_user_assertion`，未編造顏色；日文措辭待修。 |

八輪均在 Safari 逐輪實見泡泡及下方 runtime graph；raw `assistant_reply`＝同輪 graph `utterance.payload.reply`＝泡泡 **8/8**。T3／T7 展開專用節點均見 `selected_unique_user_episode`，`source_user_utterance` 分別逐字等於 T1／T5，`memory_id` 分別為 `1c0e0d1e-83e4-4710-9dba-e2408055682b`／`48a5c3eb-be5e-4438-a70f-3b5187414ca4`；handoff `explicit_recall_focus_handoff`、selected `recall_context`、`final_visible_surface_matches_contract=true`。T8 展開節點為 `unavailable`、focus `屋上の看板の色`、0 唯一來源。這支持**專用來源節點→選定核心→最後可見句**的有界一致，不等於整張圖逐欄一致。

## 失敗、成本與下一個必要工作

- 事前 gate 要每輪 ≤20.0 秒；本批 **7/8** 達標，平均 **6.91625 秒**、最大 **22.8402 秒**，故整批 strict FAIL。T2 的可見句沒有回答「記得我嗎」，而是轉成「我有在意你／你呢」；這是舊 selected `ask_miss_me` 路徑的回答忠實度問題，按凍結 T2 條件式 gold 至少是**額外疑似 FAIL**，不以「非事實回憶」掩蓋。T8 的低壓不捏造方向正確，但「確かには言えない」語感不自然；自然日文 gate 也不能宣稱通過。T1 `prewarm_status=ready`、cold brain init 0.5074 秒，cognition 20.2296 秒；其中 M31 已完成驗證模型呼叫 11.7562 秒，M21 full planner 亦完成一次 8.3131 秒。不能把超時歸因於 ONNX 下載；目前可見的是同輪兩條昂貴路徑串行，尚未由隔離干預證明只改一條就足以達標。T5 另有 M31 完成呼叫 11.0615 秒，沒有 T1 的 full-planner route；等待 13.7760 秒。新准入 gate 自身 0 model calls；可追溯至少上述三次完成呼叫。完整管線可靠 token ledger、實際 token 總量與金額成本 **unavailable**，不是 0。
- 既有 `selected_plan.memory_anchor` 在 T3 指 T2 `short_term` 關係句、在 T7 指 T6 `short_term` 睡意句；舊 `post_check.did_reply_use_memory_explicitly=false`。它們是專用 focus 接管前的舊快照，與新 focus 的真實答案來源不一致。不能讓外行讀圖時誤以為短期干擾造成最終答案；圖的完整來源忠實度仍未過。此批只報已核對的專用 focus、selected core 與 utterance，不把舊欄位洗白。
- 前一批錯答 `少し前に言った集合の目印` 時，舊路徑把無關關係句當記憶答案；本批新的兩個正例使用不同直接來源與兩種時間片語，均回到有來源的原話，其中第二組在重啟後才建立來源。這是**新的前瞻同團隊案例的有界功能進展**，不是同一題前後 A/B、重啟前來源的可見回憶、正式 holdout、普遍記憶正確性或對強 LLM 的因果優勢。
- 下一個單變因先只讀歸因 **普通直接陳述 T1 為何 M31 + M21 連續呼叫**，在新未曝光題及同一 20 秒門檻下，選一條有來源保障、可保留人格／日文／寫回的最小快路徑；T1/T5 不重播追分。舊 graph anchor／post-check 來源不一致與 T8 日文措辭另立必要卡，不混入性能修正。若新前瞻修正仍失敗，保存 `REVIEW_REQUIRED`，不反覆加規則。正式同模型強 LLM、人評、temporal holdout、完整 VRM／Function Calling 仍 pending；Goal active。
