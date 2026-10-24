# P4 M46 審核判斷介面：一次性配對實測負結果

狀態：`REVIEW_REQUIRED / component FAIL`。這是事前凍結的本機、開發者撰寫封包元件測試；**兩臂均未通過絕對門檻，新介面 B 不接產品，也不授權重跑或微調本次題目追分。**

## 可追溯範圍

- 設計審查：`analysis/p4_m46_reviewer_decision_interface_design_review_2026-09-30.md`。首次 freeze `fa298078a47900c1963c252cf62875dc036cb711`；0 模型呼叫時依獨立稽核修正引文契約與有效方案口語表面後，正式 freeze `7abf74579e7793c22d3111b149037d9d7bdc5393`。runner commit `0b1dcfcaa63f9ea5af51f5c95cfca94482925848`。
- 不可覆寫的原始結果：`analysis/p4_m46_decision_interface_result_2026-09-30.json`，SHA-256 `66321bb7b01eae6dafe0a81dbb79f74f355ee6c64debab1eae4e5eec83692a46`。結果綁定 frozen contract/dataset/runner SHA-256，記錄每個呼叫、兩臂輸出、共同選擇與 guard、token、wall time。
- 同一 `qwen3.5:9b` 模型 digest、Apple M2 Pro 32 GB、同一 source、同一預選 plan、相同生成參數、320 completion-token 上限。A 是原 M46 review contract，B 只換一次審核的 prompt＋schema／判斷契約；A/B 各對 10 題呼叫一次，交錯順序；另 1 題共同 deterministic guard 不送模型。0 重試、0 M51 自然生成、0 正式資料庫與產品 runtime 變更。
- 資料是中／英／日 3 valid＋7 invalid 的**新字串、已曝光類型、開發者事前標註 proxy**；不是獨立真人標註、自然使用分布或正式 temporal holdout。來源和選定方案兩臂逐題相同；10/10 兩臂完成、JSON 可解析、token 與 source identity 完整；共同 guard 1/1 阻擋。

## 預定門檻與實得結果

| 指標 | 絕對門檻／解讀 | A 原介面 | B 新介面 |
|---|---:|---:|---:|
| 保留有效方案 | 3/3 | 2/3 | **0/3** |
| 錯放無效方案 | 0/7 | **2/7** | 0/7 |
| 指出預定錯誤類別 | 7/7 | 5/7（舊布林多對一映射） | **0/7**（明確軸 `fail`＋primary） |
| reviewer-only 中位／最大秒數 | 最大 ≤20 秒 | 13.60179／14.72437 | 8.64255／10.78069 |
| reviewer prompt／completion tokens | 實際值，非品質替代 | 8,606／2,891 | 6,876／1,652 |

B 比 A 更快且沒有放出本批負例，卻是**全部拒絕**，不是更會判斷。10/10 的 JSON 可解析不等於 B 結構合格；B 只有 3/10 通過本地 schema／引文檢查。兩臂的「理由命中」定義並不同構，不能把 5/7 對 0/7 當作對等人類理由品質比較；B 的 0/7 只表示未命中它自己事前要求的明確錯誤軸與結構門檻，不能說它連一個相關軸訊號也沒有：原始輸出對 3/7 負例把預定軸標為 `fail`，但只有 1/7 同時以該軸為 primary，且該題引文格式仍不合格。配對決策上 B 獨有正確阻擋 2 題、A 獨有正確保留 2 題，沒有淨品質改善可宣稱。

## 最小反例與失敗機制

1. **有效的使用者操作被誤認為助手代操作。** 英文有效題 `p4_m46_di_valid_en_001` 要使用者從手邊傳票抄一個日期，選定日文是「まず配送伝票一枚の日付だけ索引に写してみて。写せたらそこで終わり。」B 把 `actor_capability=fail`，稱這是「助手代行物理操作」，並給出不在 source／instruction 中的英文引文；A 在此題保留有效方案。日文有效題 `p4_m46_di_valid_ja_001` 的「足してみて」同樣被 B 判成助手宣稱自己執行，即使引文格式通過仍拒絕。這不是只修引文格式就能救回的有效方案。
2. **錯誤的任務沒有被辨出真正錯誤。** `p4_m46_di_wrong_task_zh_001` 的使用者要求整理讀書會問題、明說不要改摘要；選定方案卻叫人改摘要小標題。A 錯放，B 擋下；但 B 將 `task_alignment=pass`，以 `actor_capability` 作 primary，沒有辨出錯任務，因此不能說 B 理解了為何要擋。
3. **真正的行動者錯誤也沒有穩定提供合格理由。** `p4_m46_di_actor_surface_ja_001` 明說「你不要操作，只說手順」，選定句卻寫「うちが閉じておく」。B 的 `actor_capability=fail`、primary 同軸，但 `evidence_jp` 只有來源引文、沒有必要的日文說明，故事前結構 gate 不通過。與此同時，所有 10 個可交審封包都被 B 標成 `actor_capability=fail`，9/10 以此為 primary；這個軸失去區辨力。B 的 evidence anchor 也只有 3/10 通過。不能把這些解析／引文失敗全部歸咎於模型語義，也不能把全部語義錯誤歸咎於 parser。

## 結論與下一個必要交付

這次證明的是：在固定 9B、固定方案與固定成本下，**這個單次新審核介面未解決「有效要放、無效要擋、原因要對」的三重需求**。原介面 A 也未過關。B reviewer-only 最大 10.78 秒不等於完整產品 ≤20 秒；另一次 M51 第一呼叫已花 17.64 秒並在 360 token 截斷，兩者屬不同實驗，僅提示兩階段時間／表示資源的架構風險，不能相加宣稱已測得完整延遲。

依事前分支，停止 reviewer 第三次 prompt／gold／timeout 小修，不改 M51/M46/M45/M39 產品路徑、不旁通 guard、不因 B 速度快而接產品。下一個必要交付是**兩階段候選→審查→交付的架構設計審查**：在已曝光反例上比較「單次結構化候選＋同次可驗證理由」、「將來源／行動者／使用者可執行性分成可測的表示與 deterministic guard」、「維持 fail-closed 並縮小交付範圍」等互斥選擇的品質、延遲、token 與安全代價；只選一個可歸因變因並另凍結全新資料和 gate，才能再做 scored 實驗。真實自然 M51、多輪記憶、M45/Web/Safari、真人理由評分、正式 holdout、強 LLM 對照與人類方程式主張均未由本試驗授權。
