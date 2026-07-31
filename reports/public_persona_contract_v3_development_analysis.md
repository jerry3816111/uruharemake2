# 公開人格條件契約 V3 本機模型結果

- 決策：`freeze_v3_negative_result_and_reassess_carrier_model_or_scorer`
- 只比較固定人格 brief 與條件式 surface brief；其他輸入相同。

| 條件 | 語意通過 | 人格策略通過 | 表面 gate | 中位延遲 |
|---|---:|---:|---:|---:|
| c0_static_persona_brief | 18/20 | 10/15 | 17/20 | 3.338s |
| t1_conditional_surface_brief | 18/20 | 10/15 | 15/20 | 4.080s |

- 新增人格策略通過：0 cases
- 人格策略退步：0 cases
- 非適用情境輸出完全一致：5/5

## 證據邊界

V3 construction can prove only that a condition-specific public-persona contract is separated into planning and surface layers and that the optional RightBrain carrier preserves protected fields. A later development model pass can show only payload sensitivity and non-regression on synthetic cases. Neither result proves unseen-context persona fidelity, authorizes training or runtime default activation, or permits opening the V2 sealed holdout.
