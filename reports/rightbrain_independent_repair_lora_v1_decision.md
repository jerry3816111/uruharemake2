# RightBrain Independent Repair LoRA v1 Decision

## 結論

獨立 repair adapter 的訓練流程已完成，但這版 `uruha_rightbrain_repair_lora_v1_base` 不上線。

## 這次和上一輪有什麼不同

- 上一輪 v12 是從 v8 surface adapter 繼續訓練，可能污染初次生成。
- 這一輪 v1 是從 base model 新建 LoRA，`init_adapter_ref=base_model_new_lora`。
- 初次生成仍固定使用 v8 surface adapter。
- repair 階段才切到獨立 repair adapter。

## 訓練結果

| 項目 | 數值 |
|---|---:|
| dataset | rightbrain_repair_curriculum_v1.json |
| rows | 720 |
| train/eval | 663 / 57 |
| epochs | 0.20 |
| optimizer updates | 17 |
| nonfinite loss skips | 0 |
| nonfinite gradient skips | 0 |
| initial eval loss | 3.4490 |
| sampled eval loss | 3.0309 |

## Holdout 結果

| seed | 條件 | raw acceptance | repair success | effective acceptance | final pass |
|---|---|---:|---:|---:|---:|
| 20260704 | v8 baseline | 40% | 0/6 | 40% | 100% |
| 20260704 | v8 + independent repair v1 | 40% | 0/6 | 40% | 100% |
| 20260707 | v8 baseline | 20% | 1/8 | 30% | 100% |
| 20260707 | v8 + independent repair v1 | 20% | 1/8 | 30% | 100% |

## 判斷

獨立 LoRA 沒有降低初次生成，這證明雙 adapter 隔離有效。但它也沒有提升 repair success。20260707 的 1 次修復成功不是新 adapter 造成，因為 baseline prompt-only repair 已經同樣成功。

## 上線決策

- 保留 `--init-adapter ""` 的訓練入口，因為它能做乾淨的獨立 LoRA 實驗。
- 不設定 `URUHA_RIGHT_BRAIN_REPAIR_ADAPTER_PATH`。
- 不開啟 `URUHA_RIGHT_BRAIN_MODEL_REPAIR_ENABLED`。
- 不把 `uruha_rightbrain_repair_lora_v1_base` 當正式 adapter。

## 下一步

下一輪不應再只增加相同格式的 SFT 步數。需要改 repair 資料格式或訓練目標，例如：

- 將 rejected draft 特徵壓縮成結構化錯誤槽位，但仍不直接暴露原文草稿。
- 增加「錯誤輸出類型 -> 修正策略 -> 合格輸出」的中間決策欄位。
- 將 repair 從直接生成改成 rerank / verifier-assisted selection，避免小模型重新生成時再次漏槽位。
