# P3-C3 外部語用基準 discovery 驗收

日期：2026-09-20  
結論：`no_executable_external_benchmark_now`

## 這一步回答什麼

C2 已經用凍結的 developer-authored context-flip dev cases 得到負／混合結果：system 的 mean Brier 只改善
`0.012333`，低於事前 `0.03` SESOI，且成本更高。C3 不修改 C2，也不偷跑 C1 holdout；它只回答一個後續研究問題：
目前是否有外部作者提供、可合法重現、且能公平測「情境敏感」和「不過度腦補」的受控資料？

事前 fit criteria 均不可省略：

1. 同一句表面文字在不同情境下有可比較目標；
2. 同時能觀察需要語用推論時是否接住，以及字面情境時是否過度解讀；
3. baseline 與 system 可取得相同完整 context、使用相同基礎模型與資源上限；
4. 有可核對 provenance、reuse permission，以及在讀取答案前能凍結的 train/dev/test 邊界。

## 候選與決策

### DRInQ：任務最接近，但目前只能列為 conditional

- ACL 2026 論文明確把 question surface form 固定、改變 conversational context 與 implied meaning，這正是 C1/C2
  想隔離的核心變因。
- 作者 GitHub 公開一個 `drinq_validated.csv`；README 列出 `question/context/options/consensus/implied_comment`。
- discovery 只讀 repository metadata 與 README，沒有下載或讀 CSV row。GitHub metadata 未顯示 license，root 也未見
  train/dev/test split files。
- 因此不得直接複製、重分後把其中一部分稱為獨立 holdout。可執行的前置依賴是作者補上明確 dataset license／授權說明，
  再在讀 row 前凍結 family-level split。即使取得資料，也仍需補 literal guard，因為 DRInQ 主要比較 implicature alternatives。

決策：`conditionally_eligible_blocked`。

### PaCE：方法 fit 最完整，但官方 artifact 尚不可執行

- ACL 2026 論文報告 3,125 組人工驗證的 context-flip pairs，直接比較 literal 與 pragmatic context，最貼近
  「能推言外之意，也不能逢句就腦補」的雙邊要求。
- 論文的任務是 English binary NLI，資料為 synthetic、經 expert verification；論文表示供 academic research release。
- 但本次在 ACL 官方頁、attachments 與精確題名／benchmark 名稱的官方來源搜尋中，未發現可核對的 dataset repository
  或 supplement。因此無法檢查實際 schema、license file、split，也無法合法重現。
- 「本次未發現」不等於資料永遠不存在；日後作者釋出 artifact 時可重新審查，不得把搜尋負結果誇大為不存在。

決策：`method_fit_artifact_blocked`。

### PUB：有正式 artifact 與 MIT license，但不是這次要測的 intervention

- PUB 是廣泛語用能力 MCQA，14 tasks、4 phenomena、約 28k questions，資料可取得且 license 清楚。
- 它不是同 surface 的 literal/pragmatic context pair，不能回答 C2 失敗後最關鍵的「顯式語用 state 是否同時提高
  context sensitivity 且不增加 overinterpretation」。
- 本專案以前的 M13/M15 已接觸 PUB，因此它也不能重新命名成未曝光的 independent holdout。

決策：`rejected_for_p3_c3`；仍可保留為歷史廣度測試，不作 C3 因果證據。

## 驗收與邊界

- executable candidate：`0`
- conditional candidate：`1`（DRInQ）
- method-fit but artifact-blocked：`1`（PaCE）
- task mismatch／already exposed：`1`（PUB）
- benchmark dataset download／row read／hidden test answer access：`0 / 0 / 0`
- model call／new Uruha source／future／human label／production write：全部 `0`
- metadata-only network access 確實發生；跨 browser/provider 沒有權威 request count，因此保存 `null` 與原因，不捏造數字。

這個結果沒有證明 UruhaBrain 優於外部 benchmark，也沒有證明所有語用機制無效。它證明的是：在目前可核對條件下，
沒有一個候選同時滿足 task fit、官方可執行 artifact、明確 reuse permission 與 prospective split，故不能誠實地開始外部評測。

## 對產品／研究流程的實際影響

P3 的受控開發 lane 已有完整可重現的負結果，且外部獨立驗證目前受資料依賴阻擋；因此不再無限找 benchmark、改 C1 case
或偷跑 holdout。C1 explicit pragmatic-state candidate 目前**不取得產品整合授權**。專案下一個獨立且必要的交付轉到 P4：
先盤點既有本機聊天、真實 node graph、VRM 與 Function Calling 的可用入口與缺口，再只整合真正缺少的連線。
這不會把 P3 負結果說成 P4 成功，也不會替代 M55/M56 的真人與正式研究門檻。
