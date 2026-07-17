# 記憶鞏固來源保留實驗 V1

**資料門檻判定：KEEP**

本實驗只改變原始 `turn_episode` 在鞏固後的處理與來源欄位。模型、Prompt、temperature、檢索排序與測試輸入保持不變。

| 指標 | 修改前 | 修改後 |
|---|---:|---:|
| 原始經歷保留 | 0/20 | 20/20 |
| 具有完整來源 ID 的衍生記憶 | 0/3 | 3/3 |
| 被實體刪除的原始經歷 | 20 | 0 |
| 第二次執行是否重複產生記憶 | 否 | 否 |

## 門檢結果

| 門檢 | 預期 | 實測 | 結果 |
|---|---|---|---|
| `source_episode_count_before_exact` | `20` | `20` | 通過 |
| `source_episode_count_after_exact` | `20` | `20` | 通過 |
| `source_episode_retention_rate_exact` | `1.0` | `1.0` | 通過 |
| `source_episode_ids_unchanged` | `True` | `True` | 通過 |
| `source_episode_documents_unchanged` | `True` | `True` | 通過 |
| `source_consolidation_state_exact` | `consolidated` | `consolidated` | 通過 |
| `source_consolidation_batch_count_exact` | `1` | `1` | 通過 |
| `derived_record_count_after_first_exact` | `3` | `3` | 通過 |
| `derived_records_with_exact_source_ids_exact` | `3` | `3` | 通過 |
| `derived_records_with_source_digest_exact` | `3` | `3` | 通過 |
| `derived_records_with_batch_id_exact` | `3` | `3` | 通過 |
| `deleted_episode_count_exact` | `0` | `0` | 通過 |
| `preserved_episode_count_exact` | `20` | `20` | 通過 |
| `marked_consolidated_count_exact` | `20` | `20` | 通過 |
| `stub_model_calls_after_first_exact` | `1` | `1` | 通過 |
| `stub_model_calls_after_second_exact` | `1` | `1` | 通過 |
| `second_mode_exact` | `decay_only` | `decay_only` | 通過 |
| `second_pass_created_no_duplicate_derived_records` | `True` | `True` | 通過 |

## 證據邊界

這次結果只證明來源保留、可追溯、無重複鞏固，以及失敗後可重試。它不證明摘要內容正確、檢索改善、對話改善、像人類，也不代表原始經歷應永久保存。
