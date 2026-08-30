# V2.18–V2.22 50 輪記憶修正、比較與分析（2026-08-14）

## 結論先行

三個由 V2.18 定位的故障中，兩個已在新值 50 輪案例上完成 end-to-end 修復，一個只完成部分修復：

1. **T26 明確更新被主動澄清蓋過：已修復。** 使用者說現在改成 `ほうじ茶` 時，系統直接承接新值，profile 同步撤回 `麦茶`。
2. **T48 正確記憶到達決策、卻輸出內部日文修復指令：已修復。** 正確 `favorite_drink → ほうじ茶` anchor 現在能成為自然日文回答。
3. **T50 偏好疑問句被當成使用者斷言：部分修復。** 系統不再把 `レモネード` 寫成使用者偏好，也從錯誤肯定修成直接否定；但尚未穩定回溯 T41 的「朋友」來源，因此未通過嚴格人物綁定 gate。

V2.22 第一次完整正式結果為 **4/5 strict task、gate failed**。完整 transcript LLM 同樣是 4/5；因此不能主張 UruhaBrain 回答品質全面優於單純 LLM。UruhaBrain 的已證明差異是有限上下文外的狀態保留、撤回、來源 trace、全 checkpoint 日文與錯誤定位；代價是更高 token 與約 23 倍延遲。

## 實驗序列與失敗保留

| 版本 | 改動／目的 | 第一次正式結果 | 是否保留 |
|---|---|---|---|
| V2.18 | 原始 coffee → chamomile tea 50 輪診斷 | 主要有來源回溯 1/2；T26、T48、T50 暴露三個不同 failure stage | 是 |
| V2.19 | 新值 `麦茶 → ほうじ茶`，套用第一批修復 | 主要回溯 2/2、strict task 3/5；T50 仍錯誤肯定 | 是 |
| V2.20 attempt 1 | 鎖定同題 causal replay | 五輪生成後 summary key `KeyError`，沒有 raw，不能算實驗結果 | 是；另有 failure report |
| V2.21 | 只修 T50 denial polarity | strict task 4/5；T50 正確否定但沒說朋友 | 是 |
| V2.22 | 嘗試從可觀察近期事件穩定綁定人物 | strict task 4/5；T50 仍只找到「無使用者偏好紀錄」，沒取到 T41 | 是 |

V2.20 attempt 1 沒有產生 `raw.json`，所以不能被當成 pass 或 fail，也不引用當時未保存的模型回答。V2.21 與 V2.22 都重新凍結 runtime、runner、prereg、測試與既有 baseline raw；第一次完整結果保留。

## 新的 50 輪測試設計

- T1：使用者說準備簡報時最喜歡 `麦茶`。
- T2–T24：23 輪干擾，其中 T7 是朋友的 `レモネード`，T14 是老師的紅茶，T21 是菜單上的抹茶拿鐵。
- T25：24 輪後回溯舊偏好。
- T26：明確撤回 `麦茶`，改成 `ほうじ茶`。
- T27–T47：21 輪干擾，其中 T34 是妹妹喝 `麦茶`，T41 再次出現朋友的 `レモネード`。
- T48：22 輪後回溯目前偏好。
- T49：確認 `麦茶` 沒有被保留為目前最愛。
- T50：詢問使用者是否曾說自己最喜歡 `レモネード`；嚴格成功必須說出物件、否定使用者所有權、並指出朋友來源。

非 checkpoint 輪次是新凍結 transcript 經 production `save_episode` 寫入隔離 DB；T25、T26、T48、T49、T50 才是完整 Uruha runtime 生成。不得稱為 50 輪全部 fresh generation。

## 三組公平比較

| 條件 | 資料可見性 | 生成方式 |
|---|---|---|
| UruhaBrain | 外部 episodic/profile memory、最近對話、decision trace | qwen2.5 規劃＋deterministic memory surface＋visible guard |
| 單純 LLM最近 8 輪 | 只看 prior 8 turns，沒有外部記憶 | 同一 qwen2.5:7b 單次生成 |
| 單純 LLM完整 transcript | 看完整 prior transcript，沒有外部記憶 | 同一 qwen2.5:7b 單次生成 |

