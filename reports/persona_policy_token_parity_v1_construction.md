# 人格策略 prompt token 公平配置建構報告

**construction_passed**

| 指標 | 結果 |
|---|---:|
| 配對情境 | 6 |
| 每組配置 prompt tokens | 640 |
| 最少 masked padding | 49 |
| 配置 token 排程一致 | 通過 |
| 有效 token 差異仍可見 | 是 |
| legacy 行為變更 | 0 |
| 真模型權重載入／生成 | 0/0 |

較短的 prompt 只在左側補 attention-mask=0 的 tokens；原 token 序列不截斷、不重排。超過 640 tokens 時直接失敗關閉。

這只證明公平運算配置可用，尚未證明目標人格更相似。下一步才可執行小型實際本機模型 target／neutral pilot。
