# Qwen3 provider-pair CPO objective probe 診斷

## 正式判定

本輪依預註冊判定為 `provider_pair_cpo_holdout_margin_not_improved`，不授權 64-step fresh generation、adapter 保存、人格訓練或 production。實際未通過的唯一檢查是 `candidate_train_final_margin_exceeds_control=False`；未知來源的 holdout margin 本身有改善。

## Control 與 Candidate

| 條件 | Preferred loss | Pairwise loss | 更新數 | Forward／backward |
|---|---:|---:|---:|---:|
| SFT control | 1 | 0 | 16 | 完全相同 |
| Provider-pair CPO | 1 | 1 | 16 | 完全相同 |

兩組使用相同 Qwen3-4B、LoRA 初始化、16 個 train rows、順序、optimizer、512 tokens、Metal GPU 與八個 holdout prompts。Prompt pair 除 `persona_expression_brief` 外完全相同；rejected answer 是同情境、同 variant 的另一個 provider 回答。

## 主要數據

| Candidate 相對 Control | 差值 | 判讀 |
|---|---:|---|
| Holdout margin 增益 | +0.011355 | 未知來源方向較好 |
| Post holdout margin | +0.011355 | Candidate 高於 control |
| Holdout correct preference rate | 0.000000 | 兩組同為 5/8 |
| Holdout preferred NLL | +0.004683 | Candidate 稍差，但在 +0.02 門檻內 |
| Post train margin | -0.008293 | Candidate 低於 control，觸發失敗 |

SFT control 的 holdout margin 變化為 `-0.000169`；CPO 為 `+0.011187`。三次重跑的每步軌跡、最終參數與 optimizer state 在各自條件內完全一致。兩組 peak MLX memory 均為 `14,846,551,024` bytes，單次約 190–193 秒。

## 可以與不能主張的事

可以主張：

- Pairwise term 對完全未使用來源產生可重現的正向 likelihood-margin 訊號。
- 改善沒有讓 8 題中的正確偏好數量增加，也沒有同時勝過 control 的 train margin。
- 直接放大為 64 steps 仍缺乏足夠證據。

不能主張：

- CPO 已解決 persona provider 滲漏。
- Likelihood margin 的小幅改善必然會改變實際生成。
- Pairwise objective 失效；它也可能受弱 provider cue 或對稱梯度干擾限制。

## 下一個可推翻假設

目前 target／neutral 的差異只藏在大型 JSON 深層的 `persona_expression_brief`。下一輪應先固定模型與回答流程，只增加一個簡短、明確、可審計的 top-level provider control signal，使用剩餘四個從未測過來源做 prompt-only paired generation。若這個單一介面變因仍不能提升 provider 可區分性，就不應繼續用更多 CPO steps 掩蓋輸入條件不清楚的問題。
