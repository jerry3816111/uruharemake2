# P2 integrated product baseline：acceptance

日期：2026-09-09

## 結果

P2 現有五組產品控制在同一個最新入口、同一份 5-session／9-turn 本機 qwen2.5:7b run 中共同成立：

| 控制 | 結果 | 真正證明到的行為 |
|---|---|---|
| 重複婉拒 | PASS | 保留低干預回覆，沒有產生新的 pending；arbitration node 存在 |
| 當輪中文求助 | PASS | `solve_regulation` 覆蓋前輪 listening；current-request/task-handoff nodes 存在 |
| 明確要求獨處 | PASS | 最終尊重獨處，錯誤二選一未進 pending；explicit-space node 存在 |
| 跨語言引句來源 | PASS | 已選 episode 的 user role 形成 deterministic factual/memory 回覆；speaker node 存在 |
| 無上下文 `那個。` | bounded abstention PASS | 只要求多一點資訊，沒有把未知指稱寫入 pending |

全局 runtime checks 4/4；9 輪 persistence 全部 saved、graph current ID 存在、無 prediction 的回合不殘留 pending、
各 graph 保留 calibration。兩次實際一般 planner call 都由本機 qwen2.5:7b 完成，共 2,900 個帳本 token；ledger 不保存
raw prompt/reply。這次只重用已完成的最終 run，不重跑模型追分，也沒有更動任何產品程式。

## 凍結內容

`research/p2_integrated_product_baseline_freeze_2026-09-09.json` 綁定產品 commit `be59317`、P1/P2 入口與 adapter hashes、
最終 JSON／graph HTML hashes、5/5 case gate、4/4 structural gate、呼叫數、tokens、時間及證據邊界。這讓 P3 可以明確知道
「system condition」是哪一個不可偷改的版本，而不是用後來調過的程式回頭重跑開發案例。

## 判定界線

可稱：**P2 bounded product baseline frozen**。四個機制案例與一個保守 abstention 在同一次整合 run 內沒有互相覆蓋。

不可稱：完整 P2 open-world 成功、跨任意長對話可靠、相對強 LLM 優勢、holdout、人類被理解感、Safari 驗收、正式研究結果，
或人類方程式已解出。`rightbrain_transformer_loaded=false` 代表這次使用產品的非 transformer right-brain path；比較時不能隱瞞。
Safari 仍因工具拒絕目前網址而 pending，離線 graph HTML 只作可追溯證據。

P3 下一步是先凍結公平比較問題、baseline/system 介面、同模型與 token-accounting 規則，以及不曾參與本輪開發的新案例來源；
在這些定案前不生成比較結果。
