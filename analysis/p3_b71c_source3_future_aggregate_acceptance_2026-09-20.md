# P3-B71C source3 future aggregate acceptance

日期：2026-09-20

## 結論

`MIXED / NO SOURCE3 SYSTEM ADVANTAGE / PROXY COLLAPSE WARNING`。第三來源四列一次揭盲後，row wins為baseline/system/tie=
`2/2/0`；平均actual-label probability=`0.375/0.2375`、平均Brier=`0.81845/0.95215`、top-1 hits=`2/4`與`1/4`，
均是baseline較好。這沒有重現B68第一來源的system 4/4 row wins。

## 逐列結果

- `s3r0600`：baseline勝；actual=`acknowledge_then_continue`，機率baseline/system=`0.45/0.10`。
- `s3r1200`：system勝；actual=`acknowledge_then_continue`，機率=`0.10/0.15`，兩組top-1都錯。
- `s3r1800`：system只以Brier勝；actual機率兩組同為`0.10`，兩組top-1都錯。
- `s3r2400`：baseline勝；actual機率=`0.85/0.60`，兩組top-1都對。

## 評價限制與真正觀察

四列的first-three-cues都沒有命中任何較高優先marker，因而全部落到default `acknowledge_then_continue`。因此這批不只顯示system
未穩定勝出，也顯示既有caption-marker proxy在第三來源缺乏label diversity，不能充分評估語用理解或預測文字品質。不得以跨來源
row wins簡單相加宣稱system整體較強；B71C反而要求停止追加同類影片追分，先審計proxy的辨識有效性。

執行符合freeze：future access=`4`、scores=`8`，model/human/LLM judge、prediction mutation、retry、fallback=`0/0/0/0`；
private full caption在public scoring前刪除。本結果不是人類真值、被理解感、人類方程式或formal holdout證據。
