# 右腦候選 Gate 與 Selector 可觀測性 Multiseed 報告

## 一句話結論

新 gate 主要提升候選品質邊界與 selector 可觀測性，不追求提高模型接管率；兩個 seed 的 final quality 皆維持 100%，且 20260709 擋掉更多不自然候選。selector 診斷顯示未接管候選平均分數仍低於 deterministic，因此目前不應放寬 selection margin。

## 對照表

| seed | accepted before | accepted after | delta | selected before | selected after | final quality after | avg score gap after |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20260708 | 16 | 16 | 0 | 2 | 2 | 100.0% | -0.1929 |
| 20260709 | 21 | 16 | -5 | 2 | 2 | 100.0% | -0.325 |

## 這次改動代表什麼

- gate 變嚴格：會擋外文字形、異常標點、客服/照護者語氣、非日文字形殘留。
- 可修復的 tokenizer 空格會先正規化：例如「胃 が」會變成「胃が」，避免把可修復表面問題誤判成語意失敗。
- selector 沒有被放寬：因為診斷顯示未接管的模型候選平均仍比 deterministic 低，現在放寬只會增加壞輸出風險。

## 新報告欄位

- `model_surface_selection`: 每題保存 deterministic 分數、模型候選分數、margin、最後選擇來源。
- `model_selection_score_gap`: 最佳模型分數減 deterministic 分數；負數代表 deterministic 更適合保留。
