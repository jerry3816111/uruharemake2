# P2 Repeated Refusal Arbitration 驗收報告

日期：2026-09-08

## 結論

本工作項 **通過 bounded product acceptance**。當使用者連續兩輪用不同語言表達仍未被證實或否定的婉拒／延後，
產品現在保留這個 provisional pragmatic hypothesis 與後續校正資料，但不再重複把「其實是不容易拒絕」說給使用者，
也不再用不相干的「想被放著或想被聽」二選一覆蓋當輪 qwen2.5:7b 已產生的低干預直接回覆。

這只證明一個已重現的 response-arbitration 缺口已修正。它不是人評、正式 holdout、一般 LLM 對照、完整語用理解，
也不證明已解出人類反應方程式。

## 修改前因果鏈

隔離兩輪為 `考えとく。` → `また今度にしようかな。`。修改前第二輪的 compact planner 已產生
`また今度ね。`，後續卻依序被兩層覆蓋：

1. pragmatic attunement 重複輸出「不是想去，而是不好拒絕」的暫定推測；
2. active validation 只依 `pragmatic_implicit_need` 類型套用通用問題，輸出與實際 value 不相干的 listen／alone 二選一。

最後可見回覆因此成為 `いや、今は放っといてほしいのか、少し聞いてほしいのかだけ教えて。`。修改前 raw 證據為
`analysis/p2_active_validation_prechange_gap_probe_2026-09-08.json`；前瞻工作卡為
`research/p2_repeated_refusal_arbitration_plan_2026-09-08.md`。

## 唯一核心變因

新增產品限定 `uruha_repeated_refusal_arbitration_p2.py`。只有 completed three-candidate compact direct plan、前後兩輪
typed label 都是 `indirect_refusal`、前輪 outcome 仍是 `uncertain`、當輪有 current-text `decline_or_delay` 證據，且沒有
safety／identity／memory／boundary／correction、direct report、verified communication preference 或既有 pending validation 時，
才讓當輪既有 compact core 取得最終 action authority。

仲裁只撤回當輪新建立的 intrusive pending question。longitudinal layers、revision history、typed calibration 與關係模型照常
更新；不新增固定回覆、不寫 raw user dialogue、不把私人意圖當事實、不增加模型呼叫，也不改凍結研究程式或正式資料。

## 實作中保留的失敗

第一次相鄰測試為 81/82：新 adapter 一開始包在 grounded-validation installer 外層，破壞既有 installer 的 idempotent
identity 契約。修正方式不是放寬舊測試，而是把仲裁插在 grounded validation 的既有 delegate 內側，使舊 owner 仍保有
公開 hook；失敗 JUnit 保存在 `analysis/p2_repeated_refusal_arbitration_adjacent_tests_2026-09-08.xml`。

## 測試證據

- Focused 最終 9/9：三組 source-disjoint 中／英／日 repeated-refusal、first exposure、support bid、supported／contradicted、
  noncompact、protected、既有 pending、graph idempotence、無 raw dialogue 與完整產品 contract。
- 測試另外以未仲裁的同一 longitudinal delegate 作對照，逐欄確認除本輪 `active_validation` 回復外，其餘模型狀態一致；
  input model 本身也未被就地改寫。
- 相鄰最終合併組 91/91，8 個既有 dependency warnings，29.88 秒。涵蓋 personhood、grounded validation、compact
  planner、expression commit、current-request authority、P1 identity 與 supported-feedback closure。
- 最終 JUnit：`analysis/p2_repeated_refusal_arbitration_final_tests_2026-09-08.xml`。

## 本機真實模型控制

使用本機 qwen2.5:7b、產品入口、隔離 session／memory，5 sessions 共 9 輪；不是 mock model、正式 DB、holdout 或人評。

| 指標 | 修改前控制 | 修改後控制 | 觀察 |
|---|---:|---:|---|
| 目標輪 compact core | `また今度ね。` | `また今度ね。` | 上游模型能力相同 |
| 目標輪 final | 不相干 listen／alone 二選一 | `また今度ね。` | 仲裁真正決定 final |
| active validation | 新 pending question | `pending=null` | 只撤回本輪多餘確認 |
| 目標輪延遲 | 10.166233 秒 | 9.983426 秒 | 只記錄，不主張效能提升 |
| 全 run 模型呼叫 | 3 | 3 | 機制新增 0 calls |
| 全 run tokens | 4,471 | 4,434 | 生成隨機差異，不作成本因果主張 |
| 全 run elapsed | 37.170483 秒 | 37.056903 秒 | 只記錄 |
| 非目標 final | 8 輪 | 8 輪逐字相同 | 這次實測未觀察到旁路變化 |
| 結構 checks | 4/4 | 4/4 | persistence／graph／pending／calibration 保持 |

修改後 raw：`analysis/p2_repeated_refusal_arbitration_local_run1_2026-09-08.json`。

## 圖像化驗收

`analysis/p2_repeated_refusal_arbitration_local_run1_2026-09-08.html` 是實際 9 輪 runtime graph，不是手畫示意圖。
目標輪出現可點擊的 `repeated_refusal_arbitration_p2` decision node，位於 active validation 前，並連到既有流程；節點保留
base compact action、被拒絕的 pragmatic proposal、validation proposal、selected core、各 digest 與 claim boundary。
同一圖可看到 `compact_general_plan_p2`、`contextual_expression_commit_p2`、`utterance` 與 calibration chain，且 final surface
等於 selected core。

Safari 實際點擊仍是 **pending**：本輪之前 CUA 工具拒絕目前網址並結束控制階段，外部狀態未改變，因此沒有繞過或偽稱
Safari 驗收。HTML 生成與 graph contract 通過不能代替 Safari 證據。

## 對長期目標的貢獻與下一步

這次增加的是「多個認知候選發生衝突時，依證據狀態與互動成本選擇回覆」的可追溯機制：系統可以保留對言外之意的
假設供未來驗證，卻不必每輪把同一低信心推測壓到使用者臉上。這比單純新增一句模板更接近可反駁、可修正的候選反應方程式，
但目前只在 narrow repeated-refusal 結構成立。

下一個唯一產品問題是 explicit correction surface authority：`違う。今日は一人にしてほしい。` 已明確修正前輪，現 final
卻仍追加無來源的「沒睡／想事情」二選一。下一工作項須先凍結 correction core → unsupported add-on 的 trace，且不得同批修
quoted-source／cross-session recall。
