# P4 M46 審核判斷介面：前瞻比較計畫

狀態：設計審查後、模型呼叫前。本文與後續 config／dataset／scorer／離線 tests
必須在**第一次 scored call 前 commit**；正式結果不可回頭改本計畫。

## 問題與單一變因

已曝光固定封包中，現有 M46 8/8 呼叫完整，卻只保留 1/3 有效方案，且對一個
助理無授權代操作錯誤的類別理由漏判；無審核反事實則錯放全部五個預構造負例。
詳見 `analysis/p4_m46_reviewer_decision_interface_design_review_2026-09-30.md`。
本研究只問：對**同一個**來源與已選定行動候選，把 M46 審核輸出從 14 個全真
布林欄位改成精簡、證據錨定、能區分未知前提與行動者的判斷介面，是否能在
成本上限內更可靠地保留有效方案、辨出無效原因？

A＝現有 `REVIEW_SYSTEM`、`review_schema`、`inspect_goal_progress`；
B＝新的單次 reviewer prompt＋schema＋parser／score。兩臂皆用同一
`qwen3.5:9b`、相同完整 source／selected plan、共同 M51/M52/M53/P4-AV
deterministic guard 與隔離 M39 exact surface 檢查，既有產品 guard 與模型
均不改。兩臂唯一差別是**review decision interface 整體**；不能拆稱某一句
prompt 有效。B 若通過也只為元件候選，不替換產品 M46。

## 資料、標註與可反駁性

全新 developer-authored 繁中／英／日完整封包 10 個可交審：3 個內容與日文
均明確有效，7 個分別是 wrong-task、unsupported specificity、private
inference、non-action、無 receipt 助理代操作、虛構執行前提、不自然日文
表面；另有 1 個共同 deterministic guard control，兩臂皆不送模型。
每個封包先有完整 source、固定兩候選 batch、selected plan、內容效用、
日文表面、行動者三層的開發者事前 gold、合成 valid/invalid label、
expected failed axis 與文字理由。這些是**新字串但已曝光類型的開發 proxy**，
不是獨立語義 holdout。對自然度的異議在 reviewer 呼叫前處理，
不能事後修改 gold；若有不可裁定項，先凍結為 uncertain，放行一律當風險，
且不能拿它湊足 3 個 valid 分母。舊九題只作已曝光回歸，不重跑作新分數。

每個新封包必須先通過共同 selector parity、來源 id/span、M46 structural、
M53/P4-AV label 和隔離 M39 exact guard；否則對兩臂皆不可交審。
預期 10 可交審、1 guard control。正式前離線 freeze test 若不符，停止在
0 model calls，修資料／規格後重新凍結，而非跑一部分再換題。這是
developer-authored proxy，不是人評、自然分布、正式 temporal holdout。

## 不變條件與執行上限

