# V2.17 Long-Dialogue Memory Trace 驗收報告（2026-08-14）

## 結論

在一個隔離資料庫中，UruhaBrain 完成了 25 輪長對話記憶實驗：第 1 輪寫入偏好，經過 15 個無關話題後於第 17 輪回溯；第 18 輪明確撤回舊偏好並指定新偏好，再經過 5 個無關話題後於第 24、25 輪確認新值與舊值撤銷。四個 checkpoint 的使用者可見回答皆為自然日文，目標記憶皆可在 runtime trace 中追到「檢索／結構化狀態 → 傳入決策 → memory anchor → 回答」。

這是 `bounded pass`：它證明這一個 25 輪、單一偏好修正案例在本機隔離環境成立，不證明無限長、跨月、跨裝置或任意類型記憶都成立。

## 實際對話節點

| 輪次 | 作用 | 使用者輸入 | 實際可見回答 | 結果 |
|---:|---|---|---|---|
| 1 | 記憶種子 | 我讀論文時最喜歡喝草莓牛奶。 | 凍結 transcript，經正式 `save_episode` 寫入隔離 DB | 寫入 |
| 2–16 | 干擾 | 15 個彼此無關的話題 | 凍結 transcript，經正式 `save_episode` 寫入隔離 DB | 保持干擾 |
| 17 | 延遲回溯 | 隔了這麼多個話題，你還記得我讀論文時最喜歡喝什麼嗎？ | 前にいちごミルクが好きって言ってたし。 | PASS |
| 18 | 明確修正 | 不過現在改了。我不能喝草莓牛奶了。我最喜歡 ginger ale。 | 今はジンジャーエールが一番なんだな。そっちに更新しとく。 | PASS |
| 19–23 | 再干擾 | 5 個彼此無關的話題 | 凍結 transcript，經正式 `save_episode` 寫入隔離 DB | 保持干擾 |
| 24 | 修正後回溯 | 那我現在讀論文時最喜歡喝什麼？ | ジンジャーエールって言ってただろ。 | PASS |
| 25 | 撤銷確認 | 你沒有還把草莓牛奶當成我現在最喜歡的吧？ | 前のままじゃない。いちごミルクは今の本命から外してる。 | PASS |

第 17、18、24、25 輪走完整 UruhaBrain runtime。其餘 21 輪中的記憶種子與 20 個干擾輪是凍結 transcript，使用 production `save_episode` 路徑寫入；它們不是 fresh model generation。這個區分是本實驗的證據邊界。

## 成功條件與證據

- 總輪數：25。
- 干擾輪數：20。
- full-runtime checkpoints：4。
- 15 輪後初始偏好回溯：PASS。
- 修正後 5 輪再回溯：PASS。
- 舊偏好不再被當成目前偏好：PASS。
- 四個 checkpoint 可見回答皆為日文：PASS。
- 四個 checkpoint 的目標訊息皆傳入決策：PASS。
- 記憶 anchor 因果代理檢查：移除目標訊息會改變／移除 anchor，移除無關訊息不影響 anchor：PASS。
- 正式資料庫 aggregate SHA-256 前後相同：`c56a8201731a004c8c031d01908e8c6ebd7c7b3aafdd295dc6d898873d859da6`。

因果檢查目前只到 decision-anchor mechanism proxy；尚未為每個 checkpoint 再做一次「移除記憶後重新呼叫模型」的完整生成級 ablation，因此不可稱為 full-model causal proof。

## 失敗與修正紀錄

1. 第一次正式執行：初始與修正後回溯成功，但第 18 輪回答仍重複舊值，第 25 輪也被語言 guard 錯誤拉回草莓牛奶。
2. 修正 current-input preference priority 與否定語意後，第二次執行產生正確回答，但 evaluator 的正規式把正確否定句誤判失敗。
3. 修正 scorer 與中日記憶正規化後，第三次執行通過回答層，但 UI 的 trace 選到錯誤 passed row。
4. 修正 UI 目標列對齊後，最終執行完整通過。

原始失敗結果保留為 `analysis/v2_17_long_dialogue_memory_raw_attempt1.json` 至 `attempt4.json`；當前正式結果為 `analysis/v2_17_long_dialogue_memory_raw.json`。

## 測試範圍

- 針對性測試：`test_long_dialogue_memory_v2_17.py`、`test_user_visible_japanese_guard_v2_11.py`、`test_equation_lab_v2_16.py`，33 passed。
- 相關擴充測試：191 tests，190 passed；1 個 failure 是舊 frozen harness 對 `uruha_brain_mac.py` 的預期 hash 因本次有意修改而漂移，不是 runtime 行為失敗。
- 全歷史 `unittest`：3729 tests，60 failures、42 errors、1 skipped；包含既有缺少 `mlx`／LoRA artifacts、舊 frozen hashes 與資料集 audit 問題。不得宣稱全套測試通過。

## 圖像展示

Web 第一頁為 `Long Memory Lab`，以 25 個 node 顯示對話時間軸；點選四個 checkpoint，可查看來源輪次、目前 profile、實際傳入決策的記憶列、決策 anchor 與最終日文回答。頁面同時顯示所有正式嘗試與失敗原因，不把技術分析傾倒在一般 Chat 回覆中。

Safari 驗收截圖：

- `analysis/v2_17_safari_long_memory_turn17.png`
- `analysis/v2_17_safari_long_memory_turn25.png`

## 還沒有證明的部分

- 100+ 輪、跨程序重啟、跨日／跨月的可靠回溯。
- 姓名、事件、關係承諾、情緒變化等非飲料偏好的通用記憶修正。
- 多個相似、互相干擾或部分矛盾記憶下的誤召回率。
- 完整生成級 memory ablation。
- 相同模型與 token budget 下，相對長上下文／一般 RAG／直接 LLM 的盲評優勢。

下一個最有價值的單一研究單元，是凍結一組 100+ 輪、多種記憶類型、跨程序重啟的 holdout，加入 false-memory controls 與 full-model ablation；完成前，不把本次 bounded pass 外推為完整長期記憶能力。
