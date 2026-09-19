# P3-B59 source-semantic availability probe acceptance

日期：2026-09-20

## 結論

`PASS / CAPTION PATH AVAILABLE`。同一 frozen public source 沒有可選日文人工字幕，但有日文自動字幕，且提供優先格式
`json3`。因此 B57–B58 的 direct-audio transport 關閉後，仍存在可做 capability separation 的語意資料路徑。

這一步只探測 track metadata；沒有下載、閱讀或保存字幕文字，也沒有取得 hidden-future outcome。

## 執行證據

| 項目 | 結果 |
|---|---:|
| 事前 B54–B59 affected suite | `87 passed` |
| yt-dlp resolver | exit `0`, `1.598962 s` |
| private stdout / stderr | `508363 / 0 bytes`，投影後丟棄 |
| manual language-code count | `1` |
| automatic language-code count | `157` |
| 日文人工字幕 | `false` |
| 日文自動字幕 | `true` |
| frozen selection | `automatic / ja / json3` |
| caption content download | `0` |
| raw metadata / track URL persisted | `false / false` |
| future / semantics / prediction / model / training | `0 / 0 / 0 / 0 / 0` |
| paid API / login / cookies | `0` |

保存結果：`analysis/p3_b59_source_semantic_availability_probe_result_2026-09-20.json`；result hash
`8972b5cde89361709b075a90accd20d865e671f32ef2cddc934d1b14b28a74cf`。

## 下一個必要交付

B60 才能新增內容取得，而且必須先凍結兩個程序的能力界線：

1. private acquisition/extraction worker 可取得 raw `automatic/ja/json3`，但 URL、raw metadata、完整 caption 與 cutoff 後文字
   不得落盤或傳給 prediction side；只輸出 `3000 <= cue_start` 且 `cue_end <= 3180` 的 context artifact。
2. fresh public reader 在 private material 清除後，只能讀 context artifact與manifest，逐 cue 驗證時間上界、hash、排序與禁止欄位。

此資料準備程序可能在 private acquisition memory 中短暫接觸完整 caption，這是 curator/extractor side，不是 prediction side；
必須把 `acquisition raw access` 與 `prediction future access=0` 分開記錄，不能寫成整個程序完全沒碰過 future。B60 成功也只代表真實
pre-cutoff context 已取得，尚未凍結預測、解鎖 outcome、評分或證明系統優勢。
