# P3-B60 private caption cutoff extractor acceptance

日期：2026-09-20

## 結論

`NEGATIVE / ONE CAPTION-PATH CORRECTION REMAINS`。B60 resolver 成功選出 frozen `automatic / ja / json3`
track，但 Python urllib 的唯一 caption GET 在取得內容前以 `tls_or_network` 失敗。因此 0 raw caption、0 public context、
0 prediction-side future access。

## 證據

- 事前 B54–B60 affected suite：`104 passed`；合成 raw 中跨 cutoff 與 future sentinel 均未進 public artifact。
- resolver：exit `0`，`1.661879 s`，private stdout `508451 bytes` 使用後丟棄。
- caption GET：`1` invocation，0 bytes，`tls_or_network`。
- URL/hash、resolver raw、caption raw、post-cutoff text persisted：全部 `false`。
- public artifact/manifest：`0/0`；prediction/model/training/paid access：全部 `0`。

保存結果：`analysis/p3_b60_private_caption_cutoff_extractor_result_2026-09-20.json`；result hash
`1413e030d352687058d65ffce3346a96343948001e4de244010c7acadc5e4dfc`。

## 接續

B61 可做 caption 路徑第二個、也是最後一個前瞻修正：保持同一 source、track、cutoff extraction、public artifact與reader，
只把「resolver URL + urllib GET」換成 yt-dlp 原生 `--write-auto-subs --sub-langs ja --sub-format json3 --skip-download`
寫入私有暫存目錄。成功才做相同 cutoff projection並刪除 private raw；失敗則關閉自動 caption acquisition，要求合法本機
artifact或另凍結來源。不得增加 retry、cookies、登入或顯示字幕文字。
