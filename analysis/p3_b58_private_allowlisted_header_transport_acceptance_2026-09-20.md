# P3-B58 private allowlisted-header transport acceptance

日期：2026-09-20

## 結論

`NEGATIVE / DIRECT-AUDIO-BRANCH REVIEW_REQUIRED`。B58 的 resolver 正常取得一個 private Googlevideo URL，並從
extractor request metadata 選出 3 個合規非敏感 header；但是 direct ffmpeg 仍在 0.079168 秒以 exit `8`、
`tls_or_network` 類別失敗，沒有產生 `3000..3180` observable-context artifact。

因此「B57 只是因為少傳一般 HTTP headers 才失敗」已被這次單一變因反證。因為 raw stderr 依事前 freeze 丟棄，
不能進一步斷言特定 HTTP status、特定 header、TLS implementation 或 provider policy 是根因。

## 事前邊界與驗收

- 使用者 2026-09-19～20 授權依既定計畫持續執行與使用 Codex token；不包含付費 API、登入、cookies／帳號資料、
  hidden future、改弱 baseline、降低 gate 或無限重試。
- source、`3000..3180` cutoff、yt-dlp/ffmpeg 版本、B54 publication gate 與 0 retry／fallback 均與 B57 相同。
- 新增能力只有 private header forwarding。允許 `User-Agent`、`Referer`、`Origin`、`Accept`、
  `Accept-Language`；Range 交由 ffmpeg 管理，其他非敏感 header 丟棄；Cookie、Authorization、
  Proxy-Authorization、Set-Cookie 直接拒絕。
- URL 與 header name/value/hash、resolver raw stdout/stderr、ffmpeg raw stderr 均不得落盤。
- 正式執行前 B54–B58 affected suite：`69 passed`。

## 唯一正式執行

| 階段 | 結果 |
|---|---:|
| yt-dlp resolver | exit `0`, `1.560216 s` |
| resolver stdout / stderr | `1403 / 0 bytes`，private parse 後丟棄 |
| URL contract | `1` URL、host category `googlevideo_cdn` |
| allowlisted private header | `3`，name/value/hash 不保存 |
| direct ffmpeg | exit `8`, `0.079168 s` |
| ffmpeg stdout / stderr | `0 / 1316 bytes`，分類後丟棄 |
| failure | stage `direct_ffmpeg`, category `tls_or_network` |
| private URL/header material persisted | `false` |
| private runtime deleted | `true` |
| public artifact / manifest | `0 / 0` |
| future / playback / semantics / prediction / model | `0 / 0 / 0 / 0 / 0` |
| paid API / login / account access | `0` |

保存結果：`analysis/p3_b58_private_allowlisted_header_transport_result_2026-09-20.json`；內部 result hash
`fc802f7777027ed92d68f18388bfb641008877da1c3da66414634188dcc1dda5`。

## 這個負結果實際縮小了什麼

1. 來源仍可由 yt-dlp 解析；不是 video ID 或 extractor 完全不可用。
2. direct ffmpeg 在 headerless（B57）與 allowlisted-header（B58）兩種條件都失敗。
3. 所以不能再把「一般 request header 沒轉交」當作主要可驗證解釋，也不應繼續添加 header 或重跑相同路徑。
4. audio transport 尚未成功，真實 context、真實預測與 future scoring 仍都是 `0`；本結果不是模型能力證據。

## 接續決策

B57、B58 已是 direct-audio transport 的兩個前瞻修正批次，依開發流程停止這個分支，不再以不同小參數反覆重試。
下一個必要且可歸因的工作改為 **B59 source-semantic availability probe**：同一公開來源只解析字幕／自動字幕的
track availability，不下載、保存或閱讀 transcript 內容，也不取得 hidden-future outcome。若存在可用日文 track，才另行
事前凍結「private raw caption → cutoff 前 context-only artifact → 刪除 raw」的能力分離方案；若不存在，明確把本來源標成
需要使用者提供合法本機媒體或更換預先凍結來源，不再猜 transport。

B59 只能回答資料路徑是否存在，不能被稱為 prediction、training、UruhaBrain 優勢或人類方程式證據。
