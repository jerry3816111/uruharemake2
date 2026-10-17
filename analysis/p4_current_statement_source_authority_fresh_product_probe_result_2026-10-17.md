# P4 當輪陳述來源優先權：六輪 Safari 產品驗收

結論：**strict FAIL，保留可用的窄能力，但不得宣稱產品 gate 通過。** 這是首輪前已凍結的全新開發者六輪，不是獨立 holdout、人評或同模型 LLM 對照。原設計、逐字題目／gold、停止規則見 `research/p4_current_statement_source_authority_design_2026-10-17.md`、`datasets/p4_current_statement_source_authority_fresh_probe_2026-10-17.json`、`research/p4_current_statement_source_authority_fresh_probe_plan_2026-10-17.md`。首輪前 commit `1b638f1` 已推送；17/17 SHA manifest 核對通過。六句各在 Safari 送一次，0 retry；舊曝光題沒有重播，gold 與凍結程式未改。

## 真實結果與可見範例

隔離 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-gmreq6ze`。原始 `web_logs/conversation.jsonl` 恰六行，SHA-256 `3520654964bf3c7e09cc5de4fc848e20b465a47ed50c359b2e9ed3d8f6b1f452`。每輪 Safari 聊天泡泡及下方 graph 的 USER SIGNAL／UTTERANCE 已目視，六個 graph utterance 均與 raw reply／泡泡對齊；**未封存 Safari 截圖**，故這是操作觀察及原始 trace，而不是可重新檢視的畫面影像。

| 輪次 | 使用者輸入 → 真實可見日文 | selected 路徑／來源稽核 | 等待 | 驗收 |
| --- | --- | --- | ---: | --- |
| T1 | `後輩は玄米柚子ゼリーが好き。` → `普通に、後輩は玄米柚子ゼリーが好きなんだね。そのくらいでいいだろ。` | 新來源 chat；M31 未呼叫；圖上來源節點 `selected_or_visible_mismatch` | 12.146s | 主語、物品、肯定陳述可見保留；來源節點 strict 狀態 FAIL |
| T2 | `私は山葵おにぎりが好き。` → `いや、山葵おにぎりが好きなんだ。いいじゃん。そのくらいでいいだろ。` | 新來源 chat；非 food offer；同一 mismatch | 2.8839s | 本人偏好不再被當邀請、恰寫一筆本人 profile；來源節點 strict 狀態 FAIL |
| T3 | `母は檸檬黒糖プリンが好き。` → `てか、母は檸檬黒糖プリンが好きなんだね。そのくらいでいいだろ。` | 新來源 chat；同一 mismatch | 2.8552s | 第三者未寫本人 profile；來源節點 strict 狀態 FAIL |
| T4 | `後輩は抹茶玄米茶が好き？` → `後輩も抹茶玄米茶が好きか。そのくらいでいいだろ。` | 沒有新來源證書；M21 full planner 完成模型呼叫 | 12.6681s | **FAIL**：真問句沒有回答「目前不知道／無證據」，`も` 加入無依據比較；語氣可能有歧義，不把它誇稱為毫無歧義的事實斷言 |
| T5 | `山葵おにぎり、一口いる？` → `はいはい、おにぎりなら一口ほしい。今それくらいがちょうどいい。` | 原 `food_offer_generic`；沒有新來源證書 | 2.6701s | 食物邀請負控制命中，沒有 profile 誤寫 |
| T6 | `私は山椒味噌せんべいが好き。` → `一回、山椒味噌せんべいが好きなんだ。いいじゃん。そのくらいでいいだろ。` | 新來源 chat；同一 mismatch | 3.176s | 本人偏好恰寫一筆；來源節點 strict 狀態 FAIL |

四個肯定陳述的 `selected_plan`／logic core 確實來自新來源證書，`planner_path=current_statement_source_authority_p4`、M21 `deterministic_rule_plan`，M31 `not_applicable`，一般 planner 模型呼叫未完成；這**不是零模型完整回覆**，因仍有下游表面產生。T4 被正確排除於新證書之外，卻走到未保留未知狀態的舊 full planner。T5 原邀請規則仍正常。六輪的 `frame_shadow` 均報 preserved，但 T4 的語用／證據錯誤未被它捕捉，不能拿該欄位替代語義驗收。

四個來源節點的 `selected_plan_matches_logic=true`、`carried_certificate_matches=true`，但 `selected_visible_same_source_commit=false`。程式的這項 status 是將最終可見字串與裸 `expected_core` 作**逐字相等**；真實人格表面另外加了前綴與 `そのくらいでいいだろ。`，造成 4/4 `selected_or_visible_mismatch`。目前看得到的四句在主語、物品和肯定 speech act 上大致保留來源；不能把 byte-exact mismatch 擴大說成四句都語義篡改。然而凍結 gate 要求 graph 的來源承諾與 utterance 可核對，現有節點卻自己報 false，故 instrumentation／surface contract 仍未通過；零模型 stub 直接回裸 core 的測試沒有覆蓋真實人格表面。

## 記憶、重啟、時延與證據界線

每輪前後的 12 份 0600 row-ID／episode-ID 快照保存在該隔離 root 的 `evidence/snapshot-*.json`；profile row-ID 差為 `[0,1,0,0,0,1]`，新增項只屬 T2 `like/山葵おにぎり` 與 T6 `like/山椒味噌せんべい`；六個不同的持久 turn episode。T3 後按計畫停 PID 80916（run `358c18cbe631949e`），controller 原紀錄 `planned_stop=true`、程序已退出且 port vacant；同 root／DB 由新 PID 81411（run `6a784115cf649381`）重啟，session 也不同；T4 前 profile row-ID 集合與 T3 後相同。T6 後第二次 planned stop 亦為 true／退出／埠無 listener。正式 DB、原始 dirty checkout 均未使用；Safari 舊分頁未關，隔離服務目前停止。

六輪 user wait 為 `[12.146, 2.8839, 2.8552, 12.6681, 2.6701, 3.176]` 秒，6/6 ≤凍結的 20 秒，上述總和約 36.400 秒、最大 12.6681 秒。T4 full planner `planner_seconds≈10.1124`；四個來源輪免一般 planner，但沒有完整模型總呼叫數、token 或價格帳本，均記 **unavailable**。不能和上一批不同題目的等待時間做因果加速比較。

首輪前開發者零模型聚焦 5/5、受影響相鄰 61/61（2 個依賴警告）、compile／diff、隔離入口 0-turn 啟停、17/17 SHA 通過，只證明各自層級；六輪 Safari 是首次有真表面、真 graph、跨 session 與 writer 的產品證據。產品 gate 因 T4 的未知證據處理及四個來源稽核狀態而 FAIL。這些資料不支持「優於強 LLM」、普遍語用理解、正式 temporal holdout、人類被理解感、VRM／Function Calling 整合或人腦方程式成立。

## 下一步設計審查：分開兩個可歸因問題

1. **第三者真問句的證據授權（優先語義風險）。** 最小反例是 T4：否定來源證書正確，但下游 full planner 未把「第三者偏好未知」維持到可見回答。下一張卡先定一個有界、可反駁的問句 evidence/unknown-answer 變因；包含已知來源、未知來源、否定／引文、本人／第三者、問句與陳述負控制，明列人格自然度、成本及安全邊界。若需新 Safari，必須全新題目與 gold、首輪前凍結，不能重播 T4 追分。
2. **來源節點與人格表面的契約校準（獨立 instrumentation 項）。** 需決定裸 core 是否必須逐字等於可見 utterance，還是改成可審計的有界語義一致性；不得直接把任意裝飾文字都標 PASS。用真實 RightBrain 的聚焦測試及前後 trace 證明節點誠實，再開新的前瞻例子。這不能和問句語義修正混為一個因果變因，也不能回寫本批 FAIL。

依流程保留負結果；目前只完成本次產品 probe 的封存與同團隊非獨立設計診斷，下一變因尚未實作或通過驗收。
