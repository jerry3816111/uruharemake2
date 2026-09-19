# P3-B64 final equal-budget prediction acceptance

日期：2026-09-20

## 結論

`TERMINAL NEGATIVE / PREDICTION NOT FROZEN / FUTURE REMAINS LOCKED`。B64保持同一模型、真實公開
pre-cutoff context、prompt、JSON Schema、condition order、seed、temperature、六個labels及每組總completion ceiling
`512`，只把每組兩個calls的分配從`256+256`改為`320+192`。

第一個`BASELINE_LITERAL` representation call完成，但用了整個`320` completion-token上限後仍未通過JSON parse。
依事前freeze，B64是第二個也是最後一個execution correction；這條two-call prediction介面到此關閉，不重跑、不放寬
schema、不增加總token。

## 實際證據

- B62–B64事前與freeze tests：`26 passed`。
- local model：`qwen3.5:9b`；provider回報相同模型。
- 完成呼叫：`1`；prompt/completion tokens=`1986/320`；latency=`25.001742s`。
- call status=`completed`；失敗發生在model response回傳後的provider/schema parse boundary。
- system representation與兩組prediction calls：`0`。
- retry / fallback / future access / outcome score：全部`0`。
- raw prompt、response、representation沒有保存；因此可支持「再次精確到達ceiling」，不能聲稱已看到確切截斷內容。

保存結果：`analysis/p3_b64_final_equal_budget_prediction_result_2026-09-20.json`；canonical result hash
`5e7c4d2a3056e97d5bec8bb7b9f3dd017499e2a5013889d714eef6029c34b1c4`。

## 這個負結果改變什麼

目前證據否定的不是「語用狀態能否改善未來預測」，而是更窄的工程假設：在既定`512` completion-token資源內，
用兩次生成先產生可持久化前的完整representation JSON，再做prediction，這個介面可穩定完成。因為兩次公平修正都在
第一個literal representation就撞到token ceiling，還沒有生成任何baseline或system prediction，不能揭盲未來、不能比較
正確率，也不能推論系統優於或劣於一般LLM。

下一步若繼續，必須是另立、事前凍結的新prediction介面設計，不能把它描述成B62的第三次調參修正。
