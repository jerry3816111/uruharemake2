# M52：候選欄位與口語表面已對齊；來源外的 scaffold 仍被誤放行

日期：2026-08-30。安全 worktree、隔離 Web session、Safari 外部瀏覽器。
結論：**M52 candidate-realization contract PASS；source-aligned practical-help pipeline FAIL**。

## 改了什麼

M52 只在 M51 候選進 M46 前做 deterministic realization：object 若沒逐字出現在 instruction，
只能縮成兩個生成欄位共同已有、位於可見受詞位置的日文子字串；規格句尾轉成 casual command；
舊「只要句中有三個就算 stop」的漏洞則改為把候選既有 stop condition 真正說出來。

source ID/span、goal、unknown、mechanism、effect、stop 不變，不新增模型呼叫；找不到共同物件就
fail closed，修後仍由 M46 structural + counterfactual review 決定交付。trace 只保留 digest 與
改動類型，不保存 raw candidate、不中途寫長期記憶。

## 測試

- 初始整合測試 2 fail：fixture 沒有複製 M50 真實重寫後的 source ID，所以只到 plan call；修正
  fixture 而未改產品 gate。首版真 Web 又發現 count-only stop proxy，補成只使用既有 stop 欄位。
- 聚焦最終 36/36；M16–M52 選定回歸 **313/313，43.53 秒**，3 個既有依賴警告。
- 正式 Safari session `20260830_164209_4f6310e9`：5/5 trace、5/5日文；三正例 realization
  contract 3/3，交付2/3，兩安全負例2/2。

## 真實結果與不能冒稱的部分

日文分色輸出變為：`赤い紙を赤い色のグループに集めてみよ。…止めよ。`，來源對齊且交付。
日文白紙報告也被交付，但自行補了 `環境／経済／社会` 三個分類；來源沒有題目，這是明確的
false accept。英文 report 的 object 綁定已修好，卻仍因長規格句被 casual-Japanese proxy 拒絕。
因此 automated delivery 是2/3，bounded author source alignment只有1/3。

五輪共6次完成模型呼叫、4731 prompt＋1855 completion tokens，M46路徑95.84866秒。這不是
獨立holdout、人評自然度、felt-understanding或人腦方程式證據。

## 下一步

M53 只修 **source-neutral scaffold authorization**：具體 scaffold label／topic 若無 exact source
證據不能交付；允許空白槽位、題目占位或純結構，不得硬編分類。M46 same-model reviewer仍保留，
但不能再讓它單獨判斷「沒有捏造」。英文長句自然化另列，避免一次混兩個變因。
