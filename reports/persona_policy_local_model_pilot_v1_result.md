# 人格策略實際本機模型 pilot V1

**pilot_failed**

| 指標 | 結果 |
|---|---:|
| 實際 7B 生成 | 10 |
| 嚴格有效輸出 | 2/10 |
| 兩組都有效的配對 | 0/5 |
| 有效且輸出不同的配對 | 0/5 |
| 不同正規化輸出 | 9/10 |
| legacy 固定回覆存取 | 0 |
| target／neutral 配置 tokens | [640, 640, 640, 640, 640] / [640, 640, 640, 640, 640] |

決策：`repair_structured_local_model_surface_before_persona_scoring`

本結果只回答 structured 人格策略能否被目前本機右腦承載並造成可觀察差異；哪一組更像目標人物仍需後續盲化編碼，不能由本 pilot 自行宣稱。
