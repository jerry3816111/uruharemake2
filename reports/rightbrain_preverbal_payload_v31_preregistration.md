# 右腦 V31 預註冊：語言 × 訊息格式

## 為什麼做

V30 顯示 V10 與原始 Qwen 都有超過 75% 的必要語意遺失，單純開關 LoRA 不是已證明的答案。目前右腦收到的是「日文內容塞在英文標籤 JSON」；這可能造成額外的語言切換或格式負擔，但論文也指出語言與格式都沒有通用最佳解，所以必須實測。

## 2×2 單一因素拆解

| 條件 | 標籤語言 | 格式 | 其他內容 |
|---|---|---|---|
| mixed_json_control | 現行英文／代碼 | 現行 JSON | 固定 |
| japanese_json | 日文 | JSON | 固定 |
| mixed_lines | 現行英文／代碼 | 行式訊息 | 固定 |
| japanese_lines | 日文 | 行式訊息 | 固定 |

這樣可以分開回答：改善若存在，來自日文標籤、行式格式，還是兩者交互作用。四組都由同一份現行 JSON 轉換，不准增加答案範例、題目提示或新記憶。

## 固定條件

- Qwen2.5-7B-Instruct，同一 revision
- 同一個正式 V10 adapter
- V29 的 12 個情境、12 個不同 source family
- seed：20260712、20260713、20260714
- 每個 seed-case 產生 3 個候選
- system prompt、採樣、最大長度、嚴格 gate 全部不變
- repair 關閉

## 判斷方法

主單位是 36 個 `seed × case` 配對；每組三個候選只要至少一個通過現行 gate，該配對才算成功。候選層通過率只作描述，不當成 108 個互相獨立樣本。

若最佳表示法相對 control 至少增加 10 個百分點、每個 seed 都不退步、必要語意遺失至少下降 5 個百分點、硬失敗不明顯增加，且 Holm 校正後 McNemar `p ≤ 0.05`，才准進入全新來源分離 holdout。這輪不准直接改 runtime，也不要求人類盲測。

## 研究邊界

「前語言訊息」在此只是軟體上的操作名稱：左腦已決定的意思交給表達器，不代表這個實驗證明了人腦生物機制。

## 研究依據

- [English vs. Target-language Instructions for Multilingual LLMs](https://aclanthology.org/2025.naacl-short.55/)
- [Does Prompt Formatting Have Any Impact on LLM Performance?](https://arxiv.org/abs/2411.10541)
- [Qwen2.5 Technical Report](https://arxiv.org/abs/2412.15115)
