# P4-K typed recall surface propagation 離線驗收

日期：2026-09-21  
狀態：`offline_pass_real_product_pending`  
單一變因：把當輪 `memory_data` 中已選中、已授權的 P4-J contract 傳到 final logic／surface／graph

## 為什麼要修這一層

P4-J 真實負結果已證明 typed record、active id、scope 與日文化值都能進入 rule plan；失敗發生在更後面。planner normalization
只保留已知 plan fields，沒有保留自訂的 `typed_current_preference_recall_p4` contract。原 visible guard 只查看 final logic，因此看不到
surface authority，既有 episode-based 回覆就成為最終輸出；materializer 同樣因缺 payload 而畫不出 P4-J node。

P4-K 沒有重做查詢、讀 DB 或增加規則值。它只在原 language guard 完成後，以固定優先序取得 contract：final logic 已有合法 contract
就沿用；否則才從同一輪 `memory_data` 取回。contract 必須同時符合正確 schema、`selected=true`、`surface_authority=true` 且有非空
`selected_core_jp`。safety-sensitive route 在取回前就直接返回，不能被覆寫。

## 先紅後綠的證據

事前凍結的新回歸在舊實作穩定得到 `2 failed, 3 passed`：

1. normalized logic 缺少自訂欄位時，沒有從 current-turn memory data 恢復 exact surface；
2. final logic 沒有恢復 contract，materializer 因此無法產生 P4-J select node。

修改後 5/5 P4-K 回歸通過，包括 exact surface、logic reattachment、單一 raw-free graph node、safety route 不接管、nonselected／invalid
contract 完全委派，以及既有 valid logic contract 優先。P4-F 至 P4-K 的受影響完整集合為 `179 passed`，只有既有 Chroma SWIG
deprecation warnings。

兩個 freeze verifier 原本把「凍結時 implementation hash」與「目前工作檔」直接比較，因此任何合法後續實作都會製造假失敗；驗證器改為
從各 freeze 已記錄的 immutable commit 讀 Git blob 再核對 hash。這只修 verifier 的時間參照，不改 freeze JSON、contract、產品路徑或案例結果。

## 尚未完成的驗收

本步沒有啟動新產品程序、沒有送 Safari 對話、沒有模型／網路／正式記憶／Function／VRM action。P4-J 的 rooibos 真實案例仍是 fail，
沒有被離線綠燈改寫。

下一步必須另立 acceptance freeze，使用全新隔離 root、新的 exact source value 與未用於 P4-J 真實案例的 query language，做兩程序、
兩輪、0 retry 的 cross-restart 驗收。只有 final visible answer、P4-J graph node、active source id、profile 不變與資源帳全部符合，才能釋出
bounded product pass。

## 證據邊界

P4-K 離線通過只證明已授權 contract 在受控測試中可以穿過 final delivery seam。它不證明真實產品已修好，也不證明 open-domain recall、
長對話可靠度、felt understanding、強 LLM 優勢或人類方程式。
