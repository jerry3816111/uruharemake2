# M43：已確認的理解，必須改變下一個說話行動

日期：2026-08-27。結論：**有來源的確認收束機制通過；整體回饋閉環仍未完整通過。**

## 這次實際改變了什麼

M42 曾記住使用者的支持，卻在 `Yes, that's exactly right.` 後繼續追問。
原因不是沒有漂亮的日文：M28 只認少量完整 token，讓當輪的「確認」失去回覆
主導權；V2.13 可能再開泛用澄清，M39 又可能要求重做上一輪策略。

M43 分開三件事：上一輪已觀察到的回饋、本輪正在做的對話行動、仍待確認的
心理假設。只有「已有支持且連結上一輪」和「整句只有確認，沒有新問題」同時
成立，才用短日文承接，禁止多開不必要確認。M39 仍檢查角色、語氣與無依據補充，
但這輪應檢查承接，而不是要求重新執行前一輪的陪伴／澄清。

`已連結的支持 → 整句確認／新內容分離 → 當輪行動 → 最後日文 → 下一輪可追溯狀態`

- 訊息含新要求、引用、否定、疑問或未解析內容時，交回原有流程；不是看到 yes 就蓋掉。
- 只在待確認事項有「真的說出口的問題」與相同 response prediction ID 時收束那個事項。
  沒有連結、舊版未綁定、其他未知事項仍保留；不把回覆被認可當心理事實被證實。
- 原 M27/M37 回饋判定、歷史關係與人格資料未被回寫；不讀聲學訊號、不加私密經歷。
- 三種有限承接取決於當輪是否道謝及已確認策略，不宣稱自由開放域自然度。

## 可歸因的封存對照

實作前封存 24 個 zh/en/ja 作者編寫案例及判準，實作／測試／evaluator 再封存，
正式只跑一次，全部 frozen gates PASS。這些是**研究者自編、可控 typed-feedback
契約**；雖與既有 M30–M42 題庫完整原句不同，但不是獨立作者或盲式 holdout。

| 項目 | M28 原有收束 | M43 |
| --- | ---: | ---: |
| 當輪是否可以收束的判斷 | 15/24，62.5% | 24/24，100% |
| 9 個純支持表達 | 0/9 | 9/9 |
| 不應收束的 15 個案例被錯誤接管 | 0/15 | 0/15 |
| 精確 pending 收束／保留 | 無本次對照主張 | 24/24 |
| 原 outcome 不變、保護路徑不變 | — | 全部通過 |

新增檢查 median 0.096ms、p95 0.136ms；新增模型呼叫 0；raw trace 原句寫入 0；
心理事實寫入 0。這只是新增檢查成本，不是整輪速度。

對照用同一輸入、提供給兩組的同一上游 outcome、同一原始 plan／pending／model。
**不是單純 LLM vs UruhaBrain，也沒有證明上游支持判斷、人類被理解感或全面優勢。**

- Reserve：`datasets/m43_supported_feedback_closure_reserve_v1.json`
- Protocol：`research/m43_supported_feedback_closure_protocol_v1.json`
- 實作前鎖：`research/m43_preimplementation_reserve_freeze_2026-08-27.json`
- 實作鎖：`research/m43_implementation_freeze_2026-08-27.json`（20 個檔案）
- 唯一正式結果：`analysis/m43_supported_feedback_closure_reserve_raw_2026-08-27.json`

## 單元、契約與回歸

- 13 個新增 M43 core/evaluator 測試，加原選定 210 個 M16–M42/personhood 回歸：
  **223/223，29.61 秒**；3 個既有依賴棄用警告。不表示全歷史測試套件全部通過。
- 另 1 個只改 CSS 的呈現不干擾契約通過。
- 覆蓋整句範圍、引號／否定、新要求、保護／事實路徑、回饋不變、精確關聯、
  不提升心理事實、M39 當輪行動、圖節點／連線、所有既有 installer 共存、
  真正 runtime 的 final snapshot／same-cycle history；runtime 契約使用 fake generation。
- 只有單元／契約驗證到「一個精確綁定、真的說出口的舊 pending 被關閉」；本次
  Web 沒有產生這種合格 pending，所以**不能把這部分寫成 Web 全流程成功**。

## Safari 真實 10 輪：逐輪看回覆與下方圖

本機原模型及真實 Web 管線，測試資料全部位於 `/tmp/uruha-m43-safari.xZvLgA`。
每次貼上後先確認輸入，再按 Send；10 輪皆是有效預期輸入。

