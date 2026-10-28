# P4 f7：Safari 送出前 admission 失敗，0 Send

狀態：**strict FAIL（pre-Send admission gate），沒有 fresh 生成模型回覆／可見品質結果**。f7 的單一變因產品碼與零模型測試已在 `3ef6a55f4d5b5f04c294220864ffa65b36b5d271` 推至 PR #435；主項 60/60、隔離負向路由 3/3、受影響回歸 220/220 通過，只證明有限契約和接線。事前凍結的 `初めて自分で庭のベンチを塗り直した。今は一言だけ励まして。` 曾在原生 Safari 新分頁預填，**沒有按 Send、沒有重試**。因此不存在 f7 的模型回覆、human-turn graph、episode、候選集或最終 utterance；不得判定來源效用被真輪操弄，也不得宣稱產品品質改善。

## 原件、時序與停止

- 只使用全新私有 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-l4685av5`，port 7934。zero-turn rehearsal run `e527d01f41221c53`／PID 45950 同 PID ready 後 planned stop；正式 run `3f3cd74884417b9e`／PID 46244 同 PID ready。正式 session `20261024_082327_bcdd3f3a`，active DB 始終是隔離的 `memory_db`；沒有碰正式 DB、原始 dirty checkout 或無關 `output/graduate_application_report/`。
- 0600+fsync 快照 `evidence/db-t0.json` SHA-256 `bef01dd6929684cfabbafca221ffeb0f64284806bec417525ce8c9982bba15e5`；預填後 `evidence/db-tpre.json` SHA-256 `de1000151bbf976f8da72eb7fe8d679a45c271ac45b252d2eb5ad8f986241269`。兩者同 PID/session、`reset_generation=0`、`autonomous_tick_index=0`、`human_submission_finish_count=0`，唯一 `memory_db/chroma.sqlite3` 176128 bytes、SHA-256 `ab58c9ac9b3737ab0d067f463cfd2d5fbc5a15834559deb6c7516c3fc441e307`。Tpre journal 8 筆，即 4 組完整背景 start/end。
- 凍結門檻要求 Tpre→human arrival ≤10 秒且無背景交錯。Tpre 結束 monotonic `1801383935284333`；下一個背景 `sequence=9 background_start` 在 `1801386783485666`，僅 **2.848201333 秒**後。此時因執行額度中斷，未有 Send/click 或 human arrival；恢復工作時已過數小時，兩項 admission 條件確定無法成立。沒有用背景 0 DB write 抵銷「無 interleave」硬門檻，也沒有把原題改名或換 root 重試。
- 恢復後保存 `evidence/db-tpost.json` SHA-256 `31b0cf4b5ab9b0d5137b0c3a58a6ffaf0ff1afcb4f2f0e2cf2d3f7604d610cf6`；兩快照 `monotonic_end_ns` 之差 **12378.120186083 秒**。journal 最終 SHA-256 `b667f9774d71107abd5bd4276e4b9ce760599c0be25bf32c4535fdae6b06c299`，2412 筆＝1206 組背景 start/end、**0 human event**；end 為 605 `idle_noop`、601 `completed`。背景帳本合計 3005 次 `get/query` vector-store operation、0 reported memory write、0 returned vector mutation、0 generation token；journal `error_type` 與 vector mutation error 均為 0。Tpost tick 601，但隔離 DB 檔案 SHA 與 T0/Tpre 相同；這不代表記憶體內狀態完全不變，也不是 user-turn 成本。
- 原生 Safari 只關本次新開且未送出的 7934 分頁（53→52），未關原先頁面；沒有保存 native PNG/AX，故 visual gate 未測。正式 stop receipt SHA-256 `6986dd0b3e261b9492ada1022d27588032610349dd18b0325ae12a6c2d3201bb` 記錄 PID 46244 `original_pid_exited=true`、`planned_stop=true`、7934 `port_vacant=true`。Web 對話 log 無檔。

## 判定與後續

f7 目前是**零模型機制 PASS、真產品未測且本次 Safari strict FAIL**。沒有可與 f6 或強 LLM 比較的 f7 可見回答；正式 temporal holdout、人評、VRM/Function Calling 與完整 Goal 仍 pending。下一次若要測來源事件效用，必須事前凍結**新的 source-disjoint 題與 gold**，先完成靜態核對、選背景 pair 結束後 Tpre→立即一次 Send，再以 journal 硬判；不得重送本題追分或放寬 ≤10 秒／無 interleave 條件。若真輪候選全泛稱或 surface 漏事件，依原 f7 設計保留負結果並單變因定位。
