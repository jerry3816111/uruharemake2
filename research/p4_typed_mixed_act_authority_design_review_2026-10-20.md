# P4 雙行動交付與來源授權：G 批之後的只讀設計審查

狀態：**因果定位與下一變因建議，不是前瞻凍結計畫或新產品 PASS。** 只讀依據是 `analysis/p4_verified_producer_graph_fresh_product_probe_result_2026-10-20.md` 的新 G1–G3 原件、既有 mixed-source／explicit-rewrite 代碼與原先權限契約。G/L/W/A 題都已曝光，不能重送追分。未讀取正式 holdout 未來答案、未更動正式 DB。

## 為何不是再補圖或聲稱缺記憶

G2 原件有 `mixed_request`、`quoted_rewrite`＋`past_user_place_recall` 兩 typed actions 及 linked event→M31→M32 parentage；新 Safari 圖像 3 節點／2 箭頭已實際可見。但 action coverage 仍 `unverified`，沒有權限移交。M31 `surface_authority=false`，M32 `surface_authority=true`，最終只重述任務，並沒有完成任一子任務；`mixed_past_place_source_authority_p4` 與只接單一改寫的 `explicit_rewrite_action_p4` 未接管 G2。G2 `memory_snapshot.recent_turns` 和 `memory_provenance.passed_to_leftbrain` 有前輪 User 直接說「我決定集合地點」的原話，也有混入歸屬錯誤的 assistant 回覆；因此不能把失敗診斷為「完全沒有記憶」，也不能用 assistant 自稱當 User 事實來源。

G1/G2/G3 的 `visible_language_guard` 都將 `私`→`うち`，對 User 歸屬句造成主語反轉；這是獨立的可見 actor-preservation 缺陷。不能在雙行動補丁內順手改 guard，否則不能歸因。即使雙行動機制在新 case 成功，若新產品再有 actor reversal，整批 strict FAIL。

## 下一個單一核心變因候選

`typed mixed-act atomic delivery/authority transaction`：不是因 raw receipt linked 就把 M32 降權。新 opt-in 交易只有在 current User 的 raw digest／cycle／兩 action spans／event→M31→M32 直接父證據重新核對、非 protected、無 M33 或其他更高優先級事實契約時才候選。從既有 mixed past-place source certificate 只收同日期直接 User 原話；未知、矛盾、撤回、第三人／assistant-only 不得補地點。從既有 quote rewrite candidate 取得日文候選，獨立驗證保留原句語義、友達向け常體、不增加約定。兩子任務各有可追溯 receipt，完整可見候選一次組合；最後 guard、graph、episode/hash 與 visible reply 同一交易確認後才可記 `covered`／表面權限移交。任一證書或交付驗證失敗要保留原路徑或有界未知，不能部分完成卻標兩項完成。原 M31/M32 的 selected/authority 與失敗仍留 shadow。

目前 `cognitive_tick` 先 apply M31/M32，`emit` 又作末端 `ensure_*_reaches_surface`；僅覆寫 `core_message_jp` 會被後段覆蓋。既有 source 與 rewrite gate 的 competing-authority 條件會擋 M32=true；新交易若實作，需顯式、來源綁定的優先序收據與末端完整交付稽核，不能靜默把舊 M32 `surface_authority` 改為 false。此審查不預設最終權限方案一定安全；若無法明確證明轉移先後及回滾，就維持 `REVIEW_REQUIRED`，改走其他獨立必要交付。

## 在程式前應凍結的驗收

以未曝光、source-disjoint 的新 developer probes 再立計畫／題本／SHA：正例直接 User 日期地點→下一輪雙任務；負例無來源、日期不同、矛盾、撤回、第三人、assistant-only、protected、單一改寫，以及錯／缺／重複 parent、digest、cycle、M33 authoritative。凍結條件 gold、允許檔案、單一變因、精確聚焦／相鄰回歸、安全與來源、自然日文及 actor-preservation、泡泡＝raw＝guard＝graph＝episode、隔離 profile、不超過 20 秒、額外／全管線可得 calls/tokens/latency 和真 Safari 每題一次／0 retry。可考慮新 opt-in module、聚焦 test、薄 Web/controller；圖若需 action receipt 只作純 renderer 投影。不可改核心黑板／正式資料／舊 gold 來使案例通過。

資源風險是真實的：G2 已等 14.7718 秒，其中 M31 11.6876 秒；額外 rewrite 模型呼叫可能超過 20 秒。先做 0-call 邊界與成本設計；若必要模型成本不可接受，應保留 FAIL 並審查可歸因的替代，而非放寬 latency 或削弱 baseline。即使成功也只是 bounded 產品能力，非正式強 LLM 優勢、真人主觀理解、完整人類方程式或一般語用正確性。
