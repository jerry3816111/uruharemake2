# P3-B56 allowlisted diagnostic transport acceptance

日期：2026-09-19

## 結論

`NEGATIVE / REVIEW_REQUIRED`。B56 成功地把 B55 的泛稱 `network_transport` failure 收斂為
`ffmpeg_or_postprocessing`，但沒有產生真實 observable-context artifact。因此 B54 的合成 isolation 仍有效，
真實來源 gate 仍未通過，不能開始語意解讀、prediction 或 hidden-future verification。

## 事前固定與分類器證據

- 使用者 2026-09-19「請繼續」被記為採用 B55 review 建議1的一次性授權；不授權 cookies、登入、換來源、改 cutoff 或 future。
- 正式請求前凍結 9 個 allowlisted 類別、優先序、0 retry/fallback、相同 B55 V2 命令及 B54 success gate。
- 7 個分類 fixture 全通過；freeze 前找到並修正 1 個歧義：`Requested format is not available` 不再被錯分成 source unavailable。
- fixture 中的 private `secret-canary` 從未進入 category/result；raw stderr text、hash、excerpt/token 均禁止。
- B54–B56 freeze 前離線 suite：`41 passed`。

## 唯一正式診斷請求

| 欄位 | 結果 |
|---|---:|
| source / interval | `youtube_4y5GiQpgJgo` / `3000..3180` |
| network attempts | `1` |
| network elapsed | `2.944204 s` |
| yt-dlp / ffmpeg | `2026.02.04` / `8.0.1` |
| return code | `1` |
| allowlisted category | `ffmpeg_or_postprocessing` |
| stdout / stderr bytes discarded | `0 / 35` |
| stderr text/hash/excerpt persisted | `false / false / false` |
| private runtime deleted before receipt | `true` |
| public artifact / manifest | `0 / 0` |
| future / playback / semantic inspection / prediction / model | `0 / 0 / 0 / 0 / 0` |

保存結果：`analysis/p3_b56_allowlisted_diagnostic_transport_result_2026-09-19.json`，result hash
`63cd7ea589999cb654665823b0e4215bef148775798b88966f4d0813c240998c`。

## 不增加網路請求的排除結果

- Homebrew yt-dlp 自己的 `FFmpegPostProcessor` 回報 available，找到 `ffmpeg`、`ffprobe`，版本均為 `8.0.1`。
- 直接執行 ffmpeg 8.0.1 對 1 秒合成音做 mono 16 kHz PCM pipeline，exit `0`。
- 因此可排除「ffmpeg 未安裝／yt-dlp 完全找不到 ffmpeg」；但不能從 category 與 35-byte count 判定是
  segment input、cut/re-encode、container、provider media URL 或其他 postprocessing 子原因。
- 系統 Python 不能 import Homebrew yt-dlp module；以 yt-dlp 自己的 embedded Python 做上述 discovery，未發網路請求。

## 下一個必要設計審查

若要繼續同一來源，最小可歸因變因是把 transport 拆成兩個 private 階段：

1. yt-dlp 只解析並在記憶中輸出一個 `bestaudio` media URL；URL／stderr／metadata 絕不落盤或進 receipt。
2. 直接以已驗證的 ffmpeg 對該 URL 裁 `3000..3180`，再交給原 B54 duration/hash/public-reader gate。

這會新增一次 provider request、暴露短暫 signed media URL 給 private worker，且仍不能保證 provider network byte-range
精確等於 180 秒，所以是新的 capability design，不能由 B56 授權自動外推。替代方案仍是使用者提供本機媒體、重選來源，
或使用登入/cookies；後兩者分別帶來 selection bias 與隱私／重現性成本。

## 證據邊界

B56 只證明：分類器沒有洩漏 raw error、一次真實請求 fail-closed，且錯誤位於 ffmpeg/postprocessing 類別。
它不證明已取得真實 context、不證明模型理解或預測，也不是正式 M56 或系統優勢證據。
