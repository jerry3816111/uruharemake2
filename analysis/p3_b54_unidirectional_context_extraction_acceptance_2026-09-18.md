# P3-B54 unidirectional observable-context extraction acceptance

日期：2026-09-18

## 結論

`PASS`，但只通過**合成媒體的能力隔離 gate**。B54 已把「私有 worker 可暫時持有較長 transport」與
「generation 只可讀截止點前 artifact」拆成兩個程序。這不是保證真實 YouTube transport 已同樣隔離，
也不是行為預測、模型品質或系統優勢證據。

## 單一改變與 before／after

- Before：B53 只有 `3000..3180` 的時間界線，尚無媒體裁切器；若直接把來源交給生成程序，就無法證明
  它沒有讀到 `3180` 後內容。
- After：private extractor 以 frozen `atrim` 產生 mono 16 kHz PCM WAV；standalone public reader 只有
  public-root capability，先核對 owner／mode／single-link、manifest SHA-256、artifact SHA-256，再以
  `ffprobe` 核對 codec、sample rate、channel 與 duration。
- public manifest 是 exact-field allowlist；沒有 URL、title、description、transcript、future、behavior、
  raw path 或 source duration。reserved source profile 在 B54 明確 fail-closed，尚不能執行。

## 正式合成 rehearsal

| 檢查 | 結果 |
|---|---:|
| private raw transport | `0.0..5.0 s` |
| generation-visible artifact | `1.0..3.0 s` |
| artifact duration | `2.0 s` |
| cutoff 後 2000 Hz／可見 440 Hz 能量比 | `6.781521697810383e-31` |
| cutoff 後 sentinel | absent under frozen `<= 0.0001` gate |
| raw 刪除後才啟動 reader | yes |
| reader 啟動時 private root mode | `000` |
| fresh reader processes | `2/2 exit 0` |
| restart artifact hashes | `2/2 identical` |
| manifest forbidden fields | `0` |
| private filename canary hits | `0` |
| public reader private imports | `0` |
| reserved-source／hidden-future／prediction／model calls | `0 / 0 / 0 / 0` |

保存結果：`analysis/p3_b54_unidirectional_context_extraction_result_2026-09-18.json`，result hash
`7f5748844da1962d5ba64ece65df2ed4cc4f09915f4b79faae9b22a7f8d538ce`。

## Fail-closed 與回歸證據

- B54 targeted：`10 passed`。涵蓋 2.25 秒超長 WAV 即使 manifest 聲稱 2.0 秒仍被 `ffprobe` 拒絕、
  content-hash 篡改、禁止欄位注入、symlink、hardlink、group/world permission、失敗裁切後 raw 刪除，
  以及未授權 reserved-source profile 在接觸媒體前拒絕。
- B51–B54 immediate affected set：`28 passed`。
- B52 全版本結果、B53 結果與 B54：`58 passed`。
- 這些是 contract／synthetic fixture 證據；沒有 Safari、人評、fresh model generation 或正式 M56 結果。

## 下一個必要 gate

synthetic isolation、duration gate、restart hash 與 fail-closed 均通過，因此可以進入 B55 的
**真實 observable-context transport preregistration**。B55 要先凍結 `yt-dlp`／ffmpeg 呼叫、transport
可能 overfetch 的揭露、private temporary root、刪除證據、實際 bytes／duration／耗時與失敗分支，才可對
B53 reserved source 取得 `3000..3180`。仍不得取得或建立 `3181..3241` hidden-future artifact，也不得執行預測。
