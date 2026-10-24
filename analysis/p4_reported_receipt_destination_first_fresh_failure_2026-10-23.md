# P4 接收地點角色：第一批 fresh Safari 失敗紀錄

日期：2026-10-23。這是事前凍結 `datasets/p4_reported_receipt_destination_probe_2026-10-23.json` 的首次產品驗收，不是正式 holdout、人評或同模型對照。設計／架構／程式已在真題前分別推送於 `1a5f27d`、`cde6b69`、`9999e41`；26/26 聚焦及 109/109 相鄰零模型測試不代替以下產品結果。

## 已執行與觀察

- 隔離 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-u7mk0xh6`（0700）。官方 ONNX archive 83,178,821 bytes，SHA-256 `913d730...`，複製成私有 0600、不同 inode；封鎖下載的預熱得到 384 維向量、0 次下載。首次暖機腳本在計算 embedding 後因 `PosixPath` JSON 序列化失敗，修正暖機腳本後成功；沒有將該腳本失敗算成模型題。
- zero-turn run `c8a956d526db2045`，PID 29132，同 PID HTTP ready、空 DB，依計畫停止。產品 run `5e215d0ea7f72cb8`，PID 29382；初次 ready 查詢超時，稍後確認同 PID HTTP ready、T0 記憶與 session embedding 均 0、127.0.0.1:7894 listening。兩次均有 exact-PID planned stop 與 port vacant 收據。
- 原生 Safari 在專用新分頁送出且只送出 r0：`同僚は2096年3月14日に銅の望遠鏡を受け取る場所を灰色の温室の北廊下に決めたらしい。`。同一 session 輸入後可見 user bubble、assistant `...`、思考階段，約 20.618 秒後出現兩個 `錯誤` 標記；沒有最終 assistant 回覆，也沒有當輪 graph 可核。新分頁已關，Safari 舊 52 分頁未碰。
- stderr 在 `uruha_reported_receipt_destination_relation_p4.py:226`，核心 `emit_response_if_ready` 的 `_attach_reply_post_check` 期間拋出 `RuntimeError: reported receipt destination pre-episode mismatch`。這證明最後寫入前的 gate 擋住了回覆，不證明是哪一個 predicate 失配。私有 stderr 35,086 bytes，SHA-256 `f7448fc41c924a37782a34d5b062345f57dbe32edbda23195e41fe3f39142302`；原始證據仍保留在隔離 root。
- 停止後記憶 DB 與 session DB 的 embedding 都是 0，`conversation.jsonl` 不存在；沒有正式長期記憶污染。未保存原生 Safari PNG／AX 檔；只有當時 UI 觀察，不能冒充持久視覺證據。

## 判定與邊界

**整批 strict FAIL，0/1 已試產品題成功；r1–r3 沒有送出，r0 不重試。** 日文品質、來源地點角色、圖節點／連線、bubble＝raw＝guard＝history＝episode、reload、成本與 ≤20 秒均沒有通過。約 20.618 秒是到 UI 錯誤的觀察等待，不是成功回覆延遲；完整 token ledger 不可得。這是新 adapter 的產品阻擋，不改寫舊 f2／c0／c1 判定，也不宣稱 P4-Z/D 或正式研究完成。

下一步先以零模型和唯讀路徑核對 pre-episode 各 predicate，記下可重現的最小反例；若能定位單一因果，另立修正設計與 source-disjoint **新**題並事前凍結，最多兩個有根據修正批次。已曝光 r0 只能當回歸／診斷，不可用作 prospective 成績；凍結但未送的 r1–r3 也不在本次失敗後追分。