V2.21／V2.22 causal replay 沒有重新生成兩個 LLM baseline，而是逐 byte 沿用 V2.19 第一輪結果；只有修正後 UruhaBrain 重新生成。這讓同題前後差異較容易歸因於程式修正，但不是 fresh baseline comparison，也不是獨立 holdout。

## V2.22 正式自動結果

| 指標 | UruhaBrain | LLM最近 8 輪 | LLM完整 transcript |
|---|---:|---:|---:|
| 主要 current value hit | 2/2 | 0/2 | 2/2 |
| 主要 source-grounded recall | 2/2 | 0/2 | 2/2 |
| strict task | 4/5 | 1/5 | 4/5 |
| stale value revival | 0 | 1 | 0 |
| false-memory positive assertion | 0 | 1* | 1* |
| visible Japanese | 5/5 | 3/5 | 4/5 |
| model calls | 4 | 5（V2.19 frozen） | 5（V2.19 frozen） |
| total tokens | 13,435 | 2,526 | 7,405 |
| checkpoint latency | 255.51 s | 12.53 s | 10.99 s |

`*`：舊 base scorer 對「まだレモネードについて言及してない」的否定窗口辨識不足，因此把兩個 baseline T50 標成 false positive。V2.19 預先加嚴的 task gate仍要求人物來源，所以兩者 T50 都不通過；工程分析必須直接看句子，不把這個 proxy 當語意真值。

Uruha 相對完整 transcript 為約 **1.81× tokens、23.24× latency**；相對最近 8 輪為約 **5.32× tokens、20.40× latency**。這是 full-system 非 token-parity 成本，不能只歸因於記憶模組。

## 五個 checkpoint 實際回答

### T25：舊值長距離回溯

- UruhaBrain：`麦茶って言ってただろ。` — pass，profile trace 指到 T1。
- 最近 8 輪：`簡報前はいつもカフェラテだね。` — fail，來源不存在且捏造カフェラテ。
- 完整 transcript：`記憶にある限りでは、準備する時は麦茶が好きなんだな。` — pass。

### T26：明確更新

- UruhaBrain：`今の本命はほうじ茶ってことな。覚え直しとく。` — pass；新值可見、profile 變成 `favorites=[ほうじ茶] / dislikes=[麦茶]`。
- 最近 8 輪：`了解した。今後ほうじ茶が飲むのが標準になるのかな。` — 內容承接，但日文略不自然。
- 完整 transcript：`了解だ。今後はほうじ茶が一番なんだな。覚えておく。` — pass。

### T48：修正後長距離回溯

- UruhaBrain：`忘れてないし、ほうじ茶だろ。` — pass；`favorite_drink → ほうじ茶`。
- 最近 8 輪：`現在のあなたの飲料偏好は話題外ですが、簡報時は水分補給にレモネードが良いかもしれませんね。` — fail；錯猜レモネード並混入中文。
- 完整 transcript：`今ならほうじ茶が一番なんだな。` — pass。

### T49：撤回舊值

- UruhaBrain：`麦茶はもう前の情報だろ。今の好みとして見てない。` — pass；舊值留在 history/dislike，而不是 current favorite。
- 最近 8 輪：`そういえば、あなたは麦茶を現在一番好むとおっしゃっていましたね。` — fail；直接復活舊值。
- 完整 transcript：`すみません、現在はほうじ茶が好きだっていうのを忘れていました。forgettable` — 內容方向正確，但英文漏出、語氣不符。

### T50：人物綁定控制

