# P4 關係問句泛用記憶答案權限：六輪前瞻 Safari 產品驗收

**整批 strict FAIL；不改題、不重播追分。** 這是同團隊事前編寫的產品探針，不是獨立 temporal holdout、人評或同模型 LLM 比較。T2/T6 的有限答案權限機制得到真 Web 正例；T4 的直接事實回憶錯答使凍結整批 gate 失敗。

## 首輪前與隔離證據

- 先凍結計畫／六句：`1da572e`；再凍結 opt-in 程式與產品 SHA：`f7796f6`，均推既有 PR #435。新 manifest **8/8**、上一層 **13/13** SHA OK；聚焦／相鄰零模型 **33/33**。程式只在 selected `ask_miss_me`、普通 high-road、非保護 scene 且錨點為泛用 `context` 時撤銷該錨點的**可見答案權限**，不改檢索排序、selected core、模型呼叫或事實寫入。這些檢查本身不是產品 PASS。
- 全新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-jsji3y1x`。0-turn run `c33725f94ae934f5`／PID `44986` 通過同 PID localhost HTTP readiness，planned stop；它不是六輪中的重啟。官方 Chroma ONNX archive 83,178,821 bytes，SHA256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`；私有 0600 副本不同 inode、link count 1；fresh interpreter 封鎖下載仍得 1×384 finite embedding，約 0.521 秒。僅在這個 root 明示建立空 `user_profile`，T0 完整內容 receipt 是 present／0 rows／digest `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。
- Safari session A：`20261018_195207_b3432d9a`，run `d43b7097f54c5c58`／PID `66354`，T1–T4；T4 後 planned stop，PID exited／7894 vacant。同一 root／DB restart；session B：`20261018_195529_475a79d9`，run `f172d2ce95af6c23`／PID `67060`，T5–T6；終局 planned stop、PID exited／7894 vacant。兩個 Safari 測試分頁保留；服務已停止，舊頁內容只作當輪留存，不能當作仍在運行的網站。原始 dirty checkout、正式 DB 與無關 `output/graduate_application_report/` 均未觸碰。
- 每句一次、0 retry。raw 原件是 root 內 `web_logs/conversation.jsonl`，六行 SHA256 **`c57f1c95087c96ee10240ae312829d359a884cae24011d7878429b974e6f3797`**。T0–T6 七份 full-profile 收據皆 present／0 rows／同 digest；末次 isolated DB 有六個不同 `turn_episode` ID。每輪 Safari 實見聊天泡泡與下方 runtime graph；**6/6** raw `assistant_reply`＝圖 `utterance.payload.reply`＝當輪泡泡。T2/T6 另展開圖的 `relationship_context_answer_authority_p4` 節點，看到 selected intent、短期來源 trace、來源 role 與撤權狀態。

## 可見結果與事前 gate

| 輪 | 使用者輸入 | Safari 最終日文回覆 | user wait 秒 | 判定 |
|---|---|---|---:|---|
| T1 | `「まだ私のこと覚えてる？」って台詞、重すぎる？` | `少し重く聞こえるかも。相手との距離感次第だな。` | 2.7833 | 外層台詞評價正確，非本輪關係請求。 |
| T2 | `ねえ、私のことまだ覚えてる？` | `まあ気にしてるし。お前はどうなんだよ。` | 2.6777 | selected `ask_miss_me`；T1 `quoted_line_feedback` short-term context 被檢索，但不再當作答案。 |
| T3 | `集合の目印は青い時計の下だよ。` | `集合の目印は青い時計の下にあるんだね。` | 14.8248 | 直接事實被作為一個 episode 保存；當輪回覆沒有改成個人 profile 事實。 |
| T4 | `少し前に言った集合の目印、覚えてる？` | `前に:ねえ、うちのことまだ覚えてる？` | 2.9895 | **FAIL**：沒有答 T3 的 `青い時計の下`，反而引用 T2；冒號也不自然。 |
| T5 | `「ちゃんと私のこと覚えてる？」って台詞、重すぎる？` | `少し重く聞こえるかも。相手との距離感次第だな。` | 2.6363 | planned restart 後仍答外層台詞評價。 |
| T6 | `ちゃんと私のこと、まだ覚えてる？` | `別に少しくらいは思うだろ。そこは察しろって。` | 2.7759 | selected `ask_miss_me`；T5 `quoted_line_feedback` short-term context 保持 trace、撤銷答案權限；未引用台詞。 |

六輪等待皆 ≤20 秒；平均 **4.7813 秒**，最大 T3 **14.8248 秒**。新 gate 自身新增模型呼叫 0；T3 的 M31 有一次完成的 qwen3.5:9b 呼叫，約 **11.7006 秒**，全管線實際 token ledger unavailable，不能說零 token。ONNX 複製／0-turn readiness／兩次服務啟動／profile 測量均是額外設施成本，未混入每輪 user-wait。T3 有實際較慢的 14.8248 秒，不能拿其餘 deterministic 快輪概括全系統延遲。

T2/T6 raw `logic` 與 graph 均有相同撤權 receipt：`source=short_term`、`source_role=quoted_line_feedback`、`source_match_count=1`、`prior_memory_use_expected=true`、`answer_use_authorized=false`、`selected_core_still_same=true`、`final_contains_serialized_memory_role=false`。圖上順序是 `selected_plan → relationship_context_answer_authority_p4 → utterance`。這證明原記憶仍被看見、只有其可見答案權限撤銷；它不是「真的記得使用者私人事實」的證據。兩句用含蓄關係語氣回應而未字面確認具體記憶；本團隊不把這點評成獨立人類語意認可。

## 失敗歸因、界線與下一項

T4 不是 T3 記憶消失：T3 青時計來源在 `working_memory_items` 排 **#2／2.3911**；T2 無關的 `覚えてる？` 來源排 **#1／2.3964**。舊 planner 的具體回憶識別未涵蓋 `少し前に言った`，泛用 `覚えてる？` 則把 T4 選成 `chat/memory_presence_reply`，不是 `recall_context`；舊 generic anchor fallback 拿 top-1 T2，`_memory_grounded_reply` 先於其他候選生成，最後只被語言 guard 刪掉 ASCII `User`。本次新權限 gate 僅處理 selected `ask_miss_me`，在 T4 沒啟用，亦未改 T4 排序／selected／回覆；不能以 T2/T6 正例掩蓋 T4。T3/T4 的最小反例與舊代碼位置為 `uruha_brain_mac.py` 的 specific-recall、generic memory fallback、memory-grounded surface 路徑。

額外圖像化限制：T2/T6 新權限節點在 `runtime_trace`、同輪 `runtime_state.blackboard` 與 history mirror 都存在，且最終泡泡與 `utterance` 逐字一致；但整份 `runtime_state.blackboard`／history 與最終 `runtime_trace.blackboard` **並非逐欄完全相等**（後段 latency／surface delivery 等 late nodes 有不同步）。因此只報收據節點與 utterance 的可追溯性，不報整張鏡像完全一致。真 Safari 當輪目視不是錄影或獨立人評。

下一個必要單變因是**來源限定的具體事實回憶焦點**：在不放寬關係／引述保護、也不重播本六句的前提下，讓使用者提及「稍早說過的具體物件」時，只從可核對的同主題直接使用者 episode 形成答覆，來源無效／衝突就不猜；先凍結新正負控、來源和 latency gate，再實作 opt-in、零模型及全新隔離 Safari。T1 cold latency、T7 類混合 frame 與 T8 類具體精簡交付仍分開。正式同模型強 LLM 優勢、人類被理解感、temporal holdout、VRM／Function Calling 整合與人類方程式都**未被本批證明**；Goal 維持 active。
