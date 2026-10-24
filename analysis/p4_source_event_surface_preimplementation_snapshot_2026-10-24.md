# P4 來源事件 surface：產品改碼前的同起點快照

狀態：**source-only／fake provider 快照 PASS；回覆品質、真模型、Web／Safari 均未驗證**。本檔是 `research/p4_source_event_surface_diagnostic_plan_2026-10-24.md` 的入場證據，不改 f7d／f8 負結果或正式 holdout。執行時 HEAD `52f852fa46afaa749b71ffd533c937a8e512514d`，產品碼尚未改動；原 source freeze 10/10 SHA OK，新快照 source freeze 2/2 SHA OK。

## Before 和取得方式

f8 的真 M21 off/on 都選泛稱 `頑張ったね！`，原始候選有根據覆蓋皆 0/3，事前可見 gold 皆 FAIL。下一個診斷必須固定同一 *post-M21* 狀態，否則 surface off/on 的差異可能是 planner 重新抽樣。`test_p4_source_event_surface_diagnostic.py` 用題本三個固定 compact-schema 原始候選和 `_IsolatedContractBrain` 執行一次 fake-provider `cognitive_tick`；回傳剛好 1 次假 `create`，不載入 RightBrain 模型、不做 utterance／episode、無真 provider、正式 DB、Web 或 Safari 呼叫。捕捉完整 `logic+route_info`、來源 handoff、初始 memory／psyche／persona／RightBrain history。原件在 `0700` 私有暫存目錄的 `0600` JSON，不提交原文。

實際 route 為 `full_planner`／`completed_within_budget`，`fallback_used=false`；source utility 為 `no_grounded_candidate`，舊／新 index 均 0，選中 core `頑張ったね！`，正是事前要診斷的泛稱邊界。快照包含 83 個 logic top-level keys、2 個 route-info keys；不是只鎖三個原始 core。來源檔和原 fixture 未被變更。

## 可核數值

| 內容 | SHA-256／結果 |
|---|---|
| 固定初始 source/handoff/memory/psyche/persona/history canonical JSON | `d2a36b84a8e69b8461016641e477206a72a1e0ec4fdf75f0be4ae7bfe47af491` |
| 兩次重建後的 normalized post-M21 `logic+route_info` | `a1759ae06069fc608d9ebc0826e7a7b98bd236babc5bf39a5030b0a064ba8335`，相等 |
| 本次**原始** post-M21 `logic+route_info`、供 off/on 各 deep-copy | `4b2c6694fff4d7e44b992e5c41c79cde0177120ff4bd9a185d396f06d7ec1f32`，兩臂相等且原件不變 |
| fake M21 request arguments | `7ea80ae71e923d0d795dd710c2ef701c104d41ee3589460eb581d06be3857323` |
| 完整私有 JSON 檔 bytes | `74a72a10ab53fed34365697a7d73b1df7be3a7b3099014ae8710a7ad0e1fb16e` |
| source-only 相關測試 | `62 passed`、9 個既有相依套件警告、18.86 秒；其中本快照新測試 3 項 |

完整快照目前位於 `/private/var/folders/mz/rbx076rs3fndf_32r12qkszr0000gn/T/uruha-p4-surface-snapshot-0ksr7sic/preimplementation_full_snapshot.json`；暫存路徑不是耐久的 repo artifact，失去該檔時**不能**只憑本報告重建相同原始 SHA。`full_private_json_sha256=cf8e94ae8e565811b3e867430c9a40b66aa90e381b0a763127903333c075ece8` 是不含外層 hash wrapper 的 snapshot canonical JSON SHA，與上列檔案 bytes SHA 不同。對同次 off/on 比較要讀原始完整快照；normalized 投影只為跨重建檢查，移除了具名耗時及測試當下產生的 provisional timestamps，**絕不餵給 surface**。因原始資料含這些變動欄位，跨次原始 SHA 不宣稱重現；只能宣稱同次兩臂原始 bytes 相同。

命令：`.venv/product_checks/bin/python -m pytest -q test_p4_source_event_surface_diagnostic.py test_p4_source_event_core_utility_f7.py test_p4_source_event_core_utility_f7_route.py`；產品改碼前、且 HEAD 恰為上列基準時可用 `.venv/product_checks/bin/python test_p4_source_event_surface_diagnostic.py --capture` 另捕捉新私有快照。後者在 HEAD 漂移時故意拒絕，不能在產品碼改後偽稱 preimplementation capture。source SHA 核對用 `shasum -a 256 -c research/p4_source_event_surface_diagnostic_source_freeze_2026-10-24.sha256` 及同名 preimplementation snapshot freeze。

## 判定與下一步

本關卡只證明 deterministic comparison 的**初始資料等同**及 source freeze；0 真生成／0 Web／0 Safari／0 新產品行為。不能推斷最終日文保真、人格、用藥負控、圖或成本改善，更不能稱產品部署安全。下一步依凍結計畫在允許檔案實作唯一 opt-in 來源槽→deterministic surface treatment、同一 audit-only final check，先跑固定候選 off/on 和負控；只有 on-only final gold PASS 才允許一次新 M21，之後條件式另一題 Safari。任何 fail 保留，不改題、gold、baseline 或這份快照。
