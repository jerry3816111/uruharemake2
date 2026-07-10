# RightBrain Runtime Adapter Multi-seed Promotion Gate

## 結論

建議採用 runtime gate 改動：2 個 matched seeds 的 raw candidates 完全相同，以同一版 checker 重評後，最終表面通過率由 90.9% 提升至 100.0%；修正 2 個壞輸出且未新增壞輸出。

## 控制變因

- baseline adapter: `configured_default`
- candidate adapter: `configured_default`
- comparison mode: `same_adapter_runtime_gate_check`
- seeds: `[20260708, 20260709]`
- candidates per case: `3`
- raw candidates identical: `True`
- raw candidates fully accounted: `True`
- metric gate pass: `True`
- final quality guard: `True`
- diagnostic only: `False`

## 合計結果

| 指標 | baseline adapter | candidate adapter |
|---|---:|---:|
| raw 候選接受 | 32/60 (53.3%) | 26/60 (43.3%) |
| 模型實際接管 | 4/22 | 3/22 |
| 最終品質通過率 | 100.0% | 100.0% |
| 同版 checker 重評的表面通過率 | 90.9% | 100.0% |

## Rejection Reason 解讀

baseline 與 candidate 使用同一個 adapter，且本報告要求每題 raw candidates 完全相同。因此新增 rejection reason 代表 checker 新抓到的表面問題，不代表模型生成能力退步；是否採用改動由配對後的壞輸出修正數、零新增問題與最終品質防線共同決定。

## 各 Seed

| seed | raw 相同 | baseline surface | candidate surface | 修正 | 新增問題 |
|---:|---|---:|---:|---:|---:|
| 20260708 | yes | 90.9% | 100.0% | 1 | 0 |
| 20260709 | yes | 90.9% | 100.0% | 1 | 0 |

## 配對後的最終輸出變化

| seed | case | before issues | after issues | before | after |
|---:|---|---|---|---|---|
| 20260708 | reference_fragment_probe | language_or_symbol_artifact | - | まあ、その言葉の元ネタは何 ? | まあ、それ何ネタだよ。歌詞なら曲名まで出せって。 |
| 20260709 | reference_fragment_probe | language_or_symbol_artifact | - | まあ、その部分だけで何の元ネタだというの？曲名や作品名言ってくれないの？>< | まあ、その部分だけじゃわからんね。元ネタ教えて？ |

## Rejection Reason Family Delta

| family | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| awkward_or_caregiver_surface | 0 | 5 | +5 | new_detection |
| ascii_symbol_artifact | 0 | 2 | +2 | new_detection |

## Rejection Reason Exact Delta

| reason | baseline count | candidate count | delta | direction |
|---|---:|---:|---:|---|
| awkward_or_caregiver_surface | 0 | 5 | +5 | new_detection |
| ascii_symbol_artifact | 0 | 2 | +2 | new_detection |

## Case-level Regression Diagnostics

| case | category | accepted delta | selected delta | new rejection reasons | resolved reasons |
|---|---|---:|---:|---|---|
| explicit_stomach_coffee | audited_memory | -2 | +0 | awkward_or_caregiver_surface | - |
| reference_fragment_probe | repair | -1 | -1 | ascii_symbol_artifact | - |
| background_family_pressure | audited_memory | -1 | +0 | awkward_or_caregiver_surface | - |
| daily_state_answer | daily | -1 | +0 | awkward_or_caregiver_surface | - |
| support_tired_no_closing_template | support | -1 | +0 | awkward_or_caregiver_surface | - |
| no_memory_plain_question | audited_memory | +0 | +0 | ascii_symbol_artifact | - |

研究邊界：此 gate 在相同 seed、相同候選數下進行配對比較；同 adapter 的 runtime checker 比較還要求每題 raw candidates 完全相同。它只證明已定義表面缺陷的攔截與受保護整合，不等同完整的人類自然度。若提供 curriculum report，會檢查 holdout overlap；有重疊時會阻止升版。
