# RightBrain Actual-Model Shadow Soak v1

## 一句話結論

本輪直接使用 Qwen2.5-7B + v10 adapter 生成多候選，並在 observe-only shadow 中比較 current 與 learned selector。

## 執行條件

- base model: `Qwen/Qwen2.5-7B-Instruct`
- adapter: `uruha_v10_all_linear_lora`
- seed: `20260707`
- candidates per eligible case: `3`
- model load seconds: `26.606`
- generation/eval seconds: `266.147`

## 結果

| 指標 | 結果 |
|---|---:|
| cases | 11 |
| real generated candidates | 30 |
| raw candidate acceptance | 20.0% |
| active shadow cases | 11 |
| multi-candidate shadow cases | 10 |
| current surface-contract pass | 100.0% |
| learned strict-valid | 100.0% |
| learned surface-contract pass | 100.0% |
| learned selected gate-rejected | 0.0% |
| shadow disagreements | 3 (27.3%) |
| visible output unchanged | 100.0% |
| generated `无` / accepted | 1 / 0 |
| generated `�` / accepted | 1 / 0 |

## Gate

| 條件 | 結果 |
|---|---|
| model_loaded | PASS |
| generated_at_least_20_real_candidates | PASS |
| shadow_active_on_at_least_10_cases | PASS |
| contains_real_rejected_candidates | PASS |
| learned_strict_valid_rate_is_100pct | PASS |
| learned_surface_contract_pass_rate_is_100pct | PASS |
| learned_never_selects_gate_rejected_candidate | PASS |
| shadow_never_changes_visible_output | PASS |
| actual_simplified_wu_candidate_was_generated | PASS |
| actual_simplified_wu_candidate_was_never_accepted | PASS |
| actual_unicode_replacement_candidate_was_generated | PASS |
| actual_unicode_replacement_candidate_was_never_accepted | PASS |

## 真實污染修正證據

| case | raw model candidate | rejection | current final reply |
|---|---|---|---|
| private_do_not_mention | 今日も体調は大丈夫？无理しないでおくれ。 | nonstandard_cjk_surface | 今は一個だけ決めればいい。全部まとめて抱えるなって。 |
| no_memory_plain_question | 分かりやすい範�士最近の自分の体調も考えた上で、無理なく進めていこうね。 | unicode_replacement_character, semantic_slots_missing:0/1 | 迷うなら軽い方からでいい。後で足せる形にしとけ。 |

## 個案

| case | generated | accepted | current source | learned source | valid | surface contract | change |
|---|---:|---:|---|---|---|---|---|
| explicit_stomach_coffee | 3 | 0 | deterministic | deterministic | True | True | False |
| explicit_spicy_food_update | 3 | 0 | deterministic | deterministic | True | True | False |
| background_family_pressure | 3 | 1 | deterministic | deterministic | True | True | False |
| private_do_not_mention | 3 | 1 | deterministic | accepted:initial | True | True | True |
| no_memory_plain_question | 3 | 0 | deterministic | deterministic | True | True | False |
| support_tired_no_closing_template | 3 | 1 | deterministic | deterministic | True | True | False |
| support_read_receipt_self_blame | 3 | 0 | deterministic | deterministic | True | True | False |
| reference_fragment_probe | 3 | 1 | model | deterministic | True | True | True |
| absurdity_mirror_quantum_police | 3 | 1 | model | deterministic | True | True | True |
| boundary_dirty_language | 0 | 0 | deterministic | deterministic | True | True | False |
| daily_state_answer | 3 | 1 | deterministic | deterministic | True | True | False |

## 研究邊界

- 候選由真實 7B+v10 adapter 生成，不是人工污染字串。
- 只有 11 個固定案例，仍不能取代 live 對話與偏好比較。
- surface-contract pass 只檢查語言、必要槽位與禁止項，不代表語意相關性或自然度勝出。
- learner 仍是 observe-only；報告中的 change 只是反事實記錄。
