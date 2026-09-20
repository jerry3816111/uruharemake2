# P3-C2 controlled context-flip execution acceptance

日期：2026-09-20

## 執行是否完整

完整。事前凍結的 8 次 train format smoke 全部通過後，才執行 24 次 dev calls；總計 32/32 calls、32/32 validated
predictions，0 retry、0 fallback、0 holdout input/target access、0 新 Uruha source/future access。B70 adapter 兩組皆綁定，但 32 個
weight sums 原本都是 1.0，因此 normalization applied=`0/32`，本次完成不能歸因於 normalization。

實際總成本為 22,952 prompt tokens、6,497 completion tokens、326.528142 秒 model latency。

## 事前成功條件與實際結果

Primary 是 developer-authored dev target 上的 mean multiclass Brier，system 至少要比 baseline 低 0.03；此外 system 的字面過度解讀率
不得更差，paired context-flip top-1 也不得更差。

| 指標 | BASELINE_DIRECT | SYSTEM_PRAGMATIC_STATE | 判定 |
|---|---:|---:|---|
| mean Brier | 0.133050 | 0.120717 | system 改善 0.012333，未達 0.03 |
| mean log loss | 0.847280 | 0.826137 | system 小幅較低 |
| target top-1 | 12/12 | 12/12 | 平手、題目出現 ceiling |
| paired flip top-1 | 6/6 | 6/6 | guard 通過 |
| literal overinterpretation | 0/6 | 0/6 | guard 通過 |
| pragmatic underreading | 0/6 | 0/6 | 平手 |

因 primary 未達 SESOI，`controlled_lane_success=false`。不能用兩個 guard 沒退步來取代 primary，也不能把小幅 Brier 差說成優勢成立。

## 分層結果與反例

- English Brier：`0.1700 → 0.1005`，system 較低。
- Chinese Brier：`0.12335 → 0.10335`，system 較低。
- Japanese Brier：`0.1058 → 0.1583`，system 反而較高。
- Implicature 8 rows/condition：`0.142925 → 0.098175`，system 較低。
- Deixis 2 rows/condition：`0.0608 → 0.1658`，system 明顯較高。
- Presupposition 2 rows/condition：兩組都是 `0.1658`。

其中 `dev_ja_02 / また今度ね。` 的 literal control，baseline 給 target top-1 probability 0.65，system 只有 0.45；pragmatic side
兩組同為 0.75。這是 system 顯式分析沒有帶來一致好處的最小反例，與 aggregate 未達 SESOI 一致。

所有 dev rows 兩組 top-1 都正確，代表這批 developer-authored dev 題對 `qwen3.5:9b` 太容易，只剩 probability calibration 的細小差。
這不是「一般 LLM 很弱」；相反地，強 direct baseline 已能正確使用完整 context。

## 成本

兩組各 16 calls。system 相對 baseline：

- prompt tokens：12,908 vs 10,044，`1.2851×`；
- completion tokens：4,917 vs 1,580，`3.1120×`；
- model latency：227.987501 vs 98.540641 秒，`2.3136×`。

因此目前沒有「相同品質但成本更低」的替代正面結論；system 是更貴且未達事前效果量。

## 決策

不執行 C1 holdout。原因不是 runner 失敗，而是完整 dev evidence 已否定本 lane 的事前成功條件，且出現 top-1 ceiling、Japanese/deixis
方向反轉與明顯成本增加。為了追分而修改已凍結 target、SESOI、baseline 或直接偷跑 holdout，都會破壞研究可信度。

下一個必要交付應改為找正式公開、未由本專案作者撰寫的 controlled pragmatic benchmark／刺激材料，先確認 license、官方資料欄位、
same-surface context pairs、train/dev/test 邊界與 task fit；只做 metadata/schema/licensing discovery，不先讀 test answer，也不沿用 C1 結果調新答案。

## 證據邊界

這是完整、可重現的 development negative/mixed result，不是正式 holdout 或真人偏好。它證明 runner 與比較可以跑完，也證明目前這個
顯式 pragmatic state 版本不值得依 C1 標準直接進 holdout；不能外推成所有語用架構都無效，亦不能外推成人腦方程式成立或失敗。
