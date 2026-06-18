# ToMBench 前後比較 2026-06-08

## 這次改了什麼

- 改動位置：`run_formal_brain_benchmarks_v2.py` 的 p2 general solver。
- 改動內容：左腦 process trace 仍然不直接產生答案；只有當 candidate verifier 對 A/B/C/D 有 high confidence 時，才把最高分選項當作答案。
- 研究意義：這是在補「左腦已經做出人物意圖/語用推理，但沒有完成候選回答選擇」的管線缺口，不是把題目答案寫進規則。

## 主要結果

| 測試範圍 | Before | After | 差異 | unparsed 差異 |
|---|---:|---:|---:|---:|
| Social 5 tasks / 1310 題 | 21/1310 (1.60%) | 235/1310 (17.94%) | +214 題 / +16.34 pp | 1289 -> 1020 (-269) |
| ToMBench 全 2860 題 | 810/2860 (28.32%) | 1024/2860 (35.80%) | +214 題 / +7.48 pp | 2037 -> 1768 (-269) |

## Social 5 tasks 分項

| Task | 題數 | Before | After | 差異 | unparsed Before -> After |
|---|---:|---:|---:|---:|---:|
| Discrepant Intentions | 40 | 0 (0.00%) | 18 (45.00%) | +18 / +45.00 pp | 40 -> 22 |
| Faux-pas Recognition Test | 560 | 4 (0.71%) | 80 (14.29%) | +76 / +13.58 pp | 556 -> 451 |
| Hinting Task Test | 103 | 2 (1.94%) | 13 (12.62%) | +11 / +10.68 pp | 101 -> 90 |
| Scalar Implicature Test | 200 | 12 (6.00%) | 72 (36.00%) | +60 / +30.00 pp | 188 -> 111 |
| Strange Story Task | 407 | 3 (0.74%) | 52 (12.78%) | +49 / +12.04 pp | 404 -> 346 |

## 解讀

- 這次提升不是來自記憶系統；ToMBench ablation 條件中記憶仍關閉。
- 最大改善來自原本 unparsed 的 social-pragmatic 題可以被 high-confidence verifier 轉成選項。
- 仍有 1768/2860 題未解析，代表左腦 social reasoning coverage 還不夠；下一輪應針對 Strange Story、Faux-pas、Unexpected Outcome 的低覆蓋做更通用的語用/情緒/行動後果模型，而不是增加題目小抄。

## 驗證

- `test_tombench_social_candidate_verifier_integration.py`: 1 test OK
- `test_social_reasoning_core.py`: 56 tests OK
- `run_tombench_component_ablation.py --task-set social --full`: 1310 題 OK
- `run_tombench_component_ablation.py --task-set all --full`: 2860 題 OK
