# P4 現行產品跨重啟、視窗外說話者來源 before 探針

狀態：**開發者自製的新隔離產品診斷，非正式 holdout／強 LLM 比較**。先凍結本檔及資料，再作一次 10 輪真實產品觀測；不在看見答案後改題、rubric 或同題重跑追分。此前 `V2.22` 是 2026-08 舊產品 50 輪（僅 5 checkpoint fresh generation）：system／完整 transcript 嚴格任務同為 `4/5`，system `13,435` vs `7,405` tokens、`255.51` vs `10.99` 秒；T50 沒找到朋友來源。2026-09 `P4-S` 是舊入口 12 輪＋重啟 typed 偏好 lifecycle `12/12`，但其四個可見語義錯不在凍結 gate。兩者都**不能直接代表 2026-10 現行入口**。

## 新探針唯一要回答的問題

現行 `uruha_web_ui_product_p4_status_truth.py` 在來源 T1 已離開最近八輪、且 T5 後真正換 process／session 時，能否從持久記憶找回「紗枝喜歡桑の葉茶」的**人物歸屬**，同時拒絕把朋友／引用／老師的內容寫成使用者自己的偏好，並用自然日文回答 T10？這直接檢查 V2.22 未閉合的 source→actor→surface 缺口，不修程式、不跑舊題。單一觀測因素是**現行完整產品版本在全 fresh 十輪跨重啟情境**；不是這一步做因果變因比較。

精確十輪與事前 source-only 答案見 `datasets/p4_current_relation_recall_probe_2026-10-01.json`。T10 問句含飲料但**不含紗枝名字**；T1 到 T10 時不在 prior eight（prior eight 為 T2–T9）。T3 是引用、T6 是使用者自己的不同飲料、T7 是老師的一次性飲用，不能把它們混成 T1 的朋友偏好。資料目前已供開發者看見，之後不得稱 sealed 或獨立。

## 執行與資料邊界

- 使用現行隔離 launcher `p4_status_truth_safe_isolated_product_launcher.py`、本機現有模型與 Safari；不改 model/prompt/temperature、記憶或產品碼。首啟省略 `--runtime-root`，由 launcher 建立有 manifest 的系統 temp 隔離 root，帶 `--preserve-runtime`；記錄其 root、PID、session 與 DB。T5 完成後確定舊 PID 已退出、listener 已關，再以**同一精確 root**、`--reuse-runtime --preserve-runtime` 啟第二 process。不得手動 seed 記憶、使用正式 DB、原始 dirty checkout、外部部署／付費 API 或關閉使用者既有 Safari tab。已知繼承的最初 import preflight 僅用隔離環境變數、發生在 sandbox profile 建立之前；server 與新入口 probe 才在 sandbox 內，故本案不宣稱完整 preflight write-isolation。
- 每輪從現行產品入口送 exact input、保存 exact visible output、graph 與 episode ID、實測 end-to-end 秒數、實際模型 call/token（無欄位即 `unavailable`，不填 0）；T10 另記檢索來源、speaker/owner、選用的 memory provenance 和最終字句。只讀確認正式 DB 未被碰；隔離 root 在記錄完成前保存，事後清理須只針對 launcher 回報的精確 root。
- 若 preflight／模型不可用，在 0 scored turn 停止並保留故障；不把 partial 當 fail/pass，也不換入口或繞過 sandbox。若某輪失敗，記原樣繼續剩餘輪以定位後果，0 retry、0 修改輸入。

## 事前判準與分支

主要 strict T10 PASS **同時**要求：否認使用者自稱喜歡桑の葉茶、指出紗枝為說喜歡者、值與關係正確、沒有把引用／老師或 T6 的使用者偏好串錯、可見自然日文；且 graph／持久 episode 顯示 T1 的真實先前來源確實進入檢索／決策。只說「沒有你的偏好紀錄」而不找回紗枝只算 partial；從當輪問題猜人名或引用錯來源算 fail。若有安全拒答但沒有來源，也不算完整理解。

次要 lifecycle gate：10/10 輪同一產品入口有可見日文與 graph、10/10 有持久 episode；T5→T6 真 PID／session 變化、同 DB 路徑；朋友／引用／老師不變成 user-current preference；逐輪 latency 及模型資源如實核帳。目標每輪 `≤20s`，超時另標成本 fail，不隱去品質結果。Safari 每輪可視檢查；若只完成 API 層，Safari 保持 pending。

此案無論正負都只建立**目前版本 before**，不證明比強 LLM 好。若 T10 失敗，先分 retrieval、actor decision、surface、持久性四層找最早失真，再只選一個有證據的修正變因；若通過，下一步是以全新未曝光案例、同基礎模型／同資訊／同生成上限的完整 transcript 強 baseline 比品質與成本，不重用本題當 holdout。Safari、真實長輪、真人、正式 temporal holdout 的結論彼此不代替。
