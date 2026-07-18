# V70 跨 session profile 最終回答結果

**決策：** `freeze_and_keep_profile_out_of_answers`

| 條件 | 全體通過 | 記憶相關通過 | 禁用詞案例 | 拒絕猜測 | 中位整輪 |
|---|---:|---:|---:|---:|---:|
| current_session_only_control | 4/24 | 0/16 | 0 | 0/4 | 1.098s |
| matched_append_only_projection_control | 11/24 | 9/16 | 5 | 0/4 | 1.079s |
| typed_active_projection_treatment | 10/24 | 8/16 | 5 | 0/4 | 1.078s |

相對 append-only：新增 0，退步 1。

只測臨時資料庫中的完整聊天回答；未授權正式回答使用。
