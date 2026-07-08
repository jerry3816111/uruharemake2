# RightBrain Repair Selection Dataset v1

## 一句話結論

建立 360 題右腦修復候選選擇資料；每題只有 1 個乾淨候選，其餘候選含已標註的語意漂移、語言污染、語氣漂移、指令外漏或過長錯誤。

## 這次新增的能力

| 項目 | 數值 | 意義 |
|---|---:|---|
| selection rows | 360 | 可測選擇器的題數 |
| total candidates | 3375 | 候選總數 |
| gold candidates | 360 | 乾淨標準候選 |
| invalid candidates | 3015 | 應被拒絕的錯誤候選 |
| semantic drift candidates | 142 | 表面乾淨但不符合目前左腦語意 |
| invalid ratio | 89.3% | 選擇器主要要避開的比例 |

## 錯誤類型分布

| 錯誤 | 候選數 |
|---|---:|
| ascii_leak | 722 |
| polite_tone_drift | 361 |
| chinese_leak | 360 |
| forbidden_marker | 360 |
| instruction_or_plan_leak | 360 |
| nonstandard_cjk_surface | 360 |
| required_marker_missing | 360 |
| over_max_chars | 356 |
| semantic_reference_drift | 142 |

## 候選來源分布

| 候選來源 | 數量 |
|---|---:|
| ascii_leak | 360 |
| chinese_leak | 360 |
| forbidden_marker | 360 |
| gold_valid_reply | 360 |
| instruction_or_plan_leak | 360 |
| missing_required_marker | 360 |
| nonstandard_cjk_surface | 360 |
| polite_tone_drift | 360 |
| over_max_chars | 353 |
| semantic_reference_drift | 142 |

## 研究邊界

- 這不是把 holdout 或 ToMBench 答案塞給模型。
- 這是在建立右腦修復選擇器的可重現訓練/評測底座。
- 語意漂移候選以跨合約、低文字重疊方式合成；它是受控 curriculum，不等同開放世界語意理解。
- 目標是讓右腦不要把左腦已經想好的語意弄丟，也不要輸出中文、英文、敬語漂移或指令文字。
