# P4 B synthetic fixture v2：一次性真沙盒預檢凍結

狀態：**前瞻 source/input/oracle 凍結候選，待獨立執行前審查與 commit/push/PR exact head；目前 NO-GO `--execute`。** 這是已曝光 v1 fixture failure 的工程診斷，非 formal holdout、非第四次真 Ollama。原 v1 唯一結果及 source/input/oracle 不改、不重跑；任何 v2 FAIL／invalid 原樣保留，v2 也 0 retry。

## 精確來源與輸入

- 安全 worktree／既有 branch；命令唯一為 `.venv/product_checks/bin/python p4_b_child_local_identity_fixture_v2_preflight.py --execute`。新 sibling A/B 與新 worker group；不得借舊 PID／port／model root；0 Ollama、0 Web、0 B Send、0 正式 DB。
- 新 standalone script SHA-256 `7d342a31b58a79c456ef35cdaa934a50b6a6c0b4b0d4373051fc9976fae10429`；新 fake test `25b392ef5ffff08ec22fb8d448278b5f2a3701104a0e07616ef58c971a148111`；實際 adapter `e523b65add5ce75a7fdcad9524266ebe497d70e5e1899dcc3925ecf4cdd89200`。舊 v1 script `ae2dc4642b7d02aa1113d70d8e163c9817714f5566d378ed9c533640ecccb8c1`、test `66fc12e82418105ea2e76a7edcfa3894139dc7fb91d7e7fbfca9fef6cabf5acd`，只比對、不執行。
- 凍結設計／前置：`research/p4_b_child_local_fixture_oracle_review_2026-10-26.md` SHA `4c56161ac44a1dc52930a8cbc09cd4a54afb2bf910e68bf7fb030ca5df54de5d`；`research/p4_b_child_local_fixture_v2_implementation_freeze_2026-10-26.md` SHA `6c4a752b6e7c9e7eab98992c9a73b9f68695b056fc65d1993f9aa5ff75a835bc`；舊失敗報告 SHA `4000a6b86729700c6b3f4fb6413ab6937566b256200ecefcda66aa1b83b1c373`。
- Profile 路徑固定 `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-xremdzdp/p4_preference_fallback_detached.6a0185bb8bc10e98.sandbox.sb`，SHA `5f759a54cfc12a5e68fb73590f585f4dee9ac9f55d50c44338f5e164684e6110`。缺失／不符則在啟程序前 invalid，不選新 profile。
- OS App binary 固定 `/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python`，SHA `93d04da16de15e537a76fa1278accf982dd35ff1107e06460433315512eb381f`、lstat uid0／regular nlink1／本機 inode889937。venv 發動的 `.venv/product_checks/bin/python` 為 uid501／inode37200054 的 symlink，readlink `python3.12`；下一層 `python3.12` 為 uid501／inode37200053 的 symlink，readlink `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12`；terminal binary lstat uid0／regular nlink1／本機 inode889709，SHA `d4f152f2a753c94e0e7935c8ebbe6b2609979e1df7898422b577d0076383d08b`。OS App 與 venv terminal **不是同一檔**。變動不自動接受，先審查／重新凍結，不用本次觀察反選 expected。
- 凍結 profile、App、venv、script/test/adapter 等 SHA 必須在實跑緊前唯讀重核且 PR #435 `headRefOid` 必須等於當前本項提交 HEAD。任一不符＝0 啟動／記 invalid；不能以舊 `c1bf851` 在後續 commit 已推時冒充 exact head。實跑後再核不變。

## 成功、失敗與資源 oracle

`schema=p4_b_child_local_adapter_sandbox_preflight_v2`。fixture A/B 每個保存 7 個固定、無敏感字串布林；六權威必須 true，`legacy_symlink_exact` 只記診斷。OS executable 與 argv0 必須是上述事前 App exact path／SHA，argv tail 必須 exact script 與 `--listen-a|b`、argc=3；raw 初次／snapshot／重讀三方相同，PPID、env 單值與 loopback listener 皆必須正確。失敗保留可得 A/B per-bit、不顯示 raw argv/env，不啟後續 observer。

同一 sandbox observer PID 的 positive 10/10 全 true；B SIGTERM/reap 後 negative A5 全 true／B5 全 false，`negative_rejected=true`、`same_observer=true`、`cleanup_verified=true`、B exit -SIGTERM、observer exit 0 或受監督 -SIGTERM、worker 受監督 -SIGTERM、shell exit 0、模型／Web/B Send 計數 0，才是窄義 `adapter_visibility_feasible`。active ≤30 秒；worker 與 supervisor 的 cleanup 各有 10 秒硬截止，`total_wall_s <= active_wall_s + 10.1` 只是 v1 沿用的報告四捨五入／排程容差，不是多給 0.1 秒清理權。留 raw JSON、shell exit、工具 wall、script/test/adapter/profile/anchor SHA、per-bit／矩陣與 cleanup。失敗／timeout／身份飄移保留原樣，**不以修 oracle 再跑 v2 追綠**。不得保存 PID、argv/env 原文、聊天或私人資料於公開結果。

預執行測試固定為 `.venv/product_checks/bin/python -m pytest -q test_p4_b_private_zero_turn_operator.py test_p4_b_private_controller_seam.py test_p4_b_private_endpoint_binding.py test_p4_b_private_child_bootstrap.py test_p4_b_private_child_chain_zero_provider.py test_p4_b_child_local_identity.py test_p4_b_child_local_identity_sandbox_preflight.py test_p4_b_child_local_identity_fixture_v2_preflight.py`，再核相鄰四檔、compile、diff。第一次聚焦 284/284、相鄰 65/65 是 source/fake 層，不預告實跑 outcome。獨立審查未放行前只許 read-only SHA/status/PR 核對。第四次真 Ollama、B Send、Safari 及正式 comparison 全 NO-GO；本輪不能聲稱 B 已修好。
