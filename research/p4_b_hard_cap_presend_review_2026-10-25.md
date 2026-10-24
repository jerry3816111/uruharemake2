# P4 B 送前資源／等待硬界：前瞻設計審查

狀態：**REVIEW_REQUIRED；不是 B 放行、不是對既有凍結實驗的事後修訂。** 本卡只處理原協定第 3 階段的送前安全缺口；A 固定題、真人作者核、off/on 比較、B 題與 gold、模型及原門檻均不改。A 真生成與 B Safari Send 目前都是 0。若 A 未取得作者三項評分及外部私有 receipt，或 A on-only final visible gold 未通過，即使本卡工程全過，仍不得進 B。

## 修改前證據與反例

原協定 `research/p4_source_event_surface_diagnostic_plan_2026-10-24.md` 將 B 的 1 次 Safari Send／0 retry、≤3 completed generations、≤2000 provider tokens、≤20s user wait 稱為硬安全上限，且原允許檔不含 Web／ledger／DB；要改它們須先設計審查。`uruha_compute_ledger.py` 的 OpenAI proxy 於 `create` **返回後**記錄，native Ollama 與 RightBrain 也在呼叫後記錄。其 `generative_token_accounting_complete` 是事後稽核，不會阻止第 2 次或超預算請求。P2 compact proxy 先把 M21 request 變成 JSON Schema 與 `max_tokens=256`，其下層 ledger proxy 才看到實際 request；其他 LeftBrain 呼叫、M31 native 路徑和 RightBrain 本機生成不能靠只包 M21 防繞道。

Web `uruha_web_ui.py` 的文字事件先顯示 `...`，然後在 `RUNTIME._lock` 內同步跑完整 `brain.run_turn_debug`；之後逐片 yield、最末才 `_finalize_surface_delivery` 計算 `target_met`。目前的 planner `timeout=20` 僅約束其中一個模型請求，並未包括 queue、鎖、brain load、後處理、TTS、串流和瀏覽器到達；`target_met=false` 也發生於成本／時間已付之後。因此「單次 timeout＋事後 FAIL」不能稱三項送前硬保證。現有 product compute receipt 與 B 的 1 M21／0 RightBrain／0 repair 判準保留為事後獨立查核。

修改前檔案 SHA-256：`uruha_compute_ledger.py` `61bea2c30434105265fc9be04d756514aa6183b69d3982d0476c02062445c87c`；`uruha_brain_mac.py` `082deb16bfd33075515637f770b528445cd53bb2e6bfceb5ef900acfd1275f51`；`uruha_compact_planner_p2.py` `52c8ff789fabd4c0cbbaa823aa45db725d7d08a5791c2c1660c5698ed94b455c`；`uruha_web_ui.py` `10bfea36200b2af51926501a5aac80bd08ddade27111335a28b8381afc6f2ec3`；P4 controller `c9d460e1767e4dfd7f56b7d68bad975d29ebe87b255c14ca75d3a02fedff0c52`。以 `git` tracked blob 與前瞻差異核對，不重寫既有負例。

## 最小執行分解（非新增 M、非增加實驗變因）

