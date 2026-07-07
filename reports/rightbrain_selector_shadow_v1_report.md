# RightBrain Selector Shadow v1

## 一句話結論

學習式 selector 已接入 F 右腦的 observe-only shadow path；它會評分真實候選並留下 trace，但不改變使用者收到的回答。

## Runtime 重播結果

| 指標 | 結果 | 意義 |
|---|---:|---|
| cases | 11 | 先前真實模型生成案例 |
| candidates | 21 | deterministic、接受與拒絕候選總數 |
| real rejected candidates | 5 | strict gate 當時拒絕的真實輸出 |
| learned strict-valid | 100.0% | learner 選到不違反合約候選的比例 |
| selected rejected candidate | 0.0% | learner 誤選已拒絕候選；越低越好 |
| agreement with current | 81.8% | learner 與現行選擇相同的比例 |
| would change | 18.2% | 只記錄差異，不實際切換 |
| visible output unchanged | 100.0% | shadow 不得改變正式回答 |

## Gate

| 條件 | 結果 |
|---|---|
| all_cases_shadow_active | PASS |
| learned_selection_strict_valid_rate_is_100pct | PASS |
| learned_never_selects_gate_rejected_candidate | PASS |
| shadow_never_changes_user_visible_output | PASS |
| contains_real_rejected_candidates | PASS |

## 差異案例

| case | current source | learned source | valid | would change |
|---|---|---|---|---|
| reference_fragment_probe | model | deterministic | True | True |
| daily_state_answer | deterministic | accepted:initial | True | True |

## 邊界

- 本輪證明 runtime 接線與安全隔離，不證明 learner 比現行回答更自然。
- 真實 web chat 的 `logic.model_surface_selector_shadow` 會自動寫入 JSONL 日誌。
- 必須累積 live disagreement 並做偏好比較後，才可討論正式接管。
