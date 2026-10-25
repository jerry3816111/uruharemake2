# P4 B 真私有 zero-turn 前瞻修正 1：canonical model root

狀態：首次真執行失敗後、任何第二次真資源啟動前凍結。失敗原件與數據見 `analysis/p4_b_private_zero_turn_first_real_presend_failure_2026-10-25.md`；不得把舊結果重判 PASS 或復用舊 root。

## Before 與單一變因

已提交 `11d4b53` 的 helper 在 macOS 建 `/var/...` alias；現有 controller/binding 對 private root 強制 `path.resolve(strict=True) == path`，所以在 child Popen 前拒絕。唯一核心變因是：**新建 model root 後立即解析成 canonical absolute path，往後 clone、callback、daemon env、descriptor 與 controller 只傳同一 canonical path**。不放寬 `_exact_private_directory`、不改 controller、receipt、Web、Brain、ledger、模型、A/B 題、正式資料或任何 Send gate。

允許改 `p4_b_private_zero_turn_operator.py` 單一 root 建立位置、`test_p4_b_private_zero_turn_operator.py` 的 symlink-alias regression，以及本計畫、結果、`CURRENT_TASK.md`。源碼修正前先核單元紅色（alias private root 的 controller 安全檢查拒絕），修正後 same test 綠色。應核：callback/root、`OLLAMA_MODELS`、descriptor `private_root` 均用 canonical 值，原 alias 不被寫成另一個身份。測試只用 fake/temp 樹，不啟 daemon/child、不碰正式 DB；執行聚焦測試與既有 controller/binding 相鄰測試、compile、diff。

## 真實再驗與停損

修正與相鄰測試、獨立只讀審查、scoped commit/push/PR exact head 都通過後，依原 `p4_b_private_zero_turn_resource_plan_2026-10-25.md` 的資源／身份門檻，只用**全新** 0700 model root、全新 prepared product root、單 daemon、單 runner、單 controller start，做一次 zero-turn；不復用 `/var/.../uruha-p4-b-zero-568srdlo` 或 `uruha-product-td8ognnp`。先核 11455/7894 無 listener、11434 原身份、≥20 GiB、固定 source/model/ONNX SHA。成功只可報真 child same-PID HTTP ready 和 planned stop、可觀測成本；對 B Send 完全不授權。任何新的失敗按原狀保留，不在同 root 重試；至多兩個有根據修正批次，不能為追 PASS 無限補規則。

超時目標仍是觀察停損線，非硬 watchdog；daemon/runner cleanup 若回 `identity_drift_no_kill`，即使事後 PID/port 空，也要列 review，不能冒稱 exact planned stop。`prewarm=False` 且無 active DB/turn-admission 收據的既有邊界不變：此 zero-turn 即使 child ready 也不證真 child Brain/SDK、全域 0 completion 或 B gate counter。B token oracle、M21 terminal、Safari click→DOM 20 秒、A 作者核准與真 A 都維持 pending。
