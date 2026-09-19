# P3-B57 split resolver/direct-ffmpeg acceptance

日期：2026-09-19

## 結論

`NEGATIVE / REVIEW_REQUIRED`。B57 成功證明公開來源可以解析成一個私有 Googlevideo media URL，也證明 URL
未寫入 artifact；但 direct ffmpeg 無法從該 URL 取得媒體，故仍沒有 `3000..3180` observable-context artifact。
問題已從 B56 的「yt-dlp ffmpeg/postprocessing」縮小到「direct CDN transport 的 TLS/network 類別」。

## 事前邊界

- 使用者 2026-09-19 再次「請繼續」授權 B57，不外推成 hidden-future、training 或 prediction 授權。
- resolver 只允許一個 HTTPS `.googlevideo.com` URL；0 cookies、0 retry、0 file download、0 sidecar/subtitle/comment。
- URL text、hash、hostname、query keys、resolver stdout/stderr 均禁止落盤或進 receipt。
- direct ffmpeg 固定 `-ss 3000 -t 180`、mono 16 kHz PCM WAV；成功仍須通過 B54 duration/hash/public-reader gate。
- 正式執行前 B54–B57 affected suite：`52 passed`。

## 唯一正式執行

| 階段 | 結果 |
|---|---:|
| yt-dlp resolver | exit `0`, `1.927396 s` |
| resolver stdout / stderr | `1124 / 0 bytes`，只在 private memory 使用後丟棄 |
| URL contract | `1` URL、host category `googlevideo_cdn` |
| direct ffmpeg | exit `8`, `0.081831 s` |
| ffmpeg stdout / stderr | `0 / 1311 bytes`，分類後丟棄 |
| failure | stage `direct_ffmpeg`, category `tls_or_network` |
| signed URL text/hash/excerpt persisted | `false / false / false` |
| signed URL reference cleared | `true` |
| private runtime deleted | `true` |
| public artifact / manifest | `0 / 0` |
| future / playback / semantic inspection / prediction / model | `0 / 0 / 0 / 0 / 0` |

保存結果：`analysis/p3_b57_split_resolver_direct_ffmpeg_result_2026-09-19.json`，result hash
`012b5744ca7ad336fb72234fa8065af8e2e375bd4f1262c849762fc968754d94`。

## 可說與不可說的原因

可以說：resolver 成功，direct ffmpeg 的 CDN request 失敗；錯誤落在 TLS/network 類別，且不是來源 ID 解析失敗。

不能說：一定是 HTTP 403、User-Agent、Referer 或特定 header。B57 依 freeze 不保存 raw stderr；URL 單獨交給 ffmpeg
缺少 yt-dlp extractor 可能提供的 request headers 是合理下一假設，但尚未被驗證。

## YouTube 資料與未來預測的角色

整體設計仍是：

1. 較早、具 provenance 的公開影片可分成 train/dev，形成「情境與歷史狀態 → 後續反應分布」的候選模型。
2. 本支影片是 temporal holdout；`3000..3180` 只能作為測試輸入，不能加入訓練。
3. 成功取得過去片段後，先凍結預測，再獨立解鎖 `3181..3241` 真實未來核對。
4. 同模型 baseline 與 UruhaBrain 都只能取得相同過去資訊；比較命中率、校準、過度推測與成本。

目前完成的是第2步的防洩漏資料工程，尚未完成真實 context 取得，因此更沒有開始第3步。公開影片也不等於可任意
再發布或訓練；後續 train corpus 仍需逐筆保存來源、時間、授權/使用條款狀態與排除清單。

## 下一個必要設計審查

B58 建議只改一個變因：resolver 在 private memory 同時輸出 media URL 與 extractor 的必要 HTTP headers；僅允許
`User-Agent`、`Referer`、`Origin`、`Accept`、`Accept-Language`、`Range` 的明確 allowlist，禁止 Cookie／Authorization，
header name/value/hash均不落盤。direct ffmpeg 以 in-memory headers 重試一次，其他 source、cutoff、B54 gate 不變。

這仍會新增 resolver/ffmpeg invocation，且 provider HTTP request count 不可精確觀察，所以 B57 不自動授權 B58。
