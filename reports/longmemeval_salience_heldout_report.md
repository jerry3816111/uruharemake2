# LongMemEval 記憶注意力一次性 Held-out 結果

## 實驗邊界

- 開發集：95 題（用來選規則）
- 測試集：375 題（只觀察一次）
- 三組使用同一 Dense top-20 候選；v2 只改候選的注意力排序。
- 候選快取不含官方答案；評分時才從固定官方資料讀取 gold session。

## 總結果

| 組別 | recall_all@5 | nDCG@5 | recall all@20 |
|---|---:|---:|---:|
| dense_chroma | 78.67% | 81.85% | 96.80% |
| legacy_wall_clock | 35.73% | 45.50% | 96.80% |
| runtime_v2 | 84.27% | 85.12% | 96.80% |

## 配對差異

| 比較 | 淨增答對題 | 差異 | McNemar p |
|---|---:|---:|---:|
| runtime_v2_vs_dense_chroma | +21 | +5.60 pp | 0.000192195 |
| runtime_v2_vs_legacy_wall_clock | +182 | +48.53 pp | 5.64644e-51 |

## 各任務相對 Dense

| 任務 | 題數 | v2 差異 |
|---|---:|---:|
| knowledge-update | 54 | +7.41 pp |
| multi-session | 92 | +5.43 pp |
| single-session-assistant | 45 | +0.00 pp |
| single-session-preference | 24 | +0.00 pp |
| single-session-user | 53 | +16.98 pp |
| temporal-reasoning | 107 | +2.80 pp |

## 決定

一次性 held-out 門檻全部通過，可將凍結的 v2 注意力規則接入正式 runtime。

| 預先設定門檻 | 結果 |
|---|---:|
| development_authorized_test | 通過 |
| heldout_count_exact | 通過 |
| runtime_beats_dense | 通過 |
| runtime_beats_legacy_by_preregistered_margin | 通過 |
| candidate_pool_preserved | 通過 |
| recall_all_at_20_preserved | 通過 |
| no_task_drop_beyond_margin | 通過 |
