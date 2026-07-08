# RightBrain Contract Projection v1

## 目的

左腦內部計畫含有未授權或與公開核心意思衝突的欄位時，先投影成可對使用者說出的契約，再交給右腦。

## 控制變因

- 同一個 Qwen2.5-7B、同一個 v10 adapter、同一 seed、同一組三題、每題三候選。
- 唯一操作變因：舊版完整計畫直接輸入，或新版公開契約投影。

## 契約投影

| case | memory policy | mode | dropped units | dropped grounding |
|---|---|---|---:|---:|
| background_family_pressure | background_only | semantic_contract_only | 1 | 1 |
| private_do_not_mention | do_not_mention | full_plan | 0 | 0 |
| no_memory_plain_question | no_memory | semantic_contract_only | 2 | 1 |

## 實際模型結果

| condition | final contract pass | final memory intrusion | gate-accepted candidates |
|---|---:|---:|---:|
| legacy_unprojected | 3/3 (100.0%) | 0 | 3/9 |
| projected_contract | 3/3 (100.0%) | 0 | 7/9 |

## 非盲自然度審核

| condition | audit pass | audit fail |
|---|---:|---:|
| legacy_unprojected | 0 | 3 |
| projected_contract | 4 | 3 |

最終回答配對：projected win 1、legacy win 0、tie 2。

自動 final contract 指標只檢查最後送出的回答；候選本身是否自然，以本節逐句 audit 為準。

### 回答對照

- `background_family_pressure`
  - before: 今やるなら小さく済ませろ。後で戻せる形にしとけ。
  - after: 今日は負担を軽くして休もうね。
- `private_do_not_mention`
  - before: まあ、じゃあ軽い話題でいいだろ。最近どうしてたんだよ。
  - after: まあ、じゃあ軽い話題でいいだろ。最近どうしてたんだよ。
- `no_memory_plain_question`
  - before: 今やるなら小さく済ませろ。後で戻せる形にしとけ。
  - after: 今やるなら小さく済ませろ。後で戻せる形にしとけ。

## Gate

- target_contracts_respect_memory_policy: PASS
- projected_contract_does_not_reduce_contract_pass_count: PASS
- projected_contract_has_no_memory_intrusion: PASS
- naturalness_audit_matches_every_accepted_candidate: PASS
- projected_candidate_audit_pass_count_improves: PASS
- projected_final_pairwise_has_no_losses: PASS

## 證據邊界

這是三個已知矛盾契約的配對開發測試，不代表整體日文自然度或 ToMBench 分數已提升。
