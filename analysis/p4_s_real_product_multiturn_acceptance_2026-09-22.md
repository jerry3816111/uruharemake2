# P4-S 真實產品多輪干擾驗收

狀態：**凍結 gate PASS；同時發現 4 個 gate 外的可見語意缺陷。**

## 這一步回答什麼

P4-R 已在離線 temporary Chroma 證明 typed-state 機制能抵抗第三人稱、引用、假設與其他 scope 的詞面干擾。P4-S 不重用那一案；它事前凍結另一組新值，透過真實產品入口、Safari、12 輪對話與一次真正 process restart，檢查這個機制是否在完整產品鏈仍成立。

## 凍結結果

| 指標 | 結果 | 門檻 |
|---|---:|---:|
| 成功對話 | 12/12 | 12/12 |
| 使用者可見自然日文 | 12/12 | 12/12 |
| 每輪 durable episode | 12/12 | 12/12 |
| 每輪 Safari node graph 可見 | 12/12 | 12/12 |
| 非寫入干擾誤寫 typed profile | 0/7 | 0 |
| 凍結 exact surface | 5/5 | 5/5 |
| 查詢中沒有答案的 recall | 2/2 | 2/2 |
| historical／negative 被拿來回答 | 0/0 | 0/0 |
| 最慢一輪 | 16.3151 秒 | ≤20 秒 |
| 12 輪總等待 | 121.1807 秒 | ≤180 秒 |
| 凍結 gate failed gates | 0 | 0 |

第 6 輪在 process 1 回答：

> 今の飲み物の好みは松葉茶。前のじゃなくて、今の方ね。

process 1 正常停止、7869 listener 關閉後才啟動 process 2；PID `30321 → 30585`、session `20260922_183428_41a5a0e9 → 20260922_184133_5916e29d`，但隔離 memory DB 不變。重啟後第 8 輪把目前飲料從 `松葉茶` 訂正為 `なた豆茶`，第 12 輪回答：

> 今の飲み物の好みはなた豆茶。前のじゃなくて、今の方ね。

最終 profile 恰有四筆：active drink=`なた豆茶`、active game=`ストラテジーゲーム`、historical drink=`松葉茶`、explicit negative drink=`松葉茶`。新飲料記錄的 `previous_current_memory_id` 指回舊飲料，negative 記錄的 `correction_current_memory_id` 指回新飲料；12 個 turn episode 另有 2 個背景 consolidation summary，兩者沒有混算。

## 成本與操作邊界

這次為 2 次 process start、1 次 restart、12 個真實 Safari turn、0 retry、0 fallback、0 付費 API、0 外部部署、0 production-memory access、0 function tool、0 VRM action、0 關閉使用者 tab。typed write/recall 的 product planner 追加 model call 為 0。

不能因此說整個流程是「零模型」：一般語意授權路徑實際完成了 9 次本機 `qwen3.5:9b` call，累計 provider elapsed `86.457` 秒；現有該 trace 沒有 token accounting，所以 token 成本必須標成 unavailable，不能填 0。

## gate 通過仍暴露的真問題

P4-S 的凍結 gate 是記憶 lifecycle gate，不是通用語意品質 gate。逐輪檢查發現四個明顯問題，而且現有 `semantic_persona_surface_verifier_m39` 都誤判為可接受：

1. 第 4 輪把「引用として…と書いた」回成 `甜茶が好きなんだ`，引用框架消失。
2. 第 7 輪把使用者「我先確認圖」回成 `うちは図が…確認する`，主體從使用者翻成角色自己。
3. 第 9 輪把「老師似乎喜歡松葉茶」改成直接問老師 `先生、松葉茶好き？`，傳聞陳述變成提問。
4. 第 10 輪沒有接住「把內嵌句當作假設」的指令，回覆與輸入目的不相干。

因此正確結論是：**P4-S 證明 typed current-preference 在一個全產品 12 輪＋重啟案例中可持久、可訂正且不被七個干擾輪污染；它同時反證目前可見回覆檢查器還不能可靠保存引用、假設、言語行為與說話者視角。**

這不能證明強 LLM 優勢、50 輪或 open-domain 記憶、被理解感、人類偏好、未來預測或人類方程式。下一步 P4-T 應只針對上述共同原因建立可反駁的「語境框架／說話者視角／言語行為保真」gate，先用曝光案例作 development failure，再用未曝光 multilingual holdout 判斷修正是否成立；不得回頭改 P4-S gate 讓它看起來更完整。
