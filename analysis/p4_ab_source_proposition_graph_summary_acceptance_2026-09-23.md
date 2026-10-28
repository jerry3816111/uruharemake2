# P4-AB readable source-proposition graph summary 驗收

## 結論

P4-AB 通過事前凍結的 presentation-only gate。P4-Z 節點不再只顯示 `18 fields`，而會在一行內呈現
「來源框架｜說話者歸屬｜已知命題欄位｜採取動作｜違規數 before→after」。這讓使用者不用先展開 JSON，也能看懂
這個節點剛剛保留了什麼、是否修正、修正後是否仍有問題。

實作採 additive `uruha_web_ui_product_p4_ab.py` entry，在 runtime 只包裝 graph signal；核心
`uruha_memory_observatory.py` 維持既有 SHA-256
`c95e756a6e8b03cbe79cef079f62bf2cecf93dd98cc3290a2ae178139e9c4b76`，避免破壞舊 release binding。
P4-AC preflight前發現第一版entry錯把P4-Z的main-only `demo`當作可import符號；當時尚未啟動server或執行案例。entry已改為
沿用其他additive entry的`_base.build_demo()`與`RUNTIME = _p4_z.RUNTIME`，sandbox probe確認P4-Z與P4-AB均已安裝。

## 實際圖上摘要

1. `引用｜引文命題｜主體/動作/時間｜修正 4→0`
2. `傳聞｜第三者｜主體/動作/對象/地點｜已符合 0→0`
3. `假設｜使用者｜主體/動作/對象/時間｜修正未通過 3→1`
4. `未支援來源｜歸屬未知｜欄位無｜保留原文 1→1`

第三個案例刻意保留 failed-closed 狀態，證明圖表不只會顯示成功，也能直接暴露仍有一項命題違規。第四個案例顯示
不支援來源時系統沒有假裝理解，而是保留原回覆。

## 凍結 gate

- exact summary=`4/4`；每個 summary 長度均不超過 42 字元。
- graph node signal 與 summary exact=`4/4`。
- payload mutation、raw sensitive token、trace detail change=`0`。
- unrelated schema 保持既有 generic signal=`1/1`。
- visible reply、P4-Z logic、model call、memory write change=`0`。
- P4-M→P4-AB 與 M24 graph 回歸=`266 passed`，3個既有 dependency deprecation warnings。

第一次 implementation 測試曾因 harness 把 before-only assertion 寫成動態呼叫已修改 renderer，且用會被 UI 截短的 label
尋找節點而失敗。修正只把 before 證據綁到 freeze 時的 renderer hash與已記錄的 `18 fields`，並用未截短的 `trace_id`
定位 graph node；凍結 summary、門檻與資料均未改。

第一次把分支直接加進核心 renderer 後，全 P4 掃描得到 `573 passed / 1 failed`；失敗測試指出舊 immutable bundle hash
不能接受核心檔變動。因此該修改已移除，改用 additive entry，核心 hash恢復。重跑現行 P4-M→AB 鏈為 `266 passed`。
全 P4 掃描另保留一個與本次 diff 無關的既存 P4-D failure：branch HEAD 的 `uruha_web_ui_product.py` hash本來就是
`842169...`，而舊 freeze仍期待`fae156...`；本次沒有修改或掩蓋它，因此不宣稱整個 repository 全綠。

## 邊界

這是可視化／可解釋性改善，不是新的理解能力。它只摘要 P4-Z 已經算出的 typed trace，沒有證明 proposition extractor 的
open-domain 準確率、自然分布表現、felt understanding、人類偏好、強 LLM 優勢或人類方程式。真實網站是否正確顯示，仍需
以不重用 P4-AA 題目的新 Safari 驗收另行確認。