- `qwen3.5:9b` digest 固定為
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`；
  Apple M2 Pro 12-core／32 GB，本機 Ollama，無外部服務或正式資料庫。
- 兩臂 `temperature=0`、`seed=20260829`、`num_ctx=4096`、
  `num_predict=320`、`stream=false`、`think=false`、`keep_alive=30m`；
  同一固定 case/arm 順序，預熱一次另記，不計 case wall。
- 每封包每臂恰一 scored call，最多 `10 × 2 = 20`；0 retry、無續跑。
  任一傳輸／parse／token 核帳失敗，立刻保留 partial 並停止；已完成的
  quality failure 則保留並繼續唯一執行，才可看到錯誤類型。每次 request
  timeout 30s，但 reviewer-only 的產品成本診斷門檻為逐案 `≤20s`。
- 原 M46 與新 B 都看不到 gold、category、expected failed axis；
  兩者的 source id/span 和 selected plan bytes 必須一致。正式 runner
  不可再生成候選、不可改原 batch。模型回覆不得改 plan 或說話內容。
- 原產品 M51/M46/M45/M39、persona、記憶、正式 DB、已凍結資料、
  原 dirty checkout 及外部部署都不變；沒有 Safari 或 Function Calling 操作。

## 絕對門檻、比較指標與分支

B 的元件 gate 為：10/10 scored calls 都完成、JSON 可解析、source identity
exact、token 核帳完整；3/3 明確有效方案保留、7/7 無效方案阻擋，
且 7/7 將事前指定的錯誤軸明確標為 `fail`、primary 指向該軸，非全拒絕；
`uncertain` 只能保守阻擋，不能計作辨出原因。`evidence_jp` 的 quote 檢查只證明
有逐字來源錨點，**不證明引文語義充分支持該軸**；此 gate 僅是 axis-label hit，
不是獨立人類理由評分。max reviewer-only wall
`≤20s`。A 用**相同**絕對 gate 逐項報，另報 A/B paired-only improvement、
paired-only regression、錯誤類型、prompt/completion tokens、median/max wall，
不能因 A 失敗就放寬 B。1 個 guard control 應兩臂均阻擋且 0 call，
不可算 reviewer 的功勞。B parser 的 `uncertain`、欄位矛盾、無來源或
對應理由不足一律 fail closed；「只是拒絕」不等於辨出原因。
原版沒有 B 的 `primary_failure` 欄；其 reason 數是事前多對一舊布林映射的
**diagnostic proxy**，B 則是明確 axis-label hit。兩者分別報，不能說成對稱的
人類理由品質評分或逐字同構 gate。

若品質失敗、超 320 tokens 截斷、或成本失敗，保存 `REVIEW_REQUIRED`
與最小反例；停止此 reviewer 小修路徑，另審兩階段架構，而不是第三次
改 prompt／gold／timeout。若 B 元件全過，只取得**全新自然 M51 生成**
與相同候選 A/B 比較的資格；必須再做全新隔離完整 runtime／Safari
驗收實際日文、來源、node graph、durability 和完整 `≤20s`，才可能選用。
即便 reviewer-only `≤20s`，兩階段也可能已超產品預算；本實驗不證明
使用者受益、強 LLM 優勢或任何人類方程式。

## Freeze 與稽核

先新增資料、精確 contract、離線 scorer、無模型測試與 `CURRENT_TASK.md`，
做 diff review、指定測試並 commit 記 full SHA。任何模型前再新增一次性
runner 與 fake transport tests，另 commit 記 full SHA；正式 preflight 要
核對前述 SHA、依賴 hash、模型 digest、硬體、固定順序與結果檔不存在。
之後只能唯一執行、逐 call checkpoint、保存成功或失敗；不覆寫、不續跑。

## 2026-09-30 首次 freeze 後、0 模型呼叫的修訂

原 freeze commit=`fa298078a47900c1963c252cf62875dc036cb711`。
獨立只讀審查在模型前指出兩個契約風險：B prompt 允許從英文 source 逐字引用，
舊 parser 卻把引文裡的 ASCII 字母當成非日文拒絕；3 個 valid 表面均用
`〜てみよ`，可能與「自然口語」gold 有歧義。這不是看到模型輸出後追分：
**目前新 scored calls=0**。修訂只做：允許 exact 2–40 字來源或 final
instruction 引文保留原語，外圍解釋仍必須日文；將 selected packet 中
較生硬的 `〜てみよ` 改為較明確的口語 `〜てみて`，並同步假回覆測試。
所有 source、任務語義、候選機制與順序、gold label／預定錯誤軸、
模型／token／call 上限、成功／失敗門檻不變。未選中的對照候選保持原樣。
這仍是開發者語感判斷，沒有獨立日語真人評分；若正式模型對自然度仍有
分歧，保留反例而非事後改 gold。修訂後再跑所有離線／相鄰測試、commit
新的 freeze full SHA，runner 必須綁**新** SHA，舊 SHA 保留可追溯。
