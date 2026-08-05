# V2.6 Corrected Oracle 建構可行性

**決策：`construction_infeasible_do_not_build_cases`**

修正後只在原始對話正文內確認答案。固定規格需要每段對話 3 題、合計 12 題，但實際只有 10 題符合。

| 已暴露 development 對話 | 需要 | 實際可用 |
|---|---:|---:|
| `conv-50` | 3 | 3 |
| `conv-48` | 3 | 2 |
| `conv-30` | 3 | 1 |
| `conv-49` | 3 | 4 |
| **合計** | **12** | **10** |

因此沒有建立 case manifest，也沒有呼叫模型。直接從其他對話補題會違反預註冊分配，不能事後修改。

下一版只可重新預註冊 development 題數與分配；Top-3 投影、模型與六段 reserve 都必須保持不動。
