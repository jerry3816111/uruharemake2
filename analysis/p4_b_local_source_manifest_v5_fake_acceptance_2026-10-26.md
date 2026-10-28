# P4-B 本地來源摘要 v5：零模型驗收

狀態：**source/fake＋提交後 committed HEAD snapshot 局部 PASS；真 Ollama、B Send、Web／Safari NO-GO。** 改碼前設計 `research/p4_b_local_source_manifest_v5_design_freeze_2026-10-26.md` 與 implementation freeze 已由兩條獨立只讀審查、先推 PR #435 exact head（`d281918ce95b3468ecc619b0b9012343e3888bf5`），沒有為測試結果改 gold digest、題本或歷史 v4／v1／v2 原件。

本次單一變因是 B child 本地產品來源綁定：原 controller/receipt 只列名 16 個安全檔，固定 entry 的 208 root 本地 Python 裡只有 9 個落在該名單。v5 保守清單為 **230 Python（208 root＋21 個本地 package＋新 helper）與兩個明列資產＝232 個 manifest 路徑**；再和原 16 去重，controller HEAD snapshot **239 個檔**。不是全 repo／第三方／全部 runtime effect 閉包。helper 以 frozen 檔名摘要 `cd9f04bf...` 守集合；每個 `name→SHA256(bytes)` 進 canonical JSON 摘要，v5 receipt 新增此 aggregate 與 helper 自身 SHA。child 在 pre-Web 與原雙 pre-create 路徑每次重核，v4 receipt 在 v5 新路徑拒絕。

controller 從逐檔 `git show` 改為一次 bounded `git archive`；串流讀取上限 16 MiB／15 秒，tar 僅允許精確 239 regular files 與三個預期 parent directory；live bytes 也用 owner/regular/no-follow/fstat＋每檔 16 MiB 上限核對。任何缺檔、額外/重複/非 regular 成員、內容漂移、超量／逾時都在 child 前 fail-closed。正常非 B 對話入口不使用這個 B snapshot。

驗收證據：

- 改前 controller 聚焦 18/18；v5 receipt 新斷言在舊碼 red 2 failed，改後 agent 25/25 targeted 與三指定檔 157/157；helper 新檔 17/17。主代理整合五檔 **197/197 passed（227.59s）**，改完 controller bounded live read 後受影響 helper/controller/ledger/identity 四檔 **68/68 passed（38.04s）**。相鄰兩檔 **26/26 passed**、9 個既有第三方 warnings；所有改檔 `py_compile`、`git diff --check` 過。
- `test_p4_b_private_identity_preflight.py` 是 implementation freeze 的錯檔名，第一次相鄰命令 exit 4、**no tests ran**；改用實際 `test_p4_b_isolated_ollama_identity_probe.py` 加 `test_p4_b_private_web_ledger_seam.py` 才取得 26/26。這不是產品退步，也不假稱原命令通過。
- WIP helper 尚未提交時，真 `_b_committed_source_snapshot()` 正確拒絕 `p4_b_committed_source_unavailable`；不可用 WIP 為真來源已綁的證據。source helper 唯讀試算 232 paths／約 0.803s；舊 16 snapshot 約 0.169s，舊 208 root 單 Git archive 約 0.105s，229＋2 archive 約 0.060849s／5,396,480B，皆是快取／局部讀取，不是 child 或 Safari 20 秒。
- scoped source/fake commit `9c7e5ce49d924abdcf4fc78b8f5951fce5bc42cd` 推 PR #435 OPEN/exact head 後，才唯讀呼叫一次真 `_b_committed_source_snapshot()`：**239/239 files**，helper、Brain、工具與兩資產均存在；archive **5,601,280 bytes／0.109487s**，整個 snapshot **0.915707s**，sorted-name digest `c22bda44f1b76938c3b0a60c0e73a8999d1dd036c1b8363f34b86672d437a080`，exit0。這是單次本機 cache 成本，不是反覆 pre-create、真模型 SHA 或使用者可見延遲；和舊 16 檔 0.169s 的差值只供規模參考，不是受控性能比較。
- 獨立只讀 source/fake 審查 GO 僅 scoped commit。安全差異掃描 ID `6de6d9cc-04e8-4aef-9eaa-93cd72e59d37` 對較早 WIP snapshot 為 **0 reportable、coverage partial**，包含無關 user output 的掃描快照已被排除於本項結論；掃描後 bounded live-read 微調由人工再審 GO，**不**把過期掃描稱為最新完整掃描 PASS。

這只證本地來源集合及變更檢查在零模型契約下連通，不能保證外部 OpenAI/Chroma/Gradio 套件、其他資產、`.env`、動態效果、同 UID 惡意競態或實際 HTTP 出口被控制。每次 pre-create 重核增加 CPU/IO，沒有拿小測時間當全端 20 秒；原第三次真零輪 `REVIEW_REQUIRED`、B token 上界、真身份與 A 作者評仍 pending，**第四次真 Ollama／B Send／Safari 不放行**。正式 DB、原始 dirty checkout、無關 output 均未觸碰。
