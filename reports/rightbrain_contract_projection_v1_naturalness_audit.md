# RightBrain Contract Projection v1 Naturalness Audit

## 方法

- 透明、非盲的 agent audit。
- 逐句檢查自然日文、當前話題、未授權記憶、公開語意契約。
- 這是三題開發集，不是人類盲測或完整自然度 benchmark。

## Gate 通過候選

| 條件 | 通過 audit | 失敗 audit | 結果 |
|---|---:|---:|---|
| legacy unprojected | 0 | 3 | 舊候選已不洩漏私人記憶，但日文話題句仍很彆扭 |
| projected contract | 4 | 3 | 背景支持與 no-memory 候選可用；topic proposal 模型候選仍不穩，final 由 deterministic fallback 保住 |

## 最終回答配對

| case | preference | 理由 |
|---|---|---|
| background family pressure | projected | 更直接表達降低負荷與休息，且沒有變成敬語客服口吻 |
| private do not mention | tie | 最終回答相同，兩者都使用新 public topic plan，沒有提私人記憶 |
| no memory plain question | tie | 最終回答相同 |

## 結論

新左腦 topic proposal plan 修掉了「今天聊什麼？」只剩空泛短回覆的問題；但 actual model 生成的 topic 候選仍有彆扭句，正式可用仍主要靠 deterministic fallback 與 gate 保住。這表示下一輪應改善右腦對 topic-opening 的自然生成，而不是再把私人記憶放進右腦。
