# RightBrain Selector Runtime Soak v1

## 一句話結論

360 組候選已完整通過 production RightBrain shadow path；主要泛化結論只採用 54 組 contract-held-out test。

## Split 結果

| split | cases | rejected candidates | runtime detected | learned gold | invalid selected | output unchanged |
|---|---:|---:|---:|---:|---:|---:|
| train | 252 | 2112 | 100.0% | 94.0% | 0.0% | 100.0% |
| validation | 54 | 449 | 100.0% | 98.1% | 0.0% | 100.0% |
| test | 54 | 454 | 100.0% | 100.0% | 0.0% | 100.0% |

## Held-out Test Gate

| 條件 | 結果 |
|---|---|
| full_case_count_is_360 | PASS |
| test_case_count_is_54 | PASS |
| contract_fingerprint_overlap_is_zero | PASS |
| test_runtime_detects_all_surface_rejected_candidates | PASS |
| test_shadow_active_rate_is_100pct | PASS |
| test_learned_gold_selection_rate_is_100pct | PASS |
| test_learned_strict_valid_rate_is_100pct | PASS |
| test_learned_never_selects_gate_rejected_candidate | PASS |
| test_visible_output_unchanged_rate_is_100pct | PASS |
| no_held_out_test_runtime_failures | PASS |

## 研究邊界

- 360 題用來做 runtime soak；其中 train/validation 只供診斷。
- 泛化 gate 只看 54 題未跨 contract fingerprint 的 test split。
- 這證明 runtime 接線與污染拒絕穩定，不證明自然度，也不計入 live 100/20 門檻。
