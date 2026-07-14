# 右腦 V32：日文語意 verifier 校準結果

本輪只重算 verifier，不重新生成、改寫或訓練任何右腦回答。

## 48 例校準結果

| 條件 | 正例 recall | 負例 specificity | critical FP | 總正確率 |
|---|---:|---:|---:|---:|
| 現行字面 matcher（對照組） | 29.2% | 91.7% | 2 | 60.4% |
| 字典形＋肯否極性 | 58.3% | 87.5% | 3 | 72.9% |
| 字典形＋肯否極性＋讀音 | 87.5% | 79.2% | 5 | 83.3% |

## 相對現行 matcher

- 字典形＋肯否極性：recall +29.2 pp；specificity -4.2 pp；新增 critical FP=1。
- 字典形＋肯否極性＋讀音：recall +58.3 pp；specificity -12.5 pp；新增 critical FP=3。

## V31 凍結候選 shadow

沒有處理條件通過基本安全選擇規則。

## 晉級門檻

- 通過：`all_hash_and_accounting_checks_pass`
- 未通過：`positive_recall_delta_vs_legacy_at_least_20pp`
- 未通過：`negative_specificity_not_below_legacy`
- 未通過：`new_critical_false_positive_count_is_zero`
- 未通過：`all_v31_newly_accepted_candidates_have_no_other_rejection_reason`
- 未通過：`v31_strict_case_coverage_noninferior_in_every_payload_condition`

## 決定

**keep_legacy_runtime_verifier**

本輪不改 runtime、不重訓模型，也不要求人類盲測。通過只允許建立新的來源分離 verifier holdout。

## 證據邊界

This is an internally authored calibration set plus retrospective frozen V31 candidates. Passing can justify only a fresh source-separated verifier holdout. It cannot promote runtime, establish semantic entailment in general, prove human-like cognition, or validate pronunciation matching across Japanese homophones.
