# P4 完整當輪偏好陳述：來源優先權設計審查

狀態：2026-10-17，**新產品工作項的設計定案；同團隊非獨立審查**。這不是前一張卡的第三次追分。前兩批的 gold／結果／凍結 commit 原封保留；第二批五輪 `37babe1` 為 strict FAIL／REVIEW_REQUIRED，不重播曝光案例。

## Before、問題和唯一變因

第二批原始 Safari T1 `友達は生姜黒蜜ゼリーが好き。` → `友達の好みは知ってるよ`，M31/M32 拒權後走 full planner，漏掉來源物品且假裝早知，26.9964s；T2 `私は梅しそおにぎりが好き。` → `じゃあ少しほしい`，舊 inline `おにぎり` 規則將本人肯定陳述當邀請；T5 `先輩は黒豆ほうじ茶ラテが好き。` → `先輩も:豆…`，M31/M32 拒權後 full planner 損壞來源字，23.8365s。來源與逐輪 row-ID、graph、成本詳見 `analysis/p4_source_bound_third_party_statement_act_fresh_product_probe_result_2026-10-17.md`。T3 的已授權 M31 表面修正僅是局部成功，不足以處理兩條失敗路徑。

單一可歸因變因：**在產品路徑對完整、直接、單句、逐字可驗的當輪偏好肯定陳述授予有界 source-rule authority**。同一證書供早期 signal／rule seed 與 M29 競爭權限使用；不把它稱作 M31 模型授權，不擴寫長期記憶。兩個 hook 是同一來源權限決策的接線，不是分別對食物和第三者加答案表。先前的 M31 授權後修正仍保留給不獲新證書的路徑。

## 來源證書與資料流

- 本人 `私はYが好き。` 等只沿用現有 postposed-aware profile owner admission 和有界物品 seed；須一筆本人 `like/Y`、source-span／value hash 精確一致，疑似人名、問句、否認、記憶要求、多子句均不授權。
- 第三者限明列關係稱謂作主語的完整 `XはYが好き。`；X/Y 為原句逐字 span，Y 限日文字元、不含內嵌 `は`、引用／傳聞／條件／否定／第二句，且 X/Y 長度有界。這只證明「使用者本輪如此說」，**不證明第三者客觀真實喜好**；不可寫入 user profile。未知姓名／代詞／歧義及非日文留原路，不擅自補完。
- 證書只含 owner、statement/affirmed、來源／X／Y hash、明確來源型別、准入理由及 raw-free provenance；不保存多一份原句。回覆以同一來源重建自然日文肯定承接，不聲稱事先知道、不把物品換給うるは或使用者、不得把陳述改問句。人格／最終日文 guard 照舊。
- `_rule_based_plan` 先算原規則：protected intent／scene、factual／profile／明示 correction／memory、真正 offer 一律維持原路；只有來源證書成立且原規則無計畫或把完整肯定句誤判為 `food_offer_generic`／同類 food offer 時，才在同一產品包裝優先使用證書，使 signal 和實際 deterministic plan 看到一致的 speech act。含危機／性／暴力等 protected lexical cue 的句子即使字形符合也 fail closed，不得在早期 classifier 前奪權。證書不存在完全交還舊路。
- 在 M29 候選建立後，只有原候選要求 projection、未有 M28 surface authority、digest 對上且 M33 source-atom unavailable 時，才撤其投影需求，讓同一來源 plan 與 M31／一般 planner 競爭。M22 safety/protected low-road、grounded memory、M33、其他更高權限仍依核心原序；M18 adaptive fast path 可能在真正 plan 前搶權，須在測試和圖上辨明、不得把候選視為已選中。若最終未真選來源 plan，圖不得宣稱已提交。
- 高 prediction error 也可能使 `_high_low_road_route` 改選 low-road；`_rule_based_plan` 同時被 low-road builder 和 planner critique repair 呼叫。新證書不能被寫成「任何上下文必然選中」，須以跨 session／高誤差的負控制及實際 selected route 判斷邊界。
- 不改 `uruha_brain_mac.py`、M31/M32 核心、writer、正式 DB、舊 gold／manifest／報告。允許新產品 overlay、新聚焦測試、既有產品入口僅在 `__main__` 安裝（保留舊 launcher 匯入式 preflight）、新前瞻資料／結果、任務卡。舊 source/entry 的 SHA 屬歷史 commit；新版本另行凍結。controller／launcher 不複製、不改其安全邊界。

## 反證、失敗分支與驗收

先做無模型：不同 X/Y 的本人、第三者，至少一個會命中舊食物詞；早期 signal、真 selected、最後日文、graph 的來源與 speech act 一致，第三者 writer 0、本人只寫本人來源。負控制須包括真食物邀請、真正第三者問句、否認／撤回、引文／傳聞／假設／多句／後句反駁、歧義主語與客體、明示記憶要求、關係問句、safety/拒絕/grounded recall、中文與英文。負例證書 0 不能代替最終路由與可見語義檢查。不得降低原有 test 斷言或將既有 `frame_shadow=0` 當語義成功。

通過聚焦與受影響相鄰回歸、`compileall`／`git diff --check`、隔離 0-turn 後，**另選未曝光**且不含上面曝光 X/Y 的開發者案例；逐字 input/gold、0 retry、每輪 user wait ≤20s（含冷啟）、一次同 DB 真重啟、row-ID 集合差、全輪 graph／bubble／raw／selected 語義、模型呼叫／token／延遲／價格可得欄位事前凍結並在首輪前 commit+SHA。每個語義、記憶、程序、安全、graph 或成本 gate 不達就整批 strict FAIL，保留所有反例，不重試題目追分。新證書所選快路若主張省呼叫，須實際 trace 顯示 M31=0、full planner=0；完整成本帳本缺值標 unavailable。只有同一類型的未曝光新前瞻 Safari 輪次才可稱產品層證據，單元/mock 不替代。

若早期 source-rule 包裝改變 protected/M33/grounded 優先序、M18 在目標正例搶權、第三者寫入本人 profile、或最終語義仍不一致，先停在 `REVIEW_REQUIRED` 並比較撤回整個優先權或縮窄准入，不再沿曝光題追加例外。就算本批通過，僅證實窄日文直接陳述的產品路徑；正式同模型對照、人評、temporal holdout、長對話泛化與 VRM/tool 完整整合仍未證明。
