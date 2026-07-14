# 右腦 V30：V10 LoRA 對原始 Qwen 7B 的單一變因實驗

## 實驗問題

相同 Qwen2.5-7B、12 個情境、三個 seed、payload、採樣與 gate；唯一差別是 V10 LoRA 開或關。

舊 V10 報告因 gate 版本不同已排除；本表只使用 V30 runner 在現行 gate 下重新產生的兩組結果。

## 總結果

| 指標 | V10 LoRA | Base-only |
|---|---:|---:|
| 每組至少一個合格候選 | 27.8% | 36.1% |
| raw 候選通過率 | 12.0% | 14.8% |
| 語言/格式硬失敗率 | 51.9% | 42.6% |
| 必要語意遺失率 | 78.7% | 75.9% |
| 敬語/客服語域漂移率 | 9.3% | 15.7% |

## 配對差異

- Base-only 勝：7 組
- V10 勝：4 組
- Base-only 相對 V10 覆蓋率差：8.3% 個百分點
- McNemar exact p：0.5488
- 95% case-cluster bootstrap：[-13.9%, 30.6%]

## 預註冊門檻

- all_hash_and_shape_checks_pass: False
- base_strict_case_coverage_delta_at_least_10pp: False
- base_strict_case_coverage_not_lower_in_any_seed: True
- base_hard_surface_failure_rate_not_higher: True
- base_semantic_omission_rate_increase_at_most_2pp: True

## 決定

**keep_v10_no_runtime_change**

這次自動結果不會直接改 runtime。即使 Base-only 通過，也只能進入新的同政策人類盲評。

## 診斷

Base-only 在整體覆蓋率上小幅領先，但配對檢定不顯著且信賴區間跨過零；V10 較能壓住敬語漂移，卻有更高的語言/格式硬失敗。兩組都有超過七成的必要語意遺失，因此不能據此關閉 LoRA，也不能把增加 epoch 當成已被證明的答案。

- 注意：預註冊把類別數寫成 8，固定案例實際為 9；案例內容與 hash 未變，但此 metadata mismatch 仍保留為失敗檢查，不事後修稿。
- 下一個研究動作：先比較日文精簡的前語言訊息與現行混合語言 JSON payload，再決定是否需要重新訓練；不直接增加 epoch。

## 自動 gate 的限制

通過 gate 仍不等於自然日文。例如 V10 仍出現「オム梨ス」與「食べた気持ちいいな」，Base-only 也有殘缺文法。這些是非盲、事後診斷，不回改正式分數，只證明目前自動通過率仍是上限估計，不能冒充真人自然度。

## 證據邊界

This diagnostic matched ablation can retain V10 or authorize a new human blind review. It cannot establish human likeness, justify benchmark claims, or promote base-only runtime.
