# P4 B：合成 sandbox PASS 後的真產品放行審查

狀態：**只讀設計／證據審查；GO 僅下一個來源閉包盤點，NO-GO 第四次真 Ollama、B Send、Safari。** `analysis/p4_b_child_local_fixture_v2_first_sandbox_result_2026-10-26.md` 只證兩個受控 Python listener 的新 adapter 在該 profile 下可見；原第三次真 Ollama 的 `process_generation_unavailable`／`REVIEW_REQUIRED`、原兩個修正批次失敗、正式 A/B 與人評 gate 均不改判。本卡不授權模型冷啟、provider 或新的外部副作用。

## 從替身到產品的缺口，不用一個 PASS 抹平

| 層 | 已核證 | 尚缺／此刻判定 |
|---|---|---|
| B zero-turn identity source | 16 個列名安全關鍵 repo 檔在 controller HEAD snapshot 與 receipt v4 SHA 雙綁；v2 替身同 observer 正負控成立 | 16 檔是**列名窄路徑**，不是 transitive Web import／Brain／B Send 閉包。入口仍 import `uruha_web_ui_product_p4_question_evidence.py`、四個 `install_*` overlay，`uruha_web_ui.py` import `uruha_brain_mac.py`；至少這些未在 16 檔表。缺漏為非零，真 B 不放行 |
| 真 Ollama 身分等價 | child 的 raw OS observer 在合成 Python 程序可讀；零輪 fake child→Web→SDK 契約 completion POST=0 | fake chain 刻意 mock `_inspect_live_identity` 及 Brain。真 daemon／runner 的 exec+argv digest、`serve`／model/host/port/offline/no-jinja/chat-template flags、PPID、`OLLAMA_MODELS`／`OLLAMA_NO_CLOUD`、唯一 listener、binary/model SHA、雙 raw 夾核與清理尚未在修正後真輪驗。不能以替身判定真 Ollama 已修 |
| 每輪生成／token | opt-in `P4BResourceGate` 的 fake 32/32 證明可攔第二個 M21；ledger 在 create 前後呼叫 revalidate | 真 child 的 `prompt_token_upper_bound` 預設 None；P2 轉換後請求需可靠 upper bound ≤1744，因 `max_tokens=256`、總 cap 2000。M21 寬 fallback／其他 LeftBrain、native、RightBrain 路徑還需 terminal fail-closed／effect closure；不得以事後 ledger 當送前硬界 |
| 延遲與成本 | 真第三次 zero-turn 262.7400s（約 240s 等 ready）、clone 4,683,088,190B、helper 3 次模型 SHA 下界 14,049,264,570B；快取條件 4 次 `_model_store` 讀 4,683,073,952B GGUF 實測 9.301121s wall／43,925,504B max RSS | 現每 create 前後 identity 雙核，每 `_inspect_live_identity` 又雙 SHA，至少 18,732,295,808B ≈18.73GB 邏輯讀。9.301s 是 cache microbenchmark，不含排隊、生成、postprocess、DOM；20s Safari click→DOM 尚無可承諾硬界。第三次 262.74s 不是正常對話延遲，full RSS/cost 未儀表化 |
| A/B 與人評 | 合成機制與產品管線部分 fake contracts 留存 | 作者自然日文／人格／非照抄三項真評及外部 0600 receipt、真 A on-only gold、兩個真 ready roots 未滿；B 題 0 Send。正式 temporal／人類反應方程式證據不因此增加 |

## 下一個單一必要交付：B0 來源／effect 閉包盤點

在**不改產品碼、不 import 執行入口、不啟模型／Web／Safari**下，沿固定產品 entry 的 `bootstrap → _prior/overlays → base Web → Brain/SDK → provider create` 做靜態／只讀 import、call、effect 盤點。逐入口列出會決定 zero-turn side effect、身份、M21 准入及 B Send 生成／tool/writeback 的 repo 檔與函式，分類 `bound`、`not applicable + reason`、`missing`；區分「import-time 0 provider」和「turn-time completion」兩條。至少把上表已知缺漏逐一納入或明確說明不適用，不以動態 `rg` 命中數或只列 16 個檔稱完整。保留 controller HEAD snapshot／child receipt／pre-create revalidation 的時序圖，指出可被 source drift 影響的兩段間隙。此盤點可誠實留下具名 `missing`；交付後才可**前瞻**決定最小 source-lock 改碼範圍與假負控，改碼前另審單一變因與安全成本。改碼及負控通過後，相關缺漏為零才談真輪審查。

真第四次 zero-turn 的獨立放行仍需：上述 zero-turn 必要來源/effect closure、真 daemon/runner 等價的 pre-Web／pre-create 明確 oracle、fresh roots/PIDs/ports、共用 11434 不受影響、model/binary SHA 與 cleanup、冷啟／revalidation 成本及 20s 風險、兩批修正已用完後的重大設計審查。即使 zero-turn ready，也**不能**直接 B Send；後者另需轉換後 token upper-bound oracle、所有生成 chokepoint terminal fail-closed、非 B 題 0-provider Safari queue/lock/stall/late-result watchdog、A 作者真評與真 A、同一 browser T0→DOM T1 ≤20s。任何一項缺失，維持 B no Send；不改弱 baseline、限額或先前 frozen 結果追分。

審查方法：本輪讀既有結果／原碼，無模型、Web、Safari、資料寫入。合成 0.415383s 不外推為真模型 latency；新增這份審查不算一個新 M 或能力提升。若來源盤點顯示 Web/Brain transitive closure 不可控或 18.73GB/create／20s 無法同時滿足，允許保留 B 安全常閉並以負結果收斂，不無限追加支援工程。
