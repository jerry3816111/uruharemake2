# P4 selected food-offer action：首次凍結 Safari 產品批次 T1 runtime abort

狀態：2026-10-17，**整批 strict FAIL／未取得語義驗收，不是修正成功**。凍結前 commit `f622cdce46675a0b378bd690acb173e1372dbfa5`、既有 PR #435；新 manifest 8/8、所依賴舊 manifest 21/21 OK。六句/gold/程式凍結原件不改。零模型聚焦 7/7、相鄰 73/73（8 warnings）只證契約與回歸，不能替代本批。

## 一次真 Safari 觀察

- 全新隔離 root `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-product-re4aaj3d`（0700），run `c32498d784e6261d`，final Python PID `22274`，新 Safari 第 8 分頁 session `20261017_130102_573fa441`。`verify-ready` 在啟動 race 後，對**同一次 run**證明同 PID 單一 loopback `127.0.0.1:7894` listener 與 HTTP 200；此為可啟動，不是可完成對話。
- T1 唯一送出逐字 `胡椒ポテト、一口いる？`，Safari 真泡泡先顯示 `...`、狀態 `thinking`。20.216 秒仍無回覆，已超事前 ≤20 秒門檻；約 37.838 秒時 UI 出現「錯誤」，仍沒有可見最終日文、graph selected/verify/utterance 也未形成。T2–T6 **未送**，不算 5 次失敗答案，整批因 T1 產品 runtime abort strict FAIL；不得重播本六題或把 T1 當「未曝光」。
- `stderr` 真堆疊：`MemoryManager.get_runtime_snapshot`→`_procedural_summary`→Chroma `collection.query`→`ONNXMiniLM_L6_V2._download_model_if_not_exists`→`httpx.ReadTimeout`。錯誤後**當時觀察**隔離 HOME archive 為 30,412,800-byte 部分下載；稍後同 root 內另一載入工作把 archive 完整下載／解壓，停機後 SHA256 為 `913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3`。這表示失敗不是永久沒有資產，較精確的是首次 query 尚未具備 ready cache、並發／網路載入期間出現 timeout；不能據此假稱 offer-action 表面機制有語義正負結果。host 既有 archive 的 SHA256 亦與 Chroma 套件宣告相符；是否／如何安全地供給**全新**隔離 root 須另行前置檢查，不能改本批資料追分。
- 隔離 DB row-ID 快照：T0 `db_status=absent`、profile `[]`、episode `[]`；T1 錯誤後 `db_status=present`、profile `[]`、episode `[]`。無事實性長期偏好寫入的證據僅限此隔離 root。服務按計畫 `stop`：原 PID exited、port vacant；root/raw 留存，舊 Safari 分頁沒有關閉。

## 原始證據完整性與下一步

保留 root 檔案：`p4_preference_fallback_detached.c32498d784e6261d.stderr.log` SHA256 `2f98b16ad44c5cafcad9b054cd01d092853df417379eb1c20bc1185ba1f32684`；同名 `.stdout.log` `870c33e1a1d02fa49d76c98c2ff92f361c1d14a52bf0c728744cadf0f323d67c`；`evidence/snapshot-t0_before.json` `c44b5360b871eff80422c0485edd4f4f7aca3bbc812158774eafe6b9b06a6f17`；`evidence/snapshot-t1_after_error.json` `95ec4edfe4fef6795e850ea6ddb70984b98f01a09a6f92030ea71c9c942b9599`。這些 hash 只指向現存本機隔離原件，不把敏感 raw 對話複製進 Git。

下一個必要交付是**新批次前的可重現 embedding-cache readiness**：先對全新 0-turn／已停、無 episode/profile 的隔離 root，核對本機 archive 官方 hash 並於 root 內離線供應與載入；做不含 prompt 的 embedding preflight，且記資產來源、容量與啟動延遲。若仍失敗，保留新的程序 FAIL；若通過，再凍結**全新**未曝光題與金標並首輪前 commit/manifest，真 Safari 驗收。不可因 cache 修好便宣稱本次 T1 或原已曝光六輪 PASS。長期研究同模型對照、人評與 temporal holdout 全部仍 pending。
