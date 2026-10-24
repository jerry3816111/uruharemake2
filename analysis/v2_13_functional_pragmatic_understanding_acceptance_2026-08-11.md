# V2.13 功能性語用理解驗收報告

日期：2026-08-11  
工作區：`persona-data-provenance` 安全 worktree  
結論：**V2.13 的可追溯機制與教師展示路徑已建立；真實 Web 核心案例可用，但泛化穩定性仍未達研究完成。**

## 1. Canonical requirements summary

1. 研究主體是人類思考、語用理解與下一步預測，不是 Uruha 模仿；一ノ瀬うるは只是主要人格實驗與展示案例。
2. 對外回覆追求 `felt understanding / pragmatic attunement`：自然接住核心困境或言外需求，不把 confidence、alternatives、JSON 或技術分析倒給使用者。
3. 對內理解必須可反駁與修正：observation、hypothesis、evidence、alternatives、unknown、prediction、verification、contradiction 與 calibration 均可追溯。
4. literal content、communicative intent、emotion/stance、relationship signal、implicit need 與 action tendency 分開表示。
5. 純文字只使用文字可見訊號；現有語音管線沒有可靠聲學摘要時，語速、停頓、音量與韻律標為 `unavailable`，不得假裝讀到語氣。
6. 心理與語用推測不可寫成事實性長期記憶；未知不編，矛盾時撤銷／降權並保留更正歷史。
7. Uruha 是 `public-evidence-grounded persona model`，不是本人；公開語言、價值、風格和互動傾向要有 provenance，童年、私密關係、私人記憶與未公開心理狀態保持空白。
8. 系統需跨多輪、跨中文／英文／日文、使用關係與記憶，同時維持自然日文輸出、うるは自我身分、安全與 idle guard。
9. 驗收需同時看可觀察機制、對照式輸出與主觀被理解感；少量固定案例、契約測試和 proxy 不等於一般化能力或人類偏好證據。
10. 不宣稱意識、真正讀心、人類等價、真人複製、理解所有人類語用或 production ready。

## 2. 真正改變的能力

現在每輪會建立可被下一輪推翻的語用狀態，而不是只保存聊天文字：

`signal → literal/pragmatic dimensions → layered other-model → prediction/active validation → self × relationship × public persona appraisal → action → Japanese surface → later verification/calibration`

- `stable / situational / provisional` 三層使用者模型都有來源、時間、信心、確認／反駁歷史、stale/expired/withdrawn 狀態。
- 下一輪會將上一輪分成 `supported / contradicted / uncertain / not_available`，錯誤推測保留原紀錄但撤銷或降權。
- 高價值且反覆影響回覆的不確定假設會觸發一個低壓澄清；普通寒暄不應被強行補成心理需求。
- typed calibration 會累積各推測類型的支持、反駁、未知與 overconfidence gap。
- runtime graph 顯示 pragmatics、other-model、prediction、verification、calibration、self、relationship、persona、action、utterance 與 writeback；聊天表面不顯示內部分析。

## 3. 契約與回歸證據

- V2.13 + V2.14 新增測試：`34/34` 通過。
- 相鄰日文、身份、idle、路由與 Web graph 回歸：新增 ginger-ale 日文化回歸後 `102/102` 通過。
- frozen holdout 綁定的 6 個來源 hash 在正式輸出後未修改。
- `git diff --check` 通過。
- 全 repo 測試不是全綠：3671 個測試中仍有 59 failures、42 errors、1 skipped，主要是缺 MLX／模型、歷史資料集或舊 frozen hash；因此不能稱 full-suite 或正式環境 ready。

## 4. Safari 真實 Web 證據

本機網址：`http://127.0.0.1:7862`，僅綁定 `127.0.0.1`，沒有 share 或外部部署。隔離記憶根：`/tmp/uruha_v213_web.IbZlm0/startup_db`；隔離 log：`/tmp/uruha_v213_web.IbZlm0/web.jsonl`。

### 核心成功案例

