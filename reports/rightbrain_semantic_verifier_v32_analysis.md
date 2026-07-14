# 右腦 V32：日文語意 verifier 校準結果

本輪只重算 verifier，不重新生成、改寫或訓練任何右腦回答。

## 48 例校準結果

| 條件 | 正例 recall | 負例 specificity | critical FP | 總正確率 |
|---|---:|---:|---:|---:|
| 現行字面 matcher（對照組） | 29.2% | 91.7% | 2 | 60.4% |
| 字典形＋肯否極性 | 58.3% | 91.7% | 2 | 75.0% |
| 字典形＋肯否極性＋讀音 | 87.5% | 83.3% | 4 | 85.4% |

## 相對現行 matcher

- 字典形＋肯否極性：recall +29.2 pp；specificity +0.0 pp；新增 critical FP=0。
- 字典形＋肯否極性＋讀音：recall +58.3 pp；specificity -8.3 pp；新增 critical FP=2。

## V31 凍結候選 shadow

預註冊規則選出的處理：**字典形＋肯否極性**。

| V31 payload | 現行覆蓋率 | shadow 覆蓋率 | 差異 | 新通過候選 |
|---|---:|---:|---:|---:|
| japanese_json | 30.6% | 30.6% | +0.0 pp | 0 |
| japanese_lines | 33.3% | 33.3% | +0.0 pp | 0 |
| mixed_json_control | 27.8% | 36.1% | +8.3 pp | 4 |
| mixed_lines | 47.2% | 50.0% | +2.8 pp | 2 |

## 晉級門檻

- 通過：`all_hash_and_accounting_checks_pass`
- 通過：`positive_recall_delta_vs_legacy_at_least_20pp`
- 通過：`negative_specificity_not_below_legacy`
- 通過：`new_critical_false_positive_count_is_zero`
- 通過：`all_v31_newly_accepted_candidates_have_no_other_rejection_reason`
- 通過：`v31_strict_case_coverage_noninferior_in_every_payload_condition`

## 決定

**authorize_source_separated_verifier_holdout_for_lemma_polarity**

本輪不改 runtime、不重訓模型，也不要求人類盲測。通過只允許建立新的來源分離 verifier holdout。

## 證據邊界

This is an internally authored calibration set plus retrospective frozen V31 candidates. Passing can justify only a fresh source-separated verifier holdout. It cannot promote runtime, establish semantic entailment in general, prove human-like cognition, or validate pronunciation matching across Japanese homophones.
