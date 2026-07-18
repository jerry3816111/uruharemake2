# V68 使用者資料直接陳述邊界結果

**決策：** `authorize_production_guard_integration`

| 條件 | 完全正確 | 非陳述誤寫 | 直接陳述保留 | Fact precision | Fact recall | 中位額外延遲 |
|---|---:|---:|---:|---:|---:|---:|
| 現行無 guard | 12/24 | 12 | 12/12 | 50.0% | 100.0% | 0 ms |
| assertion scope guard | 24/24 | 0 | 12/12 | 100.0% | 100.0% | 0.002 ms |

新答對 12 題，退步 0 題。
預註冊門檻：全部通過。

本實驗只測 profile facts 是否來自使用者直接自我陳述；尚未測持久化、狀態更新、檢索或最後回答。
