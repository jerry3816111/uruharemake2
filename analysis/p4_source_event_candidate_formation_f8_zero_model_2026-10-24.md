# P4 f8：來源事件進入候選形成，零模型實作檢查

日期：2026-10-24。前瞻題本、visible gold、單一變因和資源上限已先在 `542d4b9` 推 PR #435；本頁沒有 f8 fresh model 或 Safari 品質結論。既有 f7d 真 Safari strict FAIL 保留：User 說自己把香草苗種下，最終卻回成播種；f7 的三候選均無 `grounded`，所以排序無法補救候選形成的來源錯誤。

本批只在 opt-in control／f7 utility／M21 compact full route 加入來源綁定的候選形成約束。當輪 M29/M33 handoff 與有限事件語法雙重驗證過後，約束才在 compact request 尾端送給**同一模型**，要求三個真生成候選保留 User 行為者、已完成動作、物件與原文明說的首次。關閉 flag 時 compact request 不變；不改 f7 排序、最終 guard、memory write、人格資料或正式 DB。事件關係超過 20 Unicode 字元、第三人、引文、否定、多句、非日文等不注入。子進程 opt-in flag 只在 control product start、生效 compact schema 與 f7 utility 齊備時可用；prepare／inert／錯 arm 均拒絕。來源 receipt 只有固定欄位、有限狀態與 SHA；transport 再投影白名單後才寫 audit／graph，原文只暫時存在 provider request。

## 可重核的機制證據

- 凍結 plan 與 dataset SHA 仍分別為 `602102aa...b12132d01a`、`fc8818fd...944aa`；preimplementation manifest 中的舊 product SHA 刻意保留，不覆寫成實作 SHA。
- 焦點與相鄰契約：`test_p4_source_event_candidate_formation_f8.py test_compact_planner_p2.py test_p4_source_event_core_utility_f7.py test_p4_source_event_core_utility_f7_route.py test_p4_source_event_core_utility_f7_route_negative.py`，**114/114 passed，42.73s**。涵蓋凍結 5 eligible／7 ineligible、20／21 字界、非首次不捏造首次、偽造／過期 handoff、關閉 flag 的 byte-equal request、打開後只追加 suffix、不同 User turn 不注入、一個 fake provider call／三真 schema candidates、f7 及 episode/graph 同輪路由、receipt 原文隔離。此處三候選是**測試 stub**，不構成真模型品質證據；stub 的 event core 亦未保留首次，不能據此判 visible gold 通過。
- 受影響控制器／M29 handoff／f4–f5 compact route／d1 taxonomy 回歸：**57/57 passed，35.87s**。五個 product/測試檔 `py_compile` 與 `git diff --check` 均通過。未重跑無關長套件。
- 實作 SHA-256：純來源約束 `37f3f91463daf0a9329f39893412a48269becb753bd210621be200933488cf3e`；compact transport `52c8ff789fabd4c0cbbaa823aa45db725d7d08a5791c2c1660c5698ed94b455c`；Brain 接線 `55c74b51405261dafc6ce3a55d44952d9a65abcd0dd08723ee9a995b4ab12721`；controller `113ee90fde6b8af8d86d2009b0d4b5f721b86b9c518000908805e33be6031b60`；聚焦測試 `689592da05435e3daf7ec0b87bf23634b4b23e6b55b8f53720f98d85d0280994`。

這只證明可控接線、棄權與圖上 raw-free receipt；尚未證明真模型會生成承接事件的候選。下一必要關卡是**兩個獨立 LeftBrain、同序列化初始狀態、同模型及資源上限**的各一次真 M21 配對。依 frozen gold 同時核原始三候選、選定原始 core、f7 coverage、final core、日文語義與 tokens/latency；唯 on-only-pass 可放行另一凍結題一次原生 Safari。其餘結果保存為 parity、失敗或退步，不改題／不在曝光題追分。Safari、完整產品、強 LLM 公平比較、人評與正式 holdout 均 pending；不能宣稱解出人類反應方程式。
