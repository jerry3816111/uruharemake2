# RightBrain Casual Register Gate v2

## 結論

一般化敬語問句檢查補到 1 個先前漏判，且未誤殺 6 個 audit pass；但只抓到 5 個自然度失敗中的 1 個，因此這是人格語域增量，不是完整自然度解法。

## Audit 結果

| 指標 | 結果 |
|---|---:|
| true positive | 1 |
| false positive | 0 |
| true negative | 6 |
| false negative | 4 |
| failure precision | 100.0% |
| failure recall | 20.0% |
| false positive rate | 0.0% |

## 同候選重算

- stored candidates: 90
- newly rejected: 1
- newly accepted: 0

## Gate

| 條件 | 結果 |
|---|---|
| audit_covers_all_sampled_cases | PASS |
| detects_recorded_polite_persona_failure | PASS |
| audit_false_positive_count_is_zero | PASS |
| saved_candidate_rescore_is_monotonic | PASS |
| saved_candidate_rescore_newly_accepts_zero | PASS |

## 邊界

- 本輪只改善 casual persona 的敬語／接客服務語域檢查。
- failure recall 20% 表示錯字、搭配詞與語意扭曲仍未解決。
- 不使用這個局部結果宣稱完整日文自然度已提升。
