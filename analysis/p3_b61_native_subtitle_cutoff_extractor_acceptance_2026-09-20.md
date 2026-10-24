# P3-B61 native subtitle cutoff extractor acceptance

日期：2026-09-20

## 結論

`PASS / REAL PRE-CUTOFF CONTEXT AVAILABLE`。B61 使用 yt-dlp 原生 automatic-subtitle downloader 取得同一 frozen
`automatic / ja / json3`，再用未改動的 B60 cutoff projector 只發布 `3000..3180` 內 cue。這是目前第一個真實公開
YouTube holdout context artifact；先前 B54 只有合成隔離證據，B55–B60 都沒有真實 context。

## 執行證據

| 項目 | 結果 |
|---|---:|
| 事前 B54–B61 affected suite | `114 passed` |
| yt-dlp native downloader | exit `0`, `1.888588 s` |
| private full-caption bytes | `1,483,058`，投影後刪除 |
| public context cue count | `65` |
| first / last public cue | `3002.760 / 3176.079 s` |
| public artifact SHA-256 | `7a690e386e0945785f0dbe8d5573a2eda6f7ed6be64c28e01ee9e4cbbd5d0537` |
| fresh reader | exit `0`、hash一致、caption text returned `false` |
| private caption / runtime deleted before reader | `true / true` |
| raw / filename / hash / post-cutoff content persisted | 全部 `false` |
| prediction-side future access | `0` |
| human display / semantics / prediction / model / training | 全部 `0` |

保存結果：`analysis/p3_b61_native_subtitle_cutoff_extractor_result_2026-09-20.json`；result hash
`733d2be240bfc4b3b07a434da4373610deba65347306c167b6deac213c6fa5bc`。公開 artifact 位於 gitignored
`external_data/p3_b61_public_caption_context/`，不把字幕內容提交到 Git 或在驗收報告顯示。

## 科學邊界

private curator 在取得完整 caption 時可能短暫看見 cutoff 後資料；這被明確記成 acquisition-side raw access，不是假裝為 0。
真正要接受公平評測的 prediction side 只可讀 hash-bound public artifact，future access 仍為 0。

B61 只完成「真實過去輸入」；尚未做 prediction、baseline/system comparison、future outcome unlock 或 scoring。下一步 B62
必須先把同一輸入、候選輸出契約、模型／資源與兩條 condition 凍結，執行並封存 prediction 後，才可由另一程序解鎖
`3181..3241` outcome。
