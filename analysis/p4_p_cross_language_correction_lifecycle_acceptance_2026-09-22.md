# P4-P 跨語言更正生命週期：終端 protocol failure

## 結果

P4-P 依事前 freeze 執行唯一一次、零重試的兩 process Persistent Chroma 診斷，gate 為 **fail（10 個 delivery gate）**。
這不是記憶遺失：中文寫入 `菊花茶` 後，以日文更正為 `クロモジ茶`；舊 positive、linked explicit negative、
新 positive 三筆資料都跨 process 保留，record IDs 與三個 canonical hashes 在重啟前、重啟後、recall 後完全相同。

實際 lineage：

- unique active：新值 `クロモジ茶` 1 筆；
- historical：舊值 `菊花茶` 1 筆；
- explicit negative：否定舊值 1 筆，且 `correction_current_memory_id` 指向新 active；
- process PID `14370 → 14371`，session ID 不同，同一 Persistent Chroma DB；
- 0 retry、0 fallback、0 model、0 paid API、0 production memory、0 external deployment。

但英文 answer-absent query 回覆的是 `今の飲み物の好みは、記録から確認できない。`，不是凍結的
`今の飲み物の好みはクロモジ茶。前のじゃなくて、今の方ね。`。

## 原因定位

P4-P 把 write/correction timestamps 固定為 `08:00` / `08:01`，實際執行後的本機時鐘觀察仍是 `07:57:12 +08:00`。
typed record 會把 timestamp 寫入 `valid_from`；validity policy 在 reference time 早於 `valid_from` 時，正確標成
`not_yet_valid`。因此：

- probe 用明示 `08:02` 檢查 process-start lineage 時，新值是 active；
- P4-O 用真實 wall clock 做 default-time recall 時，兩個 positive 都尚未生效，所以回 `no_active`。

這是 **凍結測試時間晚於實際時鐘的 protocol 設計錯誤**，不是已證實的產品缺口。依事前規則不重跑、
不改同一 pair、不修改答案或 gate。

## 下一個必要交付

P4-Q 需另立 freeze，使用全新 value pair，唯一改變是把 timestamps 固定在已經過去的時間；產品碼、lineage、
answer-absence、日文 surface、零重試與資料保留規則全部不變。P4-Q 通過前，不能宣稱跨語言更正已成功交付。

## 證據邊界

P4-P 只證明三筆更正 lineage 跨真實 Python-process restart 沒有遺失或被改寫；因 protocol timestamp 錯誤，
它沒有有效驗證 default-time delivery，也不能外推為任意多語更正、長對話記憶、被理解感、優於 LLM 或人類方程式。