| 輪 | 輸入／目的 | 真正結果與判定 |
| --- | --- | --- |
| 1 | When my presentation gets stuck, stay with me instead of giving advice. | 回陪伴；但 M37 不認 presentation trigger，沒有可持久重用關係。泛化缺口 FAIL。 |
| 2 | Yes, that's exactly right. | **うん。じゃ、その感じでいこう。** M43 有連結支持、抑制新泛用澄清，PASS。 |
| 3 | When the report gets stuck, stay with me instead of giving advice. | 原支援情境形成 task_stall → share_arousal 候選；尚未當真。 |
| 4 | 沒錯，就是這樣，謝謝。 | **ん、伝わってたならよかった。** 已確認的關係真正保存，PASS。 |
| 5 | The report has stalled again. | 命中已保存關係，回 **進んでないのか。まあ、今はうちがここにいる。**；但下一輪 pending 被 M32 清掉。 |
| 6 | その通り、ありがとう。 | 原 pending 不存在；M43 不偽造支持，仍回 **ん、そこもう少しだけ聞かせて。** 產品體驗 FAIL。 |
| 7 | 我現在只想讓你聽我說，先不要給建議。 | 回 **うん。今は方法出さないから、そのまま話して。そのくらいでいいだろ。** 傾聽有實現。 |
| 8 | その通り、ありがとう。（與第 6 輪同句） | 這次有有效上一輪 prediction，回 **ん、伝わってたならよかった。** PASS；其他未綁定 pending 沒被清除。 |
| 9 | Exactly, but now tell me one practical next step for the report. | M43 正確不收束；但原 planner 仍回泛用追問，沒有給下一步。新要求完成度 FAIL。 |
| 10 | Who are you? | **うちは一ノ瀬うるは。そこは間違えてない。** 角色身分回歸 PASS，不等於真人宣稱。 |

4 個 Web 純支持回合中，3 個有有效上游連結、3/3 收束；缺連結的 1 個仍失敗。
不可只報 3/3 而省略第 6 輪。第 9 輪亦不能因為 M43 沒吞新要求就說整體正確。

10/10 可見回覆皆是日文；人工由開發代理逐句檢查，不是盲式人評或自然度量表。
實際 user-wait **2.014–19.6267 秒**；短確認仍可能等約 10 秒，因為原規劃路徑仍會
先執行，M43 不主張延遲改善。

## 圖表、資料隔離與可用性

- 10 輪實際看下方圖；第 2 輪展開 M43 node。49/49 可用 M39/M40/M42/M43/
  response-binding payload 在 logic、主圖來源與同 cycle history 相同；沒有補造缺失 node。
- M43 node 接到實際 decision stage；binding 是真的 post-emission 檢查，不是假裝已寫入。
- 整句原文不在 adaptive store，留下的是 typed relation、digest、信心與歷史。測試
  dialogue／episodic DB 本身仍有原句，**不是說所有儲存都沒有原文**；它們全部隔離。
- 測試程序實際開啟的 Chroma 檔案只在隔離目錄，沒有開啟正式 DB。
- 原始 checkout 與安全 worktree 的兩個正式 Chroma SQLite 檔案，測前／測後
  SHA-256 完全相同；雜湊留在呈現驗收證據中。這不是對其他背景程序的全面監控。
- 初版圖卡在 Safari 因繼承深色文字而不清楚，失敗截圖保留；另加只改 CSS 的新
  presentation overlay，不改 frozen core／題庫／結果，也不重跑正式測試。
- 呈現修正額外跑 2 個 session、共 4 輪真實 Web，重複「先傾聽→確認」案例，
  使用同一隔離測試 DB；這是 CSS QA，不是 4 個新 holdout。20/20 node payload
  在 logic／runtime／同 cycle history 一致；4/4 重建圖皆有唯一已連線 M43 節點且
  未超出圖表預算。最後的四個狀態、標題與箭頭都經 Safari 截圖目視核對。
- 第一次呈現服務輸出曾有一個無 turn ID 的 Ollama timeout 警告，不能歸到某一輪；
  四輪最後皆有完整紀錄。不能寫成全程零警告。
- 整張大圖仍擁擠且含大量工程名詞；新增簡明卡不等於整個 outsider UX 已完成。
- 同一 Safari 分頁使用，27 個分頁沒有增減。已停止舊 M42／初版 M43 測試服務；
  保留全部檔案及測試資料。關閉分頁不會刪掉成果。

精簡證據索引：`analysis/m43_safari_isolated_web_evidence_2026-08-27.json`。
呈現修正另見 `analysis/m43_readability_web_evidence_2026-08-27.json`。
最終截圖：`analysis/m43_safari_readable_flow_verified_2026-08-27.jpeg`。
目前隔離展示：`http://127.0.0.1:7882/?m43readable=1`；不是正式部署。

## 下一個必要工程：M44 已執行行動的後續回饋紀錄

已只讀定位：`uruha_brain_mac.py` pending 決策段在 M29/M31/M32/M33 的
`suppresses_new_pending_prediction` 任一為真時清掉 selected；第 5 輪 M32 以字面
repair 接管，再由 M39 真正實現 M37 陪伴，但 pending 仍然是 null。

下一步只修「真的說出口的已驗證策略，必須留下可供下一輪驗證的紀錄」，不能
把純字面回覆都當已執行心理策略，也不能從使用者的後續肯定反推前一輪證據。
參見 `research/m44_executed_action_feedback_plan_2026-08-27.md`。

presentation 泛化、新要求辨識、第三者早餐角色錯置、拒絕句無根據意象、延遲與
大圖易讀性仍是另外的未完成事項。M43 不是人腦方程式完成，也不是整體聊天完成。
