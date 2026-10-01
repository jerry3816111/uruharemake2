# P4 記憶承諾真實性：新十一輪隔離 Safari 驗收

狀態：開發者自製、尚未生成的新前瞻產品案例；非 sealed holdout、
獨立真人資料、強 LLM 比較或正式 temporal evidence。前項 T9 已曝光，
本案更換值與完整輸入，但部分句型沿用已曝光案例；不能用它改判
前項 strict FAIL，也不能稱新語法或新人物泛化。
完整輸入與每輪 source-only gold 在
`datasets/p4_profile_write_ack_fresh_probe_2026-10-01.json`；十一個新值在
執行前對其他 repo 檔案 exact `rg` 為 0-hit。這只是開發資料新鮮度，
不是未被開發者接觸的獨立 holdout。

## 同一個修正與預期分流

只檢查「准入決策 → plan／日文回覆 → writer 真實結果」一致性。
十一輪順序固定：日文朋友傳話拒寫 → 日文本人 write → 日文本人 correction
→ 英文引述朋友拒寫 → **T4 後真 process/session 重啟** → 中文本人 write
→ 中文朋友報述拒寫 → 英文本人 write → 英文雙候選拒寫 →
同一舊值分別在 `drink`／`食べ物` scope 寫入 → 無 scope 訂正因兩個 active
scope 而拒寫、請使用者指定範圍。後三輪是凍結前獨立 code review
發現的 state-dependent 預檢／writer 分歧，不是事後追分。

這裡的 source-only 是指**事前鎖定輸入序列、空白隔離 DB 起始狀態與
前輪實際持久資料**後標註，不看模型回覆來改 gold；不是每輪孤立
看原句。逐輪新增 profile row 數為 `[0,1,2,0,1,0,1,0,1,1,0]`；
純文字 owner 預檢准入數為 `[0,1,1,0,1,0,1,0,1,1,1]`，但 T11
必須由同源 state guard 以 `old_value_has_multiple_active_scopes`
在 episode 前撤回承諾，讓 typed writer 報出歧義，同時只攔同輪
legacy fallback。獨立 writer-only before 已證實若讓舊 fallback
執行會錯寫一筆畸形的本人偏好，因此預期的 0
增量是修正目標，不是既有 writer 觀察。第三者來源的三輪須明確**不把
該偏好當使用者本人喜好存入 profile**；T8 是兩個明確的本人候選，
須承認無法唯一選定並自然請求澄清，不能說它們不是本人的喜好。
T11 須指出是哪個範圍不明並低壓請求指定；五個未寫入輪都不可說
`覚えとく`／已記住；成功寫入六輪須逐字維持資料檔鎖定的既有 P4-H
write／correction 短日文承諾。
拒寫輪依資料檔的 source-only `visible_rubric` 判讀；不能靠固定禁詞
單獨判成功。不同語言輸入
的最終使用者可見句都須為自然日文。所有十一輪的 turn episode 仍需
持久、ID 互異；profile 拒寫不刪除原對話。T3 後前一個 drink 正向值
是 resolver historical、不是物理 metadata 改寫，新的值為 current。
英文引用、中文報述、日文傳話、雙值與 T11 未指定 scope 的新值
在 profile 不得出現；T9 將 T3 桂皮茶的 drink 正向列解析為
historical，T10 不應碰 drink；T9/T10 同值在 drink／食べ物 兩
scope 各自 active 保留。測前須核對隔離 profile 空白，T9/T10
後再核對這兩個 active scope，不能跳過 state 前置條件。

## 先後、資源與唯一執行

先完成 additive 程式、聚焦＋相鄰 tests、launcher 0-turn `check`，
獨立唯讀審查 dataset／plan；再以 full SHA-256 manifest 與 commit
鎖定程式、資料、測試及門檻，首輪前核對所有 hash。只使用安全
worktree、launcher-owned `0700` 系統 temp root、同一新 Safari tab
和本機 port；不碰正式 DB、原始 dirty checkout、既有 tabs 或外部服務。
T1–T4 exact 各送一次，確認四輪落盤，停舊 process 並驗證 port 關閉；
沿用同一隔離 root／DB 以新 PID/session 啟動，再送 T5–T11。
0 回答重試，輸入錯／程序偏差須保留原樣，不重跑此已曝光案例追分。

每輪保存 Safari final、user wait、session/PID、JSONL input/reply、
episode ID、`profile_owner_admission_p4`、新 truth node、P4-H audit、
memory writeback、`selected_plan` 與 `utterance`。查隔離 SQLite 的
持久 `user_profile` 值／subject／scope／resolver state，不能只看
當輪 session snapshot。保存 raw JSONL 完整 hash；測後停 server，
保留隔離 root 供覆核。每輪等待 `≤20s` 為獨立成本 target，超時記
成本 FAIL，但不單獨推翻記憶承諾真實性 gate；全產品
model calls/tokens/價格沒有可靠完整 ledger 就寫 `unavailable`，
不能把 overlay `0 extra calls` 冒充產品零成本。

## 不可改判的 strict gate

1. 十一個 exact input 各一次、每輪完整 final＋graph、十一個不同持久
   episode ID，兩個 session、T4→T5 真重啟、同一隔離 DB。
2. 逐輪 writer 新 row 與 source-only gold **11/11**；未寫入五輪零
   profile 增量且原 episode 保留；成功寫入六輪的值／scope／歷史正確。
   T11 須核對 owner 純文字預檢准入 `1`、typed writer 實際
   `ambiguous_extraction`／`typed_write_not_completed`、legacy fallback
   明確 suppressed、profile 新增 `0`、舊兩 scope 仍 active；不能把
   owner 准入偷當持久化成功。
3. 未寫入五輪 plan／final 無假記憶承諾，且不可把 T8 本人雙候選或
   T11 scope 不明誤稱第三者；成功六輪既有承諾保留；
   新 truth node 的 preflight／actual writer／reply verdict 與同輪
   P4 owner、P4-H、utterance、Safari 泡泡一致，沒有相反的成功節點。
4. 不洩漏內部分析給普通聊天泡泡；十一輪可見答覆須自然日文且符合
   資料檔逐輪語義，不誤指所有權。若只通過 writer/graph 而可見答覆
   有外語混入、錯誤承諾或錯誤角色，產品 strict FAIL；其他人格細節
   另列，不能用 script-only Japanese 或 graph 內部 PASS 掩蓋可見錯誤。

任一項失敗保留 FAIL，至多兩個有根據修正批次，**不得重播此案**；
新修正需另建前瞻資料。此 gate 即使通過，也只證明有限 memory-act
transaction truth，不處理前項 T10 source intent drift、混合句角色
表面、真人被理解感、同模型強 baseline、VRM/tool 全產品或完整方程式。
