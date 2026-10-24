# P4 第三者偏好真問句：六輪 Safari 產品驗收

結論：**本批 strict FAIL**，但留下可核對的窄機制進展。這是開發者撰寫、首輪前由 `19f9a03` 凍結／推送的六次操作（五個不同字串；T4 事前預定重問 T1），不是獨立 holdout、人評、同模型對照或普遍語用理解。21/21 SHA manifest 在兩個啟動嘗試前均核對通過；原題／gold／程式在輸出後未改，無回答 retry。第一次獨立 root 在 0-turn 啟動就退出，**程序 FAIL、沒有任何題目曝光**，另見 `analysis/p4_third_party_question_evidence_preflight_abort_2026-10-17.md`；它不能從產品穩定性分母消失。本報告只評估第二個 root 中實際完成的六輪。

## 真實 Safari 可見結果

第二 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-gz4ggeku` 為控制器建立的 0700 隔離資料庫。Safari 新分頁逐字 T1–T6 各送一次，UI `Log` 指向本 root；raw `web_logs/conversation.jsonl` 恰六行，SHA-256 `c9e0472f5c0dd08a4918359f9a7b6ffd268343666ba680f1b07b4d767f0d8d84`。送出時和完成後均檢查真聊天泡泡、selected plan、圖上新 gate（若適用）與 UTTERANCE；raw 的六個 utterance payload 均逐字等於 `assistant_reply` 和當時 Safari 泡泡。這是 Safari AX／目視與 raw 對帳，**沒有把可重開的 Safari 截圖檔封存**；最後一次 screenshot 只目視了 T6 的聊天畫面，不能冒稱有整張 graph 的封存影像。

| 輪次 | 輸入 → 最終可見回覆 | selected／圖節點 | user wait | 凍結驗收 |
| --- | --- | --- | ---: | --- |
| T1 | `先生は焙じ茶りんごゼリーが好き？` → `一回、先生が焙じ茶りんごゼリーを好きかどうかは、今の話だけじゃ分からないな。` | 新問句 gate、M21 deterministic；圖 `selected_or_visible_mismatch` | 14.5961s | 日文保留 X/Y 與未知、無偏好捏造；但表面新增未事前許可的 `一回、`，圖表 strict FAIL。不能事後加入白名單追分 |
| T2 | `海苔昆布おにぎり、一口いる？` → `先に、今は昼のゆるい感じだけど、その話なら普通に分かる。` | 原 `food_offer_generic`、沒有新 gate | 2.7461s | 路由負控制 PASS；**表面沒有回答「要不要一口」**，語義 FAIL。selected core 原為 `おにぎりなら普通にあり。少しもらう`，問題在下游表面 |
| T3 | `祖母は柚子炭酸ゼリーが好き？` → `祖母が柚子炭酸ゼリーを好きかどうかは、今の話だけじゃ分からないな。そのくらいでいいだろ。` | 新問句 gate、圖 `visible_unknown_preserved` | 3.0288s | 窄未知句與圖 PASS |
| T4 | 重問 T1，T3 後同 DB 重啟 → 同 T1 最終回覆 | 新問句 gate、圖 `selected_or_visible_mismatch` | 2.7175s | **先前同題問句沒有變成第三者偏好事實**；表面 `一回、` 再使圖表 strict FAIL，不是答案重試 |
| T5 | `父は深煎り麦茶が好き？` → `父が深煎り麦茶を好きかどうかは、今の話だけじゃ分からないな。そのくらいでいいだろ。` | 新問句 gate、圖 `visible_unknown_preserved` | 2.8963s | 窄未知句與圖 PASS |
| T6 | `同僚は黒糖生姜ラテが好き？` → `同僚が黒糖生姜ラテを好きかどうかは、今の話だけじゃ分からないな。そのくらいでいいだろ。` | 新問句 gate、圖 `visible_unknown_preserved` | 3.0492s | 窄未知句與圖 PASS |

五個問句輪均 `planner_path=third_party_question_evidence_p4`、`intent=chat`、M21 `deterministic_rule_plan`／一般 planner `model_call_attempted=false`，M31 `not_applicable`；新節點都在真 selected 後才出現，`selected_plan_matches_logic=true`、來源 digest 對齊。T2 正確排除 gate。五句最終文字均有真正的「今の話だけじゃ分からない」而非肯定／`も`，但這**只說所見五句的語義**；嚴格圖表僅 3/5 `visible_unknown_preserved`，另外 2/5 是保守預定語法對 `一回、` 的 false negative，不能把 false 節點改稱 true。T2 是獨立、實質的 action-to-utterance 遺失；既有 M39 報 `accepted_verified_surface`、frame shadow 報 preserved，兩者未涵蓋「邀請須真的作答」，不能用它們掩蓋。

## 記憶、重啟、時延與成本

本 root 的 `evidence/snapshot-before/after-t1..t6.json` 共 12 份 0600 row-ID／episode-ID 證據；profile row-ID 差 `[0,0,0,0,0,0]`，最終為零；每輪新增恰一個持久 turn episode、最後六個不同 ID。T3 後 run `1beb6ce63c0d99c1`／PID `12372` planned stop，原 controller `planned_stop=true`、PID 退出、port 無 LISTEN；同一 root／DB 由新 run `db541a9f7e2be650`／PID `12980` 啟動並 verify-ready，同 PID 獨占 `127.0.0.1:7894`、HTTP 200。Safari 重載後 session `20261017_121455_1a1e963d` → `20261017_121816_51f0f689`；T4 前 ID 集合與 T3 後相同。T6 後第二次 planned stop true／PID 退出／port vacant。正式 DB、原始 dirty checkout 與無關報告目錄均未碰；Safari 原有 tabs 不關。

六輪 user wait `[14.5961,2.7461,3.0288,2.7175,2.8963,3.0492]` 秒，6/6 ≤預定 20 秒，合計 29.034 秒、最大 14.5961 秒。這只是當輪等待，不代表和不同題目的舊系統作因果速度比較。M21 六輪沒有一般 planner 生成呼叫，M31 六輪不適用；沒有覆蓋所有背景／表面模型、token 與價格的完整 ledger，總呼叫／token／金額標 **unavailable**，不能從局部零呼叫外推成本零或公平 LLM 優勢。首輪前 6/6 零模型聚焦、31/31 相鄰、0-turn 曾成功和 21/21 manifest，只是各自層級；本批真 Safari strict 仍 FAIL。

## 失敗分析與下一個必要單變因

機制進展是「真第三者問句不因當輪或前一輪同題而被當成偏好事實」在本批 5/5 真 selected，跨重啟 T4 仍成立；這是可反駁的窄產品觀察，不是通用的記憶理解。產品嚴格失敗有兩個不同位置，不能打包成一個追分 patch：

1. **優先的可見行動缺口**：T2 已選 `food_offer_generic`、`named_offer_accept`，最終卻成為「その話なら普通に分かる」，沒有接受或拒絕邀請。先做 read-only 路徑審查，界定 selected action 到最終日文的保留義務、正負控制與來源界線，再設計新的、未曝光的前瞻案例；不可重播 T2 或順便修改問句 gold。這直接關係使用者是否感到被接住。
2. **獨立的圖表校準**：T1/T4 的 `一回、` 並未建立第三者偏好命題，但不在事前有限裝飾語法。圖節點如實回 mismatch，所以 strict 失敗；後續要以新的表面驗證設計判斷此詞能否安全准入，同時保留「未知＋後接相反命題」會被拒絕的對抗性，不可直接放寬成字串包含。

若繼續同一問句 gate 的修正，開發期已有兩個有根據 preflight 修正批次，且本批已曝光，應列 `REVIEW_REQUIRED` 而不是在舊六題上再追分。總體產品仍有最初 0-turn 啟動 abort，後續即使新 semantic gate 通過亦不能刪。沒有證據可宣稱強 LLM 對照勝利、人評被理解感、正式 temporal holdout、長對話泛化、VRM／Function Calling 全鏈路或已解出人類方程式。
