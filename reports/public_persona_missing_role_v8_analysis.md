# 公開人格 Missing Role V8 結果

- 決策：`freeze_negative_result_and_reassess_role_coverage_or_token_semantics_only`
- 角色投影案例：persona_v3_notice_01

| 條件 | 原核心語意 | V4 人格 | 表面 gate | 具體性 | 中位延遲 |
|---|---:|---:|---:|---:|---:|
| c0_existing_speech_plan | 18/20 | 12/15 | 14/20 | 11/12 | 3.522s |
| t1_missing_role_tokens | 18/20 | 12/15 | 14/20 | 11/12 | 3.448s |

## 配對差異

- 新增人格通過：0
- 人格退步：0
- 原核心語意退步：0
- 表面 gate 退步：0
- 具體資訊侵入退步：0
- 未修改案例相同回覆：19/19

## 證據邊界

V8 uses known synthetic development cases and evaluates only whether minimal missing-role token projection avoids V7 prompt-load regressions. A pass cannot establish unseen-context generalization, public-persona fidelity, human preference, or runtime readiness.
