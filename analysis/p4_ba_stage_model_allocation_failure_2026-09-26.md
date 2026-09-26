# P4-BA stage-specific local model allocation: formal FAIL

事前凍結的 2×2 本機模型配置實驗正式為 **FAIL**。這是一次 development-only、同資料／同硬體／同 prompt 與 schema／同生成上限的 stage-allocation benchmark；每個 unique model/case 只呼叫一次，retry=`0`。四個 arm 全部保留，沒有挑最好看的子結果，也沒有修改產品 runtime。

## 問題與公平控制

P4-AZ 已把真實 Safari 路徑的最早失敗推到第二次 model call：9B generator 完成後，9B reviewer 在產品 timeout 內未完成。P4-BA 因此只問：較小 generator 或 reviewer 能否在不改 M51/M46 品質契約的前提下，把兩階段最慢案例壓到 `<=20s`。

固定四組：

| arm | generator | reviewer |
|---|---|---|
| g9_r9 | qwen3.5:9b | qwen3.5:9b |
| g9_r08 | qwen3.5:9b | qwen3.5:0.8b |
| g4_r9 | qwen3.5:4b | qwen3.5:9b |
| g4_r08 | qwen3.5:4b | qwen3.5:0.8b |

三個模型依 `9b→4b→0.8b` 各 prewarm 一次並保持 30 分鐘；prewarm 分別為 `5.40793s / 26.00947s / 27.75885s`，不算入 case latency。兩個 generator case 與四個正反 reviewer fixtures 在模型間完全相同；generation 在 reviewer arms 間重用，避免把隨機新生成誤算成 reviewer 差異。

## 正式結果

| arm | gen 結構 | gen 合法機制 | reviewer 正反例 | full accept | max / median 兩階段 | tokens（prompt+completion） | eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| g9_r9 | 1/2 | 0/2 | 3/4 | 0/2 | 35.71618 / 34.44275s | 2573+1157 | 否 |
| g9_r08 | 1/2 | 0/2 | 2/4 | 0/2 | 22.22539 / 21.54776s | 2573+1154 | 否 |
| g4_r9 | 0/2 | 0/2 | 3/4 | 0/2 | 29.86752 / 29.57603s | 2624+1191 | 否 |
| g4_r08 | 0/2 | 0/2 | 2/4 | 0/2 | 16.78266 / 16.53749s | 2624+1200 | 否 |

20 個 scored model calls 全部 completed、JSON 可解析且 token accounting 完整；因此這次不是 transport timeout 或缺資料造成的不可判定結果。只有 `g4_r08` 通過 latency，但它同時失敗 generation structure、allowed mechanism、review discrimination、full-pipeline acceptance 四個品質 gate，不能選為產品配置。

## Generator 暴露的具體錯誤

兩個模型對兩個 case 的 selected mechanism 都是 `group_by_rule`，但凍結的 cognition case 只允許 `structure_scaffold / extract_relevant_subset / direct_atomic_completion`，report case 只允許 `structure_scaffold`，所以 allowed-mechanism=`0/2`。

這不是只差一個 enum 名稱：

- 9B cognition 把思緒自行分成「現在能做／現在不能做」，候選缺少契約可識別的 action verb；兩個候選都不通過結構 gate。
- 9B report 雖有 `2/2` structurally valid candidates，卻要求從不存在於來源的「available data sources」選項目，並仍標為 `group_by_rule`；所以結構可解析不等於來源約束下的合理進展。
- 4B cognition 自行發明「不安／興奮／記憶」三類，且不知道實際 thoughts；另一候選被判 `nonprogress_or_unknown_mechanism`。
- 4B report 兩個候選都缺少可見停止條件與契約可識別的 action verb。

因此「縮小 generator」沒有保住 M51 的可用候選；而 9B 也只在一個 case 保住形式結構，未保住 frozen mechanism。

## Reviewer 暴露的具體錯誤

固定 reviewer fixtures 有兩個應接受、兩個應拒絕，且全部預先通過 deterministic structural validation，所以不能靠 always-true 或結構 gate 混過。

- 9B 答對 `3/4`、只接受 `1/4`。它正確拒絕 random swapping，也接受有效分類；但把有效 report scaffold 以 `casual_japanese` 拒絕。更重要的是，report relabel 的 content checks 全通過，最後只是因相同 style flag 才被拒絕；這不能證明它真的辨別出「推進任務」與「換一個任務」。
- 0.8B 答對 `2/4`、接受 `0/4`：兩個正例與兩個負例全部拒絕。它不是安全而精準的 reviewer，而是退化成 always-reject；所以速度快不能換算成可靠內容驗證。

完整 pipeline 的八個組合全部 `accepted=false`。但 exact source=`2/2 per arm`、natural Japanese=`2/2 per arm`、raw dialogue trace=`0`、factual memory write=`0` 均保持，表示這次負結果沒有靠洩漏來源、污染正式記憶或破壞日文 guard 取得。

## 可以下的結論

在這個小型、已凍結的 development benchmark 上，**只做 stage-specific model downsizing 無法同時滿足 P4-AZ 後段所需的品質與 20 秒成本 gate**。0.8B reviewer 提供明顯速度改善，但失去正例辨識；4B generator 也沒有保住結構與 mechanism。這足以否定「只換小模型就是下一個產品修正」這個具體假設。

不能外推成：所有小模型都不可用、M46 的理論概念無效、系統沒有實用價值、已完成人評、已證明不如強 LLM，或已證明／否定人類方程式。資料只有兩個 generation cases 和四個 reviewer fixtures，而且屬於 development evidence。

## 下一個必要單一變因

P4-BA 的共同失敗不是 JSON transport，而是自由文字模型同時負責「選擇進展機制、填充行動、判斷語意、判斷角色表面」造成的契約混疊。下一步不再排列更多模型大小，也不重用這批 case 追分。

下一卡應 prospectively freeze **typed action compiler boundary**：讓 deterministic 層先從已授權來源與 task kind 產生少數可審計的 progress-mechanism slots，模型只填寫或實現被允許的欄位；semantic progress 與 persona-surface 分開記分，任何一層失敗仍 fail closed。P4-BA 題目只作 exposed development；正式結論必須使用全新 cases，並另外記錄 compiler coverage，不能把未知任務硬塞進模板。

這個方向要驗證的是「收窄模型責任是否同時降低 latency 與錯誤自由度」，不是把人工模板當成理解，也不是先修改產品。只有新的 offline gate 全通過後，才有資格凍結 fresh Safari integration pair。
