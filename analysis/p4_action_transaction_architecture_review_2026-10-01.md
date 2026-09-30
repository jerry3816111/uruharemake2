# P4 action transaction 負結果後的非獨立架構審查

狀態：**設計審查，未新增 scored calls；不是產品授權**。以已鎖定的
`49497bfffc819953c9e42795fc40a8a7ff22bbe4` raw、後揭盲的正式分數
及 `analysis/p4_action_transaction_v1_amend1_failure_2026-10-01.md` 為 before。
本審查與原標註同由開發者作成，不能稱獨立確認。18 題已曝光，以下只作
診斷，不得重跑或改 gold 追分。

## 最早失敗點與可能的因果解釋

1. A 的 18 次 M51 中 7 次 JSON parse 失敗、2 次 source 不合、9 次進
   selector／共同 guard 後被拒；M46 review **0 次**。因此先前的問題
   不是單純「第二次 reviewer 太慢」：這批輸入在第二次模型之前已全停。
2. B 的 9 個事前 valid 案中，模型先提出 action 5 個、先 abstain 4 個；
   5 個 action 都被 guard 擋。部分阻擋顯然合理：`p4_tx_zh_01` 把只有
   標題的稿誤作已有一段可切，違反實際目標。另一些**可能**是表示／
   守門錯配：`p4_tx_zh_02` 以「パズルピース」為 object，instruction 用
   「2枚」代稱；`p4_tx_ja_02` 的頁碼 42 行動本身可行，卻缺規定的
   mechanism／命令式表面。這只是作者事後判讀，不計成功。
3. B 的 9 個事前 invalid 案全部先輸出 abstain，故沒有錯放動作；但
   9/9 都有 `forbidden_quote_not_source_anchored`，常見形狀是
   `forbidden_source_id=null` 與 `forbidden_quote=""` 混搭，且事前原因
   label 0/9、目標引文不足。安全拒絕不等於能說清哪個來源條件阻擋。
4. B 18/18 JSON parse，來源 exact 只有 6/18、完整契約 6/18；顯示
   「JSON 可解析」不是資料來源可靠性。所有最終表面落在同一句 fallback，
   使用者無法感受到具體理解或行動價值。

## 排除的快速補丁

- 不移除 M39/M45/M46/來源與 actor guard，也不把 5 個 B action 提案
  事後追認 valid。`p4_tx_zh_01` 已示範相同欄位錯配可伴隨真正 wrong-task。
- 不只把 `""` 自動轉 `null` 來把 invalid 完整率追成 PASS；source-bound
  拒絕理由與 valid retention 仍是 0/9。這可作未來 schema 設計的一部分，
  不能修改本次 raw/score。
- 不單改 prompt 語句、拉長 timeout 或換較弱 baseline。延遲已 18/18
  達元件 20 秒，問題是內容及契約；強模型大小試驗是另個變因，不能和
  架構改動混在一次因果比較。

## 單一下一工作項：先做 0-call 的表示／守門可救性診斷

決定不立刻送第三批 scored 模型。下一個必要、可交付的工作項是：
在**已鎖 raw** 上，對 5 個 B valid action 提案逐一列出 task/禁令／actor／
來源引文、動詞／object／stop 的模型原值與 guard 失敗；以事前固定的
「不新增來源事實、不改行動目標、不改 actor、只允許機械地把 typed 欄位
渲染為 instruction／成對 null」作**診斷性 replay**。同時放入
`p4_tx_zh_01` 這個真 wrong-task 反例，確保所謂可救性不等於解除 guard。
這只判斷是否值得設計新候選介面，不產生成功率或新的 holdout 分數。

若診斷顯示無需推論新內容即可救回至少一個合理 valid，而 wrong-task
仍擋，才凍結**唯一**新介面變因：「模型出 typed task evidence；
deterministic compiler 產生口語 instruction 和明確 abstain 欄位；
guard 保留語義未知 fail closed」。它是一個整體介面變因，不把 schema、
prompt、compiler 各自宣稱獨立因果效果。新比較須用未見的新 source/gold、
同模型／硬體／資料／token/20 秒上限、valid 與 invalid 絕對 gate；
不再使用這 18 題作新分數。若 0-call 診斷不能分開合理拒絕與假拒，
本 action lane 保留 `REVIEW_REQUIRED`，不再用另一句 fallback 或小規則
追分，轉向下一個已定案的必要產品 gate。

## 對整體目標的影響

這批實驗有價值的是**否定一個過早的架構主張**並留下可追溯反例與成本：
一次 source-bound transaction 尚不能給使用者可靠、具體的下一步。
它沒有測多輪語用理解、記憶回溯、公開 Uruha 人格、VRM、工具 receipt 或
強 LLM 同資源對照，也沒有讓研究更接近可宣稱的「人腦方程式」。
下一項需把離線 component、真實本機 round-trip、Safari 與真人／時間
holdout 各層保持分離。此項最多再作**一個**有證據的前瞻架構批次，
若仍不過絕對 gate，停止此分支、保留負結論與實際產品阻礙。
