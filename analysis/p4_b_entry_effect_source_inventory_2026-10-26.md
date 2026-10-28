# P4 B 固定入口的靜態 source／effect 盤點

判定：**真 B Send 硬 NO-GO；目前 16 檔鎖不是完整產品來源閉包，且存在一條靜態可達的共享 11434 工具路徑。** 只讀沿固定入口看 import、安裝、Web→Brain→provider 呼叫；沒有 import 執行產品入口、沒有送訊息、沒有模型／Safari、沒有改正式資料。這份是具名缺口盤點，**不是**已完成全 transitive closure，也不能用未列出代表不存在。

## 固定入口與已核證的來源界線

`p4_preference_fallback_detached_control.py:53–70` 的 `B_COMMITTED_SOURCES` 列 16 個檔，controller 比對 HEAD；`uruha_p4_b_private_endpoint_binding.py:160–181` 的 receipt v4 綁相同窄路徑，child 在 Web 前及 create 前再核。這涵蓋 operator、準備、identity、resource gate、最外入口、基礎 Web、ledger、compact planner schema，**不**表示每個 import 的 source 都已鎖。

固定 `uruha_web_ui_product_p4_preference_fallback.py:9–17` 先做 B bootstrap，然後 `_prior` 遞迴進到 `uruha_web_ui_product.py`：全程 **33 個 entry modules**，只綁最外 1 個；中間 **32 個 entry 檔缺 source binding**。順序是 `preference_fallback → question_evidence → postposed_denial → profile_plan → profile_ack → profile_owner → past_source → status_truth → az → ay → ax → aw → av → au → at → as → ar → aq → ap → an → am → ah → ag → af → ad → ab → z → y → w → v → t → o → uruha_web_ui_product`；除最後的 `uruha_web_ui_product` 外，短名皆接 `uruha_web_ui_product_p4_` 前綴。AST 靜態可見 **52 個頂層 `install_*` 呼叫位置**；這是語法計數，不是 52 次已測實際副作用。各層可能 monkeypatch Brain/Web；底層 `uruha_web_ui_product.py:29–48` 設 slow-path 預算並安裝 P1–P4、Function Calling 和 VRM。`uruha_web_ui.py:740` 匯入時建日誌目錄，`:1643` 建 RuntimeManager，`RuntimeManager.__init__:829` 起 idle thread。真正 `build_demo → queue → prewarm → launch` 是最外入口 `__main__:30–35`；不能將不執行 `__main__` 誤稱無 import-time effects。

基礎 Web `uruha_web_ui.py:84` 匯入未綁的 `uruha_brain_mac.py`。正常文字 turn 經 Web `_run_turn:4169ff` → `brain.run_turn_debug:21958` → `ingest_event:18450`／`cognitive_tick:19202`／`emit_response_if_ready:20647`；Brain 初始化可做 private `models.list()`、Chroma 構造，之後 LeftBrain／RightBrain／native 分支可產生 provider、memory writeback。P2 compact request 經已綁 `uruha_compact_planner_p2.py` 後到已綁 `uruha_compute_ledger._CompletionProxy.create:632–681`，其 B create 前兩次 revalidate 和 resource gate 有 fake 證據；但 Brain、其直接 imports、overlay install source、Function Calling 及 VRM assets 等未綁。原 child→Web→SDK 的零輪 fake test 有意 mock live identity 與 Brain、completion POST=0；不能覆蓋真生成的全部 effect。dynamic patch order／條件 import／tool／writeback 的完整 closure **仍 unknown**。

## 可重現的靜態共享端點反例

這個缺口不是只有 SHA 數量。`p4_preference_fallback_detached_control.py:449–466` 的 B child env 由 `_isolated_env` 加七個 B/ledger/compact/OLLAMA 鍵；`p4_preference_fallback_launchd_control.py:72–87` 和 `p4_b_safe_isolated_product_launcher.py:155–177` 沒設 admission journal 或 exact-input arm。Web `_admission_enabled:954` 因 journal 空為 false，普通 browser text 可把空 `admission_token`／`exact_input_claim=None` 交給包裝後 `_run_turn`。底層產品 `uruha_web_ui_product.py:26,48` 安裝 `uruha_product_function_calling_p4:252–284`；明確目前 runtime status 句通過 `uruha_read_only_function_calling_p4:144–176` 的 selector 後，`uruha_product_function_calling_p4:202–249` 只有在 token／claim 非空才拒絕，否則不走原 Web cognition，而呼叫 `core.run_function_call_turn`。預設 `LocalOllamaToolsProvider:634–669` 只接受並向 **`http://127.0.0.1:11434/api/chat`** 做 urllib POST；此路徑不經私有 binding、P4B gate 或 ledger。sandbox profile `p4_b_safe_isolated_product_launcher_v2.py:24–40` 是 `(allow default)` 加 file-write deny，靜態上沒有網路 deny。

這是**靜態可達路徑與安全反例**，非本輪真的呼叫 11434；實際 POST 還取決於使用者輸入、contract、provider 建立與共享 listener。即使它最後因其他因素失敗，也不能在送前以「可能會失敗」代替硬性隔離。現有 `test_uruha_product_function_calling_p4.py` 用 fake provider 證 explicit status 會繞過 `original_run_turn` 並有一次 provider invocation，但沒有 B opt-in 負控。B Send、第四次 Ollama 與 Safari 維持 NO-GO；v2 synthetic sandbox PASS 與這條產品 effect 路徑是不同證據層。

## 下一個可歸因修正及剩餘閉包

先凍結一個 **B-only Function Calling fail-closed** 修正：在任何 provider factory／`core.run_function_call_turn` 之前辨識 B intent，對 B explicit-status route 終止、不接 shared 11434；非 B 正常工具功能與 B 非工具普通聊天保持原路徑。假測需證 B explicit 0 provider construction/invocation/HTTP、B ordinary 回原路徑、非 B explicit 原工具仍工作、偽造／不完整 B env 也常閉；不准把 B 預設工具改用 private URL 而繞過 M21 允許清單。新產品碼必須先有單一變因、允許檔與獨立改碼前審查。修正後仍需對其 source 鎖、32 個 entry 缺漏、Brain/overlay/dynamic effect、token oracle、20s、人評逐層處理；單一 bypass 修好不放行 B Send。
