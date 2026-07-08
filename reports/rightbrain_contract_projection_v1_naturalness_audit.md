# RightBrain Contract Projection v1 Naturalness Audit

## 方法

- 透明、非盲的 agent audit。
- 逐句檢查自然日文、當前話題、未授權記憶、公開語意契約。
- 這是三題開發集，不是人類盲測或完整自然度 benchmark。

## Gate 通過候選

| 條件 | 通過 audit | 失敗 audit | 結果 |
|---|---:|---:|---|
| legacy unprojected | 0 | 1 | 唯一候選仍談到不相關的腹部狀態 |
| projected contract | 3 | 2 | 背景支持改善；普通聊天仍有兩個語意空洞候選 |

## 最終回答配對

| case | preference | 理由 |
|---|---|---|
| background family pressure | projected | 更直接表達降低負荷與休息，且沒有變成敬語客服口吻 |
| private do not mention | tie | 最終回答相同 |
| no memory plain question | tie | 最終回答相同 |

## 結論

投影避免舊體調計畫繼續支配候選生成，並在一題背景支持中改善最終回答；但它沒有解決「聊什麼」這類左腦公開計畫本身資訊不足的問題。
