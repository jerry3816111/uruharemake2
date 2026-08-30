# M12 論文方法對齊評測報告

日期：2026-08-17  
狀態：**已完成目前選定 frozen artifacts 的回溯性總評**  
中央優勢結論：**不支持／NOT SUPPORTED**

## 核心結論

這次評測不只比較總平均。每一個 system prediction 都和 B5 在同一事件
上成對比較；主要指標評量完整機率分布；同時報告不確定性，而且有利方向
必須在開發資料、新語義時間線與第二人物三條證據軌重現。

結果不支持中央假說。M6 的方向有利於 hybrid system，但 M8、M9 都有利於
B5 structured-history LLM；三條證據軌都不是正式真人 Uruha 未見未來資料。
因此目前證據**不能證明系統比強 LLM baseline 更好**。

## 成對機率預測比較

差值定義為 `candidate - B5`；Brier／NLL 越低越好，因此負值有利於系統。

| 證據軌 | n | Brier 差值 [95% bootstrap CI] | NLL 差值 [95% bootstrap CI] | Top-1 差值 | 方向 |
|---|---:|---:|---:|---:|---|
| M6_DEVELOPMENT_SYNTHETIC | 8 | -0.1960 [-0.5414, +0.2500] | -0.5009 [-1.0360, +0.1357] | 12.5% | directionally_favors_candidate |
| M8_FRESH_SYNTHETIC_ROLLING | 16 | +0.3125 [-0.1186, +0.7627] | +2.0370 [+0.1771, +4.1363] | -18.8% | directionally_favors_baseline |
| M9_SECOND_PERSON_SYNTHETIC | 16 | +0.5744 [+0.0799, +1.0666] | +1.9897 [+0.5361, +3.5103] | -31.2% | directionally_favors_baseline |

- 有利於系統：1/3 條。
- 有利於 B5：2/3 條。
- 正式真人資料：0 條。
- 「同模型條件下優勢已重現」：`false`。

- `M6_DEVELOPMENT_SYNTHETIC`：Brier exact p=0.3594；NLL exact p=0.1406；Top-1 McNemar p=1.0000；判定 `inconclusive`。
- `M8_FRESH_SYNTHETIC_ROLLING`：Brier exact p=0.2044；NLL exact p=0.0670；Top-1 McNemar p=0.4531；判定 `inconclusive`。
- `M9_SECOND_PERSON_SYNTHETIC`：Brier exact p=0.0455；NLL exact p=0.0230；Top-1 McNemar p=0.1797；判定 `statistically_favors_baseline`。

這是對已曝光產物的回溯性 audit，所以 p 值是對不確定性的診斷，不是新的
預註冊 confirmatory claim。M9 的 Brier、NLL 成對結果支持 B5；M6 與 M8
沒有提供足夠統計證據判定勝方。

## Rolling cutoff 穩定性

| 證據軌 | Cutoff | Top-1 | Brier | NLL |
|---|---|---:|---:|---:|
| M8_FRESH_SYNTHETIC_ROLLING | E1 | 75.0% | 0.5290 | 0.9315 |
| M8_FRESH_SYNTHETIC_ROLLING | E2 | 50.0% | 0.9373 | 3.5475 |
| M8_FRESH_SYNTHETIC_ROLLING | E3 | 100.0% | 0.0033 | 0.0349 |
| M8_FRESH_SYNTHETIC_ROLLING | E4 | 25.0% | 1.4936 | 7.1483 |
| M9_SECOND_PERSON_SYNTHETIC | E1 | 0.0% | 1.9311 | 5.5148 |
| M9_SECOND_PERSON_SYNTHETIC | E2 | 25.0% | 1.2568 | 2.7294 |
| M9_SECOND_PERSON_SYNTHETIC | E3 | 100.0% | 0.0136 | 0.0582 |
| M9_SECOND_PERSON_SYNTHETIC | E4 | 50.0% | 0.9978 | 3.4786 |

M8、M9 每個 cutoff 都只有四個案例。大幅波動代表目前沒有穩定性證據，
不能把任何單一 cutoff 的結果當成母體效能的精確估計。

## 解釋忠實度

- 具名 interventions：80 次。
- 直接 top-feature interventions：40 次。
- 對機率造成非零變化：100.0%。
- Post-exposure 可獨立 ablate 元件：10/10。
- M7 的 preference／relationship／temporal 移除方向在 M8 重現：**0/3**。

結論：trace 確實接到真正的機率計算，但個別心理元件的重要方向沒有跨資料
穩定。這證明的是 computational faithfulness，不是私人心理狀態的真實性。

## 50 輪記憶

| 條件 | 有來源主要回溯 | Strict task | False-memory assertion | 總 tokens | 延遲 |
|---|---:|---:|---:|---:|---:|
| Uruha memory | 2/2 | 4/5 | 0 | 13,435 | 255.51s |
| Recent 8 turns | 0/2 | 1/5 | 1 | 2,526 | 12.53s |
| Full transcript | 2/2 | 4/5 | 1 | 7,405 | 10.99s |

Uruha memory 勝過只看最近八輪的 bounded baseline，但在 strict task 與
full-context LLM 打平，同時使用 1.81x tokens 與
23.24x 延遲。這只有五個 checkpoint，且不是獨立 semantic
holdout，因此不能證明通用記憶優勢。

## 論文方法依據

- [Gneiting & Raftery (2007)](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf): Brier and logarithmic scores as strictly proper scoring rules.
- [Guo et al. (2017)](https://proceedings.mlr.press/v70/guo17a.html): calibration, ECE, reliability diagrams, and temperature scaling.
- [Peyrard et al. (2021)](https://aclanthology.org/2021.acl-long.179/): compare NLP systems on paired instances, not only independent means.
- [Berg-Kirkpatrick et al. (2012)](https://aclanthology.org/D12-1091/): bootstrap-based statistical significance analysis in NLP.
- [Maharana et al. (2024)](https://aclanthology.org/2024.acl-long.747/): long-term conversational memory requires more than one recall item.
- [Liu et al. (2016)](https://aclanthology.org/D16-1230/): word-overlap metrics are poor substitutes for dialogue quality.

## 已完成與尚未完成

目前已完成：

- SHA 綁定、可執行的評測 protocol；
- 每事件成對 proper-score 統計與信賴區間；
- rolling、transfer、intervention、memory、failure 與成本總評；
- 對「是否重現 B5 優勢」給出沒有通過的誠實結論。

仍然缺少：

- 正式 temporal holdout 的 Uruha 行為資料；
- 真人資料上的 replication；
- 自然日文偏好與 felt understanding 的獨立證據；
- 足量 unseen samples 支持精確 calibration 與母體主張。

M12 沒有呼叫模型，只評估 frozen predictions；沒有在看過舊答案後假裝製造
新的 test samples。
