# 右腦角色專業化課程 V1

## 結論

課程建構與稽核通過。它只授權下一輪先登記公平的本機訓練對照實驗，尚未授權訓練、上線或宣稱人格更相似。

## 課程構造

| 項目 | 結果 |
|---|---:|
| 全新通用情境 | 20 |
| 現行聯合契約 payload | 40 |
| 訓練列 | 80 |
| 目標政策／中性政策 | 40 / 40 |
| 四種記憶模式 | 每種 20 筆 |
| 有／無程序指引 | 40 / 40 |

每個認知計畫都同時提供目標政策與中性政策，各有兩種不同說法。這些句子是訓練範例，
不是正式聊天時可以查表輸出的固定回覆。

## 品質門檻

| 檢查 | 結果 |
|---|---:|
| 現行聯合契約覆蓋 | 100.0% |
| 人格政策路徑覆蓋 | 100.0% |
| 人格政策值覆蓋 | 100.0% |
| 必要語意通過 | 100.0% |
| 記憶可說性通過 | 100.0% |
| 正式候選驗證器接受 | 100.0% |
| 禁用內容與長度通過 | 100.0% / 100.0% |
| 80 筆回答的正規化唯一數 | 80 |
| 同計畫兩種政策輸出不同 | 100.0% |

## 資料邊界

| 洩漏檢查 | 數量 |
|---|---:|
| exact_user_input_overlap_count | 0 |
| normalized_user_input_overlap_count | 0 |
| exact_payload_overlap_count | 0 |
| exact_target_overlap_count | 0 |
| normalized_target_overlap_count | 0 |
| target_identity_marker_count | 0 |
| target_utterance_count | 0 |
| benchmark_or_answer_key_field_count | 0 |
| runtime_fixed_reply_count | 0 |

教材範例由 Codex 協助合成；建構程式沒有讀取公開人物原始逐字稿，也沒有呼叫本機生成或訓練。人物原句不存在於專案證據庫，
因此本輪可證明的是來源治理、字串分離與建構程序，不把『沒有找到相同字串』誤稱為人格原創性的完整證明。

## 決策

- 結果：`authorize_matched_local_training_pilot_preregistration_only`
- 下一輪可做：先凍結同模型、同初始 adapter、同訓練預算與同評測的 matched pilot。
- 本輪不可做：直接訓練、切換正式模型、宣稱人格更像或正式上線。
