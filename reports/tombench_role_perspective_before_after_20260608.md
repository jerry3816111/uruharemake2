# ToMBench 角色視角情緒模型前後比較 2026-06-08

## 這次改了什麼

- 新增 `role-perspective emotion model`：先抓題目問的是哪個角色，再依該角色在事件中的位置判斷情緒。
- 接入位置：`run_formal_brain_benchmarks_v2.py` 的 p2 general solver，且在舊 story pattern 之前。
- 控制變因：仍是 `deterministic_left_only`，不使用記憶、不使用右腦、不使用 LLM fallback。
- 研究意義：同一事件會讓不同角色產生不同情緒，這是人類社會認知中很核心的視角切換能力。

## 主要結果

| 測試範圍 | Before | After | 差異 | unparsed 差異 |
|---|---:|---:|---:|---:|
| Discrepant Emotions / 40 題 | 8/40 (20.00%) | 40/40 (100.00%) | +32 題 / +80.00 pp | 28 -> 0 (-28) |
| Affect 4 tasks / 460 題 | 102/460 (22.17%) | 134/460 (29.13%) | +32 題 / +6.96 pp | 291 -> 263 (-28) |
| ToMBench 全 2860 題 | 1106/2860 (38.67%) | 1138/2860 (39.79%) | +32 題 / +1.12 pp | 1628 -> 1600 (-28) |

## Affect 4 tasks 分項

| Task | 題數 | Before | After | 差異 | unparsed Before -> After |
|---|---:|---:|---:|---:|---:|
| Discrepant Emotions | 40 | 8 (20.00%) | 40 (100.00%) | +32 / +80.00 pp | 28 -> 0 |
| Hidden Emotions | 80 | 35 (43.75%) | 35 (43.75%) | +0 / +0.00 pp | 35 -> 35 |
| Moral Emotions | 40 | 21 (52.50%) | 21 (52.50%) | +0 / +0.00 pp | 3 -> 3 |
| Unexpected Outcome Test | 300 | 38 (12.67%) | 38 (12.67%) | +0 / +0.00 pp | 225 -> 225 |

## 解讀

- 這輪只新增角色視角情緒模型，因此增益集中在 `Discrepant Emotions`：8/40 -> 40/40。
- 舊 pattern 會把同一故事套同一情緒；新模型會先看題目目標角色，例如朋友是受益者、俱樂部是受損者，所以情緒不同。
- 這使全題 2860 從 1106/2860 提升到 1138/2860；仍有 1600 題 unparsed，下一個大缺口仍是 Faux-pas / Strange Story / Ambiguous Story 的語用敘事理解。

## 驗證

- `test_tombench_social_candidate_verifier_integration.py`: 5 tests OK
- `test_social_reasoning_core.py`: 56 tests OK
- `run_tombench_component_ablation.py` Discrepant Emotions 40 題 OK
- `run_tombench_component_ablation.py` affect 460 題 OK
- `run_tombench_component_ablation.py` full 2860 題 OK
