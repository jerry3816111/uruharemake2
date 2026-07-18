# V71 使用者資料相關性與可說性結果

**決策：** `freeze_answer_use_and_move_downstream`

| 條件 | 選對記憶 | 全體通過 | 記憶題通過 | 無關侵入 | 不知道時拒答 |
|---|---:|---:|---:|---:|---:|
| typed_active_full_projection_control | 16/24 | 10/24 | 6/16 | 1 | 0/4 |
| typed_active_bare_key_selection_control | 21/24 | 11/24 | 5/16 | 0 | 2/4 |
| typed_active_provenance_selection_treatment | 23/24 | 12/24 | 6/16 | 0 | 2/4 |

相對 bare key：新增通過 1，退步 0。
相對整份 profile：新增通過 2。

只測臨時資料庫中的完整聊天 shadow；沒有啟用正式記憶回答。
