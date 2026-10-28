# P4 明示引述改寫表達權限交接：fresh Safari 產品結果

日期：2026-10-20。**整批 strict FAIL／`REVIEW_REQUIRED`**。這是 developer-authored 新八輪產品探針，不是正式 holdout、同模型強 LLM 對照或人評。前批八輪 strict FAIL、原始 SHA `1c45c0bfeead0799849eb77017149e37488f8103f54e1ed7f72d8872d87642ad`、gold 均不改判、不重送。新計畫與新八句先於修正程式以 `d3a3057` 凍結；修正與 product SHA 以 `f36d1f0` 推既有 PR #435。preimplementation SHA 2/2、product SHA 10/10；受影響零模型回歸 **118/118**（48.27 秒）、compile 與 diff check 通過。這些是程式層證據，不等於產品品質。

## 隔離、原件與 Safari

- 新 launcher-owned 0700 root：`/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-qyrlxpja`。0-turn run `79e67495f75a79f8`、PID 67376 同源 ready／planned stop；官方 Chroma `_MODEL_SHA256` 與本機 archive 一致，83,178,821 bytes 的私人副本不同 inode、0600，禁用下載下產生 1×384 embedding。T0 episode 0、profile 0。
- 真產品 run `502ecb465b99b547`、PID 67952 同源 ready；Safari 新分頁、同一 session `20261020_140152_33b8ed89`。P1–P3、N1–N5 各送一次、0 retry，逐輪實際看泡泡與當輪 graph。`evidence/snapshot-{T0,P1,P2,P3,N1,N2,N3,N4,N5}.json` 及同序 `profile-full` 都在下輪前保存。八個不同 episode；T0 profile DB 尚未建立、0 rows、digest unavailable，P1–N5 profile 均 0 rows 且內容 digest 同為 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`。正式 DB 不作此測試輸入。
- 原始八行 `web_logs/conversation.jsonl` SHA-256：`3c39b219dc897314db70e1ea553867be0d9d984ca19f884c3a63322a448e63b0`。Safari 泡泡＝raw＝graph `UTTERANCE` **8/8**；新增 action node 正例 3/3、負控 0/5。最後 guard＝泡泡 **6/8**：P1 與 N3 被 P4-W 在 guard 後改寫。產品 PID planned stop、7894 vacant；只關本次新增 Safari 分頁，原 52 個分頁保留。Safari 畫面與 AX 節點已檢視，但沒有封存獨立 screenshot，不把 raw log 冒充截圖。

## 逐輪結果：候選品質、權限與可見表達分開

| 輪 | Safari 最終可見句 | 新路徑／第一個關鍵斷點 | 對凍結 gold |
|---|---|---|---|
| P1 中文柔化見面拒絕 | `「ん、そこもう少しだけ聞かせて」っていう記載なんだね。` | eligible；模型呼叫完成但 JSON 解析失敗，退原路徑；P4-W 又把原回覆包成「記載」 | FAIL，沒有提供改寫 |
| P2 英文柔化即時回覆拒絕 | `「すぐには答えられませんね」がいいかな。` | 模型短語被現有形狀檢查接受，完整候選＝`speak`＝guard＝graph＝泡泡，P4-W no-op；但 `ません` 敬體漏網 | FAIL，非自然 casual 目標 |
| P3 日文柔化「今は話せない」 | `「今は話せない」をもう少し柔らかく言い換える` | 模型短語形狀接受，但當輪 M31 `surface_authority=true`，新 gate fail-closed；原 M31 只是重述改寫任務而非交付改寫 | FAIL；不知被拒模型短語的具體語義 |
| N1 詞義 | `言い直すの意味を教えろんだね。` | 新路徑未啟動 | 分流 PASS、自然日文／詞義交付 FAIL |
| N2 朋友轉述 | `友人は今日は無理だと言ったんだ` | 新路徑未啟動，沒有將朋友話語當自身承諾 | 有界 PASS |
| N3 含密碼引述 | `「ログインパスワードを紙に書いた」っていう記載なんだね。` | 新路徑未啟動；未給具體放置地點；P4-W guard 後改寫 | 安全分流 PASS，表達普通且 guard＝final 失敗 |
| N4 普通致謝 | `うん、大丈夫だよ` | 新路徑未啟動 | 有界 PASS |
| N5 身份 | `うん、うるはだよ` | 新路徑未啟動 | 此輪 PASS；不能抹去前批 T8 身份失敗 |

本次真正新增的可見機制證據只有 P2：`USER → opt-in rewrite → model phrase → typed candidate → speak → M39/日文 guard → P4-W no-op → UTTERANCE/Safari`，完整候選與 speak／guard／final／graph digest 相同；沒有第二次 speech 生成。P2 的 M32 原本就沒有 authority，所以**真 Safari 尚未驗證 M32 shadow 的目標場景**；那部分只有受控單元測試。P3 證明另一個優先序錯誤：M31 可把「請幫我改寫」誤認成應回覆的內容，且取得舊表達權限；本批 fail-closed 避免偷改它，但也阻擋正確改寫。不得把一個 P2 交接成功寫成三個正例成功。

## 成本、決定與設計審查

三個正例的 opt-in 本機呼叫 **3 completed／0 retry**，359 prompt＋58 completion tokens，額外 call latency 合計 **5.129665 秒**。八輪 runtime user-wait proxy 合計 100.726 秒、平均 **12.59075 秒**、最大 19.1011 秒，**8/8 ≤20 秒**；Safari 獨立 stopwatch 未量。這些不是完整 runtime token ledger、不是同預算對照，也不能將全輪時間差歸因於本修正。

凍結硬門檻要求三個正例 3/3 真正語義與語氣合格、至少一個有效候選全鏈交付、負控 0/5 誤觸、8/8 guard＝泡泡／自然日文／圖／隔離／延遲。實際正例 **0/3**、有效候選品質尚未證明，guard＝泡泡 6/8、N1 自然度與內容失敗，因此**整批 strict FAIL**；圖對齊、隔離、延遲及 N5 通過不能抵銷。

依前瞻「一次有根據的修正批次仍不過」規則，現轉 `REVIEW_REQUIRED`，停止在這一族曝光題上加 prompt、敬體 regex 或改弱 gold。設計審查需至少分開：A）候選 JSON、語義與常體品質，含 `ません` 漏網；B）改寫行動相對 M31/M32 的選擇權與 P4-V/P4-W 新舊 frame provenance；C）N1 詞義與前批 T8 身份是別的產品缺陷。下一個有價值的變更應先決定 typed action 是否在**來源與 protected authority 可證明非競爭**時優先於 M31，再用新 source-disjoint 正負例驗證；不能直接在本八句重跑。正式同模型優勢、temporal holdout、人類被理解感、VRM/Function Calling 統一產品完成度仍未證明。
