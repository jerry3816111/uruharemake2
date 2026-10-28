# P2 第二批：本機生成恢復，P2 整體仍 partial

## 本輪的產品改變

一般 planner 使用原 qwen2.5:7b、原輸入、Memory／Hard rules 和三個候選；只縮短輸出契約。
模型輸出恰三個 compact candidates，經嚴格檢查才展開為原 bundle。截斷／缺欄／重複／過長會失敗，
不補造候選；實際模型 usage 由原 compute ledger 在展開前記錄。凍結研究 source／入口未改。

產品預設明確改為 **20 秒上限、256 output tokens、0 retries**。`URUHA_PRODUCT_PLANNER_BUDGET_SECONDS`
可在 1–45 秒範圍設定；不要與研究 interpreter 混用。原始研究 8 秒預算未變；本報告**不是同預算研究比較**。

## 實際證據

| 檢查 | 結果 |
|---|---|
| 完整相鄰套件（P1／P2／M43／V2.13） | 62/62，18.47 秒；8 個既有依賴 warnings；不是全庫測試 |
| 舊一般 planner 診斷 | 45 秒仍逾時；服務日誌顯示 1,828 prompt tokens，產生逾 1,000 tokens 尚未完結 |
| 新兩輪本機 probe | planner 6.801727 秒完成，1,328 prompt＋83 completion tokens；三個實際候選，無 fallback |
| 新六輪／兩 sessions 本機 probe | 兩次一般 planner 都完成：6.730137／8.623820 秒，output 82／93 tokens；prompt 1,328／1,621 tokens |
| 六輪記憶／身份紀錄 | P1 八項 assertions 全過，六輪 M27 ledger 與 P1 原始本機 probe **逐欄相同** |
| 六輪總時間 | 30.651133 秒；兩個生成輪整輪為 14.057121／10.186719 秒，不能拿模型呼叫時間當整轮時間 |
| 最後圖接線兩輪 probe | 第一輪無 compact node，第二輪正好一個實際 compact node；planner 7.164712 秒、81 output tokens |
| Safari／人評／正式 holdout | 未完成／未使用；HTML 結構核對不是 Safari 視覺驗收 |

幾次觀察的 cold/warm／cache 不同，不能由此報普遍加速百分比，也未證明優於完整上下文 LLM。
Compute ledger 只涵蓋 OpenAI-compatible；native urllib／embedding 成本不完整。沒有把缺值當零。

## 真正回覆與剩餘失敗

六輪中的「そう、それでいい。」現在回：

> 先に、うん、そのとおりだ。そのくらいでいいだろ。

「うん、聞いてくれてありがとう。」現在回：

> いや、ありがとう。そのくらいでいいよ。そのくらいでいいだろ。

兩輪已不重問需求，但日文仍有不合語境的連接語與重複尾句，**自然度未達交付標準**。
來源已只讀定位：`RightBrain._finalize_surface_reply` 以輸入 hash 選 prefix；`direct_chat_answer` 的
surface variants 無條件補「そのくらいでいいだろ」。這不是本輪模型理解更差或語言 guard 失效的證明，
而是需要分開比較 model core、plan repair 與最終表達的下一個部件問題。現在尚未修改那兩段。

第一批五組 mock 控制的語意負例仍保留，compact 版本未逐一重驗；不能宣稱已修好新請求／撤回／引述理解。
第二批共通欄位由既有 normalization／BDI 邏輯補出，是系統推測而非本次模型生成的心理事實，不能當真人證據。

## 失敗與證據範圍

- `p2_warm_8s_diagnostic_2026-09-07` 名稱帶 warm，但服務日誌顯示當時模型重新載入；不是已控制的 warm-only 實驗。
- `p2_45s_planner_diagnostic_2026-09-07` 保存較大 budget 仍失敗的原始結果；沒有覆寫成 pass。
- 第一個 compact 六輪資料有 planner trace，但既有 renderer 沒把該 nested trace 顯示為節點。補最小接線後，
  `p2_compact_graph_run1_2026-09-07` 確認實際一個模型呼叫對應一個節點；舊資料不改寫。
- 每個 probe 使用獨立 temp DB；P1／正式 DB、真人資料及 frozen outcomes 未污染。未外部部署。

## 接續與有限範圍

P2 已走完兩個前瞻修正批次，整體仍 partial。下一步先做**表達層架構重評**：同一實際 plan，核對直接
日文 core 與後處理後的差別，再决定精簡哪個無來源的自動添句；不追加測試句專用答案或 M57.10。
新測試必須包含非確認的普通聊天／真正澄清／安全／記憶，以免刪掉必要內容。尚不能稱已完整理解使用者。

原始 `.json/.html`：`p2_compact_planner_run1_2026-09-07`、`p2_compact_six_turns_run1_2026-09-07`、
`p2_compact_graph_run1_2026-09-07`。最後 XML：`p2_compact_graph_tests_final_2026-09-07.xml`。
