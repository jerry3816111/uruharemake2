# V2.18 50-Turn Memory Comparison 驗收與分析（2026-08-14）

## 結論先行

第一次正式、事前鎖定的 50 輪比較 **沒有通過 UruhaBrain 預註冊門檻**。這個負結果被保留，沒有為了追分改題目、scorer 或重跑。

本案例支持一個較窄但重要的結論：UruhaBrain 的外部記憶確實能在來源離開最近 8 輪後，保留、修正並把正確狀態送進決策；但是「記憶送達決策」尚未穩定轉化為正確的最終回答。完整 transcript 的單純 LLM 也能找回主要內容，因此本實驗不支持「UruhaBrain 比單純 LLM 更會推理或回答品質全面更好」。

目前最清楚的系統價值是可追溯與可定位：T48 的錯誤能明確定位為 final surface failure，而不是 retrieval failure。代價則是本次 UruhaBrain 總 token 約為完整 transcript LLM 的 1.85 倍、總延遲約 24.97 倍。

## 為什麼不是只有兩組

| 條件 | 看見什麼 | 用途 |
|---|---|---|
| `uruha_memory` 實驗組 | 最近對話＋外部 episodic/profile memory＋decision trace | 測完整 UruhaBrain 架構 |
| `plain_recent` 主控制組 | 同一 `qwen2.5:7b`、相同人格輸出要求，只看最近 8 輪 | 測來源離開有限上下文後的直接 LLM |
| `plain_full` 診斷參考組 | 同一 `qwen2.5:7b`、相同人格輸出要求，看完整 prior transcript | 判斷外部記憶是否只是替代長上下文 |

如果只有 UruhaBrain 與最近 8 輪控制組，即使 UruhaBrain 勝出，也只能說一邊有資料、一邊沒有。加入完整 transcript 組後，才能區分：

1. 單純 LLM 在拿到原文時能不能回答；
2. 外部記憶是否帶來來源壓縮、修正與追溯；
3. 完整架構是否把正確狀態穩定轉化為可見回答。

這是架構級比較，不是 token-parity。UruhaBrain 使用多階段規劃與 deterministic surface；直接 LLM 是單次生成。成本差異是結果的一部分，但不能單獨歸因為記憶模組。

## 凍結的 50 輪內容

- T1：使用者偏好 `coffee`。
- T2–T24：23 輪無關話題；其中包含「朋友點 melon soda」「老師拿 ginger ale」「菜單上有 chamomile tea」等關係／詞彙干擾。
- T25：24 輪後詢問原偏好。
- T26：使用者明確撤回 coffee，更新為 `chamomile tea`。
- T27–T47：21 輪干擾；包含「弟弟每天喝 coffee」「朋友傳 melon soda 照片」。
- T48：22 輪後詢問目前偏好。
- T49：確認 coffee 沒有被保留為目前偏好。
- T50：詢問自己是否曾說最喜歡 melon soda；正確系統必須區分「朋友」與「使用者」。

所有非 checkpoint 回答都是凍結 transcript，透過 production `save_episode` 寫入隔離 DB，不是 50 輪 fresh generation。T25、T26、T48、T49、T50 為三條件真實生成。

## 預註冊自動結果

| 指標 | UruhaBrain | LLM 最近 8 輪 | LLM 完整 transcript |
|---|---:|---:|---:|
| 主要回溯 exact current value | 1/2 | 0/2 | 1/2 |
| 有來源的主要回溯 | 1/2 | 0/2 | 1/2 |
| 自動 task proxy | 3/5 | 1/5 | 2/5 |
| 舊值正面復活 | 0 | 0 | 0 |
| false-memory 正面斷言 | 0 | 0 | 0 |
| 日文輸出契約 | 5/5 | 3/5 | 2/5 |
| 模型呼叫數 | 4 | 5 | 5 |
| prompt tokens | 8,337 | 2,397 | 7,283 |
| completion tokens | 5,335 | 129 | 91 |
| prompt＋completion | 13,672 | 2,526 | 7,374 |
| checkpoint 總延遲 | 268.79 s | 14.33 s | 10.76 s |

`uruha_preregistered_gate_pass=false`，原因是主要有來源回溯只達 1/2，而成功門檻是 2/2。

自動 proxy 也暴露兩個限制，不能直接當成人類品質分數：

- T50 UruhaBrain 回答「もう一回だけ聞かせて」，沒有捏造但也沒有回答；預註冊 false-memory scorer 因為只要求「不正面斷言 melon soda」而算 task pass。正式數字保留，但人工分析把它列為 non-answer。
- T48 完整 transcript LLM 生成「チャモロ茶」，語意接近 chamomile tea，但 exact anchor 不承認；這是表面詞形失敗，不等於完全沒取到內容。

Web 圖像頁因此把兩種判斷分開：`凍結 auto proxy` 保留預註冊結果，`REVIEW PASS / PARTIAL / FAIL` 則是生成完成後、不回寫 scorer 的工程複核。T50 的 Uruha 回覆會同時顯示 `auto proxy ✓` 與 `REVIEW FAIL`，避免把安全但未回答的輸出包裝成成功。

