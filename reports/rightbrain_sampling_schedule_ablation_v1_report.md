# RightBrain Sampling Schedule Ablation v1

## 結論

下一個獨立驗證候選是 `conservative`；是否值得進入獨立驗證：`True`。

## 固定條件

- model: `Qwen/Qwen2.5-7B-Instruct` + `uruha_v10_all_linear_lora`
- seed: `20260707`
- cases: `11`
- candidates per eligible case: `3`
- 每組 schedule 開始前重設相同 seed；模型只載入一次。

## 結果

| schedule | raw pass | covered cases | model selected | duplicate | language rejected | semantic rejected | final pass |
|---|---:|---:|---:|---:|---:|---:|---:|
| runtime_baseline | 20.0% | 6/11 | 2 | 0.0% | 20 | 19 | 100.0% |
| balanced | 23.3% | 6/11 | 3 | 0.0% | 14 | 11 | 100.0% |
| conservative | 46.7% | 8/11 | 5 | 0.0% | 8 | 10 | 100.0% |

## 預先決策門檻

| schedule | raw gain | coverage delta | selected delta | duplicate increase | eligible |
|---|---:|---:|---:|---:|---|
| runtime_baseline | 0.0% | 0 | 0 | 0.0% | False |
| balanced | 3.3% | 0 | 1 | 0.0% | False |
| conservative | 26.7% | 2 | 3 | 0.0% | True |

## 邊界

- 這是生成策略消融，不改左腦答案、不加入題庫答案、不新增固定救援句。
- 11 案已被多次使用，因此只能選出下一個待驗證設定，不能直接當最終泛化證明。
- 若沒有設定通過預先門檻，runtime 維持原設定。
- 自動候選另見 `rightbrain_sampling_schedule_naturalness_audit_v1.md`；自然度審查可否決部署。
