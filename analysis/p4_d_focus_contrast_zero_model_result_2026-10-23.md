# P4-D-F-C：焦點圖對比修正零模型結果

日期：2026-10-23。事前設計／新 c0/c1／preimplementation SHA 已在 `84540b7` 推到 PR #435，之後才修改產品。唯一產品 diff 是 `uruha_memory_observatory.py` CSS 增加兩條規則（原始檔 +141 bytes）：標題子 `<span>` 直接 `#fef3c7`，箭頭 `<path>` 直接 stroke `#facc15`。`uruha_web_ui.py`、HTML、graph、D gate、回覆、記憶及 DB 均未改。讀取既有 HTML 結構的獨立只讀 reviewer 未見範圍阻擋；但沒有 Safari computed style，父層繼承被何樣式覆蓋僅是待驗原因。

- 新局部 CSS 契約＋既有焦點圖契約：**11/11 passed**；受影響 D gate、producer/atomic graph、browser hydration、Web final graph、teacher graph、tool truth 等共 **208/208 passed**，9 個依賴 warning。`py_compile`、Web `build_demo()`＝Blocks、`git diff --check` 通過。新測試只證靜態指定色與設計背景的名義對比，不宣稱已量測 Safari 實際對比。
- 用凍結 c0/c1 的零模型 D receipt，把 Git HEAD 修改前 renderer 於記憶體載入與本版比較，生成的 graph HTML 逐字相同；UTF-8 bytes c0 **27,867→27,867**，c1 **28,166→28,166**。各預熱 5 次、同進程 51 次中位 render：c0 **1.351→1.312 ms**、c1 **1.351→1.341 ms**；微秒級波動只說未觀察到增加，不當成速度改善。此項模型呼叫 **0**。

產品 SHA 見 `research/p4_d_focus_contrast_product_2026-10-23.sha256`。本階段**只有零模型／程式邊界 PASS**；c0/c1 fresh 原生 Safari、100% 實際尺寸、視覺可讀、隔離 DB 與 saved native PNG/AX 仍 pending。f0/f1/f2 的 strict FAIL 不改判，不能預先宣稱 teacher-ready 或全部產品 PASS。
