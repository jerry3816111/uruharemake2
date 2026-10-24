# P4: hash 開頭的來源准入（前瞻產品修正設計）

狀態：2026-10-17；同團隊、非獨立設計審查。這不是正式研究規格、真人自然度標註或既有六輪結果重評。

## 修改前的可反駁問題

已封存六輪 Safari 的 T1，selected core 是 `同僚におにぎりを一口勧められたのか。で、なんて返した？`，最後泡泡卻是 `先に、` 加上該句；舊 reported-offer audit 仍標 `visible_report_preserved`，整批 strict FAIL。來源是 `RightBrain._finalize_surface_reply` 以 intent、surface act、輸入字元和取八種固定開頭；該輪 modulo 8 為 5。這個附加操作沒有選案、使用者文字、記憶或語境證明，且發生於 P2 compact 表面提交適用範圍之外。原六題、gold、raw、舊程式與失敗結論不改、不重播。

## 單一變因與因果界線

只在新 opt-in P4 入口攔截「舊 finalizer 在已 sanitize 的完整候選前，純按 hash 新添固定開頭」這個附加操作。若舊輸出逐字等於八種前綴之一加原候選，改回原候選；若上游候選原本包含 `先に、`、`一回、` 或其他開頭，原文保留。這不是依測試句挑答案，不改 selected plan、source routing、planner、模型/參數、記憶、protected route、日文 guard 或既有 P2 compact path。八種開頭採同一來源規則，不另處理 T5 結尾、甜食 core 語法或人格全面自然度。

新獨立 graph audit 觀察實際 final 與前綴准入記錄；對 reported-offer 有界路徑，再要求 final 不含「selected core 外加的固定前綴」，不能再單靠舊 audit 的寬鬆 `_PREFIXES` 宣稱 strict PASS。它只證明附加來源，不保證上游自己寫出的時間詞一定合理。所有新節點只保留類型、數量與 SHA，不複製原始對話。

## 事前控制與成功／失敗

- 正控制：上游候選本來有 `先に、`／`一回、` 且句子有明確次序；finalizer 不得移除既有文字；P2 compact、memory/support/structured 提前返回仍等價。
- 負控制：第三者引述邀約、直接向角色邀約、第三者偏好未知、一般聊天；當舊 finalizer 只因 hash 新添前綴時去掉，selected act 和其他 core 字元不變。注入假 final 的 reported-offer graph 必須 fail closed。
- 聚焦 gate：每個候選的輸出差異只能是移除舊 hash 前綴；無額外模型呼叫／事實寫入；入口安裝順序可重複且舊 frozen 8/8 hash 不變。
- 相鄰 gate：P2 contextual expression、reported/direct offer、未知來源與 protected path 不退步。失敗保留，不放寬舊 gold。
- 全新 Safari gate（資料另先凍結）：逐字 0 retry、同 DB planned restart、每輪 ≤20 秒、泡泡／utterance／新舊 graph 實際核對、第三者與直接作用域各自正確、完整 profile collection 的 ID／metadata／document／embedding SHA 逐輪不變（另以獨立只讀快照取證）、episodes 持久。任何一項未成，整批 strict FAIL。

允許新增：產品限定 overlay、入口／launcher、聚焦測試、下一批全新資料／計畫／freeze、獨立完整 profile 快照及測試、最後結果／任務卡。禁止改：`uruha_brain_mac.py`、原 reported-offer module／gold／freeze／raw、正式資料、原始 dirty checkout、無關 `output/graduate_application_report/`。首次真輪前須檢查 SHA/PR head；若失敗，至多兩個有根據修正批次，不能換句重跑追分。真實生成成本以實際 calls、tokens、runtime wait 回報；零模型測試不能冒充生成或人評。
