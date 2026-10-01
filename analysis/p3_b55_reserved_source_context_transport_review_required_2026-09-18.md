# P3-B55 reserved-source observable-context transport — REVIEW_REQUIRED

日期：2026-09-18

## 結論

`REVIEW_REQUIRED`。B54 的合成 capability isolation 已通過，但 B55 沒有取得真實 `3000..3180` observable
context，因此不能進入語意解讀、prediction 或 hidden-future verification。兩個結果都保留，沒有以重跑覆蓋失敗。

## 兩次凍結執行的實際結果

| 版本 | 唯一改變 | network request | 結果 | public artifact | future／prediction／model |
|---|---|---:|---|---:|---:|
| V1 | 原始事前規格 | 0 | ffmpeg `--version` 不支援，pre-network fail | 0 | `0 / 0 / 0` |
| V2 | 只改為 ffmpeg `-version` | 1 | yt-dlp transport exit `1`，1.978149 s | 0 | `0 / 0 / 0` |

V2 使用 yt-dlp `2026.02.04`、ffmpeg `8.0.1`；stdout 0 bytes、stderr 35 bytes。依事前資料最小化規則，
stderr **內容**沒有被保存或顯示，只有 byte count，因此目前只能把原因定位到 `network_transport`，不能誠實地
宣稱是 TLS、來源不可用、provider challenge、extractor 或 ffmpeg section error。

保存結果：

- `analysis/p3_b55_v1_pre_network_tool_probe_failure_2026-09-18.json`
- `analysis/p3_b55_v2_reserved_source_transport_failure_2026-09-18.json`

## 已排除與未排除

已排除：

- V2 不是 ffmpeg version flag 問題；兩個工具版本均通過凍結檢查。
- 不是 B54 duration／hash／manifest reader 拒絕；V2 在任何 local media 或 public artifact 產生前就停止。
- 不是程式偷偷取用 future；兩版 hidden-future request 都是 0。
- 不是 retry、fallback、cookies、playlist、subtitle、comment 或 user yt-dlp config 造成；這些均由命令明確禁用。

尚未排除：公開來源當下可用性、YouTube provider challenge、yt-dlp extractor、TLS／網路、format selection，或
`--download-sections` 的 transport／post-processing 問題。凍結 telemetry 沒保存錯誤文字，所以不能再細分。

## 離 B55 成功差什麼

現在缺的不是另一個規則，而是一個**可分類的真實 transport 診斷證據**。在沒有 180 秒 artifact 前：

- generation 仍沒有看過真實 observable context；
- hidden future `3181..3241` 仍未建立、未讀取；
- 沒有 prediction、模型輸出、實際未來驗證或系統優勢數據；
- B54 的合成通過不能外推為真實來源通過。

## 設計審查選項

1. **建議：單次 diagnostic transport（最低研究破壞）**。另凍結一次請求，private worker 只把 stderr 映射成
   allowlisted 類別（availability／provider challenge／TLS／extractor／ffmpeg／unknown），不保存文字；若同一請求
   成功則沿用既有 B54 gate。代價：再增加 1 次 source request；須明確覆蓋 V2 的 no-additional-correction 規則。
2. **使用者提供本機來源媒體**。避免系統再向 provider 請求，但需要人工取得檔案，provenance 與是否含整段來源要
   另外約束；不能把這條路稱為相同的自動 transport 證據。
3. **重新選來源**。會讓 B52 source reservation、B53 boundary 及 B55 全部重做，且有選擇偏差風險；不建議只為過 gate。
4. **登入／cookies**。可能解 provider challenge，但涉及帳號與私密憑證，會改變可重現性；不得在未經使用者明確操作下採用。

依既有最多兩個有根據批次規則，此處停止執行，不自行選項、不再請求來源、不碰 future。

## 驗證範圍

- B55 V1/V2 contract 與 frozen offline tests：`13 passed`（包含兩份保存 failure receipt）。
- V1 runtime：failure receipt valid，0 network。
- V2 runtime：failure receipt valid，1 network request，0 public artifact。
- 未有：真實 artifact、fresh public reader、Safari、fresh generation、人評或正式 M56 證據。
