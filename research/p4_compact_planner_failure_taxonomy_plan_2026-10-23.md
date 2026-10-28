# P4 compact planner：失敗分類先於格式修復

事前定案（任何新模型呼叫前）。c 批 c0 control 已在真 Safari 失敗並依硬 gate 停止；原始模型 JSON 未保存，`unexpected fields` 同時涵蓋候選缺欄與多欄，不能從該訊息反推是哪一種。c0–c6、舊 a/b 題及結果不重送、不改判。

## 本項唯一變因

只增加 compact planner **失敗的 raw-free 類別收據**。模型、OpenAI-compatible `json_object` carrier、prompt、三個候選的嚴格欄位和值契約、256 output tokens、20 秒、既有記憶／人格／安全與最後回覆路徑均不變。原本拒絕的回覆仍拒絕；不刪多餘欄、不補缺欄、不合成候選、不重試。失敗時 trace 僅可保存固定枚舉代碼、0–2 候選索引及 bounded 欄位數，不保存模型文字、任意 key 名、prompt 或私人資料。transport 失敗與已收到但格式不合須區分；通過時保持既有三候選與 cost ledger。

允許修改 `uruha_compact_planner_p2.py`、`test_compact_planner_p2.py`、本 plan／新 source-only probe、驗收報告與 `CURRENT_TASK.md`；不改 frozen c 題／比較程式、原始 dirty checkout、正式 DB、baseline 或條件 gold。這是 P2 嚴格契約的診斷性擴充，不是調整研究分數。

## 驗收順序及失敗分支

1. Before：c0 報告與原件 SHA 已鎖；現行 `test_compact_planner_p2.py` 為 11/11。先以純假 response 覆蓋 finish、JSON、root、候選數、非 object、缺欄、多欄、缺且多、scene／mode／core 值及 duplicate；每例仍 fail closed，只在 audit 出現對應固定類別。有效與非 compact request 逐欄不變，實際 client 仍只呼叫一次。聚焦後跑相鄰 product／handoff 回歸、compile、diff check。
2. 只有上述通過、source-only 新 d0 事前提交且 source／model／隔離 preflight 合格時，才准一輪新隔離產品 Safari 診斷。d0 在 `datasets/p4_compact_planner_failure_taxonomy_d_probe_2026-10-23.json`；它是作者開發題、非 formal holdout，且不屬於 c 批九臂。先 exact-string collision check；新 0700 root、私有官方 ONNX 離線預熱、空 DB、獨立高埠 7924、same-PID ready/Tpre `memory_db`、reset0/tick0/finish0、Send 後同 PID/Tpost tick0/finish1、0 retry。每輪最多 3 generations、2,000 provider tokens、20 秒 user wait；缺收據、格式或模型 digest 變化立即停，保留原件。Safari 泡泡／native graph／本輪 JSONL 要核對；不能保存 native PNG/AX 就明列 visual pending。
3. 若 d0 有格式失敗，固定代碼應能區分缺欄／多欄等；若沒有重現，記 `non_reproduction`，不得把 c0 追認為某一 subtype，也不得宣稱品質改善。若新分類或觀測破壞現有行為，保留失敗，回退設計審查（不得清掉舊結果）。

下一個**獨立**變因只有在分類後才能決定：可能測同一路由 strict JSON Schema carrier 的 source-disjoint canary，仍由原 validator fail closed；P3-B18 的另一模型 OpenAI-compatible schema 無效、B19 native schema 通過都不能代替本模型／本產品驗收。不得把本項診斷算 certificate handoff 效果、強 LLM 優勢、人評或 Goal 完成。
