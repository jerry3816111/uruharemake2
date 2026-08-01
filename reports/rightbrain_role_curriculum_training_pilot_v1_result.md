# RightBrain 角色課程公平訓練試驗

- 決策：`reject_role_curriculum_promotion`
- 正式 runtime 修改：`0`

## 政策方向判別

| 條件 | 雙向正確率 | target 方向 | neutral 方向 |
|---|---:|---:|---:|
| initial_v10_reference | 50.0% | 0.0% | 100.0% |
| policy_permuted_control | 50.0% | 0.0% | 100.0% |
| policy_aligned_treatment | 50.0% | 0.0% | 100.0% |

## 全新生成品質

| 條件 | 嚴格閘門 | 語意 | 記憶政策 | 唯一輸出 |
|---|---:|---:|---:|---:|
| initial_v10_reference | 16.2% | 16.2% | 16.2% | 13.8% |
| policy_permuted_control | 15.0% | 15.0% | 15.0% | 13.8% |
| policy_aligned_treatment | 12.5% | 12.5% | 12.5% | 11.2% |

## 證據邊界

通過只代表政策對應在獨立案例上可被模型學到，且未明顯破壞語意或記憶契約。這不是特定人物相似度、完整聊天品質或正式上線證據。
