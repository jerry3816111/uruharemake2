# ToMBench 情緒評估層前後比較 2026-06-08

## 這次改了什麼

- 新增 `affective appraisal`：根據角色的期待、受害/受益、責任、惡意沉默、表面偽裝來判斷情緒或原因。
- 接入位置：`run_formal_brain_benchmarks_v2.py` 的 p2 general solver，放在既有精確規則之後。
- 控制變因：仍是 `deterministic_left_only`，不使用記憶、不使用右腦、不使用 LLM fallback。
- 研究意義：這補的是人類式「情緒評估」子能力，不是讓模型背題。

## 主要結果

| 測試範圍 | Before | After | 差異 | unparsed 差異 |
|---|---:|---:|---:|---:|
| Affect 4 tasks / 460 題 | 20/460 (4.35%) | 102/460 (22.17%) | +82 題 / +17.82 pp | 431 -> 291 (-140) |
| ToMBench 全 2860 題 | 1024/2860 (35.80%) | 1106/2860 (38.67%) | +82 題 / +2.87 pp | 1768 -> 1628 (-140) |

## Affect 4 tasks 分項

| Task | 題數 | Before | After | 差異 | unparsed Before -> After |
|---|---:|---:|---:|---:|---:|
| Discrepant Emotions | 40 | 8 (20.00%) | 8 (20.00%) | +0 / +0.00 pp | 28 -> 28 |
| Hidden Emotions | 80 | 3 (3.75%) | 35 (43.75%) | +32 / +40.00 pp | 74 -> 35 |
| Moral Emotions | 40 | 5 (12.50%) | 21 (52.50%) | +16 / +40.00 pp | 33 -> 3 |
| Unexpected Outcome Test | 300 | 4 (1.33%) | 38 (12.67%) | +34 / +11.34 pp | 296 -> 225 |

## 解讀

- 最大增益來自 `Hidden Emotions` 與 `Moral Emotions`，表示系統能更好區分真實情緒、表面情緒、無意造成傷害後的內疚，以及惡意沉默後的自利滿足。
- `Unexpected Outcome Test` 仍偏弱，但已從 4/300 提升到 38/300；原因是目前只處理明顯期待落差，還沒建立完整的反常情緒因果模型。
- `Discrepant Emotions` 幾乎未改善，因為我刻意沒有用 40 題小集合做逐題補洞；下一步若要做，應抽象成 role-perspective emotion model，而不是列題目規則。

## 驗證

- `test_tombench_social_candidate_verifier_integration.py`: 4 tests OK
- `test_social_reasoning_core.py`: 56 tests OK
- `run_tombench_component_ablation.py` affect 460 題 OK
- `run_tombench_component_ablation.py` full 2860 題 OK
