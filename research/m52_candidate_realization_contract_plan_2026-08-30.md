# M52 Candidate Realization Contract · 2026-08-30

## 單一問題

M51 已在三個真 Safari 正例都產生兩個不同候選，但 report 類候選有兩個可分離的「同一層」失敗：
操作物件被寫成帶動詞的長句，沒有逐字出現在 instruction；或 instruction 以規格書式字典形結尾，
content review 通過但 casual-Japanese surface review 拒絕。這些不是 task-source、goal、effect 或
counterfactual usefulness 的問題，而是同一候選內部欄位與可見日文沒有一致實現。

## 可反駁修改

只在 M51 候選送進結構檢查前做 deterministic realization：

1. object 已逐字出現在 instruction 時不改；否則只能縮成同時逐字出現在原 object 與 instruction、
   且位於可見受詞位置的日文子字串。找不到就 fail closed。
2. 把既有 instruction 的規格書式句尾轉為短 casual command；只改動已生成的操作與停止表面，
   不新增工具、順序、分類規則或任務內容。
3. batch 的 source id/span、goal、unknown，以及 candidate 的 mechanism/effect/stop 完全不變；
   operation object/verb/instruction 的前後 digest 與是否改動進 trace，不存 raw candidate。
4. 不新增模型呼叫；修後仍先過 M51/M46 structural gate，再由原 M46 same-model
   counterfactual content/surface review 決定是否交付。

## 成功條件

- 單元／契約：共同可見 object 才能縮寫、semantic fields byte-for-byte 不變、無共同 object 時拒絕、
  M46 content false 仍不能交付、missing-task/no-method 零介入、node/card 唯一相連。
- 真 Safari：日／英 report 與日文 color 三個正例都生成兩候選；至少兩個 report case 的選中候選
  structural pass，M46 實際輸出自然日文且 source-aligned；兩個安全負例不呼叫 M52/M51。
- 失敗條件：用固定 task 白名單、改 goal/effect/stop、補原候選沒有的操作、跳過 M46、只看 trace
  不看實際 Web output，或把 same-model proxy 寫成人類效用／偏好證據。

## 邊界

這只驗證候選欄位／日文表面一致化，不證明建議普遍有用、自然度已經人評、系統理解真實心理，
也不是「人腦方程式」完成。若真 Web 仍被 content review 拒絕，下一個 M 必須處理新的單一原因，
不能在 M52 放寬 reviewer。
