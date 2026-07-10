# RightBrain V21 Preferred-Likelihood Gate

## 結論

加入 preferred-likelihood guard 後，V20 會在 actual-model holdout 前被攔下；這能抓到 margin 變好但正確回答本身機率下降的 likelihood displacement。

| run | 原 gate | V21 gate | mean preferred delta | decrease rate |
|---|---|---|---:|---:|
| v19_deleted_clause_simpo | FAIL | FAIL | +0.003090 | 37.5% |
| v20_length_matched_simpo | PASS | FAIL | -0.010851 | 87.5% |

## 新增 Gate

V21 起，preference 訓練必須同時滿足：未見 pair 的 mean preferred log-prob 不下降，且至少一半 pair 的 preferred likelihood 不下降。這是本專案的保守前置 gate，只負責阻止不值得進入昂貴 runtime holdout 的 adapter。

研究邊界：This threshold is a conservative local engineering gate calibrated on V19/V20, not a universal claim from the cited paper. Actual-model multi-seed evaluation remains mandatory for promotion.
