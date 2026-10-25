# P4 B 身份適配前的安全關鍵來源盤點（唯讀）

狀態：**已證明目前 B source lock 有缺口；尚未改產品或放行真模型/B Send。** 這是 `research/p4_b_child_local_identity_adapter_design_2026-10-26.md` 的 implementation-freeze 輸入，不是完整依賴圖或安全認證。現行 `p4_preference_fallback_detached_control.py` 的 `B_COMMITTED_SOURCES` 僅六檔：controller、product entry、child bootstrap、binding、Web、ledger（第 53–60、227–249 行）；`private_child_source_digests()`／child receipt 僅對後五檔留 SHA（`uruha_p4_b_private_endpoint_binding.py` 第 145–155 行）。因此 source 清單「6／5」不等於執行中所有安全判斷已綁。

| 路徑層 | 已確認實際使用、但現未在上述 source lock 的檔案 | 直接證據與風險 |
|---|---|---|
| operator→descriptor | `p4_b_private_zero_turn_operator.py` | `_write_descriptor` 建 B descriptor（第 407–420 行）；尚未有 operator 自身 source SHA 綁定；其初次 raw generation 也尚未記於 v1 descriptor。 |
| controller root/Python | `p4_b_safe_isolated_product_launcher.py` | controller 第 168–173、327、766–801 行使用其 root／Python 解析；未在 `B_COMMITTED_SOURCES`。 |
| controller sandbox | `p4_b_safe_isolated_product_launcher_v2.py` | controller 第 346、840 行呼叫 profile／sandbox command；未綁定會影響實際隔離邊界。 |
| controller process generation | `p4_exec_detached_lifecycle_probe.py` | controller 第 486、672–700 行用其 PID／代次觀察；未綁定。 |
| controller isolated env | `p4_preference_fallback_launchd_control.py` | controller 第 116、328、801、829 行用 `_isolated_env`；未綁定。 |
| child live identity／model SHA | `p4_b_isolated_ollama_identity_probe.py` | binding 第 22–32、267–280 行直接匯入 `_model_store`、`_process_identity`；目前後者又間接呼叫被 sandbox 拒絕的 `/bin/ps`，且 helper 未綁定。 |
| child M21 resource gate | `uruha_p4_b_resource_gate.py` | bootstrap 第 24、258–259 行，binding 第 35 行，ledger 第 655–656 行使用；未綁定會影響是否能送 provider。 |
| 後續 B Send，不屬 zero-turn 放行 | `uruha_compact_planner_p2.py`、`uruha_brain_mac.py`、product entry 載入的 overlays | gate 動態使用 compact JSON schema；Brain native/RightBrain 的拒絕路徑在第 8478–8480、15268–15270 行。entry 還匯入多層 overlay。這層未完成逐函式 inventory，不能宣稱所有生成入口 source closure。 |

由前七列可知，至少 **7 個現有零輪身份／資源路徑檔案**沒有目前兩份來源清單的綁定；此數是已發現下界，不是完整 transitive closure。新 B-only observer 會是第 8 個候選檔，除非把實作放進已綁定 binding，但仍無法消除既有 helper 缺口。Controller-only helper 是否也要寫入 child receipt，應在實作契約中明訂；至少必須在 controller committed snapshot，並把 operator 來源 digest 與 descriptor/receipt provenance 連起來。單純對後五檔再算一次 SHA，不能修掉上表。

實作前要做的單一必要 gate：由 operator 啟動至 controller ready、child bootstrap、binding live identity、ledger pre/post-create，列出每個**實際決定身份／資源准入的 repo 函式**及其來源檔，建立可檢查的 allowlist；對該 allowlist 的 controller snapshot 與 child-visible receipt 各標 `bound／not_applicable_with_reason／missing`，`missing=0` 才能稱 zero-turn 安全關鍵 source closure。B Send 還須另查 compact planner、Brain 所有生成入口和 overlay，不能由 zero-turn inventory 外推。這一層只可用 source/fake tests，仍不啟第四次模型。

成本與證據界線不變：同一 `_inspect_live_identity` 兩次 `_model_store`、每 create 兩次重新驗證，至少約 18.73 GB 邏輯模型 SHA 讀；既有 cached 四次 9.301121 秒不是 Safari 20 秒。合成替身九欄 PASS 亦不證真 Ollama argv/env。原三次真 zero-turn FAIL/`REVIEW_REQUIRED` 保留，沒有 A/B 題或正式資料寫入。
