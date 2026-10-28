# P4 B：送前單 M21 生成門控（零模型工程結果）

狀態：**狹義機械門控 PASS；B 真入口仍 REVIEW_REQUIRED／不可 Safari Send。** 本批依先推送的 `research/p4_b_hard_cap_presend_review_2026-10-25.md` 做第一個獨立必要工程增量；不更動原 A/B 題、gold、模型、人格、記憶、Web、正式資料或已凍結門檻，也不新增 M。起點 `305da2b`，原 safe worktree tracked clean，僅有無關未追蹤 `output/graduate_application_report/`，未碰原始 dirty checkout。

## Before 與唯一改動

Before：`uruha_compute_ledger.py` 的 OpenAI-compatible proxy 只有 `target.create` 回來後的帳本紀錄；單次 Web 輪次內第 2 次生成、額外 `stream`／`n`、缺事前 token 上界均無送前攔截。M31 native 和 RightBrain local 亦在生成後記錄。原 B 成功路由只允許 **1 M21 + 0 RightBrain + 0 repair + 0 retry**，所以不能把外層 ≤3 completed generations 解讀成可用 3 次。現行 Web 另只有送達後的 ≤20s `target_met`，不屬本批改動。

After：新增 `uruha_p4_b_resource_gate.py`，只有明確注入 `ComputeLedger(p4_b_resource_gate=...)` 才啟動；預設 `ComputeLedger()` 與 A runner 不變。P2 compact 的 inner ledger proxy 在**轉換後、真正 `target.create` 前**核 stage、model、2-message shape、`response_format` JSON Schema、唯一 kwargs keyset、20s timeout、256 output cap 及 prompt-token 上界；只准首個 M21 attempt，其餘 stage／第 2 次／native M31／RightBrain local 在模型入口前常閉。無上界 callback、非法上界、`bound+256>2000` 也不送。counter 接收 deep copy，不得改真請求；返回後核實實際 usage 與事前上界／256／2000，失敗保留 raw-free terminal 狀態。**callback 目前只是測試注入，不是經核 Ollama tokenizer 的生產證書，真 Web child 沒有注入此 gate。**

一個可重核的局部前後差異：同一 fake client 於預設 ledger 呼叫 2 次，target 實際收到 **2** 次；有 gate 的首個 M21 呼叫後，第二個 attempt 被拒，target 只收到 **1** 次，拒絕計數 **1**。`stream=True`、`n=4`、`tools`、額外 `max_completion_tokens`、錯 model／stage/schema/timeout、缺 usage、超上界等負控均不能被錯認為合法路徑。這是測試夾具，不是正式模型成本節省量。

## 驗證分層

- 聚焦零 provider：`test_p4_b_resource_gate_zero_model.py` **32/32 passed**；含 P2 `_Proxy`→instrumented ledger 的真 wrapper 次序正／負控、平行 attempt 原子性、native/local 繞道、default off、callback 不可改 request、實際 usage drift。獨立只讀審查先抓到 `stream/n/tools` 欄位漏鎖，修後再審，未見此狹義增量的新生成繞道。
- 七檔受影響零模型相鄰：`.venv/product_checks/bin/python -m pytest -q test_compact_planner_p2.py test_p4_product_turn_compute_receipt.py test_p3_complete_product_compute_accounting.py test_p4_source_event_surface_diagnostic.py test_p4_source_event_surface_diagnostic_route.py test_p4_source_event_exact_input_web_boundary.py test_p4_b_resource_gate_zero_model.py` → **124 passed／1 skipped／2 xfailed**。兩個 xfail 是既有安全反例，沒有當作成功。
- A runner 因前述跨檔環境污染分 process 執行：`test_p4_source_event_surface_exact_input_fresh_a.py` **23/23 passed**；`test_persona_policy_compute_seam_v1.py` **17/17 passed**。曾在同一 pytest process 合跑看到 A 測試失敗；不含本批新測的既有 persona 模組 import-time `os.environ.setdefault("URUHA_SKIP_AUTO_VENV", "1")` 也會觸發 A 對 ambient `URUHA_` 的拒絕，故不是本批 gate 的新退步，亦**不**宣稱混合單進程套件全綠。正式 A 0 次。
- 四檔 `py_compile` 與 `git diff --check` 過；本批 **0 真 provider generation、0 Safari、0 正式 DB write**。圖像化及 Safari 驗收均未做：沒有真 B 成功輪次，不能用 fake 圖替代。

獨立零生成 tokenizer 可行性核對（與本批代碼 gate 分開）：本機 Ollama `0.34.4`、Qwen manifest `845dbda0…b697e`；只送非 B 句 `Tokenizer fixture only.` 到 `/v1/chat/completions` 並設 `_debug_render_only=true`，回 rendered Qwen prompt、usage 三欄皆 0、空內容。Ollama-owned runner 對同 prompt `/tokenize`（`add_special=false, parse_special=true`）得到 **33 tokens**；其暫時 port 不作固定依賴。這只證 render/tokenize 通道可行，**未證 B 實際 transformed request 的 prompt bytes／模板分支／token 上界**，不能把 33 或 HF 估算當 B 的 ≤2000 硬界。

## 歸因、失敗邊界與下一步

本批對「人類反應方程式」的貢獻是提高未來產品實驗的**成本可歸因與防額外生成能力**；沒有增加語用理解、記憶或自然日文回答品質，也沒有證明優於強 LLM。原 P4 B 三個 hard-cap 項中只建好未綁產品的單 M21 機械攔截，token 真上界與 click→DOM 20s deadline 均 pending。即使未來綁進 child，也須在 turn terminal 檢 gate 狀態，因現有 M21 broad fallback 可能吞例外；不能把 gate 單元測試說成錯答不顯示或 no-write transaction。

下一必要工程：只在同版 0.34.4／凍結模型／實際 B transformed request bytes 上完成零生成 prompt-render/tokenizer parity，產出可靠上界；再前瞻綁 opt-in child、turn terminal 檢查與非 B 題 Safari deadline 故障注入。A 作者自然日文／人格／不過度直抄三項真評分及外部 0600 receipt 仍缺，A 真 off/on 一次性條件未執行；只有 A on-only final visible gold PASS 且 B 送前三項機制證據全過，才可考慮 B 唯一 Safari Send。正式公平比較、人評、temporal holdout、P4／Goal 完成均 pending。

送後只讀補核：Ollama 0.34.4 的非 B、兩訊息 fixture 在有／無 JSON Schema 時 rendered prompt 一致，同 runner tokenizer 為 **36 tokens**；這仍不是 B 的上界。更關鍵的是共用 daemon 的 tag／runner／模板可在「render→tokenize→真請求」間變動，前後各一次 SHA 並非原子身份保證。後續 oracle 設計要先解此 TOCTOU（如受控隔離 daemon／等價綁定），否則即使 fixture 36-token 一致也維持常閉；不得為省事把 debug usage=0 當 prompt tokens。該補核 0 generation／0 B 題／0 Safari。
