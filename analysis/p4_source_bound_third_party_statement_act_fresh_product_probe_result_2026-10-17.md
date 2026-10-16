# P4 第三者陳述 speech-act：第二批前瞻 Safari 產品驗收

結論：**strict FAIL／REVIEW_REQUIRED**。這是修正後、首輪前凍結的全新五輪開發者案例；不是獨立 holdout 或人評。不要重送這五句、改 gold，或把單元／局部 T3 成功寫成產品可靠性。來源、門檻及停止規則見 `research/p4_source_bound_third_party_statement_act_fresh_probe_plan_2026-10-17.md`；首輪前 commit `4ddfe95`，22/22 freeze SHA 核對通過。

## 真實觀察

隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-shz__c7v`（0700，正式 DB 未用）；原始五行 JSONL SHA-256 `7b94a7cb75d9dfae5e867088ed5e2b3d6893f3ff3bd3be072126dea4c01170e5`。新 Safari 第五分頁的聊天泡泡和下方 graph `USER SIGNAL`／`UTTERANCE` 逐輪目視 5/5 與本表對齊；沒有留存 Safari 截圖，不能稱封存影像。每輪 exact input 各送一次，0 retry。

| 輪次 | 輸入 → 真實可見日文 | selected／新節點 | user wait | 逐輪判定 |
| --- | --- | --- | ---: | --- |
| T1 | `友達は生姜黒蜜ゼリーが好き。` → `友達の好みは知ってるよ` | `chat`；M31/M32 拒權；新節點未出現 | 26.9964s | FAIL：漏物品，無來源的「我知道」，且超過 20s |
| T2 | `私は梅しそおにぎりが好き。` → `ん、おにぎりか。じゃあ少しほしい。重くないならちょうどいい。` | `food_offer_generic`；M31 未呼叫；新節點未出現 | 2.9491s | FAIL：本人偏好被當成食物邀請；雖正確寫入本人 profile，回覆不忠實 |
| T3 | `姉は柚子抹茶プリンが好き。` → `姉は柚子抹茶プリンが好きなんだね。` | M31 `semantically_authorized`；`source_bounded_statement_repaired` | 13.7043s | 此有界路徑 PASS：第三人稱、物品、肯定 speech-act 與 graph 一致 |
| T4 | `友達は白桃麦茶が好き？` → `友達の好みは覚えてるよ。` | `chat`；新節點未出現 | 11.5485s | 未把白桃喜好寫成事實，負例隔離成立；但回答沒有說明未知，也沒有回答此物品，不能算語用品質成功 |
| T5 | `先輩は黒豆ほうじ茶ラテが好き。` → `先輩も:豆ほうじ茶ラテが好きなんだね。` | `chat`；M31/M32 拒權；新節點未出現 | 23.8365s | FAIL：`黒豆` 變成 `:豆`、不自然日文，且超過 20s |

來源追蹤：T1 的 M31 canonical 有 `友達` 與 `生姜黒蜜ゼリー`，但 `safe_surface_anchors_visible=false`、`proposal_or_repair_path_valid=false`，所以新模組所需的「M31 已授權同命題問句」前提不存在，最後一般 planner 的 `知ってるよ` 沒被攔。T2 的 source owner 准入與 profile writer 正確，但舊食物規則僅看到 `おにぎり` 就先選 `food_offer_generic`，既有 fallback 只在原規則無計畫時介入。T3 新模組原候選與 canonical 僅留 SHA，不冒稱模型自檢判斷；以來源規則修正 M31 response、selected 與 surface。T5 再次顯示 M31 拒權後會落回一般 planner／語言修補：原始 selected `core_message_jp` 是 `先輩も:black豆ほうじ茶ラテが好きなんだね。`，最後可見回覆變成 `:豆`；`self_correction_applied=true` 不能當成品質通過。M31 缺失 nested self-check 的預設 false 不是模型明確否決的證據。

## 記憶、重啟、成本、證據層級

隔離 DB 每輪 before/after row-ID 快照都在該 root 的 `evidence/snapshot-*.json`：profile row-ID 差 `[0,1,0,0,0]`，唯一本人 `like/梅しそおにぎり`，第三者／問句未寫本人 profile；五個不同的 turn episode。T3 後 controller planned stop 真確認 PID 71192 退出、埠無 LISTEN，再以同 root／DB 的 PID 72244、不同 run ID／session 重啟；T4 前 row-ID 集合未變；T5 後第二次 planned stop 也確認退出、埠空。冷啟包含在 T1 等待；5 輪只有 3 輪 ≤20s。M31 完成呼叫 T1/T3/T5；full planner 完成呼叫 T1/T4/T5；完整生成 token／統一模型呼叫總數與價格帳本此批未取得，標記 unavailable，不由局部欄位外推。

開發者零模型測試 6/6、相鄰回歸 143/143（9 個依賴警告）、compile/diff、0-turn 產品入口以及此批中 T3 的真生成，只證明各自層級。五輪 `frame_shadow` 皆回報 0 violation，卻沒有偵測到上述語義錯誤，因此該欄不能充當產品正確率。完整 Safari 產品 gate 因 T1/T2/T5 語義與 T1/T5 時延而 FAIL；即使 graph／writer／重啟子項正確，也不得宣稱同模型優勢、人類被理解感、正式 temporal holdout、VRM/tool 完整交付或「人腦方程式」成立。

## REVIEW_REQUIRED：下一個設計審查

同卡已做兩個有根據的修正批次，本批仍 FAIL，依 `DEVELOPMENT_WORKFLOW.md` 不再追加第三批規則追分。最小反例 T1、T2 表示不同上游路徑共同缺乏「明確當輪偏好陳述」的來源優先權：M31 拒權時落入一般 planner；本人偏好遇到食物詞時先被舊邀請規則奪權。下一次審查可考慮**單一優先權變因**：對逐字可驗的單句 `XはYが好き。`，在一般 planner／M31 前以來源、owner 與問句／否定／引文／假設／多子句負控制授予有界陳述承接；明列這是 source-rule authority，絕不改稱 M31 模型授權。另一選項只修 M31 錨點或只修食物邀請詞，兩者各不能解另一反例，合併不再是單一變因。需先評估安全負例、人格自然度、成本與新未曝光案例，凍結設計後才准另開產品驗收；本批原結果永久保留。