1. **生成／token 送前 admission**：僅新的隔離 B child opt-in，從 browser-bound 已授權 input 的單一 turn 建立原子 quota；default 與 A 完全不變。真正 provider chokepoint 需看見 P2 **轉換後**的 M21 request。原 B 成功條件已是 **1 次 M21、0 RightBrain、0 repair、0 retry**；故此診斷的送前 gate 比原「≤3 completed」上限更保守：只准**首個** `leftbrain_general_plan` M21 attempt，任何其他或第二次生成在 provider／local generate 前 terminal FAIL，不把 ≤3 誤當可用三次的額度。該首個 request 的可靠 prompt-token 上界 + 明確 `max_tokens=256` >2000、缺 cap 或任何身份漂移，同樣事前拒絕。事後另驗原 ≤3 completed／≤2000 實際 usage 與 1 M21／0 其他生成；provider 缺 usage 視為 FAIL，不能因 ledger 恰好少記一次就視為低成本。背景／其他 session 不能共用或繞過此 gate；無法證明隔離即禁止 B。
2. **token 計數的真實身份**：固定 Ollama `0.34.4`、`qwen2.5:7b` manifest `845dbda0…b697e`、GGUF、system 與實際模板 SHA；不得拿 HF tokenizer 估算或 Ollama 0.33.3 的有限 P3 parity 當 B 上界。候選零生成做法是同版 Ollama 的 prompt-render 觀察（若此版本可可靠啟用、且可證不生成）與相同 GGUF vocab-only tokenizer；先確認 B 路由究竟使用 Go 或 GGUF 模板，再以已具 provider usage 的**同 shape**樣本做上界差分，覆蓋 system 注入、同角色合併、Unicode、assistant continuation、schema 及模板分支。實際 B transformed request 只能在不污染新 root 的送前邊界核對；若無法取得並綁定其真正 prompt bytes／保守 token 上界，不發真請求。此處是待驗方案，**目前未取得任何 B byte parity**。任何無法核實的路由、請求變形、版本、template、模型 digest 或額外 token 使 admission 常閉。response 實際 usage 仍須事後核對，不以估算取代帳本。此階段不對 B 題做真 generation，不消耗 Safari Send。
3. **20s 全輪等待**：這不是第 1 點的附屬 flag。B 的操作性 T0 應是**原生 Safari 按 Send 的點擊時刻**，T1 是完整成功句＋圖，或明確終止畫面在 DOM／AX 真正呈現；browser click→T1 需有同一瀏覽器時鐘的可保存證據。成功句＋圖 ≤20s 且其他 gate 通過才可能算 B 成功；即使終止畫面 ≤20s，該 B 輪仍是 **FAIL／0 retry**。現行 server admission 計時始於 capability claim 之後，不能替代點擊 T0。設計必須拆為 Safari client 自己從 T0 起算的 timeout watchdog／terminal T1 回執，以及 server admission／worker 按剩餘時間停止並預留 UI 傳輸裕度；worker 不可能自行涵蓋 Gradio 排隊或 browser DOM 呈現。TTS 關閉。**成功提交前不可向使用者串流角色句**，否則逾時前已顯示的 partial 無法按 B 的 bubble／JSONL／episode 一致性契約撤回；逾時後晚到結果亦不得覆寫終止畫面。原診斷協定明說 final audit 是 audit-only，失敗隔離輪可以寫私有 episode，**不保證 no-send／狀態零殘留**；本卡不偷加跨 store transaction。deadline FAIL 時要保存已發生的私有 writeback 並禁止復用失敗 root；B 預定外部工具執行數是 0，若有工具派發或其風險無法在送前關閉，直接 B no Send，不以事後回滾假裝撤銷副作用。隔離 child exact stop 與私有失敗證據只能是止損，**不是**達成 20s 終端畫面的替代方案。一般 OS／網路下無法從單次本機模型 timeout 數學保證使用者端 ≤20s。**送前**須用非 B 題、0-provider fake worker 的新隔離 root，在原生 Safari 注入 queue／lock／provider stall／late stream，核 timeout UI 於 ≤20s 呈現、晚到角色結果不能覆寫及 click→T1 計時器可工作；這是機制演練，不消耗或代替 B 唯一真 Send。**送後**才核 B 自己的原生 click→T1 與 ≤20s；缺證、逾時、只見 spinner／network error 均為 B strict FAIL／0 retry，不因 child exact stop 或 server `target_met=true` 放行。送前注入缺口、無法運作的 click→T1 計時、晚到 partial，則 **B no Send**；不能把原協定的「硬」默默降成事後觀測門檻。

## 前瞻修改範圍／證據階梯

時戳註：browser 同域 T0/T1 以 click 與終端 DOM 事件／paint 為權威；AX／截圖是內容與可見性的交叉證據，不拿不同時鐘的 AX 工具時戳與 click 直接相減。若同域時戳不能保存，B 仍不可送／不可判時限 PASS。

第 1、2 點若經本卡獨立審查同意，只准新 opt-in quota 模組、`uruha_compute_ledger.py` 的送前 interceptor、`uruha_brain_mac.py` 的 native／local 入口、P4 child controller 的明確 flag／run 綁定及新聚焦測試；P2 request transformer 原語義、A runner、正式 DB、人格、題本／gold、輸出 guard 不改。第 3 點若要實作，需**另行前瞻 Web 事件／逾時畫面設計審查**，列出原協定未允許的 `uruha_web_ui.py` 範圍與 tool-disabled 證據，不能先編碼再補文件。這些全是 B safety infrastructure，不是 treatment；零模型 off/on 測試均用同一 admission，**真 B Safari 總共只准 1 Send**，不另做 B off/on 雙送。

紅燈測試須先證目前第 2／4 次意外呼叫、token 超界或缺 usage、模型／模板漂移、native/local 繞道及假 provider 超時仍可能越過送前 gate；修後以 0 provider fake 驗證 admission 預拒、quota 原子性、預設不變、off/on 相同、不能憑部分 receipt 放行。另以假 worker 延遲測晚到可見句不得覆寫終止畫面；若私有 writeback 已發生，須記為失敗狀態並不復用 root，不能把 fake-Web 當 Safari。小測→相鄰回歸→隔離真 Web/Safari 順序；任何 stage 失敗保留 FAIL，最多兩個有據修正批次，不重用 A/B 題追分。源碼／pytest 只能證契約，不能證實 provider 服從 `max_tokens`、真使用者等待、人評或強 LLM 優勢。

## 當前結論與唯一放行鏈

目前尚無 0.34.4 的 B 實際 prompt-byte／token parity、跨入口 atomic quota 或 end-to-end deadline；**三項硬界均未成立**。本卡是堵住錯誤「B 可送」主張的必要 gate 定義，不是改閾值、不是 B 產品 PASS，也不是正式 holdout。先審此卡；可獨立實作並核驗第 1、2 點而不耗 A／B，但其後仍需 A 作者核與真 A on-only PASS，以及第 3 點用**非 B 題**做原生 Safari 零 provider deadline 演練與 late-visible 抑制證據，才可考慮唯一 B Send。B 本身 click→T1 與可見品質只能在那唯一真 Send 後驗收，失敗不重試。否則維持 `REVIEW_REQUIRED`。