- V2.19 Uruha：`レモネードが好きなんだな。そこは覚えとく。` — fail；把疑問錯說成肯定。
- V2.21 Uruha：`お前がレモネードを一番好きとは聞いてない。` — partial；否定正確，但沒有朋友來源。
- V2.22 Uruha：`レモネードが本命って記録はない。そこは勝手に足さない。` — partial；穩定、安全、自然日文，但沒有朋友來源。
- 最近 8 輪：`まだレモネードについてのお話はありませんでした。麦茶が現在一番好きだとおっしゃっていました。` — fail；否定後復活已撤回的麦茶，且敬語不符。
- 完整 transcript：`まだレモネードについて言及してないよ。今のところ、あなたが一番好きな飲み物はほうじ茶だね。` — 語意上相當好，但嚴格 gate 要求指出朋友來源，所以列 partial。

## T50 真正未解原因

T41 的原始事件是「朋友又說那杯レモネード很好喝」。到 T50 時：

1. runtime `recent_turns` 只有 prior 8 turns，即 T42–T49，T41 剛好離開視窗；
2. 外部 working-memory ranking 在 V2.19 曾選到 T41，但 V2.21／V2.22 沒有穩定選中；
3. question parser 已正確辨識這是 query，不再產生 `current_preference_update`；
4. assertion/polarity guard 阻止把它說成使用者偏好；
5. 因人物來源沒有進入 decision view，最終只能說「沒有這個使用者偏好紀錄」，不能有證據地補上「那是朋友」。

這證明「沒有捏造」與「完整理解人物關係」不是同一件事。V2.22 做到前者，尚未做到後者。

## 可以與不可以主張

### 已支持

1. 新值 50 輪案例上，V2.18 的更新承接與 surface leakage 兩個故障已修復。
2. UruhaBrain 相對 recent 8-turn LLM，能保留並回溯視窗外的目前偏好，且不復活被撤回舊值。
3. 兩次主要回溯都有 profile/source trace，可定位記憶、anchor、surface 各層。
4. Uruha 可見日文為 5/5；兩個 direct LLM 為 3/5 與 4/5。
5. T50 從錯誤肯定修成直接否定，profile 沒被 false memory 污染。
6. 正式 DB hash 前後相同，測試使用隔離 DB。

### 沒有支持

1. UruhaBrain end-to-end 回答全面優於完整 transcript LLM；兩者 strict task 都是 4/5。
2. T50 的跨視窗人物來源綁定已完成；這仍是唯一 strict gate failure。
3. token 或 latency 成本優勢。
4. 對新記憶類型、不同人物關係或 50+ 輪的獨立泛化。
5. 人類主觀被理解感或偏好；沒有完成盲評。
6. 人類意義的理解、讀心、意識或完整人腦方程式。

## Safari 圖像驗收

2026-08-14 已在使用者外部 Safari 對 `http://127.0.0.1:7863` 重新載入並實際切換三個 checkpoint：

- T26：首頁顯示 `PASS · T26`，三組回答與 `current_preference_update → ほうじ茶` flow 一致；證據 `analysis/v2_22_safari_memory_repair_t26.jpeg`。
- T48：首頁顯示 `PASS · T48`，Uruha 回答 `忘れてないし、ほうじ茶だろ。`，profile source → anchor → final reply 一致；證據 `analysis/v2_22_safari_memory_repair_t48.jpeg`。
- T50：首頁顯示 `PARTIAL · T50` 與 `4 / 5 · GATE FAILED`，且清楚標出 T41 不在 recent 8、ranked retrieval 未選入；證據 `analysis/v2_22_safari_memory_repair_t50.jpeg`。

驗收後頁面停在 T50，Safari 原有 7 個分頁全部保留，沒有關閉任何使用者頁面。Web 使用 `/tmp/uruha-v222-web-*` 隔離資料路徑，沒有使用 production memory DB。

## 下一個合理研究單元

停止在同一飲料題繼續加規則。下一步應建立**關係事件的結構化記憶分子**：`actor=user/friend/teacher`、`relation`、`object`、`predicate`、`polarity`、`time/source/confidence`，並以全新物件與全新關係做未見 50+ 輪 holdout。比較：

1. 現有 text retrieval；
2. 結構化 relation-event retrieval；
3. 完整 transcript LLM。

成功條件要同時涵蓋人物、物件、斷言方向、來源 trace、自然日文、錯誤後不污染 profile；之後才值得進行盲評。
