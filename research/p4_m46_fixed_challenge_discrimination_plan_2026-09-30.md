# M46 固定 challenge-only 辨別力：事前設計（非獨立開發審查）

## 問題與不可改寫的 before

原 P4-M46 A/B 消融在第一個 M51 生成 call 即停止：`num_predict=360` 用滿、JSON
在第二候選字串內截斷，完成 batch `0/6`、review call `0`。該次結果是
`INCONCLUSIVE / NOT RUN`，不是 M46 通過或失敗；其 freeze、runner 和結果均不續跑、
覆寫或更改。本卡只問較小的問題：對已在**原實驗模型呼叫前封存**的手寫固定封包，
現有 M46 reviewer 能否在保留有效行動的同時，辨出 deterministic guards 放過的
wrong-task、unsupported specificity、private inference、non-action 和 actor/surface 錯誤？

這是元件辨別力篩檢，非「M46 已證明產品必要」。固定封包不是 M51 的自然生成，
無法估計錯誤盛行率；B 對五個負例會放行是**事前構造**，不是新觀察到的產品危害率。

## 單一變因與固定資料

- A：相同 source、M51 格式 batch 與 M52 selected plan，通過既有 M53/P4-AV、
  M46 structural 和隔離 M39 exact-surface guard 後，呼叫未改的 M46
  `REVIEW_SYSTEM`／schema，再以 `inspect_goal_progress` 判定。
- B：完全相同 selected plan 與 deterministic guards，不呼叫 reviewer；只計算
  offline 反事實，絕不接產品。不得用全 true 假 review 偽裝 A 的模型結果。
- 輸入只取原 `datasets/p4_m46_reviewer_necessity_v1.json` 中九個 `challenge_packets`，
  byte SHA-256 鎖定於新 contract；六個 `generation_cases` 不執行、不替換、不計分。
  原 gold 是 developer-authored proxy，非真人獨立標註、非未曝光 holdout；
  在 reviewer 輸出後不得改標、刪題或重排。

事前零模型前檢須重放既有 scorer：三個 valid 與五個 semantic/surface invalid
均選 index 0、與 M53-aware selector 一致、source/plan 指紋固定、共同 guard 可交審；
唯一 guard control 兩臂阻擋且**不送** M46。隔離 M39 只在同一句 `instruction_jp`
逐字接受時視為可交審，不能把 M39 修補後的另一句當成該 action 交付。前檢有任何
不符即停止，不用調整封包追分。review payload 只含來源、已選 plan（隱去其自稱的
`progress_mechanism`）及 digest，不含 `gold`、category 或預期 check；A/B 的
source、selected plan、fingerprint 必須逐案相同。

八個 eligible call 的事前順序在 contract 明列，以 valid/invalid 交錯降低順序混淆；
guard control 仍列於末尾供前檢與評分，但不消耗 call。沒有抽樣或事後挑題。

## 呼叫、品質與成本 gate

新 freeze commit（研究計畫、contract、零 call 測試）完成後，才可另外提交新的一次性
runner/fake transport 測試。runner 可只匯入舊 runner 的 `model_json_call`、
`prewarm_model`、`_tokens_complete` 共用函式；該舊檔亦以 byte hash 鎖定，
不得呼叫它的失敗 `generate`／`review` 正式路徑。新結果用**獨立、尚不存在**的路徑。
兩個 commit 和新 runner 前檢通過以前 scored calls=`0`。

固定 `qwen3.5:9b` digest、Apple M2 Pro/32 GB、既有 M46 prompt/schema、
`temperature=0`、`seed=20260829`、`num_ctx=4096`、`num_predict=320`、
`stream=false`、`think=false`、`keep_alive=30m`。僅 localhost，一次不計分
prewarm 後最多 **8 個** scored reviewer calls；每封包一次、0 retry、30 秒 transport
timeout。每 call 保留原回覆或 failure、JSON parse、source identity、content/surface
checks、prompt/completion tokens、wall 秒；逐 call checkpoint。中斷、timeout、
JSON 不完整或 tokens 不完整即保存 partial、不可續跑或補分。

品質 PASS 必須同時滿足：A valid retained=`3/3`、五個負例 false action=`0/5`、
review calls=`8/8` completed/parseable、token accounting=`8/8`、review source
id/span=`8/8` exact、既有自然日文與隔離 M39 exact 接受=`8/8`，guard control
兩臂 blocked=`1/1`。非全拒絕只是 `3/3` 的必要結果。為免把格式／語氣拒絕
誤稱語意辨別，每個 invalid 還必須在其事前對應 check 中至少一項明確為 false：
wrong-task→`criterion_advances_goal`；unsupported specificity→`no_invented_facts`
或 `no_unknown_prerequisites`；private inference→`goal_matches_source` 或
`no_invented_facts`；non-action→`action_is_operationally_specific`、
`action_changes_task_state` 或 `criterion_is_observable`；surface→
`no_identity_or_role_error`。其他 false flags 與 `observed_progress_mechanism`
均逐案照報；若只因無關 style 或契約錯誤而拒絕，不算辨出該類錯誤。

B 的預定 offline 結果為 valid retained=`3/3`、五類錯誤 false action=`5/5`、
guard control blocked=`1/1`。若共同 guard 事實不符，屬設計／前檢失敗，
不是 A 的功勞；B 在本資料上不可取得旁通資格。A 的成本另報 reviewer-only
max/median wall、prompt/completion tokens 和 prewarm，不把固定封包臆造為零成本
M51 生成。現有產品每案兩階段門檻是 `<=20s`：reviewer 單 call `>20s` 已足以
判現配置不合格；即使全部 `<=20s` 也**不足以**推論生成＋review＋M45/M39
完整產品延遲合格。舊失敗首個 M51 call 已耗 `17.63697s` 且沒有可用封包，
不可拿它與本次不同固定封包硬配成成功的 end-to-end case。

## 事前決策與 claim 邊界

- 前檢不符：0 模型 call，審查資料／guard 邊界，不改原封包或 gold。
- 任一 scored call 失敗：封存 partial，0 retry／resume；本次完整辨別力結論
  `INCONCLUSIVE`。
- A 錯放、錯拒、全拒，或只靠無關 flag 拒絕：固定辨別力 FAIL；維持產品
  fail-closed，先審查 reviewer 架構，不直接旁通。
- A 品質全過但 reviewer-only 成本超過 20 秒：只稱有局部品質價值；現配置
  不具產品時限資格，需另設計替代／資源配置。
- A 品質全過且 reviewer-only 均不超過 20 秒：只稱固定封包的 bounded
  component discrimination；另以**全新 source** 事前凍結 M51 表示或 token 資源
  的單一變因，重測真實生成、相同候選 A/B、完整 token 與兩階段 `<=20s`。
  即使該層通過，仍需新的隔離 private runtime／Safari 驗收實際日文、source、
  node graph、durability 和 latency，不能重跑 P4-AZ 正式句。

本研究不改產品 runtime、M51/M46/M45/M39、M52/M53/P4-AV、persona、memory、
正式私有資料、原失敗 artifact 或已凍結 P4-BC/BD/BE 結果。沒有自然分布估計、
獨立人評、強 LLM 公平基線、真人效用、完整 Web 交付或「人類方程式」主張。
