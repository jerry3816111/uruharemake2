# P4 Web 計算帳本 retention：fresh Safari 產品輪次

日期：2026-10-23。證據級別：事前凍結、開發者自寫的一個本機產品工程案例；不是正式 holdout、真人偏好、同模型比較或長會話 RAM 上界。舊 cost0/cost1 和 h0–h3 結果不重播、不改判。設計與題目見 `research/p4_product_turn_compute_retention_plan_2026-10-23.md`、`datasets/p4_product_turn_compute_retention_probe_2026-10-23.json`；程式／題目 9/9 SHA 在實輪後核對通過，產品 code 為 `96d1996`。

## 執行邊界與實際結果

- 全新 controller 0700 隔離 root `uruha-product-l7cxr3qs`；官方 ONNX 83,178,821 bytes／SHA-256 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3` 複製成不同 inode，在該 root 以封鎖下載入口完成 1×384 finite embedding、0 嘗試下載。zero-turn 啟停與後續產品進程各自同 PID；第一次 readiness 查驗碰上尚未綁定 listener，僅重查同一 PID，未重新啟動。產品 PID `75889`、run ID `ffb073db4c2a676c`，T0 兩個隔離 Chroma DB 各五集合均 0 embeddings、尚無 web log。這不證明 OS 全域無網路。
- 原生 Safari 只新增一個分頁（52→53），凍結輸入 `夕方、青いノートを閉じた。今は短い一言だけほしい。` 核對後只按一次 Send、0 retry。Safari 顯示日文 `夕方に青いノートを閉じたんだね。`；native AX 顯示 cost card `生成 1 次 · token 677 · 記憶操作 11 次`、本輪 user signal、route/decision、utterance、memory writeback。私有 JSONL 一行，session `20261023_120449_e5165af9`、turn 1，row assistant reply＝final language guard＝blackboard utterance＝Safari 泡泡。
- 私有 graph `product_turn_compute_receipt_p4` payload item ID `c088f3a97512c89cb81c7b2d6c7fd05c`＝row/receipt item ID，status `captured`、attribution complete；這個 ID 由私有 graph payload 驗，不是假稱 Safari 已展開卡片讀到完整 ID。收據窗口絕對 index 22→34，12 scoped calls、0 unscoped／other、0 failed；1 次 Ollama `qwen3.5:9b` 生成，532 prompt＋145 completion＝677 provider tokens；11 次 Chroma 操作（10 query、1 add），是 embedding-expected operations，**不是 embedding token**。已接線操作累加 12.398853 秒；M19 user wait 13.8664 秒，≤20 秒、delivery complete。
- 私有 `web_logs/conversation.jsonl` 是單 link／0600，1,067,339 bytes，SHA-256 `567fac4eafaa01d105c7667735602d7288586151142d5b938b184a8dd64a6966`。隔離 session DB 的 episode 1、profile/其他 0，獨立 memory DB 五集合仍 0。精確 PID planned stop 後原 PID exited、port 7894 vacant；只關本次 Safari 分頁，53→52，原有分頁未關。正式 DB 未碰。

## 判定、反例與未覆蓋項

凍結的**單輪工程接線門檻**通過：日文可見、圖成本摘要與完整私有收據同輪一致、guard/utterance/writeback 一致、≤20 秒，沒有重播追分。50 輪零模型測試另證每輪私有記錄後 scoped calls 可退休為 0；**這一個真 Safari 回合沒有直接讀到活進程 `_calls`，不能據此宣稱產品長會話 RAM 有界、RSS 改善或全域 hard cap**。本輪窗口前的 22 個 calls（可能包含啟動／預熱）未由此收據說明去留，不能說它們已退休。磁碟 row 仍約 1.07 MB，沒有壓縮。

同時保留一個重要的產品品質疑慮與反例：使用者明確說「今は短い一言だけほしい」，系統的確交付一句短日文，卻只重述前面的青色筆記事件，沒有對使用者希望得到哪種「一句話」作出可見承接；這不是凍結的 retention 工程 gate 失敗。trace 顯示 `general_conversation`→M31/M32 的 deterministic semantic commit，只保留 `夕方／青いノート／閉じた`，`post_check.did_reply_cover_focus=false`。不能把本案例當成「理解使用者」或 felt-understanding 成功。這是**新觀察到的獨立語用／行動選擇缺陷**，不得與 retention 單變因合修，也不得重送已曝光 `retention0` 追分。

**整體教師展示／完整產品仍 strict FAIL。** 原生 Safari live screenshot/AX 有觀察，但目前文件化 computer-use API 無本機保存操作，saved-native-visual 門檻仍 FAIL；這份文字與私有 JSONL 不能冒充視覺檔。尚無產品 50 輪 RSS、完整 token/OS/TTS/啟動成本、正式同模型比較、人評或 temporal holdout；VRM/Function Calling 未做統一驗收。下一個必要工作先按單變因審查：長會話私有 trace 磁碟膨脹，以及上面的 explicit requested-action 被 M31/M32 略過，擇一事前凍結新題與門檻，另一個保留 pending；不能改舊 gold、弱化 baseline 或把大量零模型測試外推成產品優勢。