1. 中文歧義輸入：「今天整個人都靜不下來。」
   - 回覆：「落ち着かないの、楽しみな方か不安な方かはまだ分かんね。どっち寄り？」
   - 不把高喚起直接當焦慮；Graph 標示 `ambiguous_arousal`、text-only acoustic boundary、alternatives 與 prediction。
2. 中文後續否定：「不是焦慮，是期待很久的事終於要發生了。」
   - 回覆：「あ、不安じゃなくて楽しみで落ち着かないのか。そっちだな、読み違えた。」
   - Graph 顯示上一輪 general hypothesis `contradicted`、confidence 下調、revision/decay history 保留，action 為 `pragmatic_revision`。
3. 英文身份：「Who are you?」
   - 回覆：「うちは一ノ瀬うるは。そこは間違えてない。」
   - 自我身分維持，沒有中文／英文表面文字。
4. 日文記憶回想：「私の好きな飲み物、覚えてる？」
   - 初次真實驗收暴露「忘れてないし、 だろ。」；Graph 其實已有 `favorites=ginger ale`，證明錯在 surface localization，不在檢索。
   - 最小修正加入 `ginger ale → ジンジャーエール`，相同隔離 DB 重啟後回覆：「ジンジャーエールって言ってただろ。」
   - 證據圖：`analysis/v2_13_safari_memory_recall_fixed_2026-08-11.jpeg`。

### 誠實保留的失敗

- 英文偏好陳述「My favorite drink is ginger ale.」被通用 active-validation 問句覆蓋，回覆成「今は放っといてほしいのか、少し聞いてほしいの。」；雖然 profile 寫入正確，該輪表面體驗錯誤。
- 這不是 holdout 後可回頭調 frozen V2.14 的理由；列為下一輪收窄 active-validation scope 的 V2.15 假設。
- 重新載入後的回想雖成功，runtime `actual_signal` 仍顯示 `memory_uncertain`，說明分類 trace 與後續 grounding 結果還需要更一致的標示。

### 污染與 idle 邊界

- 正式 `uruha_memory_mac_db` 測前與測後 aggregate SHA-256 均為 `c56a8201731a004c8c031d01908e8c6ebd7c7b3aafdd295dc6d898873d859da6`。
- 6 輪 Web log 只存在 `/tmp/uruha_v213_web.IbZlm0`；未按 Human Annotation，正式 annotation 檔未變更。
- Safari 等待期間 Autonomous 多次 tick，`pending=none`、`last_delivered=none`，沒有由沉默單獨產生催促式可見發話。

## 5. Completion rubric 與目前判定

### 可稱 V2.13 功能性語用理解機制完成的條件

- schema、跨輪模型、撤銷／衰減、calibration、felt-understanding planner、Web graph 和同模型 harness 均有契約證據；
- 隔離 Web 覆蓋支持、反駁、高不確定、三語、身份、記憶、安全和 idle；
- 不污染正式 DB，不洩漏內部分析，不捏造未知；
- 關鍵 surface cases 不被 generic active-validation 蓋掉。

### 現況

- 前三項大致達成；最後一項仍有真實反例，因此目前稱為「V2.13 機制與展示里程碑」，不稱穩定完成。
- 工程展示就緒度：約 **85%**；V2.13 跨情境穩定度：約 **75%**。百分比是工程估計，不是研究統計。
- 下一個最小高價值修正：讓 active-validation 只在與當輪 goal/intent 相容時接管 surface，並加入「記憶陳述／回想不可被心理澄清覆蓋」回歸。

## 6. 教師可理解的說法

一般聊天模型多半直接從目前文字生成答案。這個系統多了一個可檢查的循環：它先提出暫定理解，預測你下一步可能補充什麼；如果下一句證明它猜錯，它會留下錯誤紀錄、降低自信並改正，而不是把錯誤藏掉。使用者只看到自然的 Uruha 日文回覆，老師則可在下方 node graph 逐輪檢查「為什麼這樣理解、後來有沒有被推翻」。目前已證明這套機制存在且能在真實 Web 跑動；尚未以人評證明它普遍比同模型 baseline 更好。
