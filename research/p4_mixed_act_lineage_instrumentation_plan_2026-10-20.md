# P4 mixed-act producer lineage：前瞻 instrumentation freeze

狀態：**實作前凍結**。根據 `research/p4_mixed_act_authority_design_review_2026-10-20.md` 與前批 W1–W7 strict FAIL。這一項只處理「憑證沒有可稽核的當輪父子關係」這個單一核心變因；**不轉移 M31/M32/M33 表面權限、不宣稱已完成改寫＋回憶**。W1–W7、舊 A 題及其 gold／FAIL 不重播或改判。

## Before 與可反駁問題

前批 W2/W3/W5/W7：`current_turn_source_role_p4` 4/4 辨識 mixed，M31 4/4 具 `surface_authority=true`，新來源 gate 0/4 可見。M31 `input_digest` 只證文字相同；M32 在同一程序以 M31 結果建立，但沒有保存可核的父憑證。圖的投影線不是原生因果 edge。若在未證 event→M31→M32 的情況下直接改權限，就可能把別輪、無來源或受保護內容當作本輪依據。

## 唯一變因、允許檔案與界線

在隔離 opt-in 入口，於 `ingest_event` 產生不可重用的 `event_id`、raw SHA、cycle；於 M31/M32 **各自 producer return 時**蓋新的 proposal ID 及 parent ID；在 cognitive tick 後稽核同事件、直接父子、摘要、唯一性及 M33/protected 權限狀態。使用既有 source-role 的 raw quote/outside spans，為 mixed 建立兩個 typed `action_id`；對 M31/M32 的實際子任務覆蓋只標 `unverified`，**不得用模型自稱或輸出文字推定「未涵蓋」**。M33 若 active-authoritative，稽核標 blocked，不假接管。任何缺失、不同輪、重複、錯父、錯 digest 都 fail closed；即使鏈通過，本項 `authority_transfer_permitted=false`。graph/logic receipt 只能記 IDs／digest／型別、不能記私有原話。原本 reply、episode、profile 及舊 M31/M32 計算成本不應被新程式更動；新增模型呼叫 0。

允許修改：新增 `uruha_mixed_act_lineage_p4.py`、`test_p4_mixed_act_lineage.py`、薄 Web entry／隔離 controller、此 plan 與新 probe dataset／首輪前 SHA、驗收分析及 `CURRENT_TASK.md`。若測試證明必須觸及核心 M31/M32 原檔，先停止並重新審查，不偷改凍結舊程式。正式 DB、原始 dirty checkout、無關 `output/graduate_application_report/`、舊資料與 baseline 不動。

## 事前資料與判準

`datasets/p4_mixed_act_lineage_probe_2026-10-20.json` 是開發者新寫的 source-disjoint 四輪，不是 holdout：直接 User source、其後 mixed rewrite＋recall、無真實憑證的受保護混合句、單一改寫控制。位置／日期／引述均不重用 W1–W7。題目各送一次、0 retry；真 Safari 只新增並關閉本次測試分頁。

零模型硬 gate：混合句兩個 action 具不同 ID 與 raw span；同事件 M31/M32 producer parent 鏈可核時 status `linked`；producer 未執行時如實 `not_produced`；錯 parent／錯 event／重複 ID／錯 digest／無當輪 context 全部拒絕；M33 authoritative/protected route 拒絕權限移交。所有例子 `authority_transfer_permitted=false`，覆蓋 status 不得憑模型 reply 自動變 completed。原 M31/M32 授權與 selected core 不因本項被清除。聚焦測試、受影響相鄰回歸、薄入口 import/controller `--help` 及 SHA 全通過才跑真模型。

真產品觀測 gate：新 0700 root、0-turn same-PID ready/planned stop、官方 SHA ONNX 私有離線預熱、T0 空 profile；Safari 四輪各一次。逐輪核原生 receipt 是否在 logic/raw graph/視覺 graph 一致、raw＝最後 guard＝Safari 泡泡＝graph utterance＝episode、profile 0 rows／digest、自然日文與任務品質、≤20 秒等待 proxy；報新增／上游模型呼叫、可得 token／延遲及 setup。若原始回覆品質未過，整個 mixed product 仍 strict FAIL，不能用 lineage gate 成功抵銷；本項只可稱可追溯工程收據通過。任一溯源／一致性／隔離／安全硬 gate 不過，本項亦 FAIL。零模型或圖不代替人評／強 baseline／temporal holdout。

通過後才進下一項：另凍結實際 typed action coverage 仲裁與兩子任務原子 composer、自然改寫語義驗證、直接 User 來源 recall、最後可見同步；不能把本項憑證當成移交授權。兩個有根據修正批仍失敗則保留 `REVIEW_REQUIRED`，轉其他獨立必要產品門檻。
