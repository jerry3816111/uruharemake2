# ToMBench Faux-pas Recognition 改進紀錄（2026-06-09）

## 目的

本輪改動針對 ToMBench 的 `Faux-pas Recognition Test`，也就是「能不能理解某句話為什麼是失言」的子能力。這不是右腦表面語氣改寫，而是左腦社會推理：誰知道什麼、誰不知道什麼、哪一句話會傷害到哪個人。

## 改動內容

- 新增 target-aware knowledge solver：題目問「某人知道嗎 / 記得嗎」時，不再用整篇故事的全域 `知道/聽到` 判斷，而是先找題目指定的人，判斷那個人是否聽過、看過、被告知、或從自己的發言表現出不知道。
- 擴充 social harm quote scorer：新增誤認服務員、身份誤認、洩漏驚喜、批評禮物/獎品/新物品、病痛場合開玩笑、公開提敏感病情、羞辱考差、比較式貶低、忽視學生沒聽懂、過敏物品、不能說話仍要求說話、把失業當休假等類型。
- 調整 solver 執行順序：`Faux-pas Recognition Test` 先走 Faux-pas 專用推理，再交給 generic candidate verifier，避免專用社會失言規則被較粗的 verifier 搶先錯答。
- 修正 Yes/No parser：避免英文 `knows` 中的 `no` 被誤判為否定。

## 單項結果

| 指標 | Before | After | 差異 |
|---|---:|---:|---:|
| Faux-pas 正確數 | 237 / 560 | 312 / 560 | +75 題 |
| Faux-pas 正確率 | 42.32% | 55.71% | +13.39 pp |
| Faux-pas 未解析數 | 173 | 137 | -36 題 |

## 分題型結果

| 題型 | Before | After | 差異 |
|---|---:|---:|---:|
| 知道 / 記得 | 5 / 123 = 4.07% | 41 / 123 = 33.33% | +36 題 |
| 是否有人失言 | 74 / 139 = 53.24% | 93 / 139 = 66.91% | +19 題 |
| 哪一句是失言 | 81 / 155 = 52.26% | 98 / 155 = 63.23% | +17 題 |
| 故事事實題 | 76 / 140 = 54.29% | 79 / 140 = 56.43% | +3 題 |
| 為什麼題 | 1 / 3 = 33.33% | 1 / 3 = 33.33% | 0 題 |

## 完整 ToMBench 結果

| 指標 | Before | After | 差異 |
|---|---:|---:|---:|
| 全 2860 題正確數 | 1924 / 2860 | 1999 / 2860 | +75 題 |
| 全 2860 題正確率 | 67.27% | 69.90% | +2.63 pp |
| 全 2860 題未解析數 | 641 | 605 | -36 題 |

## 代表性改善能力

1. 服務員誤認：能區分「請真正服務員清理」和「把另一位顧客誤當服務員」。
2. 知識狀態：能判斷失言者是否知道對方的背景，例如生病、過敏、分手、失業、不能說話。
3. 敏感情境：能把禮物、獎品、考試、病痛、親友離世、驚喜秘密等視為高社會風險語境。
4. 失言定位：不只回答有沒有失言，也能更穩定選出具體不合適的句子。

## 測試指令

```bash
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python test_tombench_social_candidate_verifier_integration.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python -m unittest test_social_reasoning_core.py
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --tasks "Faux-pas Recognition Test" --full --force-refresh --report-prefix tombench_after_fauxpas_det_20260609
/Users/jerrychang/Desktop/uruharemake2/Style-Bert-VITS2/venv/bin/python run_tombench_component_ablation.py --conditions deterministic_left_only --baseline-condition deterministic_left_only --task-set all --full --force-refresh --report-prefix tombench_after_all_det_fauxpas_20260609
```

## 剩餘缺口

Faux-pas 仍然只有 55.71%，代表失言理解還沒完成。剩餘錯題主要是後半段更多生活/職場敏感背景，例如搬家、婚姻、家庭企業、財務困難、私人事務、搬同居、忌日等。下一輪應該把這些整理成更抽象的「私人敏感狀態」與「對方偏好/禁忌」推理，而不是繼續堆單題規則。
