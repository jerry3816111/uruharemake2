# M44：讓真正做過的回覆，接得住下一輪反應

2026-08-27。本機 bounded 行動紀錄機制與 Safari 回饋連結驗收完成；
**實用建議交付仍失敗，不能說整體對話系統完成。**

## 為什麼這是必要進展

M43 第 5–6 輪曾出現：系統記住「報告卡住時陪我」，也真的陪伴了，卻沒留下
待驗證紀錄；使用者說「その通り、ありがとう。」後，它又追問。

原因是 M32 字面層清掉 pending，最後 M39 又確實完成 M37 選出的陪伴。
M44 補的是**最後行動→下一輪後果**，不是事後編出一段思考過程。

`已確認約定 → 當輪選擇 → 最後真的說出口 → 保存待驗證紀錄 → 下一輪支持／否定／未知`

## 改了哪裡、沒有改哪裡

- 新增獨立 module、installer、Web 入口與 runtime 圖卡；M37–M43 frozen source 未改。
- 只有當輪仍命中 active、未過期的 M37 已確認關係，decision／branch／policy／
  input digest 一致，且 M39 確認最後可見日文真的做了該策略，才補缺失紀錄。
- 保留原有 pending；已有同 ID 的 ledger／receipt 也不覆蓋。純確認、新話題、
  未知來源、錯策略、錯 digest、安全／事實路徑都不能冒充已執行。
- typed receipt 上限 32，記錄來源 ID、回覆 digest、時間、原關係信心；可以保存／
  重新讀取。只限下一個使用者 turn，過期用既有 uncertain 路徑處理，不硬算認同。
- 下一輪判定仍用既有 M27/M38；建立紀錄本身不加成功分、不提高關係信心或 TTL，
  不把已確認關係冒充 implicit prediction 的校準樣本。心理事實寫入為 0。
- 後寫入狀態另有 receipt node，不回寫早先規劃觀察；最後 model snapshot、
  owner blackboard 與同 cycle history 一致。沒有把完整對話寫進 adaptive store。

## 分開看三層證據

### 1. 單元／契約與回歸

233/233 選定測試通過，34.14 秒，3 個既有依賴棄用警告：
9 個新 M44 測試 + 原 223 個 M16–M43/personhood 選定測試 + 1 個呈現契約。
不是全歷史套件或 production readiness。

包含 gate 反例、冪等、舊 outcome 不覆蓋、後續三種結果、過期、typed 清理、
graph／同 cycle mirror、磁碟 roundtrip。runtime 契約用 fake generation、真正 M39
checker，以及**明確注入 M32 missing-pending 故障**；它不是自然生成端到端證據。
開發中發現原 fake right brain 根本不跑 M39，已修正測試接法，未降低產品門檻。

### 2. 一次封存的 typed emission 對照

實作前封存 24 個作者自編案例；233 個測試後封存實作，正式只執行一次。
這些是具已知最終輸出／M39 audit／M37 state 的資料契約；fixture 設計也由同一
開發代理完成，**不是獨立 holdout、不是新 LLM 問答能力對照**。

| 指標 | 原有 M43 最後狀態 | M44 |
| --- | ---: | ---: |
| 紀錄應否新增的契約正確數 | 19/24 | 24/24 |
| 5 個合格但缺失的紀錄 | 0/5 | 5/5 |
| 19 個不該新增的案例誤登記 | 0/19 | 0/19 |
| 後續有判準的支持／否定／未知 | 原缺 pending | 5/5 |

全部事前 gates PASS；原參數／關係／既有 ledger 保留，新增模型呼叫 0、raw 0、
心理事實 0、implicit 校準樣本膨脹 0。新增 core check median **0.051ms**、p95
**0.167ms**，不含磁碟保存，也不是整輪延遲。

### 3. Safari 真實 9 輪

全新隔離 session `20260827_224641_b6aae58e`。每輪先核對貼上文字再送出，
實際觀察回覆和下方圖。這是已知問題的真實回歸，**不是未見情境 holdout**。