## Safari 圖像驗收

- `analysis/v2_18_safari_50_turn_comparison_t48.jpeg`：T48 正確記憶與 anchor 已抵達決策，但 final surface 失敗。
- `analysis/v2_18_safari_50_turn_comparison_t50.jpeg`：T50 凍結自動 proxy 與人工複核相反，並顯示疑問句誤解析位置。
- 兩張皆由 Safari `127.0.0.1:7863` 的實際頁面保存；驗收時維持 7 個分頁，沒有關閉使用者頁面。

## 三組實際回答與工程觀察

### T25：第一次延遲回溯

- UruhaBrain：`忘れてないし、コーヒーだろ。` — 正確，trace 指向 `favorites=coffee`。
- 最近 8 輪：`好きだった飲み物は覚えてるよ。何か飲もうか？` — 沒有來源也沒有給值，卻宣稱記得；不屬於安全 abstention。
- 完整 transcript：`読む時はコーヒーが好きだよ。` — 正確；證明單純 LLM 看得到 T1 時可以回答。

### T26：明確修正

- UruhaBrain：`先に、今は放っといてほしいのか、少し聞いてほしいのかだけ教えて。` — 回覆失敗；但 profile 已正確變成 `dislikes=[coffee]`、`favorites=[chamomile tea]`。錯在 reply planning，不在 state update。
- 最近 8 輪：`了解、今はチャモライルティーが一番だね。…` — 理解更新方向，但飲料名稱錯拼。
- 完整 transcript：`agoraは胃がbuatせんからchamomile teaが一番だな。…` — 理解更新內容，但多語混雜，輸出契約失敗。

### T48：修正後長距離回溯

- UruhaBrain：`日本語だけで、元の意味を落とさず言い直す。そのくらいでいいだろ。` — 回覆失敗。
- UruhaBrain 內部：`favorites=chamomile tea → favorite_drink → カモミールティー` 全部正確。因此可定位成 final surface／repair instruction leakage。
- 最近 8 輪：模型猜「水」，內容錯誤；T26 已離開視窗。
- 完整 transcript：`読む時はチャモロ茶が一番だよ。` — 大致找到洋甘菊茶，但名稱生成失真。

### T49：舊值撤銷

- UruhaBrain：`前のままじゃない。コーヒーは今の本命から外してる。` — 正確，而且 `dislikes=coffee` trace 可見。
- 最近 8 輪：不確定目前值，並混入英文與敬語。
- 完整 transcript：知道已更換，但名稱錯拼並混入英文。

### T50：關係綁定／false-memory control

- UruhaBrain：`ん、もう一回だけ聞かせて。` — 沒把朋友的 melon soda 寫進 profile，也沒有捏造；但沒有回答問題，而且 `_extract_explicit_current_favorite` 把疑問句誤判為 `current_preference_update`。assertion-scope 阻止了實際 profile 污染，但 decision anchor 仍錯。
- 最近 8 輪：說沒有紀錄後又建議喝 melon soda；來源不足且語言契約失敗。
- 完整 transcript：正確指出是朋友喝、使用者沒說過；但混入 `melon soda` 與中文 `朋友`，語言契約失敗。

## 真正得到的研究結論

### 已支持

1. 50 輪下，外部 profile 能保留 T1、在 T26 撤回舊值，並於 T48 將正確新值送進決策。
2. 相對最近 8 輪控制組，UruhaBrain 有來源保存與可追溯優勢。
3. UruhaBrain 的 final visible Japanese guard 明顯優於兩個直接 LLM 條件（5/5 vs 3/5 vs 2/5）。
4. trace 能把「記憶錯、決策錯、表面化錯」分開；T48 是具體反例。
5. 正式 DB aggregate hash 前後相同，測試未污染 production memory。

### 沒有支持

1. UruhaBrain 的 end-to-end 回答品質優於完整 transcript LLM。
2. 外部記憶等於更高理解力；完整 transcript 組顯示原始 LLM 在有證據時也能回溯。
3. 成本優勢；本次 UruhaBrain 比完整 transcript 組使用 1.85 倍 token、24.97 倍延遲。
4. 人類被理解感或偏好優勢；盲評 packet 已建立，但目前評分是空白。
5. 獨立 semantic holdout；此案例仍是 V2.17 preference-revision family 的長度擴張。

## 下一個修復研究單元

第一個正式結果不得覆寫。下一輪應另立新的 frozen remediation case，單一處理三個已定位失敗：

1. 明確偏好更新不得被 stale active-validation 策略蓋過；T26 應先承接新值。
2. 有可說的 memory anchor 時，final language repair 不得輸出「日本語だけで」等內部指令；必要時回退到 deterministic memory-grounded reply。
3. `最喜歡／favorite` 疑問句不得被解析成新的 preference assertion；T50 要保持 query 而非 `current_preference_update`。

修正後只能稱為 development remediation。要宣稱泛化，還需要全新記憶類型、全新值、未參與修復的 50+ 輪 holdout，再做同樣三條件比較與人工盲評。
