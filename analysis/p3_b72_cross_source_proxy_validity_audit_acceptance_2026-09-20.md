# P3-B72 cross-source proxy validity audit acceptance

日期：2026-09-20

## 結論

`PROXY_NOT_ADEQUATE_FOR_SYSTEM_ADVANTAGE_CLAIM`。目前的automatic-caption marker proxy不能支撐「完整系統優於
baseline」的主張，也不適合繼續靠增加同類影片累積row wins。

## 可重現數據

- 兩個已完成來源、8列；沒有新增來源、future、model、human或LLM judge call。
- row wins為baseline/system/tie=`2/6/0`，表面上偏system。
- 平均actual-label probability為`0.31875/0.2625`、top-1 hits為`3/8`與`2/8`，偏baseline。
- 平均Brier為`0.9947/0.982775`、log loss為`5.609082790262/1.796384009447`，偏system；baseline log loss受一個
  zero-probability row強烈放大。
- 第一來源有2種actual labels與1/4 marker hit；第三來源只有1種actual label且0/4 marker hit。
- mean actual probability、Brier、log loss在兩來源間發生方向反轉；跨來源五個primary metrics也不同向。

## 研究意義

這個結果阻止一個錯誤結論：只報system 6/8 row wins會隱藏baseline在actual-label probability與top-1較好，也會忽略第三來源
的default-label collapse。B66/B68 proxy仍可作為已曝光development diagnostic，但不能再當人類反應、語用理解、被理解感或正式holdout
的真值量尺。

B72是在看過兩來源結果後才凍結的診斷審計，不是事前effect test；它只能判斷量尺不夠，不能估計system真實效果大小。下一步必須先定義
具有清楚刺激—回應邊界的可觀察target、盲化標註與可靠度gate，再碰任何新來源的prediction/outcome。不得依已曝光8列調marker後宣稱修好。