| 輪 | 使用者輸入／目的 | 實際結果 |
| --- | --- | --- |
| 1 | When the report gets stuck, stay with me instead of giving advice. | 陪伴；先形成候選，M44 不覆蓋既有 prediction。 |
| 2 | 沒錯，就是這樣，謝謝。 | `ん、伝わってたならよかった。`；M37 約定確認保存。 |
| 3 | The report has stalled again. | `進んでないのか。まあ、今はうちがここにいる。`；原 pending=null，M44 真正補出 turn 3 紀錄並存檔。 |
| 4 | その通り、ありがとう。 | `ん、伝わってたならよかった。`；turn 3 紀錄變 supported，M43 正常承接，不再追問。 |
| 5 | The report has stalled again. | 再陪伴，建立另一份 turn 5 紀錄；turn 3 的成功保留。 |
| 6 | You misunderstood; give me one practical step I can take now. | turn 5 被否定，M34 從 share_arousal 改選 solve_regulation。但只回「一緒に決めよ」，**沒有交付步驟，FAIL**。 |
| 7 | The report has stalled again. | 沿用未被永久撤銷的約定，建立 turn 7 紀錄。本測試不能把一次「現在給步驟」解讀成永遠撤銷偏好。 |
| 8 | 明天有課。 | `明日に授業があるんだね。`；turn 7 為 uncertain，不冒算成功。內容保留，但「明日に」不如「明日は」自然，列為表達限制。 |
| 9 | Who are you? | `うちは一ノ瀬うるは。そこは間違えてない。`；既有角色身分回歸，M44 不新增紀錄；不等於真人身分證明。 |

三份新紀錄最後分別是 **supported、contradicted、uncertain**，沒有把舊失敗洗掉。
一般對話 scope 的 share_arousal reliability 從支持後的 0.6667 降至否定後的 0.5；
換話題只加 uncertain=1，mean 仍 0.5。這是少量操作性 Beta 計數，不是人類心理機率。
implicit 有效校準樣本仍 0，門檻仍 insufficient_evidence，沒有偷加證據。

9/9 可見回覆為日文；未做人類盲評，不宣稱每句自然度滿分。user wait
**2.0183–14.2507 秒**；第 4 輪短確認仍等 10.1783 秒，沒有宣稱速度已解決。
本次真正補紀錄的 core check 0.633–1.093ms，仍不含磁碟保存。

## 圖表與資料安全

- 56/56 可用 M39/M40/M42/M43/M44／binding payload，在 logic、runtime 主圖與
  同 cycle history 相同。9/9 圖有唯一已連線 M44 receipt node；3 個 outcome node
  只出現在真正有該次結果的輪次；9/9 圖表預算通過。
- Safari 第 3 輪真正展開節點；簡明流程卡文字／箭頭可讀。但整張圖仍密集，
  右側原始預覽部分被裁切且有內容上限，不能宣稱完整 outsider UX 已完成。
- `/tmp/uruha-m44-safari.JZBsIK` 內保存 Web log、episodic DB、session DB 與
  adaptive store。只有測試 DB 被此程序開啟；兩個正式 Chroma SQLite 的 SHA-256
  測前／測後完全相同。測試 episodic DB 仍有原句，**不是所有儲存都 raw-free**。
- Safari 原有 27 個分頁沒有增刪。舊 M43 的 7882 測試服務已停止，檔案皆保留。
  目前隔離站：`http://127.0.0.1:7883/?m44safari=1`；PID4142、PTY80022，續接須重查。
- 觀察到兩個沒有 turn ID 的 Ollama timeout 警告，不能指定歸屬哪輪；9 輪皆完成。
  Safari Find 有一次貼上逾時，未送出聊天，改用核對過的尋找欄位後恢復。

## 可追溯檔案

- `analysis/m44_isolated_safari_evidence_2026-08-27.json`
- `analysis/m44_executed_action_receipt_reserve_raw_2026-08-27.json`
- `research/m44_preimplementation_reserve_freeze_2026-08-27.json`
- `research/m44_implementation_freeze_2026-08-27.json`
- `research/m44_post_web_manifest_2026-08-27.json`
- `analysis/m44_safari_prospective_receipt_2026-08-27.jpeg`
- `analysis/m44_safari_contradicted_outcome_2026-08-27.jpeg`
- `analysis/m44_safari_unknown_outcome_verified_2026-08-27.jpeg`

## 邊界、交付狀態與下一步

這次把「用記憶行動→面對後果→修正可靠度」接通一個實際缺口。M44 沒有改進
M37 的語句泛化，也沒有證明長對話、人類被理解感、跨人物或同模型全面優勢。
原 M43 presentation trigger／mixed new request 失敗仍保留；原 M43 報告不回寫。

本機安全 worktree 修改、測試與隔離 Web 驗證完成。沒有碰原始 dirty checkout，
未 commit／PR／merge／外部部署；依賴仍在現有未提交工作樹，不能聲稱正式交付。

下一個 **M45 Actionable Help Delivery** 已只讀定位、列計畫，尚未實作：
`research/m45_actionable_help_delivery_plan_2026-08-27.md`。要分辨「說要給方法」與
「真的給了能做的步驟」，保留缺脈絡時自然詢問但不得冒稱完成。這才是第 6 輪的
下一個工程問題；不是修改分數或再添一個不影響對話的 lab。
