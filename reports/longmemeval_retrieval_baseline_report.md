# UruhaBrain × LongMemEval-S 官方記憶檢索基線

## 結論

目前 Uruha salience 會把部分正確 dense 結果往後排；下一步應在 development split 修正注意力因子。

## 實驗固定條件

- 官方 cleaned 資料：500 題，SHA `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
- 實際 retrieval 評分：470 題
- 依官方規則排除 abstention：30 題
- 三組使用同一題目、同一 session 文字與同一 top-k；只有選擇規則不同。
- 索引文字不含標準答案與 has_answer 標籤。

## 官方來源

- LongMemEval repository（固定 commit）：9e0b455f4ef0e2ab8f2e582289761153549043fc
- 官方資料：https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json
- 官方 retrieval 指標程式：https://github.com/xiaowu0162/LongMemEval/blob/9e0b455f4ef0e2ab8f2e582289761153549043fc/src/retrieval/eval_utils.py
- 論文：https://arxiv.org/abs/2410.10813

## 三組條件

| 條件 | 記憶選擇方式 |
|---|---|
| recent_session_order | 只取時間上最新的 session，不做語意檢索 |
| dense_chroma | 用相同 Chroma embedding 直接排序 |
| uruha_salience_rerank | 只把 Dense top-20 交給現行 Uruha attention/salience 重排 |

## 主要結果

| 條件 | recall all@5 | recall any@5 | nDCG@5 |
|---|---:|---:|---:|
| recent_session_order | 5.74% | 23.83% | 9.74% |
| dense_chroma | 76.81% | 92.55% | 81.07% |
| uruha_salience_rerank | 34.04% | 67.45% | 44.92% |

## 單一部件效果

`Uruha = dense top-20 + 現行 attention/salience 重排`

- Uruha 單獨答對：9 題
- Dense 單獨答對：210 題
- 淨差：-201 題（-42.77 pp）
- exact McNemar p-value：6.702e-51

## 預註冊 Split

| Split | Dense recall all@5 | Uruha recall all@5 | 差值 |
|---|---:|---:|---:|
| development | 69.47% | 27.37% | -42.11 pp |
| test | 78.67% | 35.73% | -42.93 pp |

## 各能力類型 recall all@5

| 類型 | dense | Uruha | 差值 |
|---|---:|---:|---:|
| knowledge-update | 77.78% | 27.78% | -50.00 pp |
| multi-session | 72.73% | 18.18% | -54.55 pp |
| single-session-assistant | 98.21% | 71.43% | -26.79 pp |
| single-session-preference | 86.67% | 23.33% | -63.33 pp |
| single-session-user | 78.12% | 65.62% | -12.50 pp |
| temporal-reasoning | 67.72% | 22.83% | -44.88 pp |

## 證據邊界

這只測英文、session-level 的 episodic retrieval，不是最終回答正確率，也不代表記憶鞏固、隱私、人格或完整聊天品質。索引文字沒有放入標準答案或 has_answer 標籤。

本報告不授權修改或升級 runtime；下一輪只能在 development split 分析與修改，完成後才可一次性檢查 test split。
