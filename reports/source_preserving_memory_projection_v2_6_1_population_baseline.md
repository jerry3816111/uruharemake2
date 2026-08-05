# V2.6.1 Corrected Development Baseline

**決策：`baseline_locked_authorize_adjacency_projection_preregistration_only`**

| 舊 Top-3 孤立 turn 投影 | 結果 |
|---|---:|
| 答案原文保留 | 4/10 |
| 答案原文遺失 | 6/10 |
| 目標 Session 平均保留字元 | 17.4% |
| 所有 record 平均保留字元 | 18.7% |
| 模型呼叫 | 0 |

舊方法壓縮幅度大，但 60% 題目的答案原文在模型之前已經消失。這個 4/10 是下一輪鄰接視窗的固定 control。

只授權在完全相同 10 題上預註冊鄰接視窗；不授權模型、reserve、runtime 或 production。
