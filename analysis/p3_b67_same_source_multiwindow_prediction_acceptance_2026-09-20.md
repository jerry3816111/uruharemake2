# P3-B67 same-source multiwindow prediction acceptance

日期：2026-09-20

## 結論

`COMPLETE PREDICTION BATCH / FOUR FUTURES STILL LOCKED`。四個時間窗在任何B67字幕投影與模型呼叫前已寫入freeze；
一次private caption acquisition只發布四段context，完整字幕與private runtime刪除後，fresh reader才把context交給原樣重用的
B65 bounded joint interface。四列、兩condition共8條prediction全部完成。

## 實際資源

- context cue counts：`77 / 72 / 66 / 72`。
- model calls：`8/8` completed；每個condition ceiling=`512`。
- prompt tokens total=`18,908`；completion tokens total=`1,697`。
- model latency total=`152.907164s`；whole stage=`155.180941s`。
- native subtitle download=`1`、1.987250s；private full caption=`1,483,058 bytes`，已刪除。
- retry/fallback/future access/outcome score=`0/0/0/0`。

## 封存的top-1差異

| row | baseline | system | 是否不同 |
|---|---|---|---|
| r0600 | acknowledge_then_continue (0.85) | acknowledge_then_continue (0.85) | 否 |
| r1200 | pause_and_reassess (0.75) | accept_support_and_continue (0.60) | 是 |
| r1800 | accept_support_and_continue (0.85) | acknowledge_then_continue (0.65) | 是 |
| r2400 | accept_support_and_continue (0.85) | accept_support_and_continue (0.85) | 否 |

這些差異讓B68能事後反駁兩組，而不是只有相同答案。prediction batch canonical hash=
`f51399ee1e226a7c92f1a547f9b6974577fdc8ab7efbf76d744baaa19a6dcb82`。

## 邊界

B67沒有讀取`781..841`、`1381..1441`、`1981..2041`或`2581..2641`的任何cue。它只證明原樣介面能在四列
完成，不包含正確率。這四列來自同一支已用於開發的公開影片，所以即使B68為正，也只能算same-source prospective
development replication，不能稱為independent holdout、人評、全面LLM優勢或人類方程式證據。
